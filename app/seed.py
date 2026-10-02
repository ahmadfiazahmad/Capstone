"""Repeatable demo seed: python -m app.seed"""
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.billing import Plan, Subscription, SubscriptionStatus, Tenant


PLANS = {"FREE": (1_000, 100_000), "PRO": (10_000, 1_000_000)}
TENANTS = [("Demo Free", "demo-free-key", "FREE"), ("Demo Pro", "demo-pro-key", "PRO")]


def seed() -> None:
    db = SessionLocal()
    try:
        plans = {}
        for code, (api_limit, token_limit) in PLANS.items():
            plan = db.scalar(select(Plan).where(Plan.code == code))
            if not plan:
                plan = Plan(code=code, api_calls_limit=api_limit, ai_tokens_limit=token_limit)
                db.add(plan)
            else:
                plan.api_calls_limit, plan.ai_tokens_limit = api_limit, token_limit
            plans[code] = plan
        db.flush()
        for name, api_key, plan_code in TENANTS:
            tenant = db.scalar(select(Tenant).where(Tenant.api_key == api_key))
            if not tenant:
                tenant = Tenant(name=name, api_key=api_key)
                db.add(tenant)
                db.flush()
            subscription = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id))
            if not subscription:
                db.add(Subscription(tenant_id=tenant.id, plan_id=plans[plan_code].id, status=SubscriptionStatus.ACTIVE))
        db.commit()
        print("Seed complete. Demo keys: demo-free-key and demo-pro-key")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
