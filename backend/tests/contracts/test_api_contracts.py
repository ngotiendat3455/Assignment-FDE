import difflib
import json
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.security import DEFAULT_PARTNER_EMAIL, DEFAULT_PARTNER_PASSWORD
from backend.app.core.tracing import (
    capture_db_snapshot,
    finish_flow_session,
    start_flow_session,
)
from backend.app.main import app
from backend.app.models.candidate import CandidateStatus
from backend.app.services.ingestion import seed_history_ledger
from backend.app.services.queue_worker import process_pending_jobs

CONTRACTS_DIR = Path(__file__).resolve().parent
EXPECTED_DIR = CONTRACTS_DIR / "expected"
PROJECT_ROOT = CONTRACTS_DIR.parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "tests" / "manual" / "results"


def assert_matches_expected_json(expected_name: str, actual: Dict[str, Any]) -> None:
    """Compare normalized JSON payload against golden reference file and write diff on mismatch."""
    expected_path = EXPECTED_DIR / expected_name
    expected_obj = json.loads(expected_path.read_text(encoding="utf-8"))

    expected_str = json.dumps(expected_obj, indent=2, sort_keys=True) + "\n"
    actual_str = json.dumps(actual, indent=2, sort_keys=True) + "\n"

    if expected_str != actual_str:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        diff_lines = list(
            difflib.unified_diff(
                expected_str.splitlines(keepends=True),
                actual_str.splitlines(keepends=True),
                fromfile=f"expected/{expected_name}",
                tofile=f"actual/{expected_name}",
            )
        )
        diff_path = RESULTS_DIR / f"contract-diff-{expected_name}.txt"
        diff_path.write_text("".join(diff_lines), encoding="utf-8")
        pytest.fail(
            f"Contract mismatch vs expected/{expected_name}. Diff saved to {diff_path}\n"
            + "".join(diff_lines)
        )


CONTRACT_FLOW_META: Dict[str, Dict[str, Any]] = {
    "test_contract_auth_login_me_and_401": {
        "id": "CT-01-auth-login-me-401",
        "flow_ref": "Feature 03 (API Auth Contract & Private 401 Guard)",
        "title": "Verify unauthenticated 401 block, Partner login contract & /api/auth/me",
        "expected_states": [],
        "forbidden": ["Unauthenticated /api/candidates ↛ 200 (Must be 401)"],
    },
    "test_contract_preflight_missing_bio_golden_diff": {
        "id": "CT-02-preflight-missing-bio",
        "flow_ref": "Feature 01 / ER-data-packing (CSV Pre-flight Contract)",
        "title": "Golden JSON diff for CSV pre-flight missing 'bio' column guard",
        "expected_states": [],
        "forbidden": ["Missing bio CSV ↛ valid=true"],
    },
    "test_contract_seed_summary_nested_shape_bug01": {
        "id": "CT-03-seed-summary-bug01",
        "flow_ref": "testing/e2e.md E2E-01 + BUG-01 (Nested StateMachineSummary Contract)",
        "title": "Verify Seed Ingestion audit + Golden nested state-summary contract",
        "expected_states": ["QUEUED_FOR_AI", "PENDING_REVIEW", "INSUFFICIENT_EVIDENCE", "SENT", "REPLIED"],
        "forbidden": ["Flat state-summary response (BUG-01)"],
    },
    "test_contract_csv_flags_and_cross_batch_dedup_bug03": {
        "id": "CT-04-csv-dedup-bug03",
        "flow_ref": "testing/e2e.md E2E-07 + ER-data-packing (T1..T3 Cross-Batch Dedup & BUG-03)",
        "title": "Verify queue_ai_enabled=False leaves QUEUED_FOR_AI & preserves REPLIED",
        "expected_states": ["QUEUED_FOR_AI", "REPLIED"],
        "forbidden": ["REPLIED ↛ QUEUED_FOR_AI on CSV re-import"],
    },
    "test_contract_dispatch_mode_bug02_and_guards_409_422": {
        "id": "CT-05-dispatch-guards-409-422",
        "flow_ref": "testing/e2e.md E2E-01, E2E-03, E2E-06, E2E-08 + BUG-02",
        "title": "Verify LIVE_X dispatch_mode forwarding, 409 double-send guard, and 422 closed-DM/ledger guards",
        "expected_states": ["PENDING_REVIEW", "SENT", "SEND_BLOCKED", "REPLIED"],
        "forbidden": ["SENT ↛ SENT (409)", "can_dm=false ↛ SENT (422)", "BLOCKED ↛ REPLIED (422)"],
    },
    "test_contract_calibration_kpi_golden_diff": {
        "id": "CT-06-calibration-kpi",
        "flow_ref": "testing/e2e.md E2E-08 + ER-F5-F6 T4 (Calibration Matrix KPI)",
        "title": "Golden JSON diff for Partner Calibration Matrix KPI (100% alignment)",
        "expected_states": [],
        "forbidden": ["Alignment Accuracy < 100%"],
    },
}


