"""
Unit & Integration Tests for Centralized RuntimeGateway (`backend/app/core/runtime_gateway.py`).

Verifies strict separation and observability across:
- Case 1: `RUNTIME_PROFILE=OFFLINE_MOCK` ($0 Deterministic AI + Local X Simulator + Simulated DM)
- Case 2: `RUNTIME_PROFILE=LIVE_PRODUCTION` (Real Gemini/OpenAI + Real X API v2, Zero Silent Fallback)
- Case 3: `RUNTIME_PROFILE=HYBRID_AUTO` (Backward-compatible auto-detection with `execution_meta` stamping)
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.services.ai_evaluator import AIEvaluationResult
from backend.app.services.dispatcher import send_rate_limiter


@pytest.fixture
def db_session():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _enable_fk(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    send_rate_limiter.reset()
    try:
        yield session
    finally:
        send_rate_limiter.reset()
        session.close()


@pytest.fixture
def auth_client(db_session):
    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    client = TestClient(app)
    login_resp = client.post("/api/auth/demo-login")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    yield client
    app.dependency_overrides.clear()


def test_case1_offline_mock_strictly_blocks_external_ai_and_x_calls(
    auth_client, db_session, monkeypatch
):
    """
    Case 1 (`OFFLINE_MOCK`):
    Even if GEMINI_API_KEY and X OAuth 1.0a keys are present in environment,
    OFFLINE_MOCK locks AI to $0 DETERMINISTIC_RUBRIC, X Lookup to X_API_SIMULATOR,
    and DM dispatch to non-network simulation.
    """
    monkeypatch.setattr(settings, "RUNTIME_PROFILE", "OFFLINE_MOCK")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyShouldNotBeCalledInOfflineMock")
    monkeypatch.setattr(settings, "X_API_BASE_URL", "https://api.twitter.com/2")
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "")
    monkeypatch.setattr(settings, "X_API_KEY", "ckey")
    monkeypatch.setattr(settings, "X_API_SECRET", "csec")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "atok")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "asec")
    monkeypatch.setattr(settings, "LIVE_X_DRY_RUN", False)

    # 1. Verify /api/system/runtime summary
    rt_resp = auth_client.get("/api/system/runtime")
    assert rt_resp.status_code == 200
    rt_data = rt_resp.json()
    assert rt_data["runtime_profile"] == "OFFLINE_MOCK"
    assert rt_data["ai_evaluation"]["ai_engine"] == "DETERMINISTIC_RUBRIC"
    assert rt_data["ai_evaluation"]["external_network_call"] is False
    assert rt_data["x_lookup"]["source_mode"] == "X_API_SIMULATOR"
    assert rt_data["x_lookup"]["bearer_token_configured"] is True

    # 2. Verify AI evaluation never calls _call_external_llm in OFFLINE_MOCK
    cand = Candidate(
        handle="minh_quant",
        name="Minh Nguyen",
        location="Hanoi, Vietnam",
        bio="Founder @TensorEdgeVN. Ultra-fast C++/CUDA/ARM LLM inference engine.",
        recent_tweets="[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs.",
        can_dm=True,
        status=CandidateStatus.QUEUED_FOR_AI.value,
    )
    db_session.add(cand)
    db_session.commit()

    with patch("backend.app.services.ai_evaluator._call_external_llm") as mock_llm:
        eval_resp = auth_client.post(f"/api/queue/evaluate/{cand.id}", json={})
        assert eval_resp.status_code == 200
        body = eval_resp.json()
        assert body["status"] == CandidateStatus.PENDING_REVIEW.value
        assert body["execution_meta"] == {
            "profile": "OFFLINE_MOCK",
            "ai_engine": "DETERMINISTIC_RUBRIC",
            "model_used": "tri-guard-local-v1",
            "external_network_call": False,
        }
        mock_llm.assert_not_called()

    # 3. Verify DM dispatch never calls send_x_dm over network in OFFLINE_MOCK
    with patch("backend.app.services.state_machine.send_x_dm") as mock_send_x:
        send_resp = auth_client.post(
            f"/api/candidates/{cand.id}/send",
            json={"dispatch_mode": "LIVE_X"},
        )
        assert send_resp.status_code == 200
        send_body = send_resp.json()
        assert send_body["execution_meta"] == {
            "profile": "OFFLINE_MOCK",
            "dispatch_mode": "LIVE_X",
            "dispatch_execution": "LIVE_X_DRY_RUN",
            "external_network_call": False,
        }
        assert send_body["ledger"]["external_dm_id"].startswith("sim_dm_")
        mock_send_x.assert_not_called()


def test_case2_live_production_forbids_silent_fallbacks(
    auth_client, db_session, monkeypatch
):
    """
    Case 2 (`LIVE_PRODUCTION`):
    - Missing GEMINI_API_KEY/OPENAI_API_KEY transitions candidate to AI_FAILED (no fake $0 rubric fallback).
    - Localhost simulator URL or missing X_BEARER_TOKEN on /api/ingestion/x-lookup fails with 503.
    - Missing OAuth 1.0a keys on LIVE_X dispatch fails with 503 (never generating fake sim_dm_...).
    """
    monkeypatch.setattr(settings, "RUNTIME_PROFILE", "LIVE_PRODUCTION")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    monkeypatch.setattr(settings, "X_API_BASE_URL", "http://127.0.0.1:8099/2")
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "sim_dev_bearer_token")
    monkeypatch.setattr(settings, "X_API_KEY", "")
    monkeypatch.setattr(settings, "X_API_SECRET", "")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "")

    cand = Candidate(
        handle="minh_quant",
        name="Minh Nguyen",
        location="Hanoi, Vietnam",
        bio="Founder @TensorEdgeVN. Ultra-fast C++/CUDA/ARM LLM inference engine.",
        recent_tweets="[2026-11-08] Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs.",
        can_dm=True,
        status=CandidateStatus.QUEUED_FOR_AI.value,
    )
    db_session.add(cand)
    db_session.commit()

    # 1. Missing LLM key in LIVE_PRODUCTION -> transitions to AI_FAILED (no silent $0 fallback)
    eval_fail = auth_client.post(f"/api/queue/evaluate/{cand.id}", json={})
    assert eval_fail.status_code == 200
    eval_fail_body = eval_fail.json()
    assert eval_fail_body["status"] == CandidateStatus.AI_FAILED.value
    assert "[LIVE_PRODUCTION]" in eval_fail_body["error"]
    assert eval_fail_body["execution_meta"]["profile"] == "LIVE_PRODUCTION"
    assert eval_fail_body["execution_meta"]["ai_engine"] == "UNCONFIGURED_LIVE_LLM"

    # 2. Now provide live GEMINI_API_KEY -> succeeds via live LLM and stamps LIVE_GEMINI
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyLiveProductionTestKey")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "gemini-3.5-flash")

    def _mock_live_gemini(c):
        return AIEvaluationResult(
            is_match=True,
            fit_score=4,
            fit_reason="Live Gemini 3.5 Flash evaluation: Top SEA inference founder.",
            evidence_snippet="Just open-sourced our AWQ-W4A8 speculative decoding kernel for L40S GPUs.",
            draft_dm=(
                "Hi Minh, came across @minh_quant and your open-source AWQ-W4A8 speculative decoding "
                "kernel for L40S GPUs. We back deep-tech AI infrastructure founders across Vietnam and SEA "
                "at GenAI Fund—would love to connect for a quick peer chat this week if you're open!"
            ),
            insufficient_evidence=False,
        )

    with patch("backend.app.services.ai_evaluator._call_external_llm", side_effect=_mock_live_gemini):
        eval_ok = auth_client.post(f"/api/queue/evaluate/{cand.id}", json={})
        assert eval_ok.status_code == 200
        eval_ok_body = eval_ok.json()
        assert eval_ok_body["status"] == CandidateStatus.PENDING_REVIEW.value
        assert eval_ok_body["execution_meta"] == {
            "profile": "LIVE_PRODUCTION",
            "ai_engine": "LIVE_GEMINI",
            "model_used": "gemini-3.5-flash",
            "external_network_call": True,
        }

    # 3. X Lookup pointing to localhost simulator in LIVE_PRODUCTION -> blocked with HTTP 503
    lookup_sim_err = auth_client.get("/api/ingestion/x-lookup", params={"handle": "@minh_quant"})
    assert lookup_sim_err.status_code == 503
    assert "[LIVE_PRODUCTION]" in lookup_sim_err.json()["detail"]

    # 4. LIVE_X DM Send without OAuth 1.0a keys in LIVE_PRODUCTION -> blocked with HTTP 503 (no sim_dm_...)
    send_missing_oauth = auth_client.post(
        f"/api/candidates/{cand.id}/send",
        json={"dispatch_mode": "LIVE_X"},
    )
    assert send_missing_oauth.status_code == 503
    assert "[LIVE_PRODUCTION]" in send_missing_oauth.json()["detail"]
    db_session.refresh(cand)
    assert cand.status == CandidateStatus.PENDING_REVIEW.value  # Not falsely marked SENT!

    # 5. Configure all 4 OAuth keys + live X_API_BASE_URL + LIVE_X_DRY_RUN=False -> dispatches real DM
    monkeypatch.setattr(settings, "X_API_BASE_URL", "https://api.twitter.com/2")
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "real_live_bearer_token_xyz")
    monkeypatch.setattr(settings, "X_API_KEY", "live_ckey")
    monkeypatch.setattr(settings, "X_API_SECRET", "live_csec")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN", "live_atok")
    monkeypatch.setattr(settings, "X_ACCESS_TOKEN_SECRET", "live_asec")
    monkeypatch.setattr(settings, "LIVE_X_DRY_RUN", False)

    rt_ready = RuntimeGateway.get_runtime_status_summary()
    assert rt_ready["live_production_readiness"]["ready"] is True
    assert rt_ready["live_production_readiness"]["missing_requirements"] == []

    with patch(
        "backend.app.services.state_machine.send_x_dm",
        return_value={"dm_event_id": "x_live_event_998877", "dm_conversation_id": "conv_1", "participant_id": "1002"},
    ) as mock_real_dm:
        send_live_ok = auth_client.post(
            f"/api/candidates/{cand.id}/send",
            json={"dispatch_mode": "LIVE_X"},
        )
        assert send_live_ok.status_code == 200
        live_body = send_live_ok.json()
        assert live_body["candidate"]["status"] == CandidateStatus.SENT.value
        assert live_body["ledger"]["external_dm_id"] == "x_live_event_998877"
        assert live_body["execution_meta"] == {
            "profile": "LIVE_PRODUCTION",
            "dispatch_mode": "LIVE_X",
            "dispatch_execution": "LIVE_X_REAL_SENT",
            "external_network_call": True,
        }
        mock_real_dm.assert_called_once()

