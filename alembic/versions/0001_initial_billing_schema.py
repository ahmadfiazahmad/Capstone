"""initial billing schema

Revision ID: 0001_initial
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    subscriptionstatus = sa.Enum("ACTIVE", "PAST_DUE", "CANCELED", name="subscriptionstatus")
    usagetype = sa.Enum("API_CALL", "AI_TOKENS", name="usagetype")
    op.create_table("tenants", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(120), nullable=False, unique=True), sa.Column("api_key", sa.String(128), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_tenants_api_key", "tenants", ["api_key"])
    op.create_table("plans", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(20), nullable=False, unique=True), sa.Column("api_calls_limit", sa.Integer(), nullable=False), sa.Column("ai_tokens_limit", sa.Integer(), nullable=False), sa.Column("stripe_price_id", sa.String(128)))
    op.create_table("subscriptions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("plan_id", sa.Integer(), sa.ForeignKey("plans.id"), nullable=False), sa.Column("status", subscriptionstatus, nullable=False), sa.Column("stripe_customer_id", sa.String(128), unique=True), sa.Column("stripe_subscription_id", sa.String(128), unique=True))
    op.create_table("usage_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("usage_type", usagetype, nullable=False), sa.Column("quantity", sa.BigInteger(), nullable=False), sa.Column("cost_microcents", sa.BigInteger(), nullable=False), sa.Column("idempotency_key", sa.String(255), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), sa.UniqueConstraint("tenant_id", "idempotency_key", "usage_type", name="uq_usage_event_tenant_key_type"))
    op.create_index("ix_usage_events_tenant_id", "usage_events", ["tenant_id"])
    op.create_index("ix_usage_events_idempotency_key", "usage_events", ["idempotency_key"])
    op.create_index("ix_usage_events_tenant_timestamp", "usage_events", ["tenant_id", "occurred_at"])
    op.create_table("processed_stripe_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("stripe_event_id", sa.String(128), nullable=False, unique=True), sa.Column("event_type", sa.String(100), nullable=False), sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_processed_stripe_events_stripe_event_id", "processed_stripe_events", ["stripe_event_id"])


def downgrade():
    op.drop_table("processed_stripe_events")
    op.drop_table("usage_events")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    op.drop_table("tenants")
    op.execute("DROP TYPE IF EXISTS usagetype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
