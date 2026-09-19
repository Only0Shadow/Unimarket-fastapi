"""Product and ProductImage models."""
import enum
from datetime import datetime

from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum as SAEnum, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProductCondition(str, enum.Enum):
    NEW = "new"
    USED = "used"
    REFURBISHED = "refurbished"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_product_price_non_negative"),
        CheckConstraint("quantity_available >= 0", name="ck_product_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))

    price: Mapped[float] = mapped_column(Float)
    previous_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity_available: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition: Mapped[ProductCondition] = mapped_column(
        SAEnum(ProductCondition), default=ProductCondition.NEW
    )

    image: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    category: Mapped["Category"] = relationship("Category", back_populates="products")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def average_rating(self) -> float:
        approved = [r.rating for r in self.reviews if r.is_approved]
        return round(sum(approved) / len(approved), 1) if approved else 0.0

    @property
    def review_count(self) -> int:
        return len([r for r in self.reviews if r.is_approved])

    @property
    def discount_percentage(self) -> int:
        if self.previous_price and self.previous_price > self.price:
            return round((self.previous_price - self.price) / self.previous_price * 100)
        return 0

    @property
    def stock_label(self) -> str:
        if self.quantity_available <= 0:
            return "Out of Stock"
        if self.quantity_available <= 5:
            return "Low Stock"
        return "In Stock"

    def __repr__(self) -> str:
        return f"<Product {self.name!r}>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    image_url: Mapped[str] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship("Product", back_populates="images")
