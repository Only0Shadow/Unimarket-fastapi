"""Small shared utilities used across feature modules."""
import re
import uuid


def slugify(value: str) -> str:
    """Turn a string into a URL-safe slug, e.g. 'Fresh Jollof Rice!' -> 'fresh-jollof-rice'."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or uuid.uuid4().hex[:8]


def unique_slug(base_slug: str, exists_fn) -> str:
    """Append a short suffix if base_slug is already taken, using exists_fn(slug) -> bool."""
    slug = base_slug
    counter = 2
    while exists_fn(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class Page:
    """Simple pagination container passed to templates."""

    def __init__(self, items: list, page: int, page_size: int, total: int):
        self.items = items
        self.page = page
        self.page_size = page_size
        self.total = total
        self.total_pages = max(1, (total + page_size - 1) // page_size)
        self.has_previous = page > 1
        self.has_next = page < self.total_pages
