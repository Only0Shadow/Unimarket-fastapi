"""Routes for viewing and mutating the wishlist."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.wishlists import service as wishlists_service

router = APIRouter(prefix="/wishlist", tags=["wishlist"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def view_wishlist(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    wishlist = wishlists_service.get_or_create_wishlist(db, user)
    return templates.TemplateResponse(request, "wishlist/wishlist.html", {"wishlist": wishlist, "user": user})


@router.post("/add")
def add_to_wishlist(
    product_id: int = Form(...),
    next: str = Form("/wishlist"),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        wishlists_service.add_item(db, user, product_id)
    except wishlists_service.WishlistError:
        pass
    return RedirectResponse(next, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/remove")
def remove_from_wishlist(item_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    wishlists_service.remove_item(db, user, item_id)
    return RedirectResponse("/wishlist", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/items/{item_id}/move-to-cart")
def move_to_cart(item_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    try:
        wishlists_service.move_to_cart(db, user, item_id)
    except wishlists_service.WishlistError:
        pass
    return RedirectResponse("/cart", status_code=status.HTTP_303_SEE_OTHER)
