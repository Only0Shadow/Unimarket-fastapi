"""HTTP routes for registration, login, and logout."""
from fastapi import APIRouter, Depends, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.auth.schemas import RegisterIn
from app.auth.service import register_user, authenticate_user, AuthError
from app.auth.security import create_session_token, SESSION_COOKIE_NAME
from app.config import get_settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "auth/register.html", {"errors": []})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    db: Session = Depends(get_db),
    first_name: str = Form(...),
    last_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    try:
        data = RegisterIn(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            phone_number=phone_number or None,
            password=password,
            confirm_password=confirm_password,
        )
        user = register_user(db, data)
    except ValidationError as exc:
        errors = [err["msg"] for err in exc.errors()]
        return templates.TemplateResponse(
            request, "auth/register.html", {"errors": errors}, status_code=400
        )
    except AuthError as exc:
        return templates.TemplateResponse(
            request, "auth/register.html", {"errors": [str(exc)]}, status_code=400
        )

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    token = create_session_token(user.id)
    response.set_cookie(
        SESSION_COOKIE_NAME, token, max_age=settings.session_max_age, httponly=True, samesite="lax"
    )
    return response


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "auth/login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    identifier: str = Form(...),
    password: str = Form(...),
):
    try:
        user = authenticate_user(db, identifier, password)
    except AuthError as exc:
        return templates.TemplateResponse(
            request, "auth/login.html", {"error": str(exc)}, status_code=400
        )

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    token = create_session_token(user.id)
    response.set_cookie(
        SESSION_COOKIE_NAME, token, max_age=settings.session_max_age, httponly=True, samesite="lax"
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
