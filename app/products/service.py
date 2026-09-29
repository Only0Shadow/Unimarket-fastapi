"""
Product business logic: public search/filter/sort/pagination, vendor CRUD,
and the various homepage query helpers (featured/popular/latest/deals).
"""
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, joinedload

from app.products.models import Product, ProductCondition
from app.products.schemas import ProductIn
from app.categories.models import Category
from app.vendors.models import Vendor, VendorStatus
from app.reviews.models import Review
from app.utils import slugify, unique_slug, Page
from app.config import get_settings

settings = get_settings()


class ProductError(Exception):
    """Raised for user-facing product validation/ownership failures."""


def _publicly_visible_base_stmt():
    """Products visible to the public: active, and belonging to an approved vendor."""
    return (
        select(Product)
        .join(Vendor, Product.vendor_id == Vendor.id)
        .where(Product.is_active.is_(True), Vendor.status == VendorStatus.APPROVED)
        .distinct(Product.id)
    )


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    stmt = _publicly_visible_base_stmt().where(Product.slug == slug)
    return db.execute(stmt).unique().scalar_one_or_none()


def get_product_owned(db: Session, product_id: int, vendor_id: int) -> Product | None:
    """Fetch a product only if it belongs to the given vendor (ownership check)."""
    stmt = select(Product).where(Product.id == product_id, Product.vendor_id == vendor_id)
    return db.execute(stmt).scalar_one_or_none()


def list_vendor_products(db: Session, vendor_id: int) -> list[Product]:
    stmt = select(Product).where(Product.vendor_id == vendor_id).order_by(Product.created_at.desc())
    return list(db.execute(stmt).scalars())


def search_products(
    db: Session,
    query: str | None = None,
    category_slug: str | None = None,
    vendor_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    condition: str | None = None,
    min_rating: float | None = None,
    in_stock_only: bool = False,
    sort: str = "newest",
    page: int = 1,
    page_size: int | None = None,
) -> Page:
    """
    Core catalog query backing /shop, /search, category pages, and store pages.
    Supports search-by-text, multi-field filtering, sorting, and pagination.
    """
    page_size = page_size or settings.default_page_size
    stmt = _publicly_visible_base_stmt()

    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.join(Category, Product.category_id == Category.id).where(
            or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
                Product.short_description.ilike(like),
                Product.brand.ilike(like),
                Category.name.ilike(like),
                Vendor.store_name.ilike(like),
            )
        )

    if category_slug:
        stmt = stmt.join(Category, Product.category_id == Category.id).where(
            Category.slug == category_slug
        )

    if vendor_id:
        stmt = stmt.where(Product.vendor_id == vendor_id)

    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)

    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)

    if condition:
        try:
            stmt = stmt.where(Product.condition == ProductCondition(condition))
        except ValueError:
            pass

    if in_stock_only:
        stmt = stmt.where(Product.quantity_available > 0)

    # Sorting
    if sort == "price_low":
        stmt = stmt.order_by(Product.price.asc())
    elif sort == "price_high":
        stmt = stmt.order_by(Product.price.desc())
    elif sort == "oldest":
        stmt = stmt.order_by(Product.created_at.asc())
    elif sort == "popularity":
        # Popularity proxied by review count until order analytics are added.
        stmt = (
            stmt.outerjoin(Review, Review.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.count(Review.id).desc())
        )
    elif sort == "rating":
        stmt = (
            stmt.outerjoin(Review, Review.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.coalesce(func.avg(Review.rating), 0).desc())
        )
    else:  # newest (default)
        stmt = stmt.order_by(Product.created_at.desc())

    # Count total distinct products matching filters (before pagination).
    # Select only the primary key into the subquery so the count doesn't
    # drag along every joined column (which previously produced a spurious
    # cartesian-product warning).
    count_subquery = stmt.distinct().with_only_columns(Product.id).subquery()
    count_stmt = select(func.count()).select_from(count_subquery)
    total = db.execute(count_stmt).scalar_one()

    stmt = stmt.distinct().offset((page - 1) * page_size).limit(page_size)
    items = list(db.execute(stmt).unique().scalars())

    # Minimum-rating filter applied in Python since it depends on the
    # computed average_rating property (kept simple rather than a HAVING
    # clause across two different sort paths).
    if min_rating:
        items = [p for p in items if p.average_rating >= min_rating]

    return Page(items=items, page=page, page_size=page_size, total=total)


def featured_products(db: Session, limit: int = 8) -> list[Product]:
    stmt = _publicly_visible_base_stmt().where(Product.is_featured.is_(True)).order_by(
        Product.created_at.desc()
    ).limit(limit)
    return list(db.execute(stmt).unique().scalars())


def latest_products(db: Session, limit: int = 8) -> list[Product]:
    stmt = _publicly_visible_base_stmt().order_by(Product.created_at.desc()).limit(limit)
    return list(db.execute(stmt).unique().scalars())


def deals_products(db: Session, limit: int = 8) -> list[Product]:
    stmt = _publicly_visible_base_stmt().where(
        Product.previous_price.is_not(None), Product.previous_price > Product.price
    ).order_by(Product.updated_at.desc()).limit(limit)
    return list(db.execute(stmt).unique().scalars())


def related_products(db: Session, product: Product, limit: int = 4) -> list[Product]:
    stmt = _publicly_visible_base_stmt().where(
        Product.category_id == product.category_id, Product.id != product.id
    ).limit(limit)
    return list(db.execute(stmt).unique().scalars())


def create_product(db: Session, vendor: "Vendor", data: ProductIn) -> Product:
    base_slug = slugify(data.name)
    slug = unique_slug(
        base_slug,
        lambda s: db.execute(select(Product).where(Product.slug == s)).scalar_one_or_none()
        is not None,
    )
    product = Product(
        name=data.name,
        slug=slug,
        description=data.description,
        short_description=data.short_description,
        category_id=data.category_id,
        vendor_id=vendor.id,
        price=data.price,
        previous_price=data.previous_price,
        quantity_available=data.quantity_available,
        brand=data.brand,
        condition=ProductCondition(data.condition),
        image=data.image,
        is_featured=data.is_featured,
        is_active=data.is_active,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product: Product, data: ProductIn) -> Product:
    product.name = data.name
    product.description = data.description
    product.short_description = data.short_description
    product.category_id = data.category_id
    product.price = data.price
    product.previous_price = data.previous_price
    product.quantity_available = data.quantity_available
    product.brand = data.brand
    product.condition = ProductCondition(data.condition)
    product.image = data.image
    product.is_featured = data.is_featured
    product.is_active = data.is_active
    db.commit()
    db.refresh(product)
    return product


def archive_product(db: Session, product: Product) -> Product:
    product.is_active = False
    db.commit()
    db.refresh(product)
    return product


def decrement_stock(db: Session, product: Product, quantity: int) -> None:
    """Safely decrement stock; raises if insufficient. Caller must be inside
    a transaction that will be committed/rolled back atomically with the
    related order creation."""
    if product.quantity_available < quantity:
        raise ProductError(f"Insufficient stock for '{product.name}'.")
    product.quantity_available -= quantity
