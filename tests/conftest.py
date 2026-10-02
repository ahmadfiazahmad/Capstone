import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.models.billing import Plan, Subscription, SubscriptionStatus, Tenant


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    free = Plan(code="FREE", api_calls_limit=1000, ai_tokens_limit=100000)
    pro = Plan(code="PRO", api_calls_limit=10000, ai_tokens_limit=1000000)
    a, b = Tenant(name="A", api_key="key-a"), Tenant(name="B", api_key="key-b")
    session.add_all([free, pro, a, b]); session.flush()
    session.add_all([Subscription(tenant_id=a.id, plan_id=free.id, status=SubscriptionStatus.ACTIVE), Subscription(tenant_id=b.id, plan_id=free.id, status=SubscriptionStatus.ACTIVE)])
    session.commit()
    yield session
    session.close()

