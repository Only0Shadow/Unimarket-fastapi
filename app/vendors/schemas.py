"""Pydantic schemas for vendor store applications and edits."""
from pydantic import BaseModel


class VendorApplyIn(BaseModel):
    store_name: str
    description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class VendorUpdateIn(BaseModel):
    store_name: str
    description: str | None = None
    logo: str | None = None
    banner: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
