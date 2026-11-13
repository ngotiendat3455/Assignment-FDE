import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.core.database import Base, get_db
from backend.app.core.security import create_access_token, ensure_default_partner_user


@pytest.fixture()
def db_session_and_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    user = ensure_default_partner_user(db)
    token = create_access_token({"sub": user.email, "role": user.role, "uid": user.id})

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield db, client

    app.dependency_overrides.clear()
    db.close()


def test_ledger_seed_history_and_filters(db_session_and_client):
    """
    AC 1 & AC 3: Verify OUT-101..OUT-104 seed history baseline, KPI counts, and filter pills.
    """
    _, client = db_session_and_client

    resp = client.get("/api/ledger")
    assert resp.status_code == 200
    data = resp.json()

    assert data["total"] == 4
    kpi = data["kpi"]
    assert kpi["dispatched_count"] == 3  # OUT-101, OUT-102, OUT-103
    assert kpi["replied_count"] == 2  # OUT-101, OUT-103
    assert kpi["needs_attention_count"] == 2  # @linhtran_robo, @harith_medai
    assert kpi["blocked_dm_count"] == 1  # OUT-104 @arjun_infer

    out_ids = [item["outreach_id"] for item in data["items"]]
    assert out_ids == ["OUT-101", "OUT-102", "OUT-103", "OUT-104"]

    # Filter: needs_attention
    urgent_resp = client.get("/api/ledger?filter_tab=needs_attention")
    assert urgent_resp.status_code == 200
    urgent_items = urgent_resp.json()["items"]
    assert len(urgent_items) == 2
    assert {i["handle"] for i in urgent_items} == {"linhtran_robo", "harith_medai"}

    # Filter: sent
    sent_resp = client.get("/api/ledger?filter_tab=sent")
    assert sent_resp.status_code == 200
    sent_items = sent_resp.json()["items"]
    assert len(sent_items) == 1
    assert sent_items[0]["handle"] == "putri_agentic"

    # Filter: blocked
    blocked_resp = client.get("/api/ledger?filter_tab=blocked")
    assert blocked_resp.status_code == 200
    blocked_items = blocked_resp.json()["items"]
    assert len(blocked_items) == 1
    assert blocked_items[0]["handle"] == "arjun_infer"


def test_simulate_founder_reply_and_mark_handled(db_session_and_client):
    """
    AC 4 & AC 5: Verify recording a founder reply transitions SENT -> REPLIED with needs_attention=True,
    and marking handled clears needs_attention=False while keeping status=REPLIED.
    """
    _, client = db_session_and_client

    # Load baseline and locate @putri_agentic (OUT-102)
    base_data = client.get("/api/ledger").json()
    putri_entry = next(i for i in base_data["items"] if i["handle"] == "putri_agentic")
    assert putri_entry["status"] == "SENT"
    assert putri_entry["needs_attention"] is False

    # Simulate founder reply on @putri_agentic
    reply_resp = client.post(
        f"/api/ledger/{putri_entry['id']}/reply",
        json={
            "reply_text": "Hi! Yes, we're scaling our Bahasa ERP voice agents across 12 depots in Jakarta. Free Thursday 3pm WIB?",
            "needs_attention": True,
        },
    )
    assert reply_resp.status_code == 200
    updated_ledger = reply_resp.json()["ledger"]
    assert updated_ledger["status"] == "REPLIED"
    assert updated_ledger["needs_attention"] is True
    assert "Jakarta" in updated_ledger["reply_text"]
    assert updated_ledger["replied_at"] is not None

    # Verify KPI updated (3 replied, 100% reply rate across 3 dispatched, 3 needs_attention)
    after_reply_kpi = client.get("/api/ledger").json()["kpi"]
    assert after_reply_kpi["replied_count"] == 3
    assert after_reply_kpi["reply_rate"] == 100.0
    assert after_reply_kpi["needs_attention_count"] == 3

    # Mark @linhtran_robo (OUT-101) as handled
    linh_entry = next(i for i in base_data["items"] if i["handle"] == "linhtran_robo")
    handled_resp = client.post(f"/api/ledger/{linh_entry['id']}/handled")
    assert handled_resp.status_code == 200
    handled_ledger = handled_resp.json()["ledger"]
    assert handled_ledger["status"] == "REPLIED"
    assert handled_ledger["needs_attention"] is False

    # Verify needs_attention count dropped from 3 to 2
    after_handled_kpi = client.get("/api/ledger").json()["kpi"]
    assert after_handled_kpi["needs_attention_count"] == 2


def test_cannot_record_reply_on_blocked_dm(db_session_and_client):
    """Verify recording a reply on a BLOCKED entry (@arjun_infer) is rejected with 422."""
    _, client = db_session_and_client

    base_data = client.get("/api/ledger").json()
    arjun_entry = next(i for i in base_data["items"] if i["handle"] == "arjun_infer")

    resp = client.post(
        f"/api/ledger/{arjun_entry['id']}/reply",
        json={"reply_text": "Should fail because DM was blocked", "needs_attention": True},
    )
    assert resp.status_code == 422


def test_partner_calibration_matrix_accuracy(db_session_and_client):
    """
    AC 6: Verify Partner Calibration Matrix achieves > 90% accuracy against Fund Reference Scores
    and verifies Prompt Injection (P017) & Sparse Profile (P018) safety blocks.
    """
    _, client = db_session_and_client

    resp = client.get("/api/ledger/calibration")
    assert resp.status_code == 200
    data = resp.json()

    kpi = data["kpi"]
    assert kpi["unique_benchmarked"] == 19
    assert kpi["alignment_accuracy"] >= 90.0
    assert kpi["safety_blocks_verified"] == 2
    assert kpi["mean_score_delta"] <= 0.15

    by_pid = {item["profile_id"]: item for item in data["items"]}
    assert by_pid["P017"]["badge_code"] == "INJECTION_BLOCKED"
    assert by_pid["P017"]["ai_score"] == 1
    assert by_pid["P018"]["badge_code"] == "SPARSE_FLAGGED"
    assert by_pid["P018"]["ai_score"] == 0
    assert by_pid["P019"]["badge_code"] == "CLOSED_DM_CAUGHT"
    assert by_pid["P020"]["badge_code"] == "DUPLICATE_MERGED"


def test_calibration_never_calls_external_llm_on_get(db_session_and_client, monkeypatch):
    """GET /api/ledger/calibration must respond instantly without burning external LLM tokens."""
    from backend.app.core.config import settings

    _, client = db_session_and_client
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaFakeKeyMustNotBeCalled")

    def _forbid_llm(*args, **kwargs):
        raise AssertionError("GET /api/ledger/calibration must not call _call_external_llm!")

    monkeypatch.setattr("backend.app.services.ai_evaluator._call_external_llm", _forbid_llm)

    resp = client.get("/api/ledger/calibration")
    assert resp.status_code == 200
    assert resp.json()["kpi"]["unique_benchmarked"] == 19

