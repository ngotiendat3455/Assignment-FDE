from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import (
    create_access_token,
    ensure_default_partner_user,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.app.models.user import User
from backend.app.schemas.user import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])

COOKIE_MAX_AGE_7_DAYS = 60 * 60 * 24 * 7


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=COOKIE_MAX_AGE_7_DAYS,
    )


@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user with email & password, return 7-day JWT and set HttpOnly 'session_token' cookie.
    Automatically seeds the default Partner account (partner@genaifund.ai) on fresh databases.
    """
    ensure_default_partner_user(db)
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role}
    )
    _set_session_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user.to_dict()),
    )


@router.post("/demo-login", response_model=TokenResponse)
def demo_partner_login(
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Zero-friction 1-Click Login as the seed GenAI Fund Investment Partner."""
    user = ensure_default_partner_user(db)
    token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role}
    )
    _set_session_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user.to_dict()),
    )


@router.post("/register", response_model=TokenResponse)
def register_user(
    payload: UserRegister,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new team member account with salted password hashing."""
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role or "partner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role}
    )
    _set_session_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user.to_dict()),
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user profile."""
    return UserResponse(**current_user.to_dict())


@router.post("/logout")
def logout_user(response: Response) -> Dict[str, Any]:
    """Clear the HttpOnly 'session_token' cookie and terminate session."""
    response.delete_cookie(key="session_token", path="/")
    return {"success": True, "message": "Signed out successfully"}
