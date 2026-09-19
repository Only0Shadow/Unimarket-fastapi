"""
Order business logic.

Order creation is the one place in the app that must be genuinely
transactional: cart items are converted to order items, stock is
decremented, and a pending Payment record is attached -- all inside a
single database transaction. If any item has insufficient stock, the
whole order is rejected and nothing is written.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.carts.models import Cart
from app.carts import service as carts_service
from app.products.models import Product
from app.orders.models import Order, OrderItem, OrderStatus, CANCELLABLE_STATUSES
from app.orders.schemas import CheckoutIn
from app.payments.service import PaymentService
from app.notifications.service import notify
from app.config import get_settings

settings = get_settings()


class OrderError(Exception):
    """Raised for user-facing order validation failures (e.g. out of stock)."""


def create_order_from_cart(db: Session, user: User, data: CheckoutIn) -> Order:
    cart = carts_service.get_or_create_cart(db, user)
    if not cart.items:
        raise OrderError("Your cart is empty.")

    # Validate stock for every item BEFORE writing anything, so a failure
    # partway through never leaves a half-decremented order.
    for item in cart.items:
        product = item.product
        if not product.is_active:
            raise OrderError(f"'{product.name}' is no longer available.")
        if item.quantity > product.quantity_available:
            raise OrderError(
                f"Only {product.quantity_available} unit(s) of '{product.name}' left in stock."
            )

    subtotal = cart.subtotal
    delivery_fee = settings.delivery_fee_estimate
    total = round(subtotal + delivery_fee, 2)

    order = Order(
        customer_id=user.id,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total,
        status=OrderStatus.PENDING,
        recipient_name=data.recipient_name,
        phone_number=data.phone_number,
        university=data.university,
        hostel=data.hostel,
        block=data.block,
        room=data.room,
        campus_location=data.campus_location,
        delivery_instructions=data.delivery_instructions,
    )
    db.add(order)
    db.flush()  # get order.id for order items

    for item in cart.items:
        product = item.product
        # Re-check and decrement atomically within this same transaction.
        if item.quantity > product.quantity_available:
            db.rollback()
            raise OrderError(f"'{product.name}' went out of stock while placing your order.")
        product.quantity_available -= item.quantity

        db.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            unit_price=product.price,
            quantity=item.quantity,
            subtotal=item.subtotal,
        ))

    # Attach a pending Payment record -- no money moves until checkout
    # actively starts a gateway session.
    PaymentService.create_placeholder_for_order(db, order)

    # Clear the cart now that its contents have become an order.
    for item in list(cart.items):
        db.delete(item)

    notify(db, user, "Order placed", f"Your order {order.order_number} has been received.")

    db.commit()
    db.refresh(order)
    return order


def list_orders_for_customer(db: Session, user: User) -> list[Order]:
    stmt = select(Order).where(Order.customer_id == user.id).order_by(Order.created_at.desc())
    return list(db.execute(stmt).scalars())


def get_order_for_customer(db: Session, user: User, order_id: int) -> Order | None:
    order = db.get(Order, order_id)
    if order is None or order.customer_id != user.id:
        return None
    return order


def cancel_order(db: Session, user: User, order_id: int) -> Order:
    order = get_order_for_customer(db, user, order_id)
    if order is None:
        raise OrderError("Order not found.")
    if order.status not in CANCELLABLE_STATUSES:
        raise OrderError("This order can no longer be cancelled.")

    # Restore stock for every item.
    for item in order.items:
        item.product.quantity_available += item.quantity

    order.status = OrderStatus.CANCELLED
    notify(db, user, "Order cancelled", f"Order {order.order_number} has been cancelled.")
    db.commit()
    db.refresh(order)
    return order


def list_orders_containing_vendor(db: Session, vendor_id: int) -> list[Order]:
    stmt = (
        select(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(Product.vendor_id == vendor_id)
        .order_by(Order.created_at.desc())
        .distinct()
    )
    return list(db.execute(stmt).unique().scalars())


# Statuses a vendor is permitted to move an order into. Cancellation remains
# a customer/admin action; vendors only progress fulfillment forward.
VENDOR_ALLOWED_TRANSITIONS = {
    OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.READY,
    OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED,
}


def update_status_as_vendor(db: Session, vendor_id: int, order_id: int, new_status: str) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise OrderError("Order not found.")
    owns_item = any(item.product.vendor_id == vendor_id for item in order.items)
    if not owns_item:
        raise OrderError("You do not have permission to update this order.")

    try:
        target = OrderStatus(new_status)
    except ValueError:
        raise OrderError("Invalid order status.")

    if target not in VENDOR_ALLOWED_TRANSITIONS:
        raise OrderError("Vendors cannot set this status.")

    order.status = target
    notify(
        db, order.customer, "Order status updated",
        f"Order {order.order_number} is now '{target.value.replace('_', ' ')}'.",
    )
    db.commit()
    db.refresh(order)
    return order


def update_status_as_admin(db: Session, order_id: int, new_status: str) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise OrderError("Order not found.")
    try:
        target = OrderStatus(new_status)
    except ValueError:
        raise OrderError("Invalid order status.")

    if target == OrderStatus.CANCELLED and order.status != OrderStatus.CANCELLED:
        for item in order.items:
            item.product.quantity_available += item.quantity

    order.status = target
    notify(
        db, order.customer, "Order status updated",
        f"Order {order.order_number} is now '{target.value.replace('_', ' ')}'.",
    )
    db.commit()
    db.refresh(order)
    return order
