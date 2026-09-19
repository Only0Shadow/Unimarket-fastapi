"""
Payment service.

Owns the full payment lifecycle for an order: create a PENDING record,
ask the configured gateway (see app.payments.gateways) to start a checkout
session, and later verify the outcome against the gateway's own API before
ever marking an order paid.

Money only ever moves on the gateway's hosted checkout page. This service
never receives, stores, or forwards a card or bank account number.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.orders.models import Order, OrderStatus
from app.payments.gateways import get_gateway
from app.payments.models import Payment, PaymentStatus

settings = get_settings()


class PaymentError(Exception):
    """Raised for payment-flow failures that should be shown to the user."""


class PaymentService:
    @staticmethod
    def create_placeholder_for_order(db: Session, order: Order) -> Payment:
        """Attach a NOT_STARTED Payment row to a newly created order."""
        payment = Payment(
            order_id=order.id,
            status=PaymentStatus.NOT_STARTED,
            amount=order.total,
            currency=settings.payment_currency,
        )
        db.add(payment)
        db.flush()
        return payment

    @staticmethod
    def initiate_payment(db: Session, order: Order, email: str) -> Payment:
        """Start a gateway checkout session for this order and record the
        resulting reference + checkout URL. Does not mark the order paid --
        only verify_payment (backed by a gateway-confirmed status) does."""
        payment = order.payment
        if payment is None:
            payment = PaymentService.create_placeholder_for_order(db, order)

        if payment.status == PaymentStatus.PAID:
            raise PaymentError("This order has already been paid for.")

        gateway = get_gateway()
        reference = f"{order.order_number}-{int(datetime.utcnow().timestamp())}"
        callback_url = f"{settings.app_base_url}/payments/verify/{reference}"

        result = gateway.initiate(
            reference=reference,
            amount=order.total,
            currency=settings.payment_currency,
            email=email,
            callback_url=callback_url,
        )

        payment.gateway = gateway.name
        payment.status = PaymentStatus.PENDING
        payment.amount = order.total
        payment.currency = settings.payment_currency
        payment.gateway_reference = result.reference
        payment.checkout_url = result.checkout_url
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def verify_payment(db: Session, reference: str) -> Payment:
        """Ask the gateway for the authoritative status of a transaction and
        update the local Payment + Order accordingly. This is the only path
        that may ever set a payment to PAID."""
        payment = db.query(Payment).filter(Payment.gateway_reference == reference).first()
        if payment is None:
            raise PaymentError("No payment found for that reference.")

        gateway = get_gateway()
        result = gateway.verify(reference=reference)

        payment.status = PaymentStatus.PAID if result.success else PaymentStatus.FAILED
        payment.verified_at = datetime.utcnow()
        if result.success and payment.order.status == OrderStatus.PENDING:
            payment.order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def refund_payment(*args, **kwargs):
        """Refunds are gateway-specific and not yet wired up. Raised
        explicitly so a half-built refund flow can never silently no-op."""
        raise NotImplementedError(
            "Refund processing isn't implemented yet -- issue refunds directly "
            "from your gateway's dashboard for now."
        )
