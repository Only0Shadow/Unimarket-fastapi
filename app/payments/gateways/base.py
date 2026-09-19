"""
Abstract payment gateway interface.

Every concrete gateway (Paystack, Flutterwave, Stripe, or the local Mock
gateway used when no real keys are configured) implements this interface.
The rest of the app -- checkout, orders, webhooks -- talks only to this
interface, never to a specific gateway's API directly. Swapping providers,
or adding a new one, means writing one new adapter class; nothing else in
the app changes.

No adapter here ever sees or stores raw card/bank details. Card entry
happens on the gateway's own hosted, PCI-compliant checkout page; this app
only ever handles a `reference` string and a redirect URL.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class InitiateResult:
    """Returned after starting a payment. checkout_url is where the browser
    should be sent to actually pay."""
    reference: str
    checkout_url: str
    raw: dict | None = None


@dataclass
class VerifyResult:
    """Returned after asking the gateway whether a payment succeeded."""
    success: bool
    status: str  # the gateway's own raw status string, kept for logging/debugging
    amount: float | None = None
    currency: str | None = None
    raw: dict | None = None


class GatewayNotConfiguredError(Exception):
    """Raised when a gateway is selected but its API keys are missing."""


class PaymentGateway(ABC):
    """Common interface for all payment gateway adapters."""

    name: str = "base"

    @abstractmethod
    def initiate(
        self, *, reference: str, amount: float, currency: str, email: str, callback_url: str
    ) -> InitiateResult:
        """Start a payment and return a URL the customer's browser should be
        redirected to in order to actually pay."""
        raise NotImplementedError

    @abstractmethod
    def verify(self, *, reference: str) -> VerifyResult:
        """Ask the gateway for the current, authoritative status of a
        payment. This -- never the browser redirect alone -- is what should
        decide whether an order gets marked paid."""
        raise NotImplementedError
