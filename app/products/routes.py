"""Public-facing product browsing, search, and detail routes."""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.products import service as products_service
from app.reviews import service as reviews_service
from app.categories import service as categories_service
from app.vendors import service as vendors_service

router = APIRouter(tags=["products"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/shop", response_class=HTMLResponse)
def shop(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    q: str | None = Query(None),
    category: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    condition: str | None = Query(None),
    rating: float | None = Query(None),
    in_stock: bool = Query(False),
    sort: str = Query("newest"),
    page: int = Query(1, ge=1),
):
    result = products_service.search_products(
        db,
        query=q,
        category_slug=category,
        min_price=min_price,
        max_price=max_price,
        condition=condition,
        min_rating=rating,
        in_stock_only=in_stock,
        sort=sort,
        page=page,
    )
    categories = categories_service.list_active_categories(db)
    return templates.TemplateResponse(
        request,
        "products/shop.html",
        {
            "page_obj": result,
            "categories": categories,
            "user": user,
            "filters": {
                "q": q or "", "category": category or "", "min_price": min_price,
                "max_price": max_price, "condition": condition or "", "rating": rating,
                "in_stock": in_stock, "sort": sort,
            },
        },
    )


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    q: str = Query(""),
    page: int = Query(1, ge=1),
):
    result = products_service.search_products(db, query=q, page=page) if q.strip() else None
    return templates.TemplateResponse(
        request, "products/search_results.html", {"query": q, "page_obj": result, "user": user}
    )


@router.get("/products/{slug}", response_class=HTMLResponse)
def product_detail(
    slug: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    product = products_service.get_product_by_slug(db, slug)
    if product is None:
        return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)

    reviews = reviews_service.list_for_product(db, product)
    related = products_service.related_products(db, product)
    my_review = reviews_service.get_user_review(db, user, product) if user else None

    in_wishlist = False
    if user and user.wishlist:
        in_wishlist = any(item.product_id == product.id for item in user.wishlist.items)

    return templates.TemplateResponse(
        request,
        "products/detail.html",
        {
            "product": product,
            "reviews": reviews,
            "related": related,
            "user": user,
            "my_review": my_review,
            "in_wishlist": in_wishlist,
        },
    )
