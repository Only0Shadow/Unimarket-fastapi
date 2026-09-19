"""
Payment model.

Every order gets exactly one Payment row, created in PENDING state the
moment checkout starts a gateway session, and updated to PAID/FAILED once
the selected gateway (see app.payments.gateways) confirms the outcome.

No card, bank, or account details are ever stored here -- only the
gateway's own transaction reference and a checkout URL. Card entry happens
entirely on the gateway's hosted, encrypted checkout page.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Base):
    # Table name kept from the original placeholder scaffolding so no
    # destructive rename migration is needed -- only new columns are added.
    __tablename__ = "payment_placeholders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True)

    gateway: Mapped[str] = mapped_column(String(30), default="mock")
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.NOT_STARTED)

    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="NGN")

    # The gateway's own transaction reference -- never a card/account number.
    gateway_reference: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    checkout_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="payment")
