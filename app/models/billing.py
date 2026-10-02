import enum
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class UsageType(str, enum.Enum):
    API_CALL = "api_call"
    AI_TOKENS = "ai_tokens"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # In a real app store a hash. A plaintext demo key keeps the capstone setup inspectable.
    api_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    subscription: Mapped["Subscription"] = relationship(back_populates="tenant", uselist=False)


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    api_calls_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_tokens_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    tenant: Mapped[Tenant] = relationship(back_populates="subscription")
    plan: Mapped[Plan] = relationship()


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", "usage_type", name="uq_usage_event_tenant_key_type"),
        Index("ix_usage_events_tenant_timestamp", "tenant_id", "occurred_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    usage_type: Mapped[UsageType] = mapped_column(Enum(UsageType), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cost_microcents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProcessedStripeEvent(Base):
    __tablename__ = "processed_stripe_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stripe_event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
