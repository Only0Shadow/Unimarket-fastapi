"""Business logic for vendor applications, store management, and dashboard stats."""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.vendors.models import Vendor, VendorStatus
from app.vendors.schemas import VendorApplyIn, VendorUpdateIn
from app.utils import slugify, unique_slug
from app.notifications.service import notify


class VendorError(Exception):
    """Raised for user-facing vendor workflow failures."""


def get_vendor_by_slug(db: Session, slug: str) -> Vendor | None:
    return db.execute(select(Vendor).where(Vendor.store_slug == slug)).scalar_one_or_none()


def list_approved_vendors(db: Session) -> list[Vendor]:
    stmt = select(Vendor).where(Vendor.status == VendorStatus.APPROVED).order_by(Vendor.store_name)
    return list(db.execute(stmt).scalars())


def apply_as_vendor(db: Session, user: User, data: VendorApplyIn) -> Vendor:
    if user.vendor is not None:
        raise VendorError("You already have a vendor application on file.")

    base_slug = slugify(data.store_name)
    slug = unique_slug(base_slug, lambda s: get_vendor_by_slug(db, s) is not None)

    vendor = Vendor(
        owner_id=user.id,
        store_name=data.store_name,
        store_slug=slug,
        description=data.description,
        contact_email=data.contact_email or user.email,
        contact_phone=data.contact_phone or user.phone_number,
        status=VendorStatus.PENDING,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def update_store(db: Session, vendor: Vendor, data: VendorUpdateIn) -> Vendor:
    vendor.store_name = data.store_name
    vendor.description = data.description
    vendor.logo = data.logo
    vendor.banner = data.banner
    vendor.contact_email = data.contact_email
    vendor.contact_phone = data.contact_phone
    db.commit()
    db.refresh(vendor)
    return vendor


def set_vendor_status(db: Session, vendor: Vendor, new_status: VendorStatus) -> Vendor:
    vendor.status = new_status
    if new_status == VendorStatus.APPROVED:
        vendor.owner.role = UserRole.VENDOR
        notify(db, vendor.owner, "Vendor application approved",
               f"Congratulations! Your store '{vendor.store_name}' is now live.")
    elif new_status == VendorStatus.REJECTED:
        notify(db, vendor.owner, "Vendor application rejected",
               f"Your application for '{vendor.store_name}' was not approved.")
    elif new_status == VendorStatus.SUSPENDED:
        notify(db, vendor.owner, "Vendor account suspended",
               f"Your store '{vendor.store_name}' has been suspended by an administrator.")
    db.commit()
    db.refresh(vendor)
    return vendor


def dashboard_stats(db: Session, vendor: Vendor) -> dict:
    """Order-value statistics for a vendor. Since payments are disabled, these
    reflect order totals, NOT settled/collected earnings."""
    from app.products.models import Product
    from app.orders.models import OrderItem, Order, OrderStatus

    total_products = db.execute(
        select(func.count(Product.id)).where(Product.vendor_id == vendor.id)
    ).scalar_one()

    active_products = db.execute(
        select(func.count(Product.id)).where(
            Product.vendor_id == vendor.id, Product.is_active.is_(True)
        )
    ).scalar_one()

    low_stock_products = db.execute(
        select(func.count(Product.id)).where(
            Product.vendor_id == vendor.id, Product.quantity_available <= 5,
            Product.quantity_available > 0,
        )
    ).scalar_one()

    out_of_stock = db.execute(
        select(func.count(Product.id)).where(
            Product.vendor_id == vendor.id, Product.quantity_available == 0
        )
    ).scalar_one()

    order_item_stmt = (
        select(OrderItem)
        .join(Product, OrderItem.product_id == Product.id)
        .where(Product.vendor_id == vendor.id)
    )
    vendor_order_items = list(db.execute(order_item_stmt).scalars())

    order_ids = {item.order_id for item in vendor_order_items}
    total_orders = len(order_ids)

    pending_orders = 0
    completed_orders = 0
    if order_ids:
        orders = db.execute(select(Order).where(Order.id.in_(order_ids))).scalars()
        for order in orders:
            if order.status in (OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING,
                                 OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY):
                pending_orders += 1
            elif order.status == OrderStatus.DELIVERED:
                completed_orders += 1

    total_order_value = sum(item.subtotal for item in vendor_order_items)

    return {
        "total_products": total_products,
        "active_products": active_products,
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "total_order_value": total_order_value,
    }
