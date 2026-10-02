from fastapi import FastAPI
from app.api.routes.billing import router as billing_router
from app.api.routes.webhooks import router as webhook_router

app = FastAPI(title="Usage Metering & Billing Engine", version="1.0.0")
app.include_router(billing_router)
app.include_router(webhook_router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
