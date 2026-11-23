import json
from pathlib import Path
from typing import Any, Dict, List
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.chunk import CandidateChunk
from backend.app.services.ai_evaluator import (
    AIEvaluationResult,
    _enforce_post_guards,
    _verify_verbatim_grounding,
    build_fortified_candidate_prompt,
    evaluate_candidate_profile,
    verify_gate_2_grounding,
)
from backend.app.services.dispatcher import send_rate_limiter
from backend.app.services.ingestion import ingest_candidate_batch, ingest_seed_pack
from backend.app.services.rag_retriever import (
    compute_bm25_scores,
    compute_vector_scores,
    explain_chunk_filter_plan,
    hard_filter_candidate_chunks,
    search_and_rerank_candidate_chunks,
    semantic_split_text_with_overlap,
    sync_candidate_chunks,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "linhtran_robo_rag_corpus.json"


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


def _seed_linhtran_robo_100_posts(db_session) -> Candidate:
    """
    Populate @linhtran_robo (P001) with a realistic 100-post corpus:
    - 2 Golden technical tweets ('185500101' and '185500102')
    - 8 BM25 Keyword / Hiring traps (Hard Negatives mentioning Jetson/ROS2/TensorRT in hiring or news retweets)
    - 10 Vector Semantic traps (Hard Negatives about sci-fi movies, Lego toys, keyboards, speakers)
    - 80 Daily lifestyle / coffee / football / holiday posts
    """
    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    ingest_seed_pack(db_session)

    linh = db_session.query(Candidate).filter(Candidate.handle == "linhtran_robo").first()
    assert linh is not None

    all_100_posts: List[Dict[str, Any]] = []
    # Add 40 lifestyle posts before golden posts
    templates = corpus["lifestyle_noise_templates"]
    for i in range(40):
        all_100_posts.append(
            {
                "post_id": f"noise_pre_{i + 1:03d}",
                "created_at": f"2026-08-{(i % 28) + 1:02d}",
                "source_type": "x_post",
                "text": f"{templates[i % len(templates)]} (Post #{i + 1})",
            }
        )

    # Insert BM25 traps and first golden tweet in the middle (testing 'Lost in the Middle' immunity)
    all_100_posts.extend(corpus["hard_negative_bm25_traps"][:4])
    all_100_posts.append(corpus["golden_posts"][0])  # 185500101
    all_100_posts.extend(corpus["hard_negative_vector_traps"][:5])
    all_100_posts.append(corpus["golden_posts"][1])  # 185500102
    all_100_posts.extend(corpus["hard_negative_bm25_traps"][4:])
    all_100_posts.extend(corpus["hard_negative_vector_traps"][5:])

    # Add remaining 40 lifestyle posts after golden posts -> total = 100 x_post items
    for i in range(40, 80):
        all_100_posts.append(
            {
                "post_id": f"noise_post_{i + 1:03d}",
                "created_at": f"2026-07-{(i % 28) + 1:02d}",
                "source_type": "x_post",
                "text": f"{templates[i % len(templates)]} (Post #{i + 1})",
            }
        )

    assert len(all_100_posts) == 100
    sync_candidate_chunks(
        db=db_session,
        candidate=linh,
        raw_posts=all_100_posts,
        replace_existing=True,
    )
    return linh


def test_retrieval_pipeline_finds_golden_tweets_for_linhtran_robo(db_session):
    """
    BÀI TEST TRỤ CỘT 3 - TẦNG 1 (Retrieval Recall@3 — $0 LLM Cost):
    Between 100 posts (98 noise + hard-negative traps + 2 golden technical tweets) of @linhtran_robo,
    the Hybrid Search (BM25 + Vector) + Cross-Encoder Reranker MUST retrieve both golden tweets
    ('185500101' and '185500102') inside the Top 3 results (Recall@3 == 1.0), ranked #1 and #2!
    """
    _seed_linhtran_robo_100_posts(db_session)

    # 1. Golden Ground Truth defined in MODULE_03_DATABASE_RAG_AND_VERIFY_GATE_2.md
    golden_post_ids = {"185500101", "185500102"}

    # 2. Run Station 2 -> Station 3 -> Station 4 RAG Secretary to retrieve Top 3 chunks:
    top_3_chunks = search_and_rerank_candidate_chunks(
        db=db_session,
        handle="linhtran_robo",
        query="embodied AI robotics hardware latency production benchmarks in Southeast Asia",
        top_k=3,
    )
    retrieved_ids = {chunk.post_id for chunk in top_3_chunks}

    # 3. Compute Recall@3 (must be 2/2 = 1.0)
    hits = golden_post_ids.intersection(retrieved_ids)
    recall_at_3 = len(hits) / len(golden_post_ids)

    assert recall_at_3 == 1.0, (
        f"LỖI TRỤ CỘT 3 (Retrieval bị mù): Chỉ tìm thấy {retrieved_ids}, "
        f"bỏ sót mất bài quan trọng của @linhtran_robo!"
    )
    # Verify the two golden posts are ranked at the very top with high Cross-Encoder scores
    assert {top_3_chunks[0].post_id, top_3_chunks[1].post_id} == golden_post_ids
    assert top_3_chunks[0].rerank_score >= 0.95
    assert top_3_chunks[1].rerank_score >= 0.90


def test_station_1_semantic_chunking_overlap_and_station_3_hybrid_complementary_strengths(db_session):
    """
    Verifies Station 1 (Semantic Chunking + Overlap + Metadata on long technical Markdown/PDF)
    and Station 3 (Why BM25 + Vector Hybrid Search are both required):
    - Long technical Markdown doc is split along sentence boundaries with overlap, never breaking
      '64ms' / '18ms' or losing post_id metadata.
    - Pure keyword query without hardware names misses post 185500102 in pure lexical match,
      whereas Vector Search captures 'Active stereo + tactile wrist feedback' with high semantic score.
    """
    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    long_doc = corpus["long_technical_markdown_doc"]

    chunks_text = semantic_split_text_with_overlap(
        long_doc["text"],
        max_words=75,
        overlap_words=18,
    )
    assert len(chunks_text) >= 2
    # Every chunk ends on a clean boundary and preserves key technical figures intact
    full_rejoined = " ".join(chunks_text)
    assert "64ms" in full_rejoined and "18ms" in full_rejoined
    assert "93.4%" in full_rejoined

    # Check complementary strength of Vector Search on post 185500102 when query uses zero matching words
    _seed_linhtran_robo_100_posts(db_session)
    all_x_chunks = hard_filter_candidate_chunks(db_session, "linhtran_robo", source_types=["x_post"])
    semantic_only_query = "deploying physical robot perception sensors in real industrial facilities"

    vec_ranked = compute_vector_scores(semantic_only_query, all_x_chunks)
    top_5_vec_ids = {chk.post_id for chk, _ in vec_ranked[:5]}
    assert "185500102" in top_5_vec_ids, (
        "Vector Search must capture post 185500102 ('Active stereo + tactile wrist feedback in 3PL warehouse') "
        "even when query shares zero exact keywords!"
    )

    exact_code_query = "TensorRT INT8 calibration Jetson AGX Orin 18ms"
    bm25_ranked = compute_bm25_scores(exact_code_query, all_x_chunks)
    assert bm25_ranked[0][0].post_id == "185500101"


def test_grounding_and_anti_hallucination_verify_gate_2_for_linhtran_robo(db_session):
    """
    BÀI TEST TRỤ CỘT 3 - TẦNG 2 (Chốt Verify Gate 2 - Verbatim & Citation Grounding):
    1. Evaluates @linhtran_robo using the Top 3 RAG chunks on the A4 Prompt sheet.
    2. Verifies evidence_snippet exists 100% verbatim in the candidate's source text and maps to post_id '185500101'.
    3. Simulates an LLM hallucination altering a single number ('18ms' -> '5ms') and proves
       Verify Gate 2 rejects the fabricated quote and restores the authentic verbatim quote!
    """
    linh = _seed_linhtran_robo_100_posts(db_session)
    top_3_chunks = search_and_rerank_candidate_chunks(db_session, handle="linhtran_robo", top_k=3)

    # Verify A4 prompt contains only the Top 3 chunks (~460 tokens) rather than all 100 posts
    a4_prompt = build_fortified_candidate_prompt(linh, retrieved_chunks=top_3_chunks)
    assert 'post_id="185500101"' in a4_prompt
    assert 'post_id="185500102"' in a4_prompt
    assert "noise_pre_001" not in a4_prompt

    # Evaluate @linhtran_robo through the AI Evaluator with RAG active
    eval_res = evaluate_candidate_profile(linh, db=db_session)
    assert eval_res.is_match is True
    assert eval_res.fit_score == 4
    assert eval_res.evidence_snippet != ""

    # 1. Verbatim Substring Check
    source_text = f"{linh.bio} || {linh.recent_tweets}".lower()
    assert eval_res.evidence_snippet.lower() in source_text, (
        "LỖI HALLUCINATION: AI đã tự chế ra câu bằng chứng không có trong hồ sơ gốc!"
    )

    # 2. DM Grounding & Anti-Familiarity Check
    assert 200 <= len(eval_res.draft_dm) <= 600
    assert "we met at" not in eval_res.draft_dm.lower()
    assert "mutual friend" not in eval_res.draft_dm.lower()

    # 3. Simulate LLM Hallucination (altering '18ms' to '5ms') -> Verify Gate 2 MUST catch and replace it
    hallucinated_snippet = (
        "Finally got our diffusion policy inference latency down from 64ms to 5ms on a single Jetson AGX Orin"
    )
    gate2_report = verify_gate_2_grounding(
        snippet=hallucinated_snippet,
        candidate=linh,
        retrieved_chunks=top_3_chunks,
    )
    assert gate2_report["is_verbatim_valid"] is False
    assert gate2_report["hallucination_rejected"] is True
    assert "64ms to 18ms" in gate2_report["verified_snippet"]
    assert gate2_report["matched_post_id"] == "185500101"

    # Also verify _enforce_post_guards overwrites fabricated LLM result.evidence_snippet
    fake_llm_output = AIEvaluationResult(
        is_match=True,
        fit_score=4,
        fit_reason="Strong robotics founder.",
        evidence_snippet=hallucinated_snippet,
        draft_dm=eval_res.draft_dm,
        insufficient_evidence=False,
    )
    guarded = _enforce_post_guards(fake_llm_output, linh, retrieved_chunks=top_3_chunks)
    assert "64ms to 18ms" in guarded.evidence_snippet
    assert "64ms to 5ms" not in guarded.evidence_snippet


def test_station_2_composite_index_explain_plan_and_3_tier_deduplication(auth_client, db_session):
    """
    BÀI TEST TRỤ CỘT 3 - TẦNG 3 (DB Composite Index Scan + 3-Tier Deduplication + RAG Explain API):
    1. Verifies `EXPLAIN QUERY PLAN` uses `idx_chunks_handle_source` (Index Scan, not full table scan).
    2. Verifies 3-Tier Deduplication blocks duplicate imports of `@LinhTran_Robo` and preserves `REPLIED` ledger state.
    3. Verifies `GET /api/candidates/{id}/rag-explain` returns all 5 stations transparently.
    """
    linh = _seed_linhtran_robo_100_posts(db_session)

    # 1. Verify Composite Index Scan via EXPLAIN QUERY PLAN
    plan = explain_chunk_filter_plan(db_session, "linhtran_robo")
    assert plan["uses_index"] is True
    assert "idx_chunks_handle_source" in plan["plan_detail"]

    # 2. Verify 3-Tier Deduplication on @LinhTran_Robo (case variation + in-batch duplicate + ledger lock)
    dup_batch = [
        {
            "handle": "@LinhTran_Robo",
            "name": "Linh Tran Duplicate 1",
            "bio": linh.bio,
            "recent_tweets": linh.recent_tweets,
        },
        {
            "handle": "https://x.com/linhtran_robo",
            "name": "Linh Tran Duplicate 2",
            "bio": linh.bio,
            "recent_tweets": linh.recent_tweets,
        },
    ]
    report = ingest_candidate_batch(db_session, dup_batch, source_label="DEDUP_TEST")
    assert report["imported"] == 0
    assert report["in_batch_duplicates_skipped"] == 1
    assert report["already_in_db_skipped"] == 1
    assert report["already_contacted_in_ledger"] == 1

    db_session.refresh(linh)
    assert linh.status == CandidateStatus.REPLIED.value
    assert db_session.query(Candidate).filter(Candidate.handle == "linhtran_robo").count() == 1

    # 3. Verify 5-Station Diagnostic Endpoint GET /api/candidates/{id}/rag-explain
    resp = auth_client.get(f"/api/candidates/{linh.id}/rag-explain?top_k=3")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["handle"] == "linhtran_robo"
    assert payload["station_1_chunking"]["searchable_post_chunks"] == 100
    assert payload["station_2_sql_hard_filter"]["uses_index"] is True
    assert set(payload["selected_post_ids"][:2]) == {"185500101", "185500102"}
    assert 'post_id="185500101"' in payload["station_5_verify_gate_2"]["a4_prompt_preview"]
