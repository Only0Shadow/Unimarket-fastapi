"""Pydantic schemas for profile editing and delivery addresses."""
from pydantic import BaseModel


class ProfileUpdateIn(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None = None
    university: str | None = None
    student_id: str | None = None
    hostel: str | None = None


class DeliveryAddressIn(BaseModel):
    label: str = "Default"
    recipient_name: str
    phone_number: str
    university: str
    hostel: str
    block: str | None = None
    room: str | None = None
    campus_location: str | None = None
    instructions: str | None = None
    is_default: bool = False
