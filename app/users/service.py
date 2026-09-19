"""Business logic for profile and delivery-address management."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import User
from app.users.models import DeliveryAddress
from app.users.schemas import ProfileUpdateIn, DeliveryAddressIn


def update_profile(db: Session, user: User, data: ProfileUpdateIn) -> User:
    user.first_name = data.first_name.strip()
    user.last_name = data.last_name.strip()
    user.phone_number = data.phone_number

    profile = user.profile
    profile.university = data.university
    profile.student_id = data.student_id
    profile.hostel = data.hostel

    db.commit()
    db.refresh(user)
    return user


def list_addresses(db: Session, user: User) -> list[DeliveryAddress]:
    stmt = select(DeliveryAddress).where(DeliveryAddress.user_id == user.id)
    return list(db.execute(stmt).scalars())


def add_address(db: Session, user: User, data: DeliveryAddressIn) -> DeliveryAddress:
    if data.is_default:
        for addr in list_addresses(db, user):
            addr.is_default = False

    address = DeliveryAddress(user_id=user.id, **data.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def delete_address(db: Session, user: User, address_id: int) -> bool:
    address = db.get(DeliveryAddress, address_id)
    if address is None or address.user_id != user.id:
        return False
    db.delete(address)
    db.commit()
    return True
