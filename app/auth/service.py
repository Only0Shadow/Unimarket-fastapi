"""Business logic for registration and login."""
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.auth.schemas import RegisterIn
from app.auth.security import hash_password, verify_password
from app.users.models import Profile
from app.carts.models import Cart
from app.wishlists.models import Wishlist


class AuthError(Exception):
    """Raised for user-facing authentication/registration failures."""


def get_user_by_identifier(db: Session, identifier: str) -> User | None:
    stmt = select(User).where(
        or_(User.username == identifier.lower(), User.email == identifier.lower())
    )
    return db.execute(stmt).scalar_one_or_none()


def register_user(db: Session, data: RegisterIn) -> User:
    if get_user_by_identifier(db, data.username):
        raise AuthError("That username is already taken.")
    if get_user_by_identifier(db, data.email):
        raise AuthError("An account with that email already exists.")

    user = User(
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
        username=data.username,
        email=data.email.lower(),
        phone_number=data.phone_number,
        hashed_password=hash_password(data.password),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(user)
    db.flush()  # populate user.id before creating dependent rows

    # Every new user gets an empty profile, cart, and wishlist so downstream
    # code never has to special-case "profile does not exist yet".
    db.add(Profile(user_id=user.id))
    db.add(Cart(customer_id=user.id))
    db.add(Wishlist(customer_id=user.id))

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    user = get_user_by_identifier(db, identifier)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Incorrect username/email or password.")
    if not user.is_active:
        raise AuthError("This account has been deactivated. Contact support.")
    return user
