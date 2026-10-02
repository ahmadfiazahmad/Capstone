from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from app.models.billing import Subscription, Tenant, UsageEvent, UsageType
from app.services.cost import as_cents
from app.services.quota import month_usage


def usage_summary(db: Session, tenant: Tenant) -> dict:
    subscription = db.scalar(select(Subscription).options(joinedload(Subscription.plan)).where(Subscription.tenant_id == tenant.id))
    if not subscription:
        return {"api_calls": {"used": 0, "limit": 0}, "ai_tokens": {"used": 0, "limit": 0}, "cost_microcents": 0, "cost_cents": "0.000000", "plan": "NONE", "subscription_status": "missing"}
    api_used = month_usage(db, tenant.id, UsageType.API_CALL)
    token_used = month_usage(db, tenant.id, UsageType.AI_TOKENS)
    total = int(db.scalar(select(func.coalesce(func.sum(UsageEvent.cost_microcents), 0)).where(UsageEvent.tenant_id == tenant.id)) or 0)
    return {"api_calls": {"used": api_used, "limit": subscription.plan.api_calls_limit},
            "ai_tokens": {"used": token_used, "limit": subscription.plan.ai_tokens_limit},
            "cost_microcents": total, "cost_cents": as_cents(total), "plan": subscription.plan.code,
            "subscription_status": subscription.status.value}
