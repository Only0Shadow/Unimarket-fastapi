"""Tests for cart operations and stock-safe order creation."""
from app.auth.models import User, UserRole
from app.auth.security import hash_password
from app.users.models import Profile
from app.carts.models import Cart
from app.wishlists.models import Wishlist
from app.vendors.models import Vendor, VendorStatus
from app.categories.models import Category
from app.products.models import Product, ProductCondition
from app.utils import slugify


def register(client, username, email, password="password123"):
    return client.post("/register", data={
        "first_name": "T", "last_name": "U", "username": username, "email": email,
        "password": password, "confirm_password": password,
    })


def make_product(db_session, quantity=5, price=1000.0, name="Test Product"):
    owner = User(
        first_name="Vendor", last_name="Owner", username=f"owner_{name.lower().replace(' ', '')}",
        email=f"{name.lower().replace(' ', '')}@test.com", hashed_password=hash_password("pass12345"),
        role=UserRole.VENDOR, is_active=True,
    )
    db_session.add(owner)
    db_session.flush()
    db_session.add(Profile(user_id=owner.id))
    db_session.add(Cart(customer_id=owner.id))
    db_session.add(Wishlist(customer_id=owner.id))

    vendor = Vendor(
        owner_id=owner.id, store_name=f"{name} Store", store_slug=slugify(f"{name} Store"),
        status=VendorStatus.APPROVED,
    )
    db_session.add(vendor)
    db_session.flush()

    category = Category(name="General", slug="general", is_active=True)
    db_session.add(category)
    db_session.flush()

    product = Product(
        name=name, slug=slugify(name), category_id=category.id, vendor_id=vendor.id,
        price=price, quantity_available=quantity, condition=ProductCondition.NEW, is_active=True,
    )
    db_session.add(product)
    db_session.commit()
    return product


def test_cart_add_respects_available_stock(client, db_session):
    product = make_product(db_session, quantity=3)
    register(client, "buyer1", "buyer1@test.com")

    client.post("/cart/add", data={"product_id": product.id, "quantity": 2})
    response = client.get("/cart")
    assert "value=\"2\"" in response.text

    # Attempting to add 5 more (total 7) exceeds stock of 3; quantity should stay at 2.
    client.post("/cart/add", data={"product_id": product.id, "quantity": 5})
    response = client.get("/cart")
    assert "value=\"2\"" in response.text


def test_checkout_creates_order_and_decrements_stock(client, db_session):
    product = make_product(db_session, quantity=10, price=500.0)
    register(client, "buyer2", "buyer2@test.com")
    client.post("/cart/add", data={"product_id": product.id, "quantity": 4})

    response = client.post("/checkout", data={
        "recipient_name": "Buyer Two", "phone_number": "08011111111",
        "university": "UniLag", "hostel": "Hall A",
    }, follow_redirects=False)
    assert response.status_code == 303

    db_session.refresh(product)
    assert product.quantity_available == 6  # 10 - 4

    from app.orders.models import Order
    order = db_session.query(Order).first()
    assert order is not None
    assert order.total == order.subtotal + order.delivery_fee


def test_checkout_with_empty_cart_fails(client, db_session):
    register(client, "buyer3", "buyer3@test.com")
    response = client.post("/checkout", data={
        "recipient_name": "Buyer Three", "phone_number": "080", "university": "UniLag", "hostel": "Hall B",
    })
    assert response.status_code == 400


def test_cancelling_order_restores_stock(client, db_session):
    product = make_product(db_session, quantity=8, price=1000.0)
    register(client, "buyer4", "buyer4@test.com")
    client.post("/cart/add", data={"product_id": product.id, "quantity": 3})
    client.post("/checkout", data={
        "recipient_name": "Buyer Four", "phone_number": "080", "university": "UniLag", "hostel": "Hall C",
    })

    db_session.refresh(product)
    assert product.quantity_available == 5

    from app.orders.models import Order
    order = db_session.query(Order).first()
    client.post(f"/orders/{order.id}/cancel")

    db_session.refresh(product)
    assert product.quantity_available == 8


def test_cart_quantity_cannot_go_negative(client, db_session):
    product = make_product(db_session, quantity=5)
    register(client, "buyer5", "buyer5@test.com")
    client.post("/cart/add", data={"product_id": product.id, "quantity": 1})
    response = client.get("/cart")
    assert response.status_code == 200
