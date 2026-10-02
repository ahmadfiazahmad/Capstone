from pydantic import BaseModel, Field, model_validator


class GenerateRequest(BaseModel):
    input_tokens: int = Field(default=0, ge=0, le=10_000_000)
    cached_input_tokens: int = Field(default=0, ge=0, le=10_000_000)
    output_tokens: int = Field(default=0, ge=0, le=10_000_000)
    reasoning_tokens: int = Field(default=0, ge=0, le=10_000_000)

    @model_validator(mode="after")
    def input_tokens_include_cached(self):
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens cannot exceed input_tokens")
        return self

    @property
    def billable_tokens(self) -> int:
        # input_tokens includes cached tokens, so avoid double-counting that overlap.
        return self.input_tokens + self.output_tokens + self.reasoning_tokens


class CheckoutRequest(BaseModel):
    # A separate, explicit confirmation makes accidental checkout creation less likely.
    confirm_pro_upgrade: bool


class UsageResponse(BaseModel):
    api_calls: dict
    ai_tokens: dict
    cost_microcents: int
    cost_cents: str
    plan: str
    subscription_status: str
