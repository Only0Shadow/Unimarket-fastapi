"""Business logic for category CRUD (admin-managed) and public listing."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.categories.models import Category
from app.categories.schemas import CategoryIn
from app.utils import slugify, unique_slug


def list_active_categories(db: Session) -> list[Category]:
    stmt = select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    return list(db.execute(stmt).scalars())


def list_all_categories(db: Session) -> list[Category]:
    return list(db.execute(select(Category).order_by(Category.name)).scalars())


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    return db.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()


def create_category(db: Session, data: CategoryIn) -> Category:
    base_slug = slugify(data.name)
    slug = unique_slug(
        base_slug, lambda s: get_category_by_slug(db, s) is not None
    )
    category = Category(
        name=data.name,
        slug=slug,
        description=data.description,
        image=data.image,
        is_active=data.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, data: CategoryIn) -> Category:
    category.name = data.name
    category.description = data.description
    category.image = data.image
    category.is_active = data.is_active
    db.commit()
    db.refresh(category)
    return category
