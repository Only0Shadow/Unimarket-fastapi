"""Business logic for the shopping cart. Quantities are always capped at
the product's currently available stock."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.carts.models import Cart, CartItem
from app.products.models import Product


class CartError(Exception):
    """Raised for user-facing cart validation failures."""


def get_or_create_cart(db: Session, user: User) -> Cart:
    if user.cart is None:
        cart = Cart(customer_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        return cart
    return user.cart


def add_item(db: Session, user: User, product_id: int, quantity: int = 1) -> Cart:
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise CartError("This product is not available.")

    cart = get_or_create_cart(db, user)
    stmt = select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    existing = db.execute(stmt).scalar_one_or_none()

    new_quantity = (existing.quantity if existing else 0) + quantity
    if new_quantity > product.quantity_available:
        raise CartError(
            f"Only {product.quantity_available} unit(s) of '{product.name}' available."
        )

    if existing:
        existing.quantity = new_quantity
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product_id, quantity=new_quantity))

    db.commit()
    db.refresh(cart)
    return cart


def update_item_quantity(db: Session, user: User, item_id: int, quantity: int) -> Cart:
    cart = get_or_create_cart(db, user)
    item = db.get(CartItem, item_id)
    if item is None or item.cart_id != cart.id:
        raise CartError("Cart item not found.")

    if quantity == 0:
        db.delete(item)
    else:
        if quantity > item.product.quantity_available:
            raise CartError(
                f"Only {item.product.quantity_available} unit(s) of '{item.product.name}' available."
            )
        item.quantity = quantity

    db.commit()
    db.refresh(cart)
    return cart


def remove_item(db: Session, user: User, item_id: int) -> Cart:
    cart = get_or_create_cart(db, user)
    item = db.get(CartItem, item_id)
    if item and item.cart_id == cart.id:
        db.delete(item)
        db.commit()
    db.refresh(cart)
    return cart


def clear_cart(db: Session, user: User) -> Cart:
    cart = get_or_create_cart(db, user)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    db.refresh(cart)
    return cart
