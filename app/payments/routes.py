"""
Payment routes.

Flow: /payments/orders/{id}/pay starts a gateway session and redirects the
browser to the gateway's own hosted checkout page -> customer pays there
(never on this app) -> gateway redirects back to /payments/verify/{ref},
which asks the gateway to confirm the outcome and updates the order.

/payments/mock-checkout/* only does anything when PAYMENT_GATEWAY=mock; a
real gateway is never routed through this app's own pages.
"""
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.orders.models import Order
from app.payments.gateways.mock import MockGateway
from app.payments.models import Payment
from app.payments.schemas import PaymentOut
from app.payments.service import PaymentError, PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])
templates = Jinja2Templates(directory="app/templates")


def _get_owned_order(db: Session, user, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None or order.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")
    return order


@router.get("/orders/{order_id}/status", response_model=PaymentOut)
def payment_status(order_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    order = _get_owned_order(db, user, order_id)
    if order.payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No payment record for this order.")
    return order.payment


@router.get("/orders/{order_id}/pay")
def start_payment(order_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    """Starts a gateway checkout session and redirects the browser there."""
    order = _get_owned_order(db, user, order_id)
    try:
        payment = PaymentService.initiate_payment(db, order, email=user.email)
    except PaymentError as exc:
        return RedirectResponse(f"/orders/{order.id}?payment_error={exc}", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(payment.checkout_url, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/verify/{reference}")
def verify_payment(reference: str, db: Session = Depends(get_db)):
    """Landing page the gateway redirects back to after checkout. Verifies
    against the gateway's own API -- never trusts the redirect alone."""
    try:
        payment = PaymentService.verify_payment(db, reference)
    except PaymentError:
        return RedirectResponse("/orders", status_code=status.HTTP_303_SEE_OTHER)
    flag = "paid" if payment.status.value == "paid" else "payment_failed"
    return RedirectResponse(f"/orders/{payment.order_id}?{flag}=1", status_code=status.HTTP_303_SEE_OTHER)


# --- Mock gateway's own "checkout page" -------------------------------------
# Only meaningful while PAYMENT_GATEWAY=mock. A real gateway sends the
# customer to its own hosted page instead of anything under this app.

@router.get("/mock-checkout/{reference}", response_class=HTMLResponse)
def mock_checkout_page(reference: str, request: Request, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(Payment.gateway_reference == reference).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Unknown payment reference.")
    return templates.TemplateResponse(
        request, "payments/mock_checkout.html", {"payment": payment, "reference": reference, "user": None}
    )


@router.post("/mock-checkout/{reference}/resolve")
def mock_checkout_resolve(reference: str, outcome: str = Form(...)):
    MockGateway.resolve(reference, "success" if outcome == "success" else "failed")
    return RedirectResponse(f"/payments/verify/{reference}", status_code=status.HTTP_303_SEE_OTHER)


# --- Gateway webhook ----------------------------------------------------------
# Reserved endpoint for real gateways' async payment notifications. Each
# real adapter's provider requires its own signature-verification scheme
# before this should trust an incoming payload -- left as a clearly-marked
# TODO rather than guessed at, since building it wrong is worse than not
# building it yet.

@router.post("/webhook/{gateway_name}")
async def payment_webhook(gateway_name: str, request: Request):
    """
    TODO before going live with a real gateway: verify this request's
    signature using that gateway's documented scheme (e.g. Paystack sends
    an `x-paystack-signature` header; Flutterwave a `verif-hash` header;
    Stripe a `Stripe-Signature` header) before trusting the payload at all.
    Until that's implemented, this endpoint intentionally does nothing with
    the payload -- verify_payment() above is the trusted path.
    """
    return {"received": True}
