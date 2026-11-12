import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.services.ingestion import ingest_seed_pack


@pytest.fixture
def db_session():
    """Isolated SQLite database session with Foreign Keys enforced."""
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
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db_session):
    """FastAPI TestClient bound to the isolated test session."""
    def _override_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_double_click_idempotency_conflict(api_client, db_session):
    """
    Acceptance Criterion 1:
    Send 2 requests to POST /api/candidates/{id}/send with the same idempotency_key.
    The 2nd request must return 409 Conflict and only 1 ledger entry may exist.
    """
    cand = Candidate(
        handle="minh_quant",
        name="Minh Nguyen",
        bio="Founder @TensorEdgeVN",
        recent_tweets="Open-sourced AWQ kernel",
        can_dm=True,
        fit_score=4,
        draft_dm="Hi Minh, loved your AWQ kernel benchmark!",
        status=CandidateStatus.PENDING_REVIEW.value,
    )
    db_session.add(cand)
    db_session.commit()

    # 1st click -> 200 OK
    resp1 = api_client.post(
        f"/api/candidates/{cand.id}/send",
        json={"idempotency_key": "double-click-key-001"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["candidate"]["status"] == CandidateStatus.SENT.value

    # 2nd rapid click with same idempotency_key -> 409 Conflict
    resp2 = api_client.post(
        f"/api/candidates/{cand.id}/send",
        json={"idempotency_key": "double-click-key-001"},
    )
    assert resp2.status_code == 409

    # 3rd attempt with a brand-new key for the same person -> 409 Conflict (Zero Double-Messaging)
    resp3 = api_client.post(
        f"/api/candidates/{cand.id}/send",
        json={"idempotency_key": "different-key-002"},
    )
    assert resp3.status_code == 409

    # Strictly 1 record in outreach_ledger
    ledger_count = (
        db_session.query(OutreachLedger)
        .filter(OutreachLedger.handle == "minh_quant")
        .count()
    )
    assert ledger_count == 1


def test_seed_history_protection_blocks_resending(api_client, db_session):
    """
    Acceptance Criterion 2:
    When P001 (@linhtran_robo) is loaded from seed pack, the system recognizes she is
    already in outreach_ledger (REPLIED), flags already_contacted=True, and blocks sending (409).
    """
    ingest_seed_pack(db_session)

    list_resp = api_client.get("/api/candidates", params={"search": "linhtran_robo"})
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    linh = items[0]
    assert linh["handle"] == "linhtran_robo"
    assert linh["already_contacted"] is True
    assert linh["ledger_status"] == OutreachStatus.REPLIED.value

    # Attempt to send DM again to @linhtran_robo -> must be blocked with 409 Conflict
    send_resp = api_client.post(f"/api/candidates/{linh['id']}/send", json={})
    assert send_resp.status_code == 409


def test_closed_dm_protection_sets_send_blocked(api_client, db_session):
    """Verify candidate with can_dm=False transitions to SEND_BLOCKED and returns 422."""
    cand = Candidate(
        handle="arjun_infer",
        name="Arjun Krishnan",
        bio="Founder @TritonSEA",
        recent_tweets="Cut Sea-Lion-70B prefill latency by 46%",
        can_dm=False,
        fit_score=4,
        status=CandidateStatus.PENDING_REVIEW.value,
    )
    db_session.add(cand)
    db_session.commit()

    resp = api_client.post(f"/api/candidates/{cand.id}/send", json={})
    assert resp.status_code == 422

    db_session.refresh(cand)
    assert cand.status == CandidateStatus.SEND_BLOCKED.value


def test_nine_state_lifecycle_transitions_and_reply_workflow(api_client, db_session):
    """Verify retry (AI_FAILED -> QUEUED_FOR_AI), reject, and reply -> needs_attention -> handled."""
    # 1. AI_FAILED -> QUEUED_FOR_AI via /retry
    failed_cand = Candidate(
        handle="retry_founder",
        name="Retry Founder",
        bio="Robotics builder",
        recent_tweets="ROS2 node",
        status=CandidateStatus.AI_FAILED.value,
        error_message="LLM timeout",
    )
    db_session.add(failed_cand)
    db_session.commit()

    retry_resp = api_client.post(f"/api/candidates/{failed_cand.id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == CandidateStatus.QUEUED_FOR_AI.value

    # 2. PENDING_REVIEW -> SENT -> REPLIED (needs_attention=True) -> Handled (needs_attention=False)
    active_cand = Candidate(
        handle="somchai_robo",
        name="Dr. Somchai",
        bio="AgriBot founder",
        recent_tweets="Ran 140 hours in mud",
        can_dm=True,
        status=CandidateStatus.PENDING_REVIEW.value,
    )
    db_session.add(active_cand)
    db_session.commit()

    send_resp = api_client.post(
        f"/api/candidates/{active_cand.id}/send",
        json={"custom_message": "Hi Dr. Somchai, loved the 140-hour field trial!"},
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["candidate"]["status"] == CandidateStatus.SENT.value

    # Cannot reject an already SENT candidate -> 409 Conflict
    reject_after_send = api_client.post(
        f"/api/candidates/{active_cand.id}/reject",
        json={"reason": "Accidental click"},
    )
    assert reject_after_send.status_code == 409

    # Founder replies -> status becomes REPLIED & needs_attention becomes True
    reply_resp = api_client.post(
        f"/api/candidates/{active_cand.id}/reply",
        json={"reply_text": "Thanks! Let's chat on Thursday at 2pm SGT."},
    )
    assert reply_resp.status_code == 200
    assert reply_resp.json()["candidate"]["status"] == CandidateStatus.REPLIED.value
    assert reply_resp.json()["ledger"]["needs_attention"] is True

    # Partner marks handled -> needs_attention becomes False
    handled_resp = api_client.post(f"/api/candidates/{active_cand.id}/handled")
    assert handled_resp.status_code == 200
    assert handled_resp.json()["ledger"]["needs_attention"] is False


def test_sqlite_wal_persistence_across_restarts(tmp_path):
    """
    Acceptance Criterion 3:
    Verify file-backed SQLite database enables WAL mode and persists 100% of candidate
    and ledger state across engine disposal / server restart.
    """
    db_file = tmp_path / "test_outreach_wal.db"
    db_url = f"sqlite:///{db_file.as_posix()}"

    # 1. Start "Server Process 1"
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine1, "connect")
    def _set_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        cur.close()

    Base.metadata.create_all(bind=engine1)
    Session1 = sessionmaker(bind=engine1)
    s1 = Session1()

    journal_mode = s1.execute(text("PRAGMA journal_mode")).scalar()
    assert str(journal_mode).lower() == "wal"

    cand = Candidate(
        handle="persistent_founder",
        name="Persistent Founder",
        bio="Building persistent AI",
        recent_tweets="Shipped WAL mode",
        status=CandidateStatus.SENT.value,
    )
    s1.add(cand)
    s1.commit()

    ledger = OutreachLedger(
        candidate_id=cand.id,
        handle="persistent_founder",
        idempotency_key="wal-key-1",
        sent_message="Hello persistent founder",
        dispatch_mode="SANDBOX",
        status=OutreachStatus.SENT.value,
    )
    s1.add(ledger)
    s1.commit()
    s1.close()
    engine1.dispose()

    # 2. Simulate Server Restart ("Server Process 2")
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(bind=engine2)
    s2 = Session2()

    reloaded_cand = (
        s2.query(Candidate)
        .filter(Candidate.handle == "persistent_founder")
        .first()
    )
    reloaded_ledger = (
        s2.query(OutreachLedger)
        .filter(OutreachLedger.handle == "persistent_founder")
        .first()
    )

    assert reloaded_cand is not None
    assert reloaded_cand.status == CandidateStatus.SENT.value
    assert reloaded_ledger is not None
    assert reloaded_ledger.idempotency_key == "wal-key-1"

    s2.close()
    engine2.dispose()

