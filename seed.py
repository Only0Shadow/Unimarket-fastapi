"""
Development seed data.

Run with:  python seed.py

Creates a handful of sample students, an admin, approved vendors with
products across several categories, and a few reviews -- enough to click
around the app locally without registering everything by hand. Safe to
re-run: it clears and recreates the SQLite dev database first.

No real financial information is created (see payments module).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import app.main  # noqa: F401  (imports every model so metadata is complete)
from app.database import Base, engine, SessionLocal
from app.auth.models import User, UserRole
from app.auth.security import hash_password
from app.users.models import Profile
from app.carts.models import Cart
from app.wishlists.models import Wishlist
from app.vendors.models import Vendor, VendorStatus
from app.categories.models import Category
from app.products.models import Product, ProductCondition
from app.reviews.models import Review
from app.utils import slugify


def make_user(db, first, last, username, email, password, role=UserRole.STUDENT):
    user = User(
        first_name=first, last_name=last, username=username, email=email,
        hashed_password=hash_password(password), role=role, is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id, university="University of Lagos"))
    db.add(Cart(customer_id=user.id))
    db.add(Wishlist(customer_id=user.id))
    return user


def main():
    print("Resetting database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("Creating admin...")
    admin = make_user(db, "Admin", "User", "admin", "admin@unimarket.test", "adminpass123", UserRole.ADMIN)

    print("Creating students...")
    noble = make_user(db, "Noble", "Adebayo", "noble", "noble@unimarket.test", "password123")
    amara = make_user(db, "Amara", "Chukwu", "amara", "amara@unimarket.test", "password123")

    print("Creating vendors...")
    v1_owner = make_user(db, "Tunde", "Okafor", "tundeeats", "tunde@unimarket.test", "password123", UserRole.VENDOR)
    v2_owner = make_user(db, "Zainab", "Bello", "zainabooks", "zainab@unimarket.test", "password123", UserRole.VENDOR)
    db.flush()

    vendor1 = Vendor(
        owner_id=v1_owner.id, store_name="Tunde's Kitchen", store_slug="tundes-kitchen",
        description="Home-style campus meals, snacks and drinks.", status=VendorStatus.APPROVED,
        contact_email=v1_owner.email,
    )
    vendor2 = Vendor(
        owner_id=v2_owner.id, store_name="Zainab Books & Stationery", store_slug="zainab-books-stationery",
        description="Textbooks, past questions, and stationery for every department.",
        status=VendorStatus.APPROVED, contact_email=v2_owner.email,
    )
    db.add_all([vendor1, vendor2])
    db.flush()

    print("Creating categories...")
    categories_data = [
        ("Food", "Home-cooked meals and campus food."),
        ("Snacks", "Chips, biscuits, and quick bites."),
        ("Drinks", "Soft drinks, juices, and water."),
        ("Textbooks", "Course textbooks and past questions."),
        ("Electronics", "Phone and laptop accessories."),
        ("Hostel Supplies", "Everything for hostel living."),
        ("Fashion", "Clothing, shoes, and accessories."),
        ("Stationery", "Pens, notebooks, and printing materials."),
    ]
    categories = {}
    for name, desc in categories_data:
        c = Category(name=name, slug=slugify(name), description=desc, is_active=True)
        db.add(c)
        db.flush()
        categories[name] = c

    print("Creating products...")
    products_data = [
        (vendor1, "Food", "Jollof Rice & Chicken", "Freshly made jollof rice with grilled chicken.", 1500, 1800, 30, "new"),
        (vendor1, "Snacks", "Meat Pie (Pack of 3)", "Golden, flaky meat pies.", 900, None, 40, "new"),
        (vendor1, "Drinks", "Chilled Zobo (1L)", "Homemade hibiscus drink, chilled.", 700, None, 25, "new"),
        (vendor1, "Food", "Fried Rice Combo", "Fried rice with coleslaw and turkey.", 2000, None, 15, "new"),
        (vendor2, "Textbooks", "Intro to Microeconomics (5th Ed)", "Lightly used, no markings.", 6500, 9000, 4, "used"),
        (vendor2, "Textbooks", "Organic Chemistry Past Questions", "Compiled past questions with solutions.", 1200, None, 50, "new"),
        (vendor2, "Stationery", "80-Leaf Notebooks (Pack of 5)", "Ruled notebooks for lectures.", 2500, 3000, 60, "new"),
        (vendor2, "Electronics", "Phone Charging Cable (Type-C)", "Durable 1m fast-charging cable.", 1800, None, 3, "new"),
        (vendor2, "Hostel Supplies", "Reading Lamp (Rechargeable)", "USB-rechargeable LED reading lamp.", 4500, 5200, 0, "new"),
        (vendor2, "Fashion", "Departmental Hoodie (Unisex)", "Comfortable fleece hoodie.", 8000, None, 12, "new"),
    ]
    created_products = []
    for vendor, cat_name, name, desc, price, prev_price, qty, condition in products_data:
        p = Product(
            name=name, slug=slugify(name), description=desc, short_description=desc[:80],
            category_id=categories[cat_name].id, vendor_id=vendor.id, price=price,
            previous_price=prev_price, quantity_available=qty, condition=ProductCondition(condition),
            is_featured=(prev_price is not None), is_active=True,
        )
        db.add(p)
        created_products.append(p)
    db.flush()

    print("Creating sample reviews...")
    db.add(Review(user_id=noble.id, product_id=created_products[0].id, rating=5, comment="Best jollof on campus!"))
    db.add(Review(user_id=amara.id, product_id=created_products[0].id, rating=4, comment="Really good, slightly pricey."))
    db.add(Review(user_id=noble.id, product_id=created_products[4].id, rating=5, comment="Saved me so much money vs. the bookstore."))

    db.commit()
    db.close()

    print("\nSeed data created successfully.")
    print("Login credentials:")
    print("  Admin:   username=admin      password=adminpass123")
    print("  Student: username=noble      password=password123")
    print("  Student: username=amara      password=password123")
    print("  Vendor:  username=tundeeats  password=password123")
    print("  Vendor:  username=zainabooks password=password123")


if __name__ == "__main__":
    main()
