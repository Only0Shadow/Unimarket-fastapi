"""
Core User model.

A single User table backs all roles (student, vendor, admin). A user with
role="vendor" additionally has a related Vendor record (see app.vendors.models)
that holds their store information and approval status.
"""
import enum
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    VENDOR = "vendor"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)

    hashed_password: Mapped[str] = mapped_column(String(255))

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.STUDENT)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # One-to-one style relationships, resolved by class name string so that
    # individual feature modules never need to import each other's model
    # modules directly (avoids circular imports across the app package).
    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    vendor: Mapped["Vendor"] = relationship(
        "Vendor", back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
    cart: Mapped["Cart"] = relationship(
        "Cart", back_populates="customer", uselist=False, cascade="all, delete-orphan"
    )
    wishlist: Mapped["Wishlist"] = relationship(
        "Wishlist", back_populates="customer", uselist=False, cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="recipient"
    )
    delivery_addresses: Mapped[list["DeliveryAddress"]] = relationship(
        "DeliveryAddress", back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def unread_notifications_count(self) -> int:
        return len([n for n in self.notifications if not n.is_read])

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
