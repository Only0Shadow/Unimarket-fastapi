"""Business logic for creating/editing product reviews."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.products.models import Product
from app.reviews.models import Review
from app.reviews.schemas import ReviewIn


class ReviewError(Exception):
    """Raised for user-facing review validation failures."""


def get_user_review(db: Session, user: User, product: Product) -> Review | None:
    stmt = select(Review).where(Review.user_id == user.id, Review.product_id == product.id)
    return db.execute(stmt).scalar_one_or_none()


def submit_review(db: Session, user: User, product: Product, data: ReviewIn) -> Review:
    """Create a new review, or update the user's existing review for this
    product (one review per user per product, editable)."""
    existing = get_user_review(db, user, product)
    if existing:
        existing.rating = data.rating
        existing.comment = data.comment
        db.commit()
        db.refresh(existing)
        return existing

    review = Review(user_id=user.id, product_id=product.id, rating=data.rating, comment=data.comment)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_for_product(db: Session, product: Product) -> list[Review]:
    stmt = (
        select(Review)
        .where(Review.product_id == product.id, Review.is_approved.is_(True))
        .order_by(Review.created_at.desc())
    )
    return list(db.execute(stmt).scalars())
