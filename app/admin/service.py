"""Business logic backing the admin dashboard and moderation actions."""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.vendors.models import Vendor, VendorStatus
from app.products.models import Product
from app.categories.models import Category
from app.orders.models import Order, OrderStatus
from app.reviews.models import Review


def platform_stats(db: Session) -> dict:
    total_users = db.execute(select(func.count(User.id))).scalar_one()
    total_customers = db.execute(
        select(func.count(User.id)).where(User.role == UserRole.STUDENT)
    ).scalar_one()
    total_vendors = db.execute(select(func.count(Vendor.id))).scalar_one()
    total_products = db.execute(select(func.count(Product.id))).scalar_one()
    active_products = db.execute(
        select(func.count(Product.id)).where(Product.is_active.is_(True))
    ).scalar_one()
    total_orders = db.execute(select(func.count(Order.id))).scalar_one()
    pending_vendor_applications = db.execute(
        select(func.count(Vendor.id)).where(Vendor.status == VendorStatus.PENDING)
    ).scalar_one()
    pending_orders = db.execute(
        select(func.count(Order.id)).where(
            Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
        )
    ).scalar_one()
    total_categories = db.execute(select(func.count(Category.id))).scalar_one()

    return {
        "total_users": total_users,
        "total_customers": total_customers,
        "total_vendors": total_vendors,
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "pending_vendor_applications": pending_vendor_applications,
        "pending_orders": pending_orders,
        "total_categories": total_categories,
    }


def list_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.created_at.desc())).scalars())


def list_vendors(db: Session) -> list[Vendor]:
    return list(db.execute(select(Vendor).order_by(Vendor.created_at.desc())).scalars())


def list_all_orders(db: Session) -> list[Order]:
    return list(db.execute(select(Order).order_by(Order.created_at.desc())).scalars())


def list_all_reviews(db: Session) -> list[Review]:
    return list(db.execute(select(Review).order_by(Review.created_at.desc())).scalars())


def toggle_user_active(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


def set_review_approved(db: Session, review_id: int, approved: bool) -> Review | None:
    review = db.get(Review, review_id)
    if review is None:
        return None
    review.is_approved = approved
    db.commit()
    db.refresh(review)
    return review


def recent_activity(db: Session, limit: int = 15) -> list[dict]:
    """A lightweight merged activity feed: recent orders and recent vendor
    applications, sorted by time. Kept simple rather than a dedicated
    audit-log table, which is a reasonable future enhancement."""
    events = []
    for order in db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(limit)
    ).scalars():
        events.append({
            "type": "order",
            "message": f"Order {order.order_number} placed by {order.customer.username}",
            "timestamp": order.created_at,
        })
    for vendor in db.execute(
        select(Vendor).order_by(Vendor.created_at.desc()).limit(limit)
    ).scalars():
        events.append({
            "type": "vendor",
            "message": f"Vendor application: {vendor.store_name} ({vendor.status.value})",
            "timestamp": vendor.created_at,
        })
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]
