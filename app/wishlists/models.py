"""Wishlist models. Every user gets exactly one Wishlist, created at registration."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Wishlist(Base):
    __tablename__ = "wishlists"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer: Mapped["User"] = relationship("User", back_populates="wishlist")
    items: Mapped[list["WishlistItem"]] = relationship(
        "WishlistItem", back_populates="wishlist", cascade="all, delete-orphan"
    )


class WishlistItem(Base):
    __tablename__ = "wishlist_items"
    __table_args__ = (UniqueConstraint("wishlist_id", "product_id", name="uq_wishlist_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    wishlist_id: Mapped[int] = mapped_column(ForeignKey("wishlists.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wishlist: Mapped["Wishlist"] = relationship("Wishlist", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
