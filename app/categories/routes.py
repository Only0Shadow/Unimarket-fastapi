"""Public-facing category routes (browsing categories and their products)."""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.categories import service as categories_service
from app.products import service as products_service

router = APIRouter(tags=["categories"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/categories", response_class=HTMLResponse)
def list_categories(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    categories = categories_service.list_active_categories(db)
    return templates.TemplateResponse(
        request, "products/categories.html", {"categories": categories, "user": user}
    )


@router.get("/categories/{slug}", response_class=HTMLResponse)
def category_detail(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
):
    category = categories_service.get_category_by_slug(db, slug)
    if category is None:
        return templates.TemplateResponse(
            request, "errors/404.html", {"user": user}, status_code=404
        )
    result = products_service.search_products(db, category_slug=slug, sort=sort, page=page)
    return templates.TemplateResponse(
        request,
        "products/category_detail.html",
        {"category": category, "page_obj": result, "user": user, "sort": sort},
    )
