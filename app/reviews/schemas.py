"""Pydantic schemas for reviews."""
from pydantic import BaseModel, field_validator


class ReviewIn(BaseModel):
    rating: int
    comment: str | None = None

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if not (1 <= v <= 5):
            raise ValueError("Rating must be between 1 and 5.")
        return v
