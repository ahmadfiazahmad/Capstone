import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.core.config import get_settings
from app.models.billing import Plan, ProcessedStripeEvent, Subscription, SubscriptionStatus, Tenant, UsageEvent
from app.schemas.billing import GenerateRequest
from app.services.metering import record_generation
from app.services.stripe_service import verify_event
from app.services.usage import usage_summary
from app.api.routes.webhooks import sync_subscription


def tenant_a(db):
    return db.scalar(select(Tenant).where(Tenant.api_key == "key-a"))


def meter(db, key, **tokens):
    return record_generation(db, tenant_a(db), key, GenerateRequest(**tokens), get_settings())


def test_normal_request_and_idempotent_retry(db):
    first, replay = meter(db, "abc123", input_tokens=100, cached_input_tokens=20, output_tokens=10, reasoning_tokens=5)
    second, replay2 = meter(db, "abc123", input_tokens=100, cached_input_tokens=20, output_tokens=10, reasoning_tokens=5)
    assert not replay and replay2 and first == second
    assert first["cost_microcents"] == 340
    assert db.scalar(select(func.count()).select_from(UsageEvent)) == 2


def test_quota_boundary_and_exceeded(db):
    db.scalar(select(Plan).where(Plan.code == "FREE")).api_calls_limit = 2; db.commit()
    meter(db, "one"); meter(db, "two")
    with pytest.raises(HTTPException, match="quota exceeded") as caught:
        meter(db, "three")
    assert caught.value.status_code == 429


def test_invalid_input_and_tenant_isolation(db):
    with pytest.raises(ValueError, match="cannot exceed"):
        GenerateRequest(input_tokens=1, cached_input_tokens=2)
    meter(db, "a1", output_tokens=50)
    b = db.scalar(select(Tenant).where(Tenant.api_key == "key-b"))
    assert usage_summary(db, b)["ai_tokens"]["used"] == 0


def test_inactive_subscription_returns_402(db):
    db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_a(db).id)).status = SubscriptionStatus.PAST_DUE; db.commit()
    with pytest.raises(HTTPException) as caught:
        meter(db, "past-due")
    assert caught.value.status_code == 402


def test_pricing_cached_and_reasoning_rollup(db):
    # Fresh input: 80*2; cached: 20*1; output + reasoning: 15*4; API: 100 = 340 microcents.
    response, _ = meter(db, "price", input_tokens=100, cached_input_tokens=20, output_tokens=10, reasoning_tokens=5)
    assert response["cost_microcents"] == 340
    assert usage_summary(db, tenant_a(db))["ai_tokens"]["used"] == 115
    assert usage_summary(db, tenant_a(db))["cost_microcents"] == 340


def test_forged_webhook_is_rejected(db):
    with pytest.raises(HTTPException) as caught:
        verify_event(b"{}", "forged", get_settings())
    assert caught.value.status_code == 400
    assert db.scalar(select(func.count()).select_from(ProcessedStripeEvent)) == 0


def test_duplicate_verified_webhook_processed_once(db):
    event = {"id": "evt_repeat", "type": "checkout.session.completed", "data": {"object": {"client_reference_id": "1", "customer": "cus_test", "subscription": "sub_test", "metadata": {"tenant_id": "1"}}}}
    db.add(ProcessedStripeEvent(stripe_event_id=event["id"], event_type=event["type"])); sync_subscription(db, event); db.commit()
    db.add(ProcessedStripeEvent(stripe_event_id=event["id"], event_type=event["type"]))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(ProcessedStripeEvent)) == 1
    assert usage_summary(db, tenant_a(db))["plan"] == "PRO"
