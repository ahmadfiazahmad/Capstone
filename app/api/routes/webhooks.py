from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.billing import Plan, ProcessedStripeEvent, Subscription, SubscriptionStatus, Tenant
from app.services.stripe_service import verify_event

router = APIRouter(tags=["stripe"])


def event_value(event, name, default=None):
    return event.get(name, default) if hasattr(event, "get") else getattr(event, name, default)


def sync_subscription(db: Session, event) -> None:
    kind = event_value(event, "type")
    data = event_value(event, "data", {})
    obj = event_value(data, "object", {})
    metadata = event_value(obj, "metadata", {}) or {}
    tenant_id = event_value(metadata, "tenant_id") or event_value(obj, "client_reference_id")
    stripe_customer_id = event_value(obj, "customer")
    stripe_subscription_id = event_value(obj, "subscription") if kind == "checkout.session.completed" else event_value(obj, "id")
    subscription = None
    if tenant_id:
        subscription = db.scalar(select(Subscription).where(Subscription.tenant_id == int(tenant_id)))
    if not subscription and stripe_subscription_id:
        subscription = db.scalar(select(Subscription).where(Subscription.stripe_subscription_id == stripe_subscription_id))
    if not subscription and stripe_customer_id:
        subscription = db.scalar(select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id))
    if not subscription:
        return  # A verified event for another app/customer must not create a local tenant.
    free = db.scalar(select(Plan).where(Plan.code == "FREE"))
    pro = db.scalar(select(Plan).where(Plan.code == "PRO"))
    if kind == "customer.subscription.deleted":
        subscription.plan = free
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.stripe_subscription_id = stripe_subscription_id
        return
    status = event_value(obj, "status", "active")
    subscription.stripe_customer_id = stripe_customer_id or subscription.stripe_customer_id
    subscription.stripe_subscription_id = stripe_subscription_id or subscription.stripe_subscription_id
    if status in {"active", "trialing"}:
        subscription.plan = pro
        subscription.status = SubscriptionStatus.ACTIVE
    else:
        subscription.status = SubscriptionStatus.PAST_DUE


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    event = verify_event(await request.body(), request.headers.get("stripe-signature"), settings)
    event_id, event_type = event_value(event, "id"), event_value(event, "type")
    try:
        db.add(ProcessedStripeEvent(stripe_event_id=event_id, event_type=event_type))
        db.flush()  # Claim the event before applying its state change.
    except IntegrityError:
        db.rollback()
        return {"received": True, "duplicate": True}
    sync_subscription(db, event)
    db.commit()
    return {"received": True, "duplicate": False}
