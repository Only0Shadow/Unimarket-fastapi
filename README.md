# University Marketplace — FastAPI Edition

A campus e-commerce platform where students browse and buy from
university/campus vendors — food, textbooks, electronics, fashion, and
general campus necessities — built with **FastAPI, SQLAlchemy, Pydantic,
Alembic, and Jinja2** (server-rendered HTML, no frontend framework).

> **Payments are intentionally disabled in this build.** Checkout creates a
> *pending order* and an inert payment placeholder record — no card details
> are collected, no gateway is contacted, and no money moves. See
> [Future payment integration](#future-payment-integration) below.

---

## 1. Project description

Students register, browse products by category or search, add items to a
cart or wishlist, and check out to create a pending order with delivery
details. Approved campus vendors manage their own store and product
catalog from a vendor dashboard and progress orders through fulfillment
statuses. Administrators approve vendors, manage categories, moderate
reviews, and oversee the whole platform from an admin dashboard.

## 2. Features

- **Auth**: registration, login/logout, bcrypt password hashing, signed
  session cookies, role-based access (student / vendor / admin)
- **Catalog**: categories, products with images/brand/condition/stock,
  full-text-ish search, filtering (price, category, vendor, condition,
  rating, in-stock), sorting (newest, price, popularity, rating), pagination
- **Cart & Wishlist**: stock-aware cart, duplicate-safe wishlist,
  move-to-cart
- **Orders**: transactional stock-safe checkout, order history/detail,
  customer cancellation with stock restoration, vendor fulfillment-status
  updates
- **Vendors**: apply-to-sell workflow, admin approval, store page, product
  CRUD, order-value dashboard stats (explicitly labeled as *order value*,
  not settled earnings, since payments are disabled)
- **Reviews**: 1–5 star ratings, one editable review per user per product
- **Notifications**: in-app only (order placed/updated, vendor
  approved/rejected/suspended)
- **Admin dashboard**: platform stats, user/vendor/category/order/review
  management
- **Payments**: fully inert placeholder module (see below)

## 3. Technologies

FastAPI · SQLAlchemy 2.x (declarative + typed `Mapped` columns) · Pydantic
v2 · Alembic · Jinja2 · vanilla HTML/CSS/JS · SQLite (dev) · pytest ·
passlib/bcrypt · itsdangerous (signed session cookies)

## 4. Folder structure

```
fastapi_version/
├── app/
│   ├── main.py, config.py, database.py, dependencies.py, utils.py
│   ├── auth/ users/ vendors/ categories/ products/ carts/ wishlists/
│   │   orders/ reviews/ notifications/ payments/ admin/
│   │   (each: models.py, schemas.py, service.py, routes.py)
│   ├── templates/   (Jinja2, extends base.html)
│   └── static/{css,js,images}/
├── migrations/        (Alembic)
├── tests/              (pytest)
├── seed.py
├── requirements.txt
├── .env.example
├── pytest.ini
├── alembic.ini
└── README.md
```

Each feature module follows the same shape: `models.py` (SQLAlchemy),
`schemas.py` (Pydantic validation), `service.py` (business logic, the only
place that touches the DB with real logic), `routes.py` (thin HTTP layer).

## 5. Installation

```bash
cd fastapi_version
python3 -m venv .venv
```

## 6. Virtual environment creation

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

## 7. Dependency installation

```bash
pip install -r requirements.txt
```

## 8. Environment variables

```bash
cp .env.example .env
```

Then edit `.env` — at minimum, change `SECRET_KEY` to a long random string
before any non-local deployment. Never commit a real `.env` file.

| Variable | Purpose |
|---|---|
| `APP_NAME` | Display name |
| `DEBUG` | Enables FastAPI debug mode |
| `SECRET_KEY` | Signs session cookies — must be secret in production |
| `DATABASE_URL` | SQLAlchemy connection string (SQLite by default) |
| `ALLOWED_HOSTS` | Reserved for future host-header validation |
| `SESSION_MAX_AGE` | Session cookie lifetime, seconds |
| `DELIVERY_FEE_ESTIMATE` | Flat delivery fee shown at checkout |

## 9. Database setup

SQLite is used for local development; the file is created automatically
(no separate "create database" step needed).

## 10. Database migrations

The app also calls `Base.metadata.create_all()` on startup as a local-dev
convenience, but Alembic is the source of truth for schema evolution:

```bash
alembic upgrade head          # apply all migrations
alembic revision --autogenerate -m "describe your change"   # after editing models
```

## 11. Seed data

```bash
python3 seed.py
```

Creates an admin, sample students, two approved vendors with products
across several categories, and a sample review. Prints login credentials
when done. Safe to re-run (rebuilds the dev database). Contains no real
financial information.

## 12. Running the development server

```bash
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000

## 13. Running tests

```bash
pytest
```

Covers registration/login, authorization boundaries, product creation and
permission checks, cart stock limits, transactional checkout and stock
decrement/restoration, review create-vs-update behavior, and vendor
approval workflow.

## 14. Default development/admin setup

After running `seed.py`:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | (printed by `seed.py`) |
| Student | `noble` | `password123` |
| Vendor | (see seed script output) | `password123` |

Change these before deploying anywhere beyond your own machine.

## 15. Known limitations

- **No real payments** — by design for this development phase (see below).
- Delivery fee is a flat estimate, not computed from an actual courier API.
- "Popularity" sort is proxied by review count; there's no order-volume
  analytics table yet.
- No email/SMS delivery for notifications — in-app only.
- Password reset has no email-delivery flow (architecture only).
- Single-currency (₦) display only.
- No image upload pipeline — product/logo images are stored as URLs.

## 16. Future payment integration location

Real payment processing (Paystack, Flutterwave, Stripe, etc.) should be
added inside `app/payments/`:

- `app/payments/models.py` — `PaymentPlaceholder` already tracks status
  (`NOT_STARTED → PENDING → PAID / FAILED / REFUNDED`) and has a reserved
  `gateway_reference` field.
- `app/payments/service.py` — `PaymentService.initiate_payment()`,
  `.verify_payment()`, and `.refund_payment()` are stub methods that
  currently raise `PaymentDisabledError`. Replace their bodies with real
  gateway calls when that phase begins — the rest of the app (checkout,
  order status, vendor dashboards) is already wired against this interface
  and won't need to change.
- `app/orders/service.py` calls `PaymentService.create_placeholder_for_order()`
  at checkout — this is the integration point for redirecting to a real
  payment step once gateways are enabled.

Do not implement real gateway calls without a full security, compliance,
and PCI-scope review — that's out of scope for this phase.
