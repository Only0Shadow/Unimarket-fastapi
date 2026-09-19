"""
Gateway factory.

get_gateway() reads PAYMENT_GATEWAY from settings and returns the matching
adapter. If the selected gateway's API keys are missing, it logs a warning
and falls back to the Mock gateway rather than crashing the app -- so a
fresh checkout of this project (before any real keys are added) always
works in sandbox mode.
"""
import logging

from app.config import get_settings
from app.payments.gateways.base import GatewayNotConfiguredError, PaymentGateway
from app.payments.gateways.flutterwave import FlutterwaveGateway
from app.payments.gateways.mock import MockGateway
from app.payments.gateways.paystack import PaystackGateway
from app.payments.gateways.stripe_gateway import StripeGateway

logger = logging.getLogger(__name__)


def get_gateway() -> PaymentGateway:
    settings = get_settings()
    choice = (settings.payment_gateway or "mock").lower()

    try:
        if choice == "paystack":
            return PaystackGateway(settings.paystack_secret_key)
        if choice == "flutterwave":
            return FlutterwaveGateway(settings.flutterwave_secret_key)
        if choice == "stripe":
            return StripeGateway(settings.stripe_secret_key)
    except GatewayNotConfiguredError as exc:
        logger.warning(
            "PAYMENT_GATEWAY=%s selected but not configured (%s) -- falling back to the mock gateway.",
            choice,
            exc,
        )
        return MockGateway()

    return MockGateway()


__all__ = ["get_gateway", "PaymentGateway"]
