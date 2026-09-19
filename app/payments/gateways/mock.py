"""
Mock/sandbox gateway.

This is the default gateway (PAYMENT_GATEWAY=mock in .env), and the one the
factory falls back to automatically if a real gateway is selected but its
API keys aren't configured yet. It moves no real money and makes no
external network calls: it fabricates a "checkout" page hosted by this app
itself (see the /payments/mock-checkout route) where a developer can click
"Simulate success" or "Simulate failure" to exercise the full
initiate -> pay -> verify flow end-to-end before any real gateway account
exists.

Swap PAYMENT_GATEWAY to "paystack" / "flutterwave" / "stripe" and add the
matching keys in .env once you're ready to test against a real sandbox.
"""
from app.payments.gateways.base import InitiateResult, PaymentGateway, VerifyResult

# In-memory store of simulated outcomes, keyed by reference. This resets on
# every app restart -- fine for a mock/dev-only gateway, never used once a
# real gateway is configured.
_SIMULATED: dict[str, str] = {}


class MockGateway(PaymentGateway):
    name = "mock"

    def initiate(self, *, reference, amount, currency, email, callback_url) -> InitiateResult:
        _SIMULATED.setdefault(reference, "pending")
        checkout_url = f"/payments/mock-checkout/{reference}"
        return InitiateResult(
            reference=reference,
            checkout_url=checkout_url,
            raw={"amount": amount, "currency": currency, "email": email, "callback_url": callback_url},
        )

    def verify(self, *, reference) -> VerifyResult:
        outcome = _SIMULATED.get(reference, "pending")
        return VerifyResult(success=outcome == "success", status=outcome)

    @classmethod
    def resolve(cls, reference: str, outcome: str) -> None:
        """Dev-only helper used by the mock checkout page to record which
        button the developer clicked. Never present in a real gateway."""
        _SIMULATED[reference] = outcome
