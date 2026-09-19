"""Pydantic schemas for categories."""
from pydantic import BaseModel


class CategoryIn(BaseModel):
    name: str
    description: str | None = None
    image: str | None = None
    is_active: bool = True
