"""Pydantic schemas for the payments API."""
from datetime import datetime

from pydantic import BaseModel

from app.payments.models import PaymentStatus


class PaymentOut(BaseModel):
    status: PaymentStatus
    gateway: str
    amount: float
    currency: str
    gateway_reference: str | None = None
    checkout_url: str | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class InitiatePaymentOut(BaseModel):
    """Returned when a payment session is started -- send the customer's
    browser to checkout_url to complete payment."""
    reference: str
    checkout_url: str
    gateway: str
