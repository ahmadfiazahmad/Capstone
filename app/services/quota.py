from fastapi import HTTPException
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.billing import Subscription, SubscriptionStatus, UsageEvent, UsageType


def month_usage(db: Session, tenant_id: int, usage_type: UsageType) -> int:
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(db.scalar(select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
        UsageEvent.tenant_id == tenant_id,
        UsageEvent.usage_type == usage_type,
        UsageEvent.occurred_at >= start,
    )) or 0)


def assert_subscription_and_quota(db: Session, subscription: Subscription, api_requested: int, tokens_requested: int) -> None:
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(402, "Subscription is not active. Upgrade or update payment to continue.")
    api_used = month_usage(db, subscription.tenant_id, UsageType.API_CALL)
    token_used = month_usage(db, subscription.tenant_id, UsageType.AI_TOKENS)
    if api_used + api_requested > subscription.plan.api_calls_limit:
        raise HTTPException(429, "API call quota exceeded. Upgrade your plan to continue.")
    if token_used + tokens_requested > subscription.plan.ai_tokens_limit:
        raise HTTPException(429, "AI token quota exceeded. Upgrade your plan to continue.")
