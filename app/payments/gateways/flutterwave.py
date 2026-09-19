"""
Flutterwave adapter.

Only ever instantiated -- and only ever makes a network call -- if
PAYMENT_GATEWAY=flutterwave AND FLUTTERWAVE_SECRET_KEY is set in .env.
Missing key -> GatewayNotConfiguredError -> factory falls back to mock.

Docs: https://developer.flutterwave.com/docs/making-payments
"""
import httpx

from app.payments.gateways.base import (
    GatewayNotConfiguredError,
    InitiateResult,
    PaymentGateway,
    VerifyResult,
)

FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"


class FlutterwaveGateway(PaymentGateway):
    name = "flutterwave"

    def __init__(self, secret_key: str | None):
        if not secret_key:
            raise GatewayNotConfiguredError(
                "FLUTTERWAVE_SECRET_KEY is not set. Add it to .env before selecting "
                "PAYMENT_GATEWAY=flutterwave."
            )
        self._secret_key = secret_key

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._secret_key}", "Content-Type": "application/json"}

    def initiate(self, *, reference, amount, currency, email, callback_url) -> InitiateResult:
        payload = {
            "tx_ref": reference,
            "amount": amount,
            "currency": currency,
            "redirect_url": callback_url,
            "customer": {"email": email},
        }
        with httpx.Client(timeout=15) as client:
            resp = client.post(f"{FLUTTERWAVE_BASE_URL}/payments", json=payload, headers=self._headers())
        resp.raise_for_status()
        data = resp.json()["data"]
        return InitiateResult(reference=reference, checkout_url=data["link"], raw=data)

    def verify(self, *, reference) -> VerifyResult:
        # Flutterwave's verify-by-reference endpoint looks transactions up by tx_ref.
        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{FLUTTERWAVE_BASE_URL}/transactions/verify_by_reference",
                params={"tx_ref": reference},
                headers=self._headers(),
            )
        resp.raise_for_status()
        data = resp.json()["data"]
        success = data.get("status") == "successful"
        return VerifyResult(
            success=success,
            status=data.get("status", "unknown"),
            amount=data.get("amount"),
            currency=data.get("currency"),
            raw=data,
        )
