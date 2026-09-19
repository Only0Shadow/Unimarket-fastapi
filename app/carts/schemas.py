"""Pydantic schemas for cart mutations."""
from pydantic import BaseModel, field_validator


class CartAddIn(BaseModel):
    product_id: int
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Quantity must be at least 1.")
        return v


class CartUpdateIn(BaseModel):
    quantity: int

    @field_validator("quantity")
    @classmethod
    def non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity cannot be negative.")
        return v
