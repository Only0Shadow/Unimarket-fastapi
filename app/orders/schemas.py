"""Pydantic schemas for checkout/order creation."""
from pydantic import BaseModel


class CheckoutIn(BaseModel):
    recipient_name: str
    phone_number: str
    university: str
    hostel: str
    block: str | None = None
    room: str | None = None
    campus_location: str | None = None
    delivery_instructions: str | None = None
