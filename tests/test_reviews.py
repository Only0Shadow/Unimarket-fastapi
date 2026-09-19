"""Tests for the review system."""
from app.reviews.models import Review


def register(client, username, email, password="password123"):
    return client.post("/register", data={
        "first_name": "T", "last_name": "U", "username": username, "email": email,
        "password": password, "confirm_password": password,
    })


def _make_product(db_session):
    from tests.test_cart_and_orders import make_product
    return make_product(db_session, quantity=10, name="Reviewable Item")


def test_submitting_review_creates_record(client, db_session):
    product = _make_product(db_session)
    register(client, "reviewer1", "reviewer1@test.com")
    client.post(f"/products/{product.slug}/reviews", data={"rating": 5, "comment": "Great!"})

    review = db_session.query(Review).filter_by(product_id=product.id).first()
    assert review is not None
    assert review.rating == 5


def test_second_review_by_same_user_updates_not_duplicates(client, db_session):
    product = _make_product(db_session)
    register(client, "reviewer2", "reviewer2@test.com")
    client.post(f"/products/{product.slug}/reviews", data={"rating": 3, "comment": "Okay"})
    client.post(f"/products/{product.slug}/reviews", data={"rating": 5, "comment": "Actually great!"})

    reviews = db_session.query(Review).filter_by(product_id=product.id).all()
    assert len(reviews) == 1
    assert reviews[0].rating == 5


def test_rating_out_of_range_is_rejected():
    from app.reviews.schemas import ReviewIn
    import pytest

    with pytest.raises(Exception):
        ReviewIn(rating=6, comment="Too high")
    with pytest.raises(Exception):
        ReviewIn(rating=0, comment="Too low")
