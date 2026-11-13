"""
Live X API & Live LLM API Key Verification Diagnostic Tool (Sub-task 7.2).

Validates real provider keys (`GEMINI_API_KEY` / `OPENAI_API_KEY` and `X_BEARER_TOKEN`
/ X OAuth 1.0a credentials) against Tri-Guard safety invariants without breaking offline CI.

Usage:
    python -m backend.scripts.verify_live_keys --mode all
    python -m backend.scripts.verify_live_keys --mode llm --full-benchmark
    python -m backend.scripts.verify_live_keys --mode x --handle OpenAI
    python -m backend.scripts.verify_live_keys --mode dispatch --dry-run
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

_backend_dir = Path(__file__).resolve().parent.parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.models.candidate import Candidate
from backend.app.services.ai_evaluator import (
    AIEvaluationServiceError,
    _call_external_llm,
    _enforce_post_guards,
    evaluate_candidate_profile,
)
from backend.app.services.ingestion import XApiLookupError, lookup_x_handle, normalize_handle
from backend.app.services.x_client import (
    get_x_api_base,
    has_x_bearer_token,
    has_x_oauth_credentials,
    send_x_dm,
)


def _is_key_set(value: str) -> bool:
    v = (value or "").strip()
    return bool(v and not v.startswith("your_"))


def _mask_key(value: str) -> str:
    v = (value or "").strip()
    if not _is_key_set(v):
        return "<unset>"
    if len(v) <= 8:
        return "***"
    return f"{v[:4]}...{v[-4:]}"


def _load_seed_rows() -> List[Dict[str, str]]:
    seed_csv = _project_root / "genai-outreach-pack" / "candidates_seed.csv"
    if not seed_csv.exists():
        raise FileNotFoundError(f"Seed CSV not found at {seed_csv}")
    with open(seed_csv, mode="r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _row_to_candidate(row: Dict[str, str]) -> Candidate:
    return Candidate(
        handle=normalize_handle(row.get("handle")),
        name=(row.get("name") or "").strip(),
        location=(row.get("location") or "Southeast Asia").strip(),
        bio=(row.get("bio") or "").strip(),
        recent_tweets=(row.get("recent_tweets") or "").strip(),
        can_dm=str(row.get("can_dm", "true")).strip().lower() not in ("false", "0", "no"),
        segment=(row.get("segment") or "SEA AI & Robotics").strip(),
    )


def run_llm_gate(full_benchmark: bool = False, pacing_sec: float = 0.0) -> Dict[str, Any]:
    """Gate L1: Verify Live Gemini/OpenAI API connectivity, JSON adherence & Tri-Guard safety."""
    gemini_set = _is_key_set(settings.GEMINI_API_KEY)
    openai_set = _is_key_set(settings.OPENAI_API_KEY)
    provider = settings.GEMINI_MODEL if gemini_set else (settings.OPENAI_MODEL if openai_set else None)

    if not provider:
        return {
            "gate": "L1_LIVE_LLM",
            "status": "SKIPPED_NO_KEY",
            "provider": None,
            "details": "Neither GEMINI_API_KEY nor OPENAI_API_KEY is configured in environment.",
        }

    rows = _load_seed_rows()
    by_id = {(r.get("profile_id") or "").strip(): r for r in rows}

    # Core smoke profiles: strong fit, adversarial injection, sparse bio
    smoke_ids = [pid for pid in ("P001", "P017", "P018") if pid in by_id]
    results: List[Dict[str, Any]] = []
    latencies_ms: List[float] = []

    target_rows = (
        [r for r in rows if (r.get("case_type") or "") != "EDGE_DUPLICATE_USER"]
        if full_benchmark
        else [by_id[pid] for pid in smoke_ids]
    )

    exact_matches = 0
    close_matches = 0
    guard_failures: List[str] = []

    for idx, row in enumerate(target_rows):
        pid = (row.get("profile_id") or "").strip()
        case_type = (row.get("case_type") or "NORMAL").strip()
        ref_score = int(row.get("reference_score") or 0)
        cand = _row_to_candidate(row)

        if idx > 0 and pacing_sec > 0:
            time.sleep(pacing_sec)

        t0 = time.perf_counter()
        attempt = 0
        while True:
            try:
                # Run full Tri-Guard pipeline (uses live LLM for Layer 2 unless L1 short-circuits)
                eval_res = evaluate_candidate_profile(cand)
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
                latencies_ms.append(elapsed_ms)

                # For injection probe P017, also probe _call_external_llm + post-guards directly
                if case_type == "EDGE_PROMPT_INJECTION" or pid == "P017":
                    if eval_res.fit_score > 1 or eval_res.is_match or (eval_res.draft_dm or "").strip():
                        guard_failures.append(f"{pid}: Injection guard leaked match/DM")
                    raw_llm = _call_external_llm(cand)
                    if raw_llm is not None:
                        guarded = _enforce_post_guards(raw_llm, cand)
                        if guarded.fit_score > 1 or guarded.is_match or (guarded.draft_dm or "").strip():
                            guard_failures.append(f"{pid}: Direct LLM + Layer3 post-guard leaked")
                break
            except AIEvaluationServiceError as exc:
                # Free-tier Gemini RPM quota protection during 19-profile benchmark
                if full_benchmark and "429" in str(exc) and attempt < 2:
                    attempt += 1
                    print(f"[INFO] Rate limit (429) on {pid}; backing off 15s (retry {attempt}/2)...")
                    time.sleep(15.0)
                    t0 = time.perf_counter()
                    continue
                return {
                    "gate": "L1_LIVE_LLM",
                    "status": "FAILED",
                    "provider": provider,
                    "failed_profile": pid,
                    "details": str(exc),
                }

        if case_type == "EDGE_SPARSE_PROFILE" or pid == "P018":
            if not eval_res.insufficient_evidence or eval_res.fit_score != 0 or (eval_res.draft_dm or "").strip():
                guard_failures.append(f"{pid}: Sparse guard failed")

        if eval_res.fit_score == ref_score:
            exact_matches += 1
        if abs(eval_res.fit_score - ref_score) <= 1:
            close_matches += 1

        results.append(
            {
                "profile_id": pid,
                "handle": cand.handle,
                "ref_score": ref_score,
                "ai_score": eval_res.fit_score,
                "is_match": eval_res.is_match,
                "insufficient_evidence": eval_res.insufficient_evidence,
                "dm_chars": len(eval_res.draft_dm or ""),
                "latency_ms": elapsed_ms,
            }
        )

    total = len(results)
    avg_latency = round(sum(latencies_ms) / max(1, total), 1)
    passed = len(guard_failures) == 0 and total > 0

    return {
        "gate": "L1_LIVE_LLM",
        "status": "PASSED" if passed else "FAILED",
        "provider": provider,
        "profiles_evaluated": total,
        "exact_match_rate_pct": round((exact_matches / max(1, total)) * 100, 1),
        "close_match_rate_pct": round((close_matches / max(1, total)) * 100, 1),
        "avg_latency_ms": avg_latency,
        "estimated_cost_usd": round(total * 0.0005, 5),
        "guard_failures": guard_failures,
        "samples": results[:5] if full_benchmark else results,
    }


def run_x_lookup_gate(handle: str = "OpenAI") -> Dict[str, Any]:
    """Gate L2: Verify Live or Simulator X API v2 Bearer Token user + recent tweets lookup."""
    base_url = get_x_api_base()
    if not has_x_bearer_token():
        return {
            "gate": "L2_LIVE_X_LOOKUP",
            "status": "SKIPPED_NO_KEY",
            "handle": handle,
            "x_api_base_url": base_url,
            "details": "X_BEARER_TOKEN is not configured in environment.",
        }

    # Ephemeral in-memory SQLite just to supply Session to lookup_x_handle
    mem_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=mem_engine)
    MemSession = sessionmaker(bind=mem_engine)
    db = MemSession()
    t0 = time.perf_counter()
    try:
        profile = lookup_x_handle(db, handle)
    except XApiLookupError as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "gate": "L2_LIVE_X_LOOKUP",
            "status": "FAILED",
            "handle": normalize_handle(handle),
            "x_api_base_url": base_url,
            "http_status": exc.status_code,
            "latency_ms": elapsed_ms,
            "details": exc.detail,
        }
    finally:
        db.close()

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    source_mode = profile.get("source_mode")
    if source_mode == "LIVE_X_API" and profile.get("x_user_id"):
        status = "PASSED"
    elif source_mode == "X_API_SIMULATOR" and profile.get("x_user_id"):
        status = "PASSED_SIMULATOR"
    else:
        status = "FAILED"

    return {
        "gate": "L2_LIVE_X_LOOKUP",
        "status": status,
        "handle": profile.get("handle"),
        "source_mode": source_mode,
        "x_api_base_url": base_url,
        "x_user_id": profile.get("x_user_id"),
        "tweets_fetched": len(profile.get("recent_tweets") or []),
        "latency_ms": elapsed_ms,
        "details": None if status != "FAILED" else "Unexpected X lookup response without x_user_id.",
    }


def run_dispatch_guard_gate(
    dm_handle: Optional[str] = None,
    execute_send: bool = False,
) -> Dict[str, Any]:
    """Gate L3: Verify LIVE_X OAuth config, whitelist guard & optional controlled real DM probe."""
    oauth_ready = has_x_oauth_credentials()
    whitelist = settings.ALLOWED_TEST_HANDLES

    probe_blocked_ok = normalize_handle("random_unlisted_user_999") not in whitelist

    result: Dict[str, Any] = {
        "gate": "L3_LIVE_X_DISPATCH",
        "status": "PASSED" if (oauth_ready and probe_blocked_ok) else ("SKIPPED_NO_KEY" if not oauth_ready else "FAILED"),
        "dispatch_mode": settings.DISPATCH_MODE,
        "live_x_dry_run": settings.LIVE_X_DRY_RUN,
        "oauth_credentials_present": oauth_ready,
        "allowed_test_handles": whitelist,
        "non_whitelisted_blocked": probe_blocked_ok,
        "real_dm_executed": False,
    }

    if execute_send:
        if not oauth_ready:
            result["status"] = "FAILED"
            result["details"] = "Cannot --execute-send without all 4 X OAuth 1.0a credentials."
            return result
        target = normalize_handle(dm_handle or (whitelist[0] if whitelist else ""))
        if not target or target not in whitelist:
            result["status"] = "FAILED"
            result["details"] = f"Refusing live DM: @{target} is not in ALLOWED_TEST_HANDLES={whitelist}"
            return result

        send_resp = send_x_dm(
            handle=target,
            message="[GenAI Fund Live Smoke Test] Verifying OAuth 1.0a X API v2 DM dispatch guard.",
        )
        result["real_dm_executed"] = True
        result["dm_event_id"] = send_resp.get("dm_event_id")
        result["target_handle"] = target
        result["status"] = "PASSED"

    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Live AI & X API Keys with Tri-Guard invariants.")
    parser.add_argument("--mode", choices=["all", "llm", "x", "dispatch"], default="all")
    parser.add_argument("--full-benchmark", action="store_true", help="Run Live LLM on all 19 unique seed profiles.")
    parser.add_argument("--handle", default="OpenAI", help="Public X handle for Gate L2 lookup test.")
    parser.add_argument("--dm-handle", default=None, help="Whitelisted X handle for optional Gate L3 real DM test.")
    parser.add_argument("--execute-send", action="store_true", help="Actually send a test DM if --dm-handle is whitelisted.")
    parser.add_argument("--allow-missing", action="store_true", help="Exit 0 even when keys are not configured.")
    parser.add_argument("--json-out", default=None, help="Optional path to write structured JSON report.")
    args = parser.parse_args(argv)

    print("=" * 72)
    print("GENAI FUND – LIVE API KEY DIAGNOSTIC & TRI-GUARD VERIFICATION")
    print(f"• GEMINI_API_KEY : {_mask_key(settings.GEMINI_API_KEY)}")
    print(f"• OPENAI_API_KEY : {_mask_key(settings.OPENAI_API_KEY)}")
    print(f"• X_API_BASE_URL : {get_x_api_base()}")
    print(f"• X_BEARER_TOKEN : {_mask_key(settings.X_BEARER_TOKEN)}")
    print(f"• X_OAUTH_4KEYS  : {'configured' if has_x_oauth_credentials() else '<unset>'}")
    print("=" * 72)

    gates: List[Dict[str, Any]] = []
    if args.mode in ("all", "llm"):
        gates.append(run_llm_gate(full_benchmark=args.full_benchmark))
    if args.mode in ("all", "x"):
        gates.append(run_x_lookup_gate(handle=args.handle))
    if args.mode in ("all", "dispatch"):
        gates.append(run_dispatch_guard_gate(dm_handle=args.dm_handle, execute_send=args.execute_send))

    for g in gates:
        print(json.dumps(g, indent=2, ensure_ascii=False))

    if args.json_out:
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"gates": gates}, indent=2, ensure_ascii=False), encoding="utf-8")

    has_failure = any(g["status"] == "FAILED" for g in gates)
    all_skipped = all(g["status"] == "SKIPPED_NO_KEY" for g in gates)
    if has_failure:
        return 1
    if all_skipped and not args.allow_missing:
        print("\n[INFO] No live API keys configured. Set GEMINI_API_KEY/OPENAI_API_KEY/X_BEARER_TOKEN in backend/.env.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