@pytest.fixture()
def contract_client(request):
    """Isolated in-memory SQLite client for Fail-Fast Tier 1 Contract tests."""
    prev_trace = settings.TRACE_REQUESTS
    settings.TRACE_REQUESTS = True

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
    db = TestingSession()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    client = TestClient(app)

    meta = CONTRACT_FLOW_META.get(
        request.node.name,
        {
            "id": f"CT-{request.node.name}",
            "flow_ref": "Tier 1 Contract",
            "title": request.node.name,
            "expected_states": [],
            "forbidden": [],
        },
    )
    tc_id = meta["id"]
    start_flow_session(
        testcase_id=tc_id,
        flow_ref=meta["flow_ref"],
        title=meta["title"],
        expected_states=meta["expected_states"],
        forbidden_transitions=meta["forbidden"],
        db_snapshot=capture_db_snapshot(db),
        reset_file=True,
    )

    yield client, db

    failed = hasattr(request.node, "rep_call") and request.node.rep_call.failed
    finish_flow_session(
        testcase_id=tc_id,
        status="FAILED" if failed else "PASSED",
        db_snapshot=capture_db_snapshot(db),
    )
    app.dependency_overrides.clear()
    settings.TRACE_REQUESTS = prev_trace
    db.close()


def _auth_headers(client: TestClient) -> Dict[str, str]:
    login_resp = client.post(
        "/api/auth/login",
        json={"email": DEFAULT_PARTNER_EMAIL, "password": DEFAULT_PARTNER_PASSWORD},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_contract_auth_login_me_and_401(contract_client):
    client, _ = contract_client

    # Unauthenticated private route MUST fail with 401
    unauth = client.get("/api/candidates")
    assert unauth.status_code == 401

    login_resp = client.post(
        "/api/auth/login",
        json={"email": DEFAULT_PARTNER_EMAIL, "password": DEFAULT_PARTNER_PASSWORD},
    )
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert set(body.keys()) >= {"access_token", "token_type", "user"}
    assert body["user"]["email"] == DEFAULT_PARTNER_EMAIL
    assert body["user"]["role"] == "partner"
    assert "session_token" in login_resp.cookies

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == DEFAULT_PARTNER_EMAIL


def test_contract_preflight_missing_bio_golden_diff(contract_client):
    client, _ = contract_client
    headers = _auth_headers(client)

    bad_csv = "handle,name,recent_tweets\n@minh_quant,Minh Nguyen,Built AWQ kernel\n"
    resp = client.post(
        "/api/ingestion/preflight",
        headers=headers,
        json={"csv_content": bad_csv},
    )
    assert resp.status_code == 200
    assert_matches_expected_json("preflight_missing_bio.json", resp.json())


def test_contract_seed_summary_nested_shape_bug01(contract_client):
    client, db = contract_client
    headers = _auth_headers(client)

    history_csv = PROJECT_ROOT / "genai-outreach-pack" / "outreach_history_log.csv"
    seed_history_ledger(db, history_csv)

    seed_resp = client.post("/api/ingestion/seed", headers=headers, json={})
    assert seed_resp.status_code == 200
    seed_data = seed_resp.json()
    assert seed_data["queued_for_ai_count"] == 16
    assert seed_data["in_batch_duplicates_skipped"] == 1
    assert seed_data["already_contacted_in_ledger"] == 3

    summary_resp = client.get("/api/candidates/state-summary", headers=headers)
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # Guard BUG-01: Must match nested Frontend TypeScript StateMachineSummary contract
    assert "state_counts" in summary and "ledger_summary" in summary
    assert_matches_expected_json("state_summary_initial_seed.json", summary)


def test_contract_csv_flags_and_cross_batch_dedup_bug03(contract_client):
    client, db = contract_client
    headers = _auth_headers(client)

    history_csv = PROJECT_ROOT / "genai-outreach-pack" / "outreach_history_log.csv"
    seed_history_ledger(db, history_csv)

    # Guard BUG-03: queue_ai_enabled=False leaves candidate at QUEUED_FOR_AI & preserves REPLIED
    csv_payload = (
        "handle,name,location,bio,recent_tweets,can_dm,segment\n"
        "@linhtran_robo,Linh Tran,Singapore,Robotics founder,Deployed warehouse fleet,true,SEG-01\n"
        "@e2e_contract_new,E2E Builder,Hanoi,Systems AI founder,Rust CUDA inference engine,true,SEG-02\n"
        "@e2e_contract_new,E2E Builder,Hanoi,Duplicate row,Duplicate tweet,true,SEG-02\n"
    )
    resp = client.post(
        "/api/ingestion/csv",
        headers=headers,
        json={
            "csv_content": csv_payload,
            "skip_ledger_collisions": True,
            "queue_ai_enabled": False,
        },
    )
    assert resp.status_code == 200
    audit = resp.json()
    assert audit["imported"] == 1
    assert audit["queued_for_ai_count"] == 1
    assert audit["in_batch_duplicates_skipped"] == 1
    assert audit["already_contacted_in_ledger"] == 1

    # Verify queued candidate stayed QUEUED_FOR_AI and @linhtran_robo remained REPLIED
    list_resp = client.get("/api/candidates", headers=headers)
    assert list_resp.status_code == 200
    by_handle = {item["handle"]: item for item in list_resp.json()["items"]}
    assert by_handle["e2e_contract_new"]["status"] == CandidateStatus.QUEUED_FOR_AI.value
    assert by_handle["linhtran_robo"]["status"] == CandidateStatus.REPLIED.value


def test_contract_dispatch_mode_bug02_and_guards_409_422(contract_client):
    client, db = contract_client
    headers = _auth_headers(client)

    history_csv = PROJECT_ROOT / "genai-outreach-pack" / "outreach_history_log.csv"
    seed_history_ledger(db, history_csv)
    assert client.post("/api/ingestion/seed", headers=headers, json={}).status_code == 200
    process_pending_jobs(db, job_type="AI_EVALUATE")

    items = client.get("/api/candidates", headers=headers).json()["items"]
    by_handle = {i["handle"]: i for i in items}

    # 1. Guard BUG-02: sending dispatch_mode="LIVE_X" on whitelisted @minh_quant records LIVE_X
    minh = by_handle["minh_quant"]
    send_resp = client.post(
        f"/api/candidates/{minh['id']}/send",
        headers=headers,
        json={
            "custom_message": "Hi Minh — contract test LIVE_X message",
            "idempotency_key": "contract-live-minh-001",
            "dispatch_mode": "LIVE_X",
        },
    )
    assert send_resp.status_code == 200
    send_body = send_resp.json()
    assert send_body["candidate"]["status"] == "SENT"
    assert send_body["ledger"]["dispatch_mode"] == "LIVE_X"

    # 2. Second send on @minh_quant -> 409 Conflict
    dup_resp = client.post(
        f"/api/candidates/{minh['id']}/send",
        headers=headers,
        json={"custom_message": "Double send attempt"},
    )
    assert dup_resp.status_code == 409

    # 3. Closed DM @arjun_infer -> 422 Unprocessable Entity
    arjun = by_handle["arjun_infer"]
    blocked_resp = client.post(
        f"/api/candidates/{arjun['id']}/send",
        headers=headers,
        json={"custom_message": "Attempt closed DM"},
    )
    assert blocked_resp.status_code == 422

    # 4. Ledger reply on BLOCKED OUT-104 -> 422 Unprocessable Entity
    ledger_items = client.get("/api/ledger", headers=headers).json()["items"]
    out_104 = next(x for x in ledger_items if x["outreach_id"] == "OUT-104")
    reply_blocked = client.post(
        f"/api/ledger/{out_104['id']}/reply",
        headers=headers,
        json={"reply_text": "Should be rejected", "needs_attention": True},
    )
    assert reply_blocked.status_code == 422


def test_contract_calibration_kpi_golden_diff(contract_client):
    client, _ = contract_client
    headers = _auth_headers(client)

    resp = client.get("/api/ledger/calibration", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"kpi", "items"}
    assert_matches_expected_json("calibration_kpi.json", data["kpi"])

