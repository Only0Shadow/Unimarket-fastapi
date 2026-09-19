"""
Paystack adapter.

Only ever instantiated -- and only ever makes a network call -- if
PAYMENT_GATEWAY=paystack AND PAYSTACK_SECRET_KEY is set in .env. If the key
is missing, the factory (see app/payments/gateways/__init__.py) catches
GatewayNotConfiguredError and falls back to the mock gateway instead of
crashing the app.

Docs: https://paystack.com/docs/api/transaction/
"""
import httpx

from app.payments.gateways.base import (
    GatewayNotConfiguredError,
    InitiateResult,
    PaymentGateway,
    VerifyResult,
)

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackGateway(PaymentGateway):
    name = "paystack"

    def __init__(self, secret_key: str | None):
        if not secret_key:
            raise GatewayNotConfiguredError(
                "PAYSTACK_SECRET_KEY is not set. Add it to .env before selecting "
                "PAYMENT_GATEWAY=paystack."
            )
        self._secret_key = secret_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._secret_key}", "Content-Type": "application/json"}

    def initiate(self, *, reference, amount, currency, email, callback_url) -> InitiateResult:
        # Paystack expects amounts in the smallest currency unit (kobo for NGN).
        payload = {
            "reference": reference,
            "amount": int(round(amount * 100)),
            "currency": currency,
            "email": email,
            "callback_url": callback_url,
        }
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize", json=payload, headers=self._headers()
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        return InitiateResult(reference=reference, checkout_url=data["authorization_url"], raw=data)

    def verify(self, *, reference) -> VerifyResult:
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=self._headers()
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        success = data.get("status") == "success"
        return VerifyResult(
            success=success,
            status=data.get("status", "unknown"),
            amount=(data.get("amount", 0) / 100),
            currency=data.get("currency"),
            raw=data,
        )
