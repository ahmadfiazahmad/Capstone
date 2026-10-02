import logging

logger = logging.getLogger(__name__)


def emit_usage_notification(tenant_id: int, idempotency_key: str) -> None:
    """Non-critical placeholder for an email/webhook provider; metering was committed already."""
    try:
        logger.info("Usage notification simulated for tenant=%s request=%s", tenant_id, idempotency_key)
    except Exception:
        logger.exception("Usage notification failed after successful metering")
