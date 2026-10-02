from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import current_tenant
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.billing import Tenant
from app.schemas.billing import CheckoutRequest, GenerateRequest, UsageResponse
from app.services.metering import record_generation
from app.services.notifications import emit_usage_notification
from app.services.stripe_service import create_checkout
from app.services.usage import usage_summary

router = APIRouter(tags=["billing"])


@router.post("/generate")
def generate(payload: GenerateRequest, background_tasks: BackgroundTasks, idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=255), tenant: Tenant = Depends(current_tenant), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    result, replayed = record_generation(db, tenant, idempotency_key, payload, settings)
    if not replayed:
        background_tasks.add_task(emit_usage_notification, tenant.id, idempotency_key)
    return {**result, "idempotent_replay": replayed}


@router.get("/usage", response_model=UsageResponse)
def usage(tenant: Tenant = Depends(current_tenant), db: Session = Depends(get_db)):
    return usage_summary(db, tenant)


@router.post("/checkout/pro")
def checkout(payload: CheckoutRequest, tenant: Tenant = Depends(current_tenant), settings: Settings = Depends(get_settings)):
    if not payload.confirm_pro_upgrade:
        raise HTTPException(422, "confirm_pro_upgrade must be true.")
    return {"checkout_url": create_checkout(tenant, settings)}
