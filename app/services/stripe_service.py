from fastapi import HTTPException
import stripe
from app.core.config import Settings
from app.models.billing import Tenant


def create_checkout(tenant: Tenant, settings: Settings) -> str:
    if not settings.stripe_secret_key or not settings.pro_stripe_price_id:
        raise HTTPException(503, "Stripe test-mode configuration is incomplete.")
    if not settings.stripe_secret_key.startswith("sk_test_"):
        raise HTTPException(500, "Only Stripe test-mode keys are permitted.")
    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription", line_items=[{"price": settings.pro_stripe_price_id, "quantity": 1}],
        success_url=settings.checkout_success_url, cancel_url=settings.checkout_cancel_url,
        client_reference_id=str(tenant.id), metadata={"tenant_id": str(tenant.id)},
    )
    return session.url


def verify_event(payload: bytes, signature: str | None, settings: Settings):
    if not settings.stripe_webhook_secret or not signature:
        raise HTTPException(400, "Invalid Stripe webhook signature.")
    try:
        return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid Stripe webhook signature.")
