import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.services.ingestion import (
    XApiLookupError,
    normalize_handle,
    parse_csv_content,
    preflight_csv_check,
    ingest_candidate_batch,
    ingest_seed_pack,
    lookup_x_handle,
)
from backend.scripts.x_simulator import simulator_app


@pytest.fixture
def db_session():
    """Create an isolated SQLite database session for unit tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_normalize_handle():
    """Verify handle normalization strips @, whitespace, quotes, and converts to lowercase."""
    assert normalize_handle("@Minh_Quant ") == "minh_quant"
    assert normalize_handle("  @Dr_Somchai_AI  ") == "dr_somchai_ai"
    assert normalize_handle("wei_devtools") == "wei_devtools"
    assert normalize_handle('"@linhtran_robo"') == "linhtran_robo"
    assert normalize_handle("https://x.com/Minh_Quant?s=20") == "minh_quant"
    assert normalize_handle("https://twitter.com/dr_somchai_ai/") == "dr_somchai_ai"
    assert normalize_handle(None) == ""


def test_parse_csv_missing_required_column():
    """Verify parser rejects CSV missing required columns (e.g. bio or recent_tweets)."""
    bad_csv = """handle,name,location
minh_quant,Minh Nguyen,Hanoi"""
    with pytest.raises(ValueError, match="Missing required column for Bio"):
        parse_csv_content(bad_csv)


def test_in_batch_deduplication(db_session):
    """Verify that multiple records with the same handle in a single CSV are deduplicated."""
    csv_text = """handle,name,bio,recent_tweets
minh_quant,Minh Nguyen,Bio 1,Tweet 1
MINH_QUANT,Minh Duplicate,Bio 2,Tweet 2
@minh_quant,Minh Triplicate,Bio 3,Tweet 3
dr_somchai,Dr Somchai,Bio 4,Tweet 4"""

    parsed = parse_csv_content(csv_text)
    report = ingest_candidate_batch(db_session, parsed)

    assert report["total_rows"] == 4
    assert report["imported"] == 2  # Only minh_quant and dr_somchai
    assert report["in_batch_duplicates_skipped"] == 2

    candidates = db_session.query(Candidate).all()
    assert len(candidates) == 2
    handles = [c.handle for c in candidates]
    assert "minh_quant" in handles
    assert "dr_somchai" in handles


def test_idempotent_csv_reimport(db_session):
    """Verify that re-importing the same CSV multiple times does not create duplicates."""
    csv_text = """handle,name,bio,recent_tweets
wei_devtools,Wei Jie Lim,Devtools founder,Shipped v0.9"""

    parsed = parse_csv_content(csv_text)
    report1 = ingest_candidate_batch(db_session, parsed)
    assert report1["imported"] == 1
    assert report1["already_in_db_skipped"] == 0

    # Second import of same candidate
    report2 = ingest_candidate_batch(db_session, parsed)
    assert report2["imported"] == 0
    assert report2["already_in_db_skipped"] == 1

    count = db_session.query(Candidate).filter(Candidate.handle == "wei_devtools").count()
    assert count == 1


def test_ledger_past_outreach_protection(db_session):
    """Verify that an account already in outreach_ledger is flagged and mapped to past status."""
    # 1. Create a candidate and mark them in outreach ledger as REPLIED
    past_cand = Candidate(
        handle="linhtran_robo",
        name="Linh Tran",
        bio="Robotics Founder",
        recent_tweets="Warehouse pilot completed",
        status=CandidateStatus.REPLIED.value,
    )
    db_session.add(past_cand)
    db_session.commit()

    ledger_entry = OutreachLedger(
        candidate_id=past_cand.id,
        handle="linhtran_robo",
        idempotency_key="test-key-101",
        sent_message="Hi Linh, congrats on pilot",
        dispatch_mode="SANDBOX",
        status=OutreachStatus.REPLIED.value,
        needs_attention=True,
    )
    db_session.add(ledger_entry)
    db_session.commit()

    # 2. Re-ingest linhtran_robo in a new CSV batch
    csv_text = """handle,name,bio,recent_tweets
linhtran_robo,Linh Tran Updated,New Bio,New Tweets"""
    parsed = parse_csv_content(csv_text)
    report = ingest_candidate_batch(db_session, parsed)

    # Should detect existing candidate in DB and skip duplicate insertion
    assert report["already_in_db_skipped"] == 1

    # Ledger record must still be intact
    ledger = db_session.query(OutreachLedger).filter(OutreachLedger.handle == "linhtran_robo").first()
    assert ledger is not None
    assert ledger.status == OutreachStatus.REPLIED.value
    assert ledger.needs_attention is True


def test_preflight_csv_check_valid_and_missing():
    """Verify pre-flight check returns 5 preview rows on valid CSV and flags missing columns."""
    valid_csv = """handle,name,bio,recent_tweets
@minh_quant,Minh Nguyen,AI Researcher,Published 3 papers
dr_somchai_ai,Dr. Somchai,Healthcare AI,Hospital deployment"""
    res_valid = preflight_csv_check(valid_csv)
    assert res_valid["valid"] is True
    assert res_valid["total_rows"] == 2
    assert len(res_valid["preview_rows"]) == 2
    assert res_valid["preview_rows"][0]["handle"] == "@minh_quant"

    invalid_csv = """handle,name,recent_tweets
