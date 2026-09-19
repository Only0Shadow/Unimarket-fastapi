"""
Vendor (store) model.

A User becomes a seller by acquiring a Vendor record. Vendors must be
approved by an administrator before their products/store become publicly
visible.
"""
import enum
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VendorStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    store_name: Mapped[str] = mapped_column(String(150))
    store_slug: Mapped[str] = mapped_column(String(170), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    banner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    status: Mapped[VendorStatus] = mapped_column(SAEnum(VendorStatus), default=VendorStatus.PENDING)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="vendor")
    products: Mapped[list["Product"]] = relationship("Product", back_populates="vendor")

    def __repr__(self) -> str:
        return f"<Vendor {self.store_name!r} status={self.status}>"
