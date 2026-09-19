"""Routes for viewing/editing profile and managing delivery addresses."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.users.schemas import ProfileUpdateIn, DeliveryAddressIn
from app.users import service as users_service
from app.orders import service as orders_service

router = APIRouter(prefix="/account", tags=["users"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def account_home(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    addresses = users_service.list_addresses(db, user)
    orders = orders_service.list_orders_for_customer(db, user)
    return templates.TemplateResponse(
        request,
        "auth/profile.html",
        {"user": user, "addresses": addresses, "orders": orders},
    )


@router.post("/profile")
def update_profile(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone_number: str = Form(""),
    university: str = Form(""),
    student_id: str = Form(""),
    hostel: str = Form(""),
):
    data = ProfileUpdateIn(
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number or None,
        university=university or None,
        student_id=student_id or None,
        hostel=hostel or None,
    )
    users_service.update_profile(db, user, data)
    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/addresses")
def add_address(
    request: Request,
    user=Depends(require_user),
    db: Session = Depends(get_db),
    label: str = Form("Default"),
    recipient_name: str = Form(...),
    phone_number: str = Form(...),
    university: str = Form(...),
    hostel: str = Form(...),
    block: str = Form(""),
    room: str = Form(""),
    campus_location: str = Form(""),
    instructions: str = Form(""),
    is_default: bool = Form(False),
):
    data = DeliveryAddressIn(
        label=label,
        recipient_name=recipient_name,
        phone_number=phone_number,
        university=university,
        hostel=hostel,
        block=block or None,
        room=room or None,
        campus_location=campus_location or None,
        instructions=instructions or None,
        is_default=is_default,
    )
    users_service.add_address(db, user, data)
    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/addresses/{address_id}/delete")
def delete_address(address_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    users_service.delete_address(db, user, address_id)
    return RedirectResponse("/account", status_code=status.HTTP_303_SEE_OTHER)
