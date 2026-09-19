"""Routes for submitting a review from a product detail page."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.products import service as products_service
from app.reviews.schemas import ReviewIn
from app.reviews import service as reviews_service

router = APIRouter(prefix="/products", tags=["reviews"])


@router.post("/{slug}/reviews")
def submit_review(
    slug: str,
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    rating: int = Form(...),
    comment: str = Form(""),
):
    product = products_service.get_product_by_slug(db, slug)
    if product is None:
        return RedirectResponse("/shop", status_code=status.HTTP_303_SEE_OTHER)
    try:
        data = ReviewIn(rating=rating, comment=comment or None)
        reviews_service.submit_review(db, user, product, data)
    except ValidationError:
        pass  # Redirect back regardless; the product page re-renders the review form.
    return RedirectResponse(f"/products/{slug}", status_code=status.HTTP_303_SEE_OTHER)
