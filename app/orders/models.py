"""Order and OrderItem models."""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Float, Integer, DateTime, ForeignKey, Enum as SAEnum, Text, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    READY = "ready"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# Statuses at or before which a customer may still cancel their own order.
CANCELLABLE_STATUSES = {OrderStatus.PENDING, OrderStatus.CONFIRMED}


def generate_order_number() -> str:
    return f"UM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, default=generate_order_number)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    subtotal: Mapped[float] = mapped_column(Float)
    delivery_fee: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float)

    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), default=OrderStatus.PENDING)

    # Snapshot of delivery details at time of order (not a live FK to
    # DeliveryAddress, so historical orders remain accurate even if the
    # user later edits or deletes that saved address).
    recipient_name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str] = mapped_column(String(30))
    university: Mapped[str] = mapped_column(String(150))
    hostel: Mapped[str] = mapped_column(String(120))
    block: Mapped[str | None] = mapped_column(String(50), nullable=True)
    room: Mapped[str | None] = mapped_column(String(50), nullable=True)
    campus_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    delivery_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    customer: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="order", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def is_cancellable(self) -> bool:
        return self.status in CANCELLABLE_STATUSES

    @property
    def payment_status_display(self) -> str:
        if self.payment is None:
            return "Not started"
        return self.payment.status.value.replace("_", " ").title()


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_item_quantity_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

    product_name_snapshot: Mapped[str] = mapped_column(String(200))
    unit_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[float] = mapped_column(Float)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
