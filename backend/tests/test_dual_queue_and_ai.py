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

