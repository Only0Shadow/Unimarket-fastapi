"""
Shared dependencies used across routers: database session, current-user
resolution from the session cookie, and role-based access guards.
"""
from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.models import User, UserRole
from app.auth.security import SESSION_COOKIE_NAME, read_session_token

__all__ = ["get_db"]


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the logged-in User, or None for guests. Never raises."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    user_id = read_session_token(token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_user(user: User | None = Depends(get_current_user)) -> User:
    """Require any authenticated, active user (student, vendor, or admin)."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/login"})
    return user


def require_vendor(user: User = Depends(require_user)) -> User:
    """Require the current user to be an approved vendor."""
    if user.role != UserRole.VENDOR or user.vendor is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor access required.")
    if user.vendor.status.value != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your vendor account is not yet approved.",
        )
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """Require the current user to be a platform administrator."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
