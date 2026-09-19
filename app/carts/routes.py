"""Routes for viewing and mutating the shopping cart."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.carts import service as carts_service
from app.config import get_settings

router = APIRouter(prefix="/cart", tags=["cart"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("", response_class=HTMLResponse)
def view_cart(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    cart = carts_service.get_or_create_cart(db, user)
    estimated_total = round(cart.subtotal + settings.delivery_fee_estimate, 2) if cart.items else 0
    return templates.TemplateResponse(
        request,
        "cart/cart.html",
        {"cart": cart, "user": user, "delivery_fee": settings.delivery_fee_estimate, "estimated_total": estimated_total},
    )


@router.post("/add")
def add_to_cart(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    product_id: int = Form(...),
    quantity: int = Form(1),
    next: str = Form("/cart"),
):
    try:
        carts_service.add_item(db, user, product_id, quantity)
    except carts_service.CartError:
        pass  # Non-fatal: user is redirected back to see current cart/stock state.
    return RedirectResponse(next, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/update")
def update_item(
    item_id: int,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    quantity: int = Form(...),
):
    try:
        carts_service.update_item_quantity(db, user, item_id, quantity)
    except carts_service.CartError:
        pass
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/remove")
def remove_item(item_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    carts_service.remove_item(db, user, item_id)
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/clear")
def clear_cart(user=Depends(require_user), db: Session = Depends(get_db)):
    carts_service.clear_cart(db, user)
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)
