import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.user import User

DEFAULT_PARTNER_EMAIL = "partner@xscout.local"
DEFAULT_PARTNER_PASSWORD = "XScout2026!"
DEFAULT_PARTNER_NAME = "X-Scout AI Investment Partner"

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash password using salted PBKDF2-HMAC-SHA256 (100,000 iterations)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000,
    )
    return f"{salt}${key.hex()}"


get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored salt$hash using constant-time comparison."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,
        )
        return hmac.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed HS256 JWT access token (defaults to 7 days = 10080 minutes)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a signed JWT token, returning None if invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None


def ensure_default_partner_user(db: Session) -> User:
    """Ensure the pre-filled seed Partner account (partner@xscout.local) exists in SQLite."""
    user = db.query(User).filter(User.email == DEFAULT_PARTNER_EMAIL).first()
    if not user:
        user = User(
            email=DEFAULT_PARTNER_EMAIL,
            full_name=DEFAULT_PARTNER_NAME,
            password_hash=hash_password(DEFAULT_PARTNER_PASSWORD),
            role="partner",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI Dependency enforcing JWT authentication on protected business routes.
    Accepts token from either 'Authorization: Bearer <jwt>' header or 'session_token' HttpOnly cookie.
    """
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("session_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing Bearer token or session_token cookie.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload (missing 'sub').",
            headers={"WWW-Authenticate": "Bearer"},
        )

    ensure_default_partner_user(db)
    user = db.query(User).filter(User.email == str(email).lower()).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
