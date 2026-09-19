"""Helpers to create and query internal notifications."""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.auth.models import User
from app.notifications.models import Notification


def notify(db: Session, recipient: User, title: str, message: str) -> Notification:
    """Create a notification. Does not commit -- caller controls the transaction
    boundary so this can be bundled with the triggering change (e.g. an order
    status update)."""
    n = Notification(recipient_id=recipient.id, title=title, message=message)
    db.add(n)
    db.flush()
    return n


def list_for_user(db: Session, user: User, limit: int = 50) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.recipient_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def unread_count(db: Session, user: User) -> int:
    stmt = select(func.count(Notification.id)).where(
        Notification.recipient_id == user.id, Notification.is_read.is_(False)
    )
    return db.execute(stmt).scalar_one()


def mark_read(db: Session, user: User, notification_id: int) -> bool:
    notification = db.get(Notification, notification_id)
    if notification is None or notification.recipient_id != user.id:
        return False
    notification.is_read = True
    db.commit()
    return True


def mark_all_read(db: Session, user: User) -> None:
    for n in list_for_user(db, user):
        n.is_read = True
    db.commit()
