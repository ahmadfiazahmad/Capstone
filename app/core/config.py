from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./metering.db"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    pro_stripe_price_id: str = ""
    checkout_success_url: str = "http://localhost:8000/docs"
    checkout_cancel_url: str = "http://localhost:8000/docs"

    # All prices are microcents (1 cent = 1,000,000 microcents); integers prevent money rounding errors.
    api_call_price_microcents: int = Field(default=100, ge=0)
    input_token_price_microcents: int = Field(default=2, ge=0)
    cached_input_token_price_microcents: int = Field(default=1, ge=0)
    output_token_price_microcents: int = Field(default=4, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
