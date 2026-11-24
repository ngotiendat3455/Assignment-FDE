"""
Module 03 & Module 05 Convergence Tests (`backend/tests/test_probabilistic_qa_and_verify_gate_4.py`):
1. Dual-Mode Embedding Gateway (`SEMANTIC_CONCEPT_AXES` 10d offline <-> Live Gemini 768d / OpenAI 1536d + Dimension Alignment Guard).
2. `LLM-as-a-Judge` (`judge_dm_quality_with_llm`) catching subtle fake familiarity that bypasses basic regex and fabricated numbers (`5ms` vs `18ms`).
3. Langfuse Python SDK `@observe()` 4-Span Distributed Trace Tree & Scores for `@linhtran_robo`.
4. Gate 4 CLI Verifier (`verify_live_keys.py --mode gate4`) achieving >= 90% on all 4 Probabilistic QA metrics.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.langfuse_tracing import get_last_candidate_trace
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.main import app
from backend.app.models.candidate import Candidate
from backend.app.models.chunk import CandidateChunk
from backend.app.services.ai_evaluator import (
    evaluate_candidate_profile,
    judge_dm_quality_with_llm,
)
from backend.app.services.dispatcher import send_rate_limiter
from backend.app.services.ingestion import ingest_seed_pack
from backend.app.services.rag_retriever import (
    compute_local_concept_embedding,
    compute_semantic_embedding,
    compute_vector_scores,
    sync_candidate_chunks,
)
from backend.scripts.verify_live_keys import run_verify_gate_4_probabilistic_eval


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


def test_dual_mode_embedding_gateway_local_10d_and_live_768d_with_dimension_guard(
    db_session, monkeypatch
):
    """
    AC-1: Verifies Dual-Mode Embedding Gateway:
    - In OFFLINE_MOCK ($0): uses 10-axis `SEMANTIC_CONCEPT_AXES` (`dimensions=10`).
    - In HYBRID_AUTO with `GEMINI_API_KEY`: calls Gemini `text-embedding-004` (`dimensions=768`).
    - Dimension Alignment Guard: if chunks in DB were stored as 10d vectors while query runs in 768d (or vice versa),
      `compute_vector_scores` automatically aligns dimensions so Cosine similarity never returns 0.0 due to mismatch.
    """
    sample_text = (
        "Week 2 of our live 3PL warehouse pilot in Tuas, Singapore. "
        "Active stereo + tactile wrist feedback saved us."
    )

    # 1. OFFLINE_MOCK -> 10d SEMANTIC_CONCEPT_AXES
    monkeypatch.setattr(settings, "RUNTIME_PROFILE", "OFFLINE_MOCK")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaFakeKeyIgnoredInOfflineMock")
    plan_offline = RuntimeGateway.resolve_embedding_plan()
    assert plan_offline.embedding_engine == "LOCAL_CONCEPT_10D"
    assert plan_offline.dimensions == 10

    vec_10d = compute_semantic_embedding(sample_text)
    assert len(vec_10d) == 10
    assert sum(vec_10d) > 0.0

    # 2. HYBRID_AUTO + GEMINI_API_KEY -> 768d Live Gemini Embedding
    monkeypatch.setattr(settings, "RUNTIME_PROFILE", "HYBRID_AUTO")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaSyLiveGeminiTestKey")
    plan_live = RuntimeGateway.resolve_embedding_plan()
    assert plan_live.embedding_engine == "LIVE_GEMINI_EMBEDDING"
    assert plan_live.dimensions == 768

    fake_768_vec = [0.05] * 768
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": {"values": fake_768_vec}}

    with patch("backend.app.services.rag_retriever.httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        vec_768d = compute_semantic_embedding(sample_text)
        assert len(vec_768d) == 768

        # 3. Dimension Alignment Guard: Chunk stored with 10d vector, Query evaluated in 768d mode
        chk = CandidateChunk(
            chunk_id="chk_dim_test_1",
            candidate_handle="linhtran_robo",
            source_type="x_post",
            post_id="185500102",
            text=sample_text,
            token_count=20,
            embedding_json=json.dumps(compute_local_concept_embedding(sample_text)),  # 10d stored
        )
        scored = compute_vector_scores("embodied AI robotics warehouse sensor", [chk])
        assert len(scored) == 1
        assert scored[0][1] > 0.90  # Realigned to 768d and computed cosine similarity accurately


def test_llm_as_a_judge_passes_grounded_dm_and_catches_subtle_familiarity_and_fake_metrics(
    db_session,
):
    """
    AC-2 (Module 05 Trạm 2 — LLM-as-a-Judge):
    - Passes an authentic, grounded peer-to-peer DM for @linhtran_robo citing '18ms' and 'Jetson AGX Orin'.
    - FAILS a DM containing subtle invented familiarity that bypasses basic 'we met at' regex
      ('I remember bumping into you at the Singapore robotics meetup last month').
    - FAILS a DM containing fabricated benchmark numbers ('down from 64ms to 5ms' when profile says '18ms').
    """
    ingest_seed_pack(db_session)
    linh = db_session.query(Candidate).filter(Candidate.handle == "linhtran_robo").first()
    assert linh is not None

    eval_res = evaluate_candidate_profile(linh, allow_external_llm=False, db=db_session)

    # 1. Authentic grounded DM -> PASS
    good_verdict = judge_dm_quality_with_llm(linh, eval_res.draft_dm, allow_external_llm=False)
    assert good_verdict["passed"] is True
    assert good_verdict["cites_real_evidence"] is True
    assert good_verdict["no_fake_familiarity"] is True
    assert good_verdict["peer_to_peer_cta"] is True

    # 2. Subtle fake familiarity ('bumping into you at the Singapore robotics meetup') -> FAIL
    subtle_fake_dm = (
        "Hi Linh, I remember bumping into you at the Singapore robotics meetup last month! "
        "Loved seeing your diffusion policy latency drop from 64ms to 18ms on Jetson AGX Orin. "
        "Open to a quick peer chat this week?"
    )
    familiarity_verdict = judge_dm_quality_with_llm(linh, subtle_fake_dm, allow_external_llm=False)
    assert familiarity_verdict["passed"] is False
    assert familiarity_verdict["no_fake_familiarity"] is False

    # 3. Fabricated metric ('5ms' instead of '18ms') -> FAIL
    fabricated_metric_dm = (
        "Hi Linh (@linhtran_robo), really impressed by how you cut diffusion policy inference latency "
        "from 64ms to 5ms on Jetson AGX Orin using TensorRT INT8. "
        "At X-Scout AI we back SEA robotics founders—open to a quick intro call this week?"
    )
    metric_verdict = judge_dm_quality_with_llm(linh, fabricated_metric_dm, allow_external_llm=False)
    assert metric_verdict["passed"] is False
    assert metric_verdict["cites_real_evidence"] is False
    assert "5ms" in metric_verdict["fabricated_metrics"]


def test_langfuse_sdk_4_span_trace_and_verify_gate_4_runner(auth_client, db_session):
    """
    AC-3 & AC-4 (Module 05 Trạm 3 & Trạm 4):
    - Verifies `@observe()` records all 4 Spans (`Span 1: Pre-Guard Check`, `Span 2: Hybrid Retrieval & Rerank`,
      `Span 3: LLM Generation`, `Span 4: Post-Guard Verification`) and trace scores for `@linhtran_robo`.
    - Verifies `GET /api/candidates/{id}/rag-explain` exposes `verify_gate_4_observability`.
    - Verifies `run_verify_gate_4_probabilistic_eval()` passes all 4 Golden Dataset thresholds.
    """
    ingest_seed_pack(db_session)
    linh = db_session.query(Candidate).filter(Candidate.handle == "linhtran_robo").first()
    assert linh is not None
    sync_candidate_chunks(db_session, linh)

    eval_res = evaluate_candidate_profile(linh, allow_external_llm=False, db=db_session)
    assert eval_res.fit_score == 4

    trace = get_last_candidate_trace("linhtran_robo")
    assert trace is not None
    assert trace["sdk"] == "langfuse"
    assert trace["status"] == "SUCCESS"
    span_names = [s["name"] for s in trace["spans"]]
    assert "Span 1: Pre-Guard Check" in span_names
    assert "Span 2: Hybrid Retrieval & Rerank" in span_names
    assert "Span 3: LLM Generation" in span_names
    assert "Span 4: Post-Guard Verification" in span_names

    # Check API diagnostic endpoint includes both Verify Gate 2 and Verify Gate 4
    resp = auth_client.get(f"/api/candidates/{linh.id}/rag-explain?top_k=3")
    assert resp.status_code == 200
    body = resp.json()
    assert "station_5_verify_gate_2" in body
    assert "verify_gate_4_observability" in body
    assert body["verify_gate_4_observability"]["langfuse_trace"]["handle"] == "linhtran_robo"

    # Run full Gate 4 Probabilistic QA benchmark (20 Golden Dataset profiles + 100-post @linhtran_robo RAG)
    gate4_report = run_verify_gate_4_probabilistic_eval(allow_external_llm=False)
    assert gate4_report["status"] == "PASSED"
    metrics = gate4_report["metrics"]
    assert metrics["context_recall_at_3_pct"] == 100.0
    assert metrics["rubric_alignment_accuracy_pct"] >= 90.0
    assert metrics["mean_score_delta"] <= 0.15
    assert metrics["faithfulness_rate_pct"] >= 98.0
    assert metrics["safety_blocks_verified"] == "2/2"
    assert metrics["llm_judge_dm_pass_rate_pct"] >= 90.0
