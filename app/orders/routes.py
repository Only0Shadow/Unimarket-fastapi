"""Routes for checkout and order history/detail/cancellation."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.carts import service as carts_service
from app.orders.schemas import CheckoutIn
from app.orders import service as orders_service
from app.users import service as users_service
from app.config import get_settings

router = APIRouter(tags=["orders"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/checkout", response_class=HTMLResponse)
def checkout_form(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    cart = carts_service.get_or_create_cart(db, user)
    addresses = users_service.list_addresses(db, user)
    estimated_total = round(cart.subtotal + settings.delivery_fee_estimate, 2)
    return templates.TemplateResponse(
        request,
        "orders/checkout.html",
        {
            "cart": cart, "user": user, "addresses": addresses,
            "delivery_fee": settings.delivery_fee_estimate, "estimated_total": estimated_total,
            "error": None,
        },
    )


@router.post("/checkout")
def checkout_submit(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    recipient_name: str = Form(...),
    phone_number: str = Form(...),
    university: str = Form(...),
    hostel: str = Form(...),
    block: str = Form(""),
    room: str = Form(""),
    campus_location: str = Form(""),
    delivery_instructions: str = Form(""),
):
    data = CheckoutIn(
        recipient_name=recipient_name,
        phone_number=phone_number,
        university=university,
        hostel=hostel,
        block=block or None,
        room=room or None,
        campus_location=campus_location or None,
        delivery_instructions=delivery_instructions or None,
    )
    try:
        order = orders_service.create_order_from_cart(db, user, data)
    except orders_service.OrderError as exc:
        cart = carts_service.get_or_create_cart(db, user)
        addresses = users_service.list_addresses(db, user)
        estimated_total = round(cart.subtotal + settings.delivery_fee_estimate, 2)
        return templates.TemplateResponse(
            request,
            "orders/checkout.html",
            {
                "cart": cart, "user": user, "addresses": addresses,
                "delivery_fee": settings.delivery_fee_estimate, "estimated_total": estimated_total,
                "error": str(exc),
            },
            status_code=400,
        )
    return RedirectResponse(f"/orders/{order.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/orders", response_class=HTMLResponse)
def order_history(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    orders = orders_service.list_orders_for_customer(db, user)
    return templates.TemplateResponse(request, "orders/history.html", {"orders": orders, "user": user})


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    order = orders_service.get_order_for_customer(db, user, order_id)
    if order is None:
        return templates.TemplateResponse(request, "errors/404.html", {"user": user}, status_code=404)
    return templates.TemplateResponse(request, "orders/detail.html", {"order": order, "user": user})


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    try:
        orders_service.cancel_order(db, user, order_id)
    except orders_service.OrderError:
        pass
    return RedirectResponse(f"/orders/{order_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/vendor/orders/{order_id}/status")
def vendor_update_status(
    order_id: int,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    new_status: str = Form(...),
):
    if user.vendor is not None:
        try:
            orders_service.update_status_as_vendor(db, user.vendor.id, order_id, new_status)
        except orders_service.OrderError:
            pass
    return RedirectResponse("/vendor/orders", status_code=status.HTTP_303_SEE_OTHER)
