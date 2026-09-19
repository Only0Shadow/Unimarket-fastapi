"""Admin dashboard and moderation routes. All require require_admin."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_admin
from app.admin import service as admin_service
from app.vendors.models import VendorStatus
from app.vendors import service as vendors_service
from app.categories import service as categories_service
from app.categories.schemas import CategoryIn
from app.orders import service as orders_service

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    stats = admin_service.platform_stats(db)
    activity = admin_service.recent_activity(db)
    return templates.TemplateResponse(
        request, "admin/dashboard.html", {"user": user, "stats": stats, "activity": activity}
    )


@router.get("/users", response_class=HTMLResponse)
def manage_users(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    users = admin_service.list_users(db)
    return templates.TemplateResponse(request, "admin/users.html", {"user": user, "users": users})


@router.post("/users/{user_id}/toggle-active")
def toggle_user(user_id: int, user=Depends(require_admin), db: Session = Depends(get_db)):
    admin_service.toggle_user_active(db, user_id)
    return RedirectResponse("/admin/users", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/vendors", response_class=HTMLResponse)
def manage_vendors(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    vendors = admin_service.list_vendors(db)
    return templates.TemplateResponse(request, "admin/vendors.html", {"user": user, "vendors": vendors})


@router.post("/vendors/{vendor_id}/status")
def set_vendor_status(
    vendor_id: int, new_status: str = Form(...), user=Depends(require_admin), db: Session = Depends(get_db)
):
    from app.vendors.models import Vendor
    vendor = db.get(Vendor, vendor_id)
    if vendor is not None:
        try:
            vendors_service.set_vendor_status(db, vendor, VendorStatus(new_status))
        except ValueError:
            pass
    return RedirectResponse("/admin/vendors", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/categories", response_class=HTMLResponse)
def manage_categories(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    categories = categories_service.list_all_categories(db)
    return templates.TemplateResponse(
        request, "admin/categories.html", {"user": user, "categories": categories, "error": None}
    )


@router.post("/categories")
def create_category(
    request: Request,
    user=Depends(require_admin),
    db: Session = Depends(get_db),
    name: str = Form(...),
    description: str = Form(""),
    image: str = Form(""),
):
    categories_service.create_category(
        db, CategoryIn(name=name, description=description or None, image=image or None)
    )
    return RedirectResponse("/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/categories/{category_id}/toggle-active")
def toggle_category(category_id: int, user=Depends(require_admin), db: Session = Depends(get_db)):
    from app.categories.models import Category
    category = db.get(Category, category_id)
    if category is not None:
        category.is_active = not category.is_active
        db.commit()
    return RedirectResponse("/admin/categories", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/orders", response_class=HTMLResponse)
def manage_orders(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    orders = admin_service.list_all_orders(db)
    return templates.TemplateResponse(request, "admin/orders.html", {"user": user, "orders": orders})


@router.post("/orders/{order_id}/status")
def set_order_status(
    order_id: int, new_status: str = Form(...), user=Depends(require_admin), db: Session = Depends(get_db)
):
    try:
        orders_service.update_status_as_admin(db, order_id, new_status)
    except orders_service.OrderError:
        pass
    return RedirectResponse("/admin/orders", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reviews", response_class=HTMLResponse)
def manage_reviews(request: Request, user=Depends(require_admin), db: Session = Depends(get_db)):
    reviews = admin_service.list_all_reviews(db)
    return templates.TemplateResponse(request, "admin/reviews.html", {"user": user, "reviews": reviews})


@router.post("/reviews/{review_id}/toggle-approved")
def toggle_review(review_id: int, user=Depends(require_admin), db: Session = Depends(get_db)):
    from app.reviews.models import Review
    review = db.get(Review, review_id)
    if review is not None:
        admin_service.set_review_approved(db, review_id, not review.is_approved)
    return RedirectResponse("/admin/reviews", status_code=status.HTTP_303_SEE_OTHER)
