from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.billing import Tenant


def current_tenant(x_tenant_api_key: str = Header(...), db: Session = Depends(get_db)) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.api_key == x_tenant_api_key))
    if not tenant:
        raise HTTPException(401, "Invalid tenant API key.")
    return tenant
