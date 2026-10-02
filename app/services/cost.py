from decimal import Decimal
from app.core.config import Settings
from app.schemas.billing import GenerateRequest


MICROCENTS_PER_CENT = 1_000_000


def token_cost_microcents(payload: GenerateRequest, settings: Settings) -> int:
    """Cached tokens are part of input_tokens, and reasoning is charged as output."""
    fresh_input = payload.input_tokens - payload.cached_input_tokens
    return (
        fresh_input * settings.input_token_price_microcents
        + payload.cached_input_tokens * settings.cached_input_token_price_microcents
        + (payload.output_tokens + payload.reasoning_tokens) * settings.output_token_price_microcents
    )


def as_cents(microcents: int) -> str:
    return str((Decimal(microcents) / Decimal(MICROCENTS_PER_CENT)).quantize(Decimal("0.000001")))
