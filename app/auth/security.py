"""
Password hashing and signed session-cookie helpers.

We use passlib/bcrypt for password hashing (never store plaintext) and
itsdangerous for a signed, tamper-evident session cookie carrying only the
user id. This avoids the complexity/footguns of storing JWTs in browser
storage for a server-rendered app.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="session-cookie")

SESSION_COOKIE_NAME = "um_session"


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    """Create a signed token encoding the user id, for storage in a cookie."""
    return _serializer.dumps({"user_id": user_id})


def read_session_token(token: str) -> int | None:
    """Decode a session token, returning the user id, or None if invalid/expired."""
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age)
        return int(data["user_id"])
    except (BadSignature, SignatureExpired, KeyError, ValueError, TypeError):
        return None