@minh_quant,Minh Nguyen,Published 3 papers"""
    res_invalid = preflight_csv_check(invalid_csv)
    assert res_invalid["valid"] is False
    assert "bio" in res_invalid["missing_columns"]


def test_ingest_seed_pack_full_audit(db_session):
    """Verify 1-Click Seed Pack loads 20 rows, merges 1 in-batch duplicate, and protects 3 sent/replied."""
    report = ingest_seed_pack(db_session)
    assert report["total_rows"] == 20
    assert report["in_batch_duplicates_skipped"] == 1
    assert "minh_quant" in report["duplicate_handles"]
    assert report["queued_for_ai_count"] == 16
    assert report["already_contacted_in_ledger"] == 3
    collision_handles = [c["handle"] for c in report["collision_details"]]
    assert "linhtran_robo" in collision_handles
    assert "putri_agentic" in collision_handles
    assert "harith_medai" in collision_handles


def _patch_httpx_to_simulator(monkeypatch):
    """Route httpx.Client traffic in ingestion service directly to Local X Simulator."""
    sim_client = TestClient(simulator_app)

    def _handler(request: httpx.Request) -> httpx.Response:
        path_qs = request.url.raw_path.decode("ascii")
        resp = sim_client.request(
            method=request.method,
            url=path_qs,
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
        )

    real_client = httpx.Client
    transport = httpx.MockTransport(_handler)

    def _sim_client(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(settings, "X_API_BASE_URL", "http://127.0.0.1:8099/2")
    monkeypatch.setattr("backend.app.services.ingestion.httpx.Client", _sim_client)


def test_lookup_x_handle_errors_and_simulator(db_session, monkeypatch):
    """Verify silent fallbacks are gone: missing key -> 503, HTTP errors -> exact status, simulator -> valid response."""
    # 1. Missing X_BEARER_TOKEN fails explicitly with 503 (no synthetic/seed fallback)
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "")
    with pytest.raises(XApiLookupError) as exc_unconfigured:
        lookup_x_handle(db_session, "@minh_quant")
    assert exc_unconfigured.value.status_code == 503

    # 2. Wire to Local X API v2 Simulator via ASGI transport ($0 HTTP simulation)
    _patch_httpx_to_simulator(monkeypatch)
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "sim_test_bearer_token")

    res_seed = lookup_x_handle(db_session, "@minh_quant")
    assert res_seed["handle"] == "minh_quant"
    assert res_seed["source_mode"] == "X_API_SIMULATOR"
    assert res_seed["can_dm"] is True
    assert res_seed["x_user_id"] == "1000000002"

    res_closed = lookup_x_handle(db_session, "https://x.com/arjun_infer")
    assert res_closed["handle"] == "arjun_infer"
    assert res_closed["can_dm"] is False

    res_custom = lookup_x_handle(db_session, "@new_sea_builder")
    assert res_custom["handle"] == "new_sea_builder"
    assert res_custom["source_mode"] == "X_API_SIMULATOR"
    assert res_custom["x_user_id"].isdigit()

    # 3. Real HTTP error status propagation (401, 402, 403, 404, 429)
    for bad_handle, expected_status in [
        ("@sim_401", 401),
        ("@credits_depleted", 402),
        ("@forbidden_handle", 403),
        ("@missing_user", 404),
        ("@rate_limit", 429),
    ]:
        with pytest.raises(XApiLookupError) as exc_info:
            lookup_x_handle(db_session, bad_handle)
        assert exc_info.value.status_code == expected_status

    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "bad_token")
    with pytest.raises(XApiLookupError) as exc_bad_tok:
        lookup_x_handle(db_session, "@minh_quant")
    assert exc_bad_tok.value.status_code == 401


def test_ingestion_api_endpoints(db_session, monkeypatch):
    """Verify FastAPI ingestion endpoints end-to-end using TestClient (including Auth Guard)."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # 0. Unauthenticated request must be blocked with 401 by Auth Guard Middleware
    unauth_resp = client.post("/api/ingestion/seed", json={})
    assert unauth_resp.status_code == 401

    # Authenticate as Partner
    login_resp = client.post("/api/auth/demo-login")
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    # 1. Seed Pack endpoint
    seed_resp = client.post("/api/ingestion/seed", json={})
    assert seed_resp.status_code == 200
    seed_data = seed_resp.json()
    assert seed_data["total_rows"] == 20
    assert seed_data["queued_for_ai_count"] == 16
    assert seed_data["already_contacted_in_ledger"] == 3

    # 2. Pre-flight check endpoint
    csv_sample = "handle,name,bio,recent_tweets\n@custom_founder,Custom Founder,Building robotics in SG,Shipped v2"
    pre_resp = client.post("/api/ingestion/preflight", json={"csv_content": csv_sample})
    assert pre_resp.status_code == 200
    assert pre_resp.json()["valid"] is True

    # 3. Live X Lookup endpoint: unconfigured -> 503; via simulator -> 200; 402 -> 402
    unconf_resp = client.get("/api/ingestion/x-lookup", params={"handle": "@minh_quant"})
    assert unconf_resp.status_code == 503

    _patch_httpx_to_simulator(monkeypatch)
    monkeypatch.setattr(settings, "X_BEARER_TOKEN", "sim_test_bearer_token")

    lookup_resp = client.get("/api/ingestion/x-lookup", params={"handle": "@minh_quant"})
    assert lookup_resp.status_code == 200
    assert lookup_resp.json()["handle"] == "minh_quant"
    assert lookup_resp.json()["source_mode"] == "X_API_SIMULATOR"

    quota_resp = client.get("/api/ingestion/x-lookup", params={"handle": "@credits_depleted"})
    assert quota_resp.status_code == 402
    assert "credits depleted" in quota_resp.json()["detail"].lower()

    # 4. Single Candidate Ingest endpoint
    single_resp = client.post(
        "/api/ingestion/single",
        json={
            "handle": "@custom_founder",
            "name": "Custom Founder",
            "bio": "Building robotics in SG",
            "recent_tweets": "Shipped v2",
            "can_dm": True,
        },
    )
    assert single_resp.status_code == 200
    assert single_resp.json()["imported"] == 1

    app.dependency_overrides.clear()


