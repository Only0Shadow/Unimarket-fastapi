"""Pydantic schemas for authentication endpoints."""
import re

from pydantic import BaseModel, EmailStr, field_validator


class RegisterIn(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    phone_number: str | None = None
    password: str
    confirm_password: str

    @field_validator("username")
    @classmethod
    def username_format(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,50}", v):
            raise ValueError(
                "Username must be 3-50 characters: letters, numbers, underscores only."
            )
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v


class LoginIn(BaseModel):
    identifier: str  # username or email
    password: str
