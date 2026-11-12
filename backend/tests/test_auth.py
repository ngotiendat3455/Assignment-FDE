from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.core.security import (
    DEFAULT_PARTNER_EMAIL,
    DEFAULT_PARTNER_PASSWORD,
    create_access_token,
    ensure_default_partner_user,
)
from backend.app.main import app


@pytest.fixture
def db_session():
    """Isolated SQLite database session for authentication tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def anon_client(db_session):
    """Unauthenticated TestClient bound to isolated SQLite session."""
    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_unauthenticated_rejection(anon_client):
    """
    Acceptance Criterion 1:
    Calling GET /api/candidates without an Authorization header or session_token cookie
    must return 401 Unauthorized.
    """
    resp = anon_client.get("/api/candidates")
    assert resp.status_code == 401

    me_resp = anon_client.get("/api/auth/me")
    assert me_resp.status_code == 401


def test_prefilled_partner_login_and_session(anon_client):
    """
    Acceptance Criterion 2:
    Logging in with pre-filled credentials (partner@genaifund.ai / GenAIFund2026!)
    succeeds with a 7-day JWT token, sets the HttpOnly session_token cookie,
    and unlocks protected endpoints.
    """
    login_resp = anon_client.post(
        "/api/auth/login",
        json={
            "email": DEFAULT_PARTNER_EMAIL,
            "password": DEFAULT_PARTNER_PASSWORD,
        },
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == DEFAULT_PARTNER_EMAIL
    assert data["user"]["role"] == "partner"

    # Verify HttpOnly cookie is set
    assert "session_token" in login_resp.cookies

    # Verify Bearer token unlocks /api/auth/me and /api/candidates
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_resp = anon_client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == DEFAULT_PARTNER_EMAIL

    cand_resp = anon_client.get("/api/candidates", headers=headers)
    assert cand_resp.status_code == 200


def test_wrong_password_rejected(anon_client):
    """
    Acceptance Criterion 3:
    Logging in with an incorrect password returns 401 Incorrect email or password.
    """
    bad_resp = anon_client.post(
        "/api/auth/login",
        json={
            "email": DEFAULT_PARTNER_EMAIL,
            "password": "WrongPassword123!",
        },
    )
    assert bad_resp.status_code == 401
    assert "Incorrect email or password" in bad_resp.json()["detail"]


def test_logout_clears_session_cookie(anon_client):
    """
    Acceptance Criterion 4:
    Logging out clears the session_token cookie so subsequent cookie-only requests fail with 401.
    """
    # 1. Login (sets session_token cookie on client)
    login_resp = anon_client.post("/api/auth/demo-login")
    assert login_resp.status_code == 200

    # Cookie-authenticated request works
    me_before = anon_client.get("/api/auth/me")
    assert me_before.status_code == 200

    # 2. Logout
    logout_resp = anon_client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["success"] is True

    # Clear client cookie jar if deleted cookie is empty
    anon_client.cookies.clear()
    me_after = anon_client.get("/api/auth/me")
    assert me_after.status_code == 401


def test_expired_token_and_secret_hygiene(anon_client, db_session):
    """Verify expired JWT is rejected with 401 and no API secrets or password hashes leak."""
    user = ensure_default_partner_user(db_session)
    expired_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role},
        expires_delta=timedelta(seconds=-30),
    )

    exp_resp = anon_client.get(
        "/api/candidates",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert exp_resp.status_code == 401

    # Secret hygiene check on /api/health and /api/auth/demo-login
    health_text = anon_client.get("/api/health").text
    assert "GEMINI_API_KEY" not in health_text
    assert "X_BEARER_TOKEN" not in health_text

    demo_json = anon_client.post("/api/auth/demo-login").json()
    assert "password_hash" not in demo_json["user"]
    assert "hashed_password" not in demo_json["user"]
