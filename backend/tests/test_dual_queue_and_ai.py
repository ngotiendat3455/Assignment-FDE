import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.models.queue import JobStatus
from backend.app.services.dispatcher import send_rate_limiter
from backend.app.services.ingestion import ingest_seed_pack
from backend.app.services.queue_worker import process_pending_jobs


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session with Foreign Keys enabled."""
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
    """Authenticated FastAPI TestClient bound to the isolated test session."""
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


def test_high_fit_profiles_p002_and_p003(db_session):
    """
    Acceptance Criterion 1:
    Test High Fit (P002 @minh_quant, P003 @dr_somchai_ai):
    - Scored is_match = True, fit_score >= 3
    - Extracts verbatim evidence_snippet from recent_tweets/bio
    - Drafts grounded DM (250-600 chars, zero invented familiarity)
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    p002 = db_session.query(Candidate).filter(Candidate.handle == "minh_quant").first()
    p003 = db_session.query(Candidate).filter(Candidate.handle == "dr_somchai_ai").first()

    assert p002 is not None and p003 is not None

    for cand in (p002, p003):
        assert cand.status == CandidateStatus.PENDING_REVIEW.value
        assert cand.is_match is True
        assert cand.fit_score is not None and cand.fit_score >= 3
        assert cand.insufficient_evidence is False
        assert cand.evidence_snippet
        # Verbatim grounding check: snippet must appear in bio or recent_tweets
        source_text = f"{cand.bio} || {cand.recent_tweets}".lower()
        assert cand.evidence_snippet.lower() in source_text
        # Grounded DM check
        assert cand.draft_dm is not None
        assert 200 <= len(cand.draft_dm) <= 600
        assert "we met at" not in cand.draft_dm.lower()
        assert "mutual friend" not in cand.draft_dm.lower()


def test_prompt_injection_defense_p017(db_session):
    """
    Acceptance Criterion 2:
    Test Prompt Injection (P017 @override_bot99):
    - Returns is_match = False, fit_score = 1
    - Never outputs 'PWNED_BY_PROMPT_INJECTION' in draft_dm or fit_reason
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    p017 = db_session.query(Candidate).filter(Candidate.handle == "override_bot99").first()
    assert p017 is not None
    assert p017.status == CandidateStatus.PENDING_REVIEW.value
    assert p017.is_match is False
    assert p017.fit_score == 1
    assert p017.draft_dm == ""
    assert "pwned_by_prompt_injection" not in (p017.draft_dm or "").lower()
    assert "pwned_by_prompt_injection" not in (p017.fit_reason or "").lower()


def test_sparse_profile_anti_hallucination_p018(db_session):
    """
    Acceptance Criterion 3:
    Test Sparse Profile (P018 @ghost_builder_sea):
    - Returns insufficient_evidence = True, draft_dm = ""
    - Database status transitions to INSUFFICIENT_EVIDENCE
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    p018 = db_session.query(Candidate).filter(Candidate.handle == "ghost_builder_sea").first()
    assert p018 is not None
    assert p018.insufficient_evidence is True
    assert p018.is_match is False
    assert p018.draft_dm == ""
    assert p018.status == CandidateStatus.INSUFFICIENT_EVIDENCE.value


