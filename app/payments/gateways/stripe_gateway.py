"""
Stripe adapter (for international/card-in-USD use, as an alternative to the
NGN-native gateways above).

Only ever instantiated -- and only ever makes a network call -- if
PAYMENT_GATEWAY=stripe AND STRIPE_SECRET_KEY is set in .env. Missing key ->
GatewayNotConfiguredError -> factory falls back to mock.

Uses Stripe's plain HTTP API directly (no stripe SDK dependency needed,
since httpx is already a project dependency) via Checkout Sessions.
Docs: https://docs.stripe.com/api/checkout/sessions
"""
import httpx

from app.payments.gateways.base import (
    GatewayNotConfiguredError,
    InitiateResult,
    PaymentGateway,
    VerifyResult,
)

STRIPE_BASE_URL = "https://api.stripe.com/v1"


class StripeGateway(PaymentGateway):
    name = "stripe"

    def __init__(self, secret_key: str | None):
        if not secret_key:
            raise GatewayNotConfiguredError(
                "STRIPE_SECRET_KEY is not set. Add it to .env before selecting "
                "PAYMENT_GATEWAY=stripe."
            )
        self._secret_key = secret_key

    def initiate(self, *, reference, amount, currency, email, callback_url) -> InitiateResult:
        # Stripe Checkout Sessions take form-encoded data, and amounts in the
        # smallest currency unit (cents for USD).
        payload = {
            "mode": "payment",
            "client_reference_id": reference,
            "customer_email": email,
            "success_url": f"{callback_url}?reference={reference}",
            "cancel_url": f"{callback_url}?reference={reference}&cancelled=1",
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": int(round(amount * 100)),
            "line_items[0][price_data][product_data][name]": f"Order {reference}",
            "line_items[0][quantity]": 1,
        }
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{STRIPE_BASE_URL}/checkout/sessions",
                data=payload,
                auth=(self._secret_key, ""),
            )
        resp.raise_for_status()
        data = resp.json()
        return InitiateResult(reference=data["id"], checkout_url=data["url"], raw=data)

    def verify(self, *, reference) -> VerifyResult:
        # `reference` here is the Checkout Session id returned by initiate().
        with httpx.Client(timeout=15) as client:
            resp = client.get(f"{STRIPE_BASE_URL}/checkout/sessions/{reference}", auth=(self._secret_key, ""))
        resp.raise_for_status()
        data = resp.json()
        success = data.get("payment_status") == "paid"
        return VerifyResult(
            success=success,
            status=data.get("payment_status", "unknown"),
            amount=(data.get("amount_total", 0) / 100),
            currency=(data.get("currency") or "").upper(),
            raw=data,
        )
