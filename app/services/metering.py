import logging
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from app.core.config import Settings
from app.models.billing import Subscription, Tenant, UsageEvent, UsageType
from app.schemas.billing import GenerateRequest
from app.services.cost import as_cents, token_cost_microcents
from app.services.quota import assert_subscription_and_quota

logger = logging.getLogger(__name__)


def duplicate_response(db: Session, tenant_id: int, key: str) -> dict | None:
    event = db.scalar(select(UsageEvent).where(UsageEvent.tenant_id == tenant_id, UsageEvent.idempotency_key == key, UsageEvent.usage_type == UsageType.API_CALL))
    return event.metadata_json.get("response") if event else None


def record_generation(db: Session, tenant: Tenant, key: str, payload: GenerateRequest, settings: Settings) -> tuple[dict, bool]:
    existing = duplicate_response(db, tenant.id, key)
    if existing:
        return existing, True
    try:
        # The subscription row acts as the per-tenant serialization point for quota checks.
        subscription = db.scalar(select(Subscription).options(joinedload(Subscription.plan)).where(Subscription.tenant_id == tenant.id).with_for_update())
        if not subscription:
            raise HTTPException(402, "No subscription found. Choose a plan to continue.")
        existing = duplicate_response(db, tenant.id, key)
        if existing:
            db.rollback()
            return existing, True
        assert_subscription_and_quota(db, subscription, api_requested=1, tokens_requested=payload.billable_tokens)
        token_cost = token_cost_microcents(payload, settings)
        total = settings.api_call_price_microcents + token_cost
        response = {
            "message": "Simulated generation completed.", "idempotency_key": key,
            "usage": {"api_calls": 1, "ai_tokens": payload.billable_tokens},
            "cost_microcents": total, "cost_cents": as_cents(total),
        }
        db.add(UsageEvent(tenant_id=tenant.id, usage_type=UsageType.API_CALL, quantity=1,
                          cost_microcents=settings.api_call_price_microcents, idempotency_key=key,
                          metadata_json={"response": response}))
        db.add(UsageEvent(tenant_id=tenant.id, usage_type=UsageType.AI_TOKENS, quantity=payload.billable_tokens,
                          cost_microcents=token_cost, idempotency_key=key,
                          metadata_json={"input_tokens": payload.input_tokens, "cached_input_tokens": payload.cached_input_tokens,
                                         "output_tokens": payload.output_tokens, "reasoning_tokens": payload.reasoning_tokens}))
        db.commit()
        return response, False
    except IntegrityError:
        # The unique database constraint is the final protection for concurrent retries.
        db.rollback()
        existing = duplicate_response(db, tenant.id, key)
        if existing:
            return existing, True
        logger.exception("Unexpected integrity error while metering tenant %s", tenant.id)
        raise HTTPException(409, "Could not safely record this request. Please retry with the same Idempotency-Key.")
