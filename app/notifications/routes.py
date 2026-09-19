"""Routes for viewing and marking notifications read."""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_user
from app.notifications import service as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_notifications(request: Request, user=Depends(require_user), db: Session = Depends(get_db)):
    notifications = notifications_service.list_for_user(db, user)
    return templates.TemplateResponse(
        request, "notifications.html", {"notifications": notifications, "user": user}
    )


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, user=Depends(require_user), db: Session = Depends(get_db)):
    notifications_service.mark_read(db, user, notification_id)
    return RedirectResponse("/notifications", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/read-all")
def mark_all_read(user=Depends(require_user), db: Session = Depends(get_db)):
    notifications_service.mark_all_read(db, user)
    return RedirectResponse("/notifications", status_code=status.HTTP_303_SEE_OTHER)