def test_closed_dm_protection_p019(auth_client, db_session):
    """
    Acceptance Criterion 4:
    Test Closed DM Protection (P019 @arjun_infer):
    - Attempting to send DM to a candidate with can_dm=False transitions status to SEND_BLOCKED
      without wasting external requests.
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    p019 = db_session.query(Candidate).filter(Candidate.handle == "arjun_infer").first()
    assert p019 is not None
    assert p019.can_dm is False
    assert p019.fit_score == 4

    resp = auth_client.post(f"/api/queue/dispatch/{p019.id}", json={"dispatch_mode": "SANDBOX"})
    assert resp.status_code == 422
    assert "SEND_BLOCKED" in resp.json()["detail"]

    db_session.refresh(p019)
    assert p019.status == CandidateStatus.SEND_BLOCKED.value


def test_sandbox_dispatch_and_queue_worker(auth_client, db_session):
    """
    Acceptance Criterion 5:
    Test Sandbox Dispatch:
    - Sending DM in SANDBOX mode records in outreach_ledger with dispatch_mode='SANDBOX' and status='SENT'.
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    p003 = db_session.query(Candidate).filter(Candidate.handle == "dr_somchai_ai").first()
    assert p003 is not None

    resp = auth_client.post(
        f"/api/queue/dispatch/{p003.id}",
        json={"dispatch_mode": "SANDBOX", "use_queue_job": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == JobStatus.COMPLETED.value
    assert data["result"]["ledger"]["dispatch_mode"] == "SANDBOX"
    assert data["result"]["ledger"]["status"] == OutreachStatus.SENT.value

    db_session.refresh(p003)
    assert p003.status == CandidateStatus.SENT.value


def test_live_x_safety_whitelist_and_ai_failed_isolation(auth_client, db_session):
    """
    Acceptance Criterion 6 & Error Isolation:
    - In LIVE_X mode, sending to a handle NOT in ALLOWED_TEST_HANDLES (@wei_devtools) is blocked
      and transitions candidate to SEND_BLOCKED; while whitelisted (@minh_quant) succeeds.
    - Simulated LLM error transitions candidate to AI_FAILED (not a low score).
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    # 1. Non-whitelisted handle in LIVE_X mode -> Blocked (SEND_BLOCKED)
    non_whitelisted = db_session.query(Candidate).filter(Candidate.handle == "wei_devtools").first()
    assert non_whitelisted is not None

    block_resp = auth_client.post(
        f"/api/queue/dispatch/{non_whitelisted.id}",
        json={
            "dispatch_mode": "LIVE_X",
            "allowed_test_handles": ["minh_quant", "linhtran_robo"],
        },
    )
    assert block_resp.status_code == 422
    assert "ALLOWED_TEST_HANDLES" in block_resp.json()["detail"]

    db_session.refresh(non_whitelisted)
    assert non_whitelisted.status == CandidateStatus.SEND_BLOCKED.value

    # 2. Whitelisted handle in LIVE_X mode -> Allowed (SENT)
    whitelisted = db_session.query(Candidate).filter(Candidate.handle == "minh_quant").first()
    assert whitelisted is not None

    allow_resp = auth_client.post(
        f"/api/queue/dispatch/{whitelisted.id}",
        json={
            "dispatch_mode": "LIVE_X",
            "allowed_test_handles": ["minh_quant", "linhtran_robo"],
        },
    )
    assert allow_resp.status_code == 200
    assert allow_resp.json()["ledger"]["dispatch_mode"] == "LIVE_X"
    assert allow_resp.json()["ledger"]["status"] == OutreachStatus.SENT.value

    # 3. Simulated LLM outage -> AI_FAILED (never a fake low score)
    keng = db_session.query(Candidate).filter(Candidate.handle == "keng_agribots").first()
    assert keng is not None
    fail_resp = auth_client.post(
        f"/api/queue/evaluate/{keng.id}",
        json={"simulate_failure": True},
    )
    assert fail_resp.status_code == 200
    assert fail_resp.json()["status"] == CandidateStatus.AI_FAILED.value

    # Retry AI evaluation -> recovers to PENDING_REVIEW with fit_score = 4
    recover_resp = auth_client.post(
        f"/api/queue/evaluate/{keng.id}",
        json={"simulate_failure": False},
    )
    assert recover_resp.status_code == 200
    assert recover_resp.json()["status"] == CandidateStatus.PENDING_REVIEW.value
    assert recover_resp.json()["evaluation"]["fit_score"] == 4


def test_regenerate_dm_preserves_fit_assessment_and_updates_draft(auth_client, db_session):
    """
    Clicking 'Regenerate with AI' inside Personalized DM Composer must ONLY regenerate
    draft_dm (returning a fresh variation and clearing stale edited_dm), while keeping
    fit_score and fit_reason ('AI Fit Assessment / Why They Fit') intact.
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    target = db_session.query(Candidate).filter(Candidate.handle == "dr_somchai_ai").first()
    assert target is not None
    original_fit_score = target.fit_score
    original_fit_reason = target.fit_reason
    original_draft = target.draft_dm

    # Simulate stale user edit shadowing draft_dm
    target.edited_dm = "Stale manual draft edit"
    db_session.commit()

    regen_resp = auth_client.post(
        f"/api/candidates/{target.id}/regenerate-dm",
        json={"current_dm": original_draft},
    )
    assert regen_resp.status_code == 200
    body = regen_resp.json()

    db_session.refresh(target)
    assert body["candidate"]["fit_score"] == original_fit_score
    assert body["candidate"]["fit_reason"] == original_fit_reason
    assert body["candidate"]["edited_dm"] is None
    assert target.edited_dm is None
    assert body["draft_dm"] != original_draft
    assert body["draft_dm"] != "Stale manual draft edit"
    assert 120 <= len(body["draft_dm"]) <= 600

    # Sparse profile -> HTTP 422 without modifying fit_reason
    sparse = db_session.query(Candidate).filter(Candidate.handle == "ghost_builder_sea").first()
    assert sparse is not None
    sparse_reason = sparse.fit_reason
    sparse_resp = auth_client.post(
        f"/api/candidates/{sparse.id}/regenerate-dm",
        json={},
    )
    assert sparse_resp.status_code == 422
    db_session.refresh(sparse)
    assert sparse.fit_reason == sparse_reason

    # Sent candidate -> HTTP 409 Conflict
    minh = db_session.query(Candidate).filter(Candidate.handle == "minh_quant").first()
    assert minh is not None
    send_resp = auth_client.post(f"/api/candidates/{minh.id}/send", json={})
    assert send_resp.status_code == 200
    sent_regen_resp = auth_client.post(f"/api/candidates/{minh.id}/regenerate-dm", json={})
    assert sent_regen_resp.status_code == 409


def test_partner_override_fit_score_with_reason(auth_client, db_session):
    """
    Partner Fit Score Override (POST /api/candidates/{id}/override-fit):
    - Allows overriding fit_score (1-4) with mandatory rationale.
    - Prefixes fit_reason with '[Partner Override (X/4)] ...', updates is_match,
      and populates an initial grounded draft_dm when upgraded to >=3.
    - Protects terminal SENT/REPLIED candidates with HTTP 409 Conflict.
    """
    ingest_seed_pack(db_session)
    process_pending_jobs(db_session, job_type="AI_EVALUATE")

    # Find a low-score candidate (Score 2, draft_dm="") and upgrade to 4/4
    low_cand = db_session.query(Candidate).filter(Candidate.fit_score == 2).first()
    assert low_cand is not None
    assert (low_cand.draft_dm or "") == ""

    up_resp = auth_client.post(
        f"/api/candidates/{low_cand.id}/override-fit",
        json={
            "fit_score": 4,
            "reason": "Met founder at Vietnam AI Summit; deep unpublished CUDA kernel work.",
        },
    )
    assert up_resp.status_code == 200
    up_body = up_resp.json()
    assert up_body["fit_score"] == 4
    assert up_body["is_match"] is True
    assert up_body["fit_reason"].startswith("[Partner Override (4/4)] Met founder at Vietnam AI Summit")
    assert len(up_body["draft_dm"] or "") >= 120

    # Downgrade to 1/4
    down_resp = auth_client.post(
        f"/api/candidates/{low_cand.id}/override-fit",
        json={
            "fit_score": 1,
            "reason": "Out of thesis scope after deeper portfolio review.",
        },
    )
    assert down_resp.status_code == 200
    down_body = down_resp.json()
    assert down_body["fit_score"] == 1
    assert down_body["is_match"] is False
    assert down_body["fit_reason"] == "[Partner Override (1/4)] Out of thesis scope after deeper portfolio review."

    # Terminal SENT candidate -> HTTP 409 Conflict
    minh = db_session.query(Candidate).filter(Candidate.handle == "minh_quant").first()
    assert minh is not None
    auth_client.post(f"/api/candidates/{minh.id}/send", json={})
    sent_override = auth_client.post(
        f"/api/candidates/{minh.id}/override-fit",
        json={"fit_score": 3, "reason": "Attempt override after send"},
    )
    assert sent_override.status_code == 409



