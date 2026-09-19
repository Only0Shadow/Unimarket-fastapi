"""Business logic for the wishlist."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.wishlists.models import Wishlist, WishlistItem
from app.products.models import Product
from app.carts import service as carts_service


class WishlistError(Exception):
    """Raised for user-facing wishlist validation failures."""


def get_or_create_wishlist(db: Session, user: User) -> Wishlist:
    if user.wishlist is None:
        wishlist = Wishlist(customer_id=user.id)
        db.add(wishlist)
        db.commit()
        db.refresh(wishlist)
        return wishlist
    return user.wishlist


def add_item(db: Session, user: User, product_id: int) -> Wishlist:
    product = db.get(Product, product_id)
    if product is None:
        raise WishlistError("Product not found.")

    wishlist = get_or_create_wishlist(db, user)
    stmt = select(WishlistItem).where(
        WishlistItem.wishlist_id == wishlist.id, WishlistItem.product_id == product_id
    )
    if db.execute(stmt).scalar_one_or_none() is None:
        db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
        db.commit()
    db.refresh(wishlist)
    return wishlist


def remove_item(db: Session, user: User, item_id: int) -> Wishlist:
    wishlist = get_or_create_wishlist(db, user)
    item = db.get(WishlistItem, item_id)
    if item and item.wishlist_id == wishlist.id:
        db.delete(item)
        db.commit()
    db.refresh(wishlist)
    return wishlist


def move_to_cart(db: Session, user: User, item_id: int) -> None:
    """Add the wishlist item's product to the cart, then remove it from the wishlist."""
    wishlist = get_or_create_wishlist(db, user)
    item = db.get(WishlistItem, item_id)
    if item is None or item.wishlist_id != wishlist.id:
        raise WishlistError("Wishlist item not found.")

    carts_service.add_item(db, user, item.product_id, quantity=1)
    db.delete(item)
    db.commit()
