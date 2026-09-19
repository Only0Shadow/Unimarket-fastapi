"""Pydantic schemas for product creation/editing."""
from pydantic import BaseModel, field_validator


class ProductIn(BaseModel):
    name: str
    short_description: str | None = None
    description: str | None = None
    category_id: int
    price: float
    previous_price: float | None = None
    quantity_available: int
    brand: str | None = None
    condition: str = "new"
    image: str | None = None
    is_featured: bool = False
    is_active: bool = True

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative.")
        return v

    @field_validator("quantity_available")
    @classmethod
    def quantity_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity available cannot be negative.")
        return v

    @field_validator("condition")
    @classmethod
    def condition_valid(cls, v: str) -> str:
        if v not in ("new", "used", "refurbished"):
            raise ValueError("Condition must be one of: new, used, refurbished.")
        return v
