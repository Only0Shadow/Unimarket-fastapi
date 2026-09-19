"""Tests for vendor application/approval workflow and product permissions."""
from app.auth.models import User, UserRole
from app.auth.security import hash_password
from app.users.models import Profile
from app.carts.models import Cart
from app.wishlists.models import Wishlist
from app.vendors.models import Vendor, VendorStatus
from app.categories.models import Category


def register_and_login(client, username, email, password="password123"):
    client.post("/register", data={
        "first_name": "T", "last_name": "U", "username": username, "email": email,
        "password": password, "confirm_password": password,
    })
    return client


def make_admin(db_session, username="admin", password="adminpass123"):
    admin = User(
        first_name="Admin", last_name="User", username=username, email=f"{username}@test.com",
        hashed_password=hash_password(password), role=UserRole.ADMIN, is_active=True,
    )
    db_session.add(admin)
    db_session.flush()
    db_session.add(Profile(user_id=admin.id))
    db_session.add(Cart(customer_id=admin.id))
    db_session.add(Wishlist(customer_id=admin.id))
    db_session.commit()
    return admin


def make_category(db_session, name="Food"):
    from app.utils import slugify
    c = Category(name=name, slug=slugify(name), is_active=True)
    db_session.add(c)
    db_session.commit()
    return c


def test_vendor_application_starts_pending(client, db_session):
    register_and_login(client, "vendoruser", "vendoruser@test.com")
    response = client.post("/vendor/apply", data={"store_name": "Test Store", "description": "desc"}, follow_redirects=False)
    assert response.status_code == 303
    vendor = db_session.query(Vendor).filter_by(store_slug="test-store").first()
    assert vendor is not None
    assert vendor.status == VendorStatus.PENDING


def test_unapproved_vendor_cannot_access_dashboard(client, db_session):
    register_and_login(client, "vendoruser2", "vendoruser2@test.com")
    client.post("/vendor/apply", data={"store_name": "Pending Store"})
    response = client.get("/vendor/dashboard")
    assert response.status_code == 403


def test_admin_can_approve_vendor(client, db_session):
    register_and_login(client, "vendoruser3", "vendoruser3@test.com")
    client.post("/vendor/apply", data={"store_name": "Approvable Store"})
    vendor = db_session.query(Vendor).filter_by(store_slug="approvable-store").first()

    admin_client = client
    admin_client.cookies.clear()
    make_admin(db_session)
    admin_client.post("/login", data={"identifier": "admin", "password": "adminpass123"})

    response = admin_client.post(f"/admin/vendors/{vendor.id}/status", data={"new_status": "approved"}, follow_redirects=False)
    assert response.status_code == 303

    db_session.refresh(vendor)
    assert vendor.status == VendorStatus.APPROVED


def test_student_cannot_create_product(client, db_session):
    register_and_login(client, "student_no_vendor", "snv@test.com")
    category = make_category(db_session)
    response = client.post("/vendor/products/new", data={
        "name": "Illicit Product", "category_id": category.id, "price": 100, "quantity_available": 5,
    })
    assert response.status_code == 403


def test_negative_price_is_rejected(db_session):
    """Product schema validation should reject negative prices before hitting the DB."""
    from app.products.schemas import ProductIn
    import pytest

    with pytest.raises(Exception):
        ProductIn(name="Bad Product", category_id=1, price=-10, quantity_available=5)
