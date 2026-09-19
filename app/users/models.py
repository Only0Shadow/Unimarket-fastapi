"""
Profile and DeliveryAddress models.

Profile holds extended, editable account information beyond the core auth
fields on User. DeliveryAddress lets a student save one or more campus
delivery locations for reuse at checkout.
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    profile_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university: Mapped[str | None] = mapped_column(String(150), nullable=True)
    student_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hostel: Mapped[str | None] = mapped_column(String(120), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="profile")


class DeliveryAddress(Base):
    __tablename__ = "delivery_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    label: Mapped[str] = mapped_column(String(60), default="Default")
    recipient_name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str] = mapped_column(String(30))
    university: Mapped[str] = mapped_column(String(150))
    hostel: Mapped[str] = mapped_column(String(120))
    block: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room: Mapped[str | None] = mapped_column(String(50), nullable=True)
    campus_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="delivery_addresses")
