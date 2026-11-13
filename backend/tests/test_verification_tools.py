"""
Hermetic verification tests for Feature 07 Sub-task 7.1 & 7.2 tools:
- Clean User-Only DB Reset (`backend/reset_clean_users.py`)
- Live X API v2 OAuth 1.0a Client & `LIVE_X` Dispatch integration (`backend/app/services/x_client.py`)
- Live Key Diagnostic Script (`backend/scripts/verify_live_keys.py`)
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.security import (
    DEFAULT_PARTNER_EMAIL,
    DEFAULT_PARTNER_PASSWORD,
    hash_password,
)
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.models.queue import JobQueue, JobStatus
from backend.app.models.user import User
from backend.app.services.ai_evaluator import AIEvaluationResult
from backend.app.services.state_machine import approve_and_send_candidate
from backend.app.services.x_client import (
    XApiRateLimitError,
    build_oauth1_header,
    send_x_dm,
)
from backend.reset_clean_users import (
    DEFAULT_ANALYST_EMAIL,
    reset_database_keep_users,
)
from backend.scripts.verify_live_keys import (
    run_dispatch_guard_gate,
    run_llm_gate,
    run_x_lookup_gate,
)


@pytest.fixture
def isolated_db():
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


def test_reset_clean_users_preserves_partner_and_login(isolated_db):
    """Sub-task 7.1: wipes candidates/ledger/jobs while retaining Partner user login."""
    partner = User(
        email=DEFAULT_PARTNER_EMAIL,
        full_name="Partner",
        password_hash=hash_password(DEFAULT_PARTNER_PASSWORD),
        role="partner",
    )
    extra = User(
        email="temp_reviewer@genaifund.ai",
        full_name="Temp",
        password_hash=hash_password("TempPass123!"),
        role="analyst",
    )
    isolated_db.add_all([partner, extra])
    isolated_db.commit()

    cand = Candidate(
        handle="reset_probe",
        name="Reset Probe",
        bio="Embodied AI builder",
        recent_tweets="Built robot policy",
        can_dm=True,
        status=CandidateStatus.SENT.value,
    )
    isolated_db.add(cand)
    isolated_db.commit()

    ledger = OutreachLedger(
        candidate_id=cand.id,
        handle=cand.handle,
        idempotency_key="idem-reset-1",
        sent_message="Hello!",
        dispatch_mode="SANDBOX",
        status=OutreachStatus.SENT.value,
    )
    job = JobQueue(
        job_type="AI_EVALUATE",
        candidate_id=cand.id,
        status=JobStatus.COMPLETED.value,
    )
    isolated_db.add_all([ledger, job])
    isolated_db.commit()

    summary = reset_database_keep_users(
        isolated_db,
        with_analyst=True,
        purge_extra_users=True,
    )

    assert summary["remaining"]["candidates"] == 0
    assert summary["remaining"]["outreach_ledger"] == 0
    assert summary["remaining"]["job_queue"] == 0
    assert summary["remaining"]["users"] == 2
    emails = {u["email"] for u in summary["retained_users"]}
    assert emails == {DEFAULT_PARTNER_EMAIL, DEFAULT_ANALYST_EMAIL}

    # Verify HTTP login still succeeds immediately after reset
    def _override_db():
        yield isolated_db

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/auth/login",
            json={"email": DEFAULT_PARTNER_EMAIL, "password": DEFAULT_PARTNER_PASSWORD},
        )
        assert resp.status_code == 200
        assert resp.json()["user"]["email"] == DEFAULT_PARTNER_EMAIL
    finally:
        app.dependency_overrides.clear()


def test_x_client_oauth1_and_live_x_state_machine_dispatch(isolated_db, monkeypatch):
    """Sub-task 7.2: OAuth 1.0a signing + real X DM dispatch on whitelisted handle."""
    header = build_oauth1_header(
        method="POST",
        url="https://api.twitter.com/2/dm_conversations/with/123456/messages",
        consumer_key="ckey",
        consumer_secret="csec",
        access_token="atok",
        access_token_secret="asec",
        nonce="fixednonce",
        timestamp="1700000000",
    )
    assert header.startswith("OAuth ")
    assert 'oauth_signature_method="HMAC-SHA1"' in header
    assert 'oauth_signature="' in header

    monkeypatch.setattr(settings, "X_API_KEY", "ckey")
    monkeypatch.setattr(settings, "X_API_SECRET", "csec")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "atok")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "asec")
    monkeypatch.setattr(settings, "LIVE_X_DRY_RUN", False)
    monkeypatch.setattr(settings, "_allowed_test_handles", "minh_quant")

    cand = Candidate(
        x_user_id="987654321",
        handle="minh_quant",
        name="Minh Quant",
        bio="CUDA inference engineer in HCMC",
        recent_tweets="Shipped INT4 kernel",
        can_dm=True,
        status=CandidateStatus.PENDING_REVIEW.value,
    )
    isolated_db.add(cand)
    isolated_db.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "data": {
            "dm_event_id": "19001122334455",
            "dm_conversation_id": "conv_999",
        }
    }

    with patch("backend.app.services.x_client.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_resp

        res = approve_and_send_candidate(
            db=isolated_db,
            candidate_id=cand.id,
            custom_message="Hi Minh, loved your INT4 CUDA benchmarks!",
            dispatch_mode="LIVE_X",
        )

    assert res["candidate"]["status"] == CandidateStatus.SENT.value
    assert res["ledger"]["dispatch_mode"] == "LIVE_X"
    assert res["ledger"]["external_dm_id"] == "19001122334455"


def test_x_client_raises_rate_limit_on_429(monkeypatch):
    monkeypatch.setattr(settings, "X_API_KEY", "ckey")
    monkeypatch.setattr(settings, "X_API_SECRET", "csec")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "atok")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "asec")

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"retry-after": "30"}

    with patch("backend.app.services.x_client.httpx.Client") as mock_client_cls:
        mock_client = mock_client_cls.return_value.__enter__.return_value
        mock_client.post.return_value = mock_429

        with pytest.raises(XApiRateLimitError) as exc_info:
            send_x_dm(handle="minh_quant", message="Test", x_user_id="987654321")
        assert exc_info.value.retry_after_seconds == 30.0


def test_verify_live_keys_diagnostic_gates(monkeypatch):
    """Sub-task 7.2: verify_live_keys reports SKIPPED_NO_KEY safely, and PASSED when live responses succeed."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "")
    monkeypatch.setattr(settings, "X_API_KEY", "")

    assert run_llm_gate()["status"] == "SKIPPED_NO_KEY"
    assert run_x_lookup_gate()["status"] == "SKIPPED_NO_KEY"
    assert run_dispatch_guard_gate()["status"] == "SKIPPED_NO_KEY"

    # Simulate configured Gemini key + valid structured response
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyMockedLiveKeyForUnitTest")

    def _fake_llm(candidate):
        if "ignore" in (candidate.bio + candidate.recent_tweets).lower():
            # Even if a compromised model tried to follow injection, Tri-Guard must neutralize it
            return AIEvaluationResult(
                is_match=True,
                fit_score=4,
                fit_reason="PWNED_BY_PROMPT_INJECTION",
                evidence_snippet="SYSTEM OVERRIDE",
                draft_dm="PWNED_BY_PROMPT_INJECTION",
                insufficient_evidence=False,
            )
        return AIEvaluationResult(
            is_match=True,
            fit_score=4,
            fit_reason="Strong robotics track match in SEA.",
            evidence_snippet=candidate.bio[:40],
            draft_dm=(
                "Hi there, really admired your concrete robotics engineering notes in Southeast Asia "
                "and how your team approached real-world warehouse deployment benchmarks. "
                "We back early technical teams at GenAI Fund—would love a quick 15-min chat if open."
            ),
            insufficient_evidence=False,
        )

    with (
        patch("backend.app.services.ai_evaluator._call_external_llm", side_effect=_fake_llm),
        patch("backend.scripts.verify_live_keys._call_external_llm", side_effect=_fake_llm),
    ):
        llm_report = run_llm_gate(full_benchmark=False)
    assert llm_report["status"] == "PASSED"
    assert llm_report["guard_failures"] == []
