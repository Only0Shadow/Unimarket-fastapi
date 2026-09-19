"""
Centralized application configuration.

All configurable values are pulled from environment variables (see
.env.example). Nothing here should ever contain a real secret.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, populated from environment variables / .env file."""

    app_name: str = "University Marketplace"
    debug: bool = False

    # Used to sign session cookies. MUST be overridden in production via env var.
    secret_key: str = "dev-secret-key-change-me"

    database_url: str = "sqlite:///./university_marketplace.db"

    allowed_hosts: str = "*"

    # Session cookie lifetime, in seconds (default: 7 days).
    session_max_age: int = 60 * 60 * 24 * 7

    # Pagination defaults.
    default_page_size: int = 12
    max_page_size: int = 60

    # Flat delivery-fee estimate shown at checkout. Real courier-fee
    # calculation is a future feature (see README "Known limitations").
    delivery_fee_estimate: float = 300.0

    # Base URL of this app, used to build gateway redirect/callback URLs.
    app_base_url: str = "http://localhost:8000"

    # Payment gateway selection: "mock" (default -- no external calls, no
    # keys needed, safe for dev/demo), "paystack", "flutterwave", or
    # "stripe". If a real gateway is selected but its keys below are blank,
    # the app automatically falls back to "mock" instead of crashing.
    payment_gateway: str = "mock"
    payment_currency: str = "NGN"

    paystack_secret_key: str | None = None
    paystack_public_key: str | None = None
    flutterwave_secret_key: str | None = None
    flutterwave_public_key: str | None = None
    stripe_secret_key: str | None = None
    stripe_publishable_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the .env file is only parsed once."""
    return Settings()
