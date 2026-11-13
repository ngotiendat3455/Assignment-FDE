import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.config import settings

logger = logging.getLogger("backend.contract_trace")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

_SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "access_token",
    "token",
    "session_token",
    "authorization",
    "api_key",
    "gemini_api_key",
    "openai_api_key",
    "x_bearer_token",
    "secret",
    "secret_key",
}

ALL_9_STATES = [
    "QUEUED_FOR_AI",
    "PENDING_REVIEW",
    "INSUFFICIENT_EVIDENCE",
    "AI_FAILED",
    "REJECTED",
    "APPROVED_QUEUED",
    "SENT",
    "SEND_BLOCKED",
    "REPLIED",
]


def sanitize_testcase_id(raw_id: Optional[str]) -> str:
    """Normalize a testcase identifier into a safe filename token."""
    if not raw_id:
        return "unassigned"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw_id.strip()).strip("._")
    return cleaned[:96] or "unassigned"


def get_trace_output_dir() -> Path:
    """Resolve and ensure trace directories exist."""
    env_dir = os.getenv("TRACE_OUTPUT_DIR")
    trace_dir = Path(env_dir) if env_dir else Path(settings.TRACE_OUTPUT_DIR)
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "raw").mkdir(parents=True, exist_ok=True)
    return trace_dir


def _state_file(trace_dir: Path, testcase_id: str) -> Path:
    return trace_dir / "raw" / f"{sanitize_testcase_id(testcase_id)}.state.json"


def _load_tc_state(trace_dir: Path, testcase_id: str) -> Dict[str, Any]:
    sf = _state_file(trace_dir, testcase_id)
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "testcase": sanitize_testcase_id(testcase_id),
        "flow_ref": "",
        "title": "",
        "expected_states": [],
        "forbidden_transitions": [],
        "observed_states": [],
        "transitions": [],
        "guards_triggered": [],
        "last_candidate_statuses": {},
        "last_db_snapshot": None,
        "last_read_sig": None,
        "read_repeat_count": 0,
        "api_count": 0,
        "status": "RUNNING",
    }


def _save_tc_state(trace_dir: Path, state: Dict[str, Any]) -> None:
    sf = _state_file(trace_dir, state["testcase"])
    sf.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_db_snapshot(db: Session) -> Dict[str, Any]:
    """Capture lightweight SQLite counts across Candidate (9 states), OutreachLedger, and JobQueue."""
    from backend.app.models.candidate import Candidate
    from backend.app.models.ledger import OutreachLedger
    from backend.app.models.queue import JobQueue

    state_counts = {s: 0 for s in ALL_9_STATES}
    rows = (
        db.query(Candidate.status, func.count(Candidate.id))
        .group_by(Candidate.status)
        .all()
    )
    total_candidates = 0
    for st, cnt in rows:
        key = st.value if hasattr(st, "value") else str(st)
        state_counts[key] = int(cnt)
        total_candidates += int(cnt)

    cand_statuses = {
        handle: (st.value if hasattr(st, "value") else str(st))
        for handle, st in db.query(Candidate.handle, Candidate.status).all()
    }

    ledger_total = db.query(func.count(OutreachLedger.id)).scalar() or 0
    ledger_attention = (
        db.query(func.count(OutreachLedger.id))
        .filter(OutreachLedger.needs_attention.is_(True))
        .scalar()
        or 0
    )
    jobs_total = db.query(func.count(JobQueue.id)).scalar() or 0

    return {
        "total_candidates": int(total_candidates),
        "state_counts": state_counts,
        "non_zero_states": {k: v for k, v in state_counts.items() if v > 0},
        "ledger_total": int(ledger_total),
        "ledger_needs_attention": int(ledger_attention),
        "jobs_total": int(jobs_total),
        "candidate_statuses": cand_statuses,
    }


def _diff_snapshots(prev: Optional[Dict[str, Any]], curr: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not curr:
        return {"transitions": [], "summary": ""}
    if not prev:
        return {
            "transitions": [],
            "summary": (
                f"Candidates={curr['total_candidates']} {curr['non_zero_states']} | "
                f"Ledger={curr['ledger_total']} (attention={curr['ledger_needs_attention']})"
            ),
        }

    transitions: List[str] = []
    prev_map = prev.get("candidate_statuses", {})
    curr_map = curr.get("candidate_statuses", {})
    for handle, new_st in curr_map.items():
        old_st = prev_map.get(handle)
        if old_st is None:
            transitions.append(f"`@{handle}`: `[*]` -> `{new_st}`")
        elif old_st != new_st:
            transitions.append(f"`@{handle}`: `{old_st}` -> `{new_st}`")

    parts = []
    if prev["total_candidates"] != curr["total_candidates"]:
        parts.append(f"Candidates: `{prev['total_candidates']} -> {curr['total_candidates']}`")
    else:
        parts.append(f"Candidates: `{curr['total_candidates']}`")
    if prev["non_zero_states"] != curr["non_zero_states"]:
        parts.append(f"States: `{curr['non_zero_states']}`")
    if prev["ledger_total"] != curr["ledger_total"] or prev["ledger_needs_attention"] != curr["ledger_needs_attention"]:
        parts.append(
            f"Ledger: `{prev['ledger_total']} -> {curr['ledger_total']}` "
            f"(attention `{prev['ledger_needs_attention']} -> {curr['ledger_needs_attention']}`)"
        )
    else:
        parts.append(f"Ledger: `{curr['ledger_total']}` (attention `{curr['ledger_needs_attention']}`)")

    return {"transitions": transitions, "summary": " | ".join(parts)}


def _append_md(trace_dir: Path, testcase_id: str, text: str) -> None:
    md_path = trace_dir / f"{sanitize_testcase_id(testcase_id)}.md"
    with md_path.open("a", encoding="utf-8") as fh:
        fh.write(text)


def set_active_testcase(testcase_id: str, reset_file: bool = False) -> Path:
    """Backward-compatible simple initializer for a testcase marker."""
    return start_flow_session(testcase_id=testcase_id, reset_file=reset_file)


def start_flow_session(
    *,
    testcase_id: str,
    flow_ref: str = "",
    title: str = "",
    expected_states: Optional[List[str]] = None,
    forbidden_transitions: Optional[List[str]] = None,
    db_snapshot: Optional[Dict[str, Any]] = None,
    reset_file: bool = True,
) -> Path:
    """Initialize a structured Flow Contract Trace document (<TC>.md) for one testcase."""
    safe_id = sanitize_testcase_id(testcase_id)
    trace_dir = get_trace_output_dir()
    (trace_dir / ".active-testcase").write_text(safe_id, encoding="utf-8")

    now_iso = datetime.now(timezone.utc).isoformat()
    state = {
        "testcase": safe_id,
        "started_at": now_iso,
        "finished_at": None,
        "flow_ref": flow_ref or safe_id,
        "title": title or safe_id,
        "expected_states": expected_states or [],
        "forbidden_transitions": forbidden_transitions or [],
        "observed_states": list((db_snapshot or {}).get("non_zero_states", {}).keys()),
        "transitions": [],
        "guards_triggered": [],
        "last_db_snapshot": db_snapshot,
        "last_read_sig": None,
        "read_repeat_count": 0,
        "api_count": 0,
        "status": "RUNNING",
    }
    _save_tc_state(trace_dir, state)

    md_path = trace_dir / f"{safe_id}.md"
    if reset_file or not md_path.exists():
        lines = [
            f"# FLOW CONTRACT TRACE: `{safe_id}`",
            f"- **Title:** {state['title']}",
            f"- **Thiết kế tham chiếu (`D:/AssignmentFDE/testing/`):** `{state['flow_ref']}`",
            f"- **Started:** `{now_iso}`",
        ]
        if state["expected_states"]:
            lines.append(f"- **State Path kỳ vọng:** {' -> '.join(f'`{s}`' for s in state['expected_states'])}")
        if state["forbidden_transitions"]:
            lines.append(f"- **Guard / Negative Contracts:** {'; '.join(f'`{g}`' for g in state['forbidden_transitions'])}")
        if db_snapshot:
            lines.append(f"- **Initial DB:** Candidates=`{db_snapshot['total_candidates']}`, Ledger=`{db_snapshot['ledger_total']}`")
        lines.extend(["", "## Timeline theo từng Bước Nghiệp vụ", ""])
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    logger.info("[FLOW][%s] START (%s) -> %s", safe_id, state["flow_ref"], state["title"])
    return md_path


def record_flow_step(
    *,
    testcase_id: str,
    step: str,
    ui_action: str = "",
    expected: str = "",
    db_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a human-readable business workflow step banner to the testcase flow trace."""
    safe_id = sanitize_testcase_id(testcase_id)
    trace_dir = get_trace_output_dir()
    state = _load_tc_state(trace_dir, safe_id)

    lines = [f"### {step}"]
    if ui_action:
        lines.append(f"- **Thao tác / Route:** {ui_action}")
    if expected:
        lines.append(f"- **Hợp đồng kỳ vọng (Expected):** {expected}")
    if db_snapshot:
        diff = _diff_snapshots(state.get("last_db_snapshot"), db_snapshot)
        lines.append(f"- **DB Checkpoint:** {diff['summary']}")
        for tr in diff["transitions"][:10]:
            lines.append(f"  - State Change: {tr}")
            if tr not in state["transitions"]:
                state["transitions"].append(tr)
        for s in db_snapshot.get("non_zero_states", {}).keys():
            if s not in state["observed_states"]:
                state["observed_states"].append(s)
        state["last_db_snapshot"] = db_snapshot
    lines.append("")

    state["last_read_sig"] = None
    state["read_repeat_count"] = 0
    _save_tc_state(trace_dir, state)
    _append_md(trace_dir, safe_id, "\n".join(lines) + "\n")
    logger.info("[FLOW][%s] %s", safe_id, step)


def finish_flow_session(
    *,
    testcase_id: str,
    status: str = "PASSED",
    notes: str = "",
    db_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Finalize testcase trace summary and persist into flow-summary.json."""
    safe_id = sanitize_testcase_id(testcase_id)
    trace_dir = get_trace_output_dir()
    state = _load_tc_state(trace_dir, safe_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    state["finished_at"] = now_iso
    state["status"] = status.upper()

    if db_snapshot:
        diff = _diff_snapshots(state.get("last_db_snapshot"), db_snapshot)
        for tr in diff["transitions"]:
            if tr not in state["transitions"]:
                state["transitions"].append(tr)
        for s in db_snapshot.get("non_zero_states", {}).keys():
            if s not in state["observed_states"]:
                state["observed_states"].append(s)
        state["last_db_snapshot"] = db_snapshot

    badge = "✅ PASSED" if state["status"] == "PASSED" else f"❌ {state['status']}"
    lines = [
        "---",
        f"## Kết luận Contract ({badge})",
        f"- **Finished:** `{now_iso}` | **API Calls Traced:** `{state['api_count']}`",
        f"- **States đã đi qua:** {', '.join(f'`{s}`' for s in state['observed_states']) or '_None_'}",
    ]
    if state["transitions"]:
        lines.append("- **State Transitions ghi nhận trên DB:**")
        for tr in state["transitions"][:25]:
            lines.append(f"  - {tr}")
    if state["guards_triggered"]:
        lines.append("- **Guards đã kích hoạt (Negative Protection):**")
        for g in state["guards_triggered"]:
            lines.append(f"  - {g}")
    if db_snapshot:
        lines.append(
            f"- **Final DB Snapshot:** Candidates=`{db_snapshot['total_candidates']}` `{db_snapshot['non_zero_states']}` | "
            f"Ledger=`{db_snapshot['ledger_total']}` (attention=`{db_snapshot['ledger_needs_attention']}`)"
        )
    if notes:
        lines.append(f"- **Ghi chú:** {notes}")
    lines.append("")
    _append_md(trace_dir, safe_id, "\n".join(lines))
    _save_tc_state(trace_dir, state)

    summary_path = trace_dir / "raw" / "flow-summary.json"
    summary_data: Dict[str, Any] = {}
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary_data = {}
    summary_data[safe_id] = {
        "testcase": safe_id,
        "flow_ref": state["flow_ref"],
        "title": state["title"],
        "status": state["status"],
        "expected_states": state["expected_states"],
        "observed_states": state["observed_states"],
        "transitions_count": len(state["transitions"]),
        "guards_triggered": state["guards_triggered"],
        "api_count": state["api_count"],
        "trace_file": f"{safe_id}.md",
    }
    summary_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_flow_coverage_report(trace_dir)


def generate_flow_coverage_report(trace_dir: Optional[Path] = None) -> Path:
    """Build _FLOW_COVERAGE_REPORT.md mapping actual test traces to testing/e2e.md 9 states & 8 E2E cases."""
    tdir = trace_dir or get_trace_output_dir()
    summary_path = tdir / "raw" / "flow-summary.json"
    summary_data: Dict[str, Any] = {}
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            summary_data = {}

    observed_all: set[str] = set()
    for item in summary_data.values():
        observed_all.update(item.get("observed_states", []))
        for guard in item.get("guards_triggered", []):
            for st in ALL_9_STATES:
                if st in guard:
                    observed_all.add(st)

    lines = [
        "# BÁO CÁO ĐỘ PHỦ FLOW & CONTRACT (Đối chiếu `testing/e2e.md` & `ER-*.md`)",
        f"- **Generated at:** `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## 1. Bảng Tổng hợp Thực thi theo Từng Kịch bản",
        "",
        "| Testcase | Tham chiếu Thiết kế (`testing/`) | Trạng thái | States đã phủ | Guards kích hoạt | File Trace chi tiết |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for tc_id in sorted(summary_data.keys()):
        entry = summary_data[tc_id]
        st_badge = "✅ PASS" if entry["status"] == "PASSED" else f"❌ {entry['status']}"
        states_str = ", ".join(f"`{s}`" for s in entry.get("observed_states", [])) or "-"
        guards_str = f"{len(entry.get('guards_triggered', []))} guard(s)" if entry.get("guards_triggered") else "-"
        lines.append(
            f"| `{tc_id}` | `{entry.get('flow_ref', '-')}` | {st_badge} | {states_str} | {guards_str} | [`{entry['trace_file']}`](./{entry['trace_file']}) |"
        )

    covered_states = [s for s in ALL_9_STATES if s in observed_all]
    lines.extend(
        [
            "",
            f"## 2. Độ phủ 9 Trạng thái State Machine (`{len(covered_states)} / {len(ALL_9_STATES)}`)",
            "",
            "| Trạng thái | Đã quan sát thực tế trên DB/API? |",
            "| :--- | :--- |",
        ]
    )
    for s in ALL_9_STATES:
        if s in observed_all:
            mark = "✅ Đã phủ trực tiếp trên DB/API"
        elif s == "APPROVED_QUEUED" and ("SENT" in observed_all or "SEND_BLOCKED" in observed_all):
            mark = "⚡ Trung gian đồng bộ trong `POST /send` (`PENDING_REVIEW -> APPROVED_QUEUED -> SENT/SEND_BLOCKED`)"
        else:
            mark = "⚠️ Chưa thấy trong trace"
        lines.append(f"| `{s}` | {mark} |")

    report_path = tdir / "_FLOW_COVERAGE_REPORT.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def get_active_testcase(header_value: Optional[str] = None) -> str:
    """Resolve active testcase ID from explicit request header or active marker file."""
    if header_value and header_value.strip():
        return sanitize_testcase_id(header_value)
    marker = get_trace_output_dir() / ".active-testcase"
    if marker.exists():
        content = marker.read_text(encoding="utf-8").strip()
        if content:
            return sanitize_testcase_id(content)
    return "unassigned"


def redact_sensitive(value: Any) -> Any:
    """Recursively mask credentials, JWTs, and API keys from traced payloads."""
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in value.items():
            key_lower = str(k).lower()
            if key_lower in _SENSITIVE_KEYS or "password" in key_lower or "secret" in key_lower:
                sanitized[k] = "***REDACTED***" if v not in (None, "") else v
            else:
                sanitized[k] = redact_sensitive(v)
        return sanitized
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def extract_contract_keys(payload: Any) -> List[str]:
    """Summarize top-level JSON contract keys (plus item keys for list wrappers)."""
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())
        items = payload.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            item_keys = sorted(str(k) for k in items[0].keys())
            return keys + [f"items[0].{k}" for k in item_keys]
        return keys
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict):
            return [f"[0].{k}" for k in sorted(str(k) for k in payload[0].keys())]
        return [f"list(len={len(payload)})"]
    return []


def _safe_json(raw_bytes: bytes) -> Any:
    if not raw_bytes:
        return None
    try:
        return redact_sensitive(json.loads(raw_bytes.decode("utf-8", errors="replace")))
    except Exception:
        return None


def _summarize_semantic_event(
    method: str,
    path: str,
    status_code: int,
    req_json: Any,
    res_json: Any,
) -> Dict[str, Any]:
    """Turn raw API payloads into high-signal contract & state facts without 50KB JSON bloat."""
    facts: List[str] = []
    guard_msg: Optional[str] = None
    observed_states: List[str] = []
    is_noisy_read = False

    if status_code >= 400:
        detail = res_json.get("detail") if isinstance(res_json, dict) else str(res_json)
        guard_msg = f"HTTP {status_code} on `{method} {path}`: `{detail}`"
        facts.append(f"🛡 **GUARD TRIGGERED (`{status_code}`):** `{detail}`")
        if status_code == 422 and "closed" in str(detail).lower():
            observed_states.append("SEND_BLOCKED")
        return {"facts": facts, "guard": guard_msg, "states": observed_states, "is_noisy_read": False}

    if path == "/api/auth/login" or path == "/api/auth/demo-login":
        user = res_json.get("user", {}) if isinstance(res_json, dict) else {}
        facts.append(f"Auth: email=`{user.get('email')}`, role=`{user.get('role')}`")
    elif path == "/api/ingestion/preflight" and isinstance(res_json, dict):
        facts.append(
            f"Pre-flight: valid=`{res_json.get('valid')}`, missing=`{res_json.get('missing_columns')}`, "
            f"total_rows=`{res_json.get('total_rows')}`"
        )
    elif path in ("/api/ingestion/seed", "/api/ingestion/csv", "/api/ingestion/single") and isinstance(res_json, dict):
        facts.append(
            f"Ingestion Audit: queued_ai=`{res_json.get('queued_for_ai_count')}`, "
            f"in_batch_dup=`{res_json.get('in_batch_duplicates_skipped')}`, "
            f"db_skipped=`{res_json.get('already_in_db_skipped')}`, "
            f"ledger_collisions=`{res_json.get('already_contacted_in_ledger')}`"
        )
        observed_states.append("QUEUED_FOR_AI")
    elif path == "/api/ingestion/x-lookup" and isinstance(res_json, dict):
        facts.append(
            f"Lookup `@{res_json.get('handle')}`: can_dm=`{res_json.get('can_dm')}`, "
            f"already_contacted=`{res_json.get('already_contacted')}` ({res_json.get('existing_ledger_status')})"
        )
    elif path.startswith("/api/candidates/") and path.endswith("/send") and isinstance(res_json, dict):
        cand = res_json.get("candidate", {})
        ledger = res_json.get("ledger", {})
        if cand.get("status"):
            observed_states.append(str(cand["status"]))
        facts.append(
            f"Outreach Dispatch: `@{cand.get('handle')}` -> `{cand.get('status')}` | "
            f"Ledger id=`{ledger.get('id')}`, mode=`{ledger.get('dispatch_mode')}`, dm=`{ledger.get('external_dm_id')}`"
        )
    elif path.startswith("/api/candidates/") and path.endswith("/reject") and isinstance(res_json, dict):
        if res_json.get("status"):
            observed_states.append(str(res_json["status"]))
        facts.append(f"Reject: `@{res_json.get('handle')}` -> `{res_json.get('status')}`")
    elif path.startswith("/api/candidates/") and path.endswith("/retry") and isinstance(res_json, dict):
        if res_json.get("status"):
            observed_states.append(str(res_json["status"]))
        facts.append(f"Retry AI: `@{res_json.get('handle')}` -> `{res_json.get('status')}`")
    elif "/evaluate/" in path and isinstance(res_json, dict):
        cand = res_json.get("candidate", {})
        ev = res_json.get("evaluation", {})
        if cand.get("status"):
            observed_states.append(str(cand["status"]))
        facts.append(
            f"AI Evaluate `@{cand.get('handle')}` -> `{cand.get('status')}` "
            f"(score=`{ev.get('fit_score')}/4`, insufficient=`{ev.get('insufficient_evidence')}`)"
        )
    elif path == "/api/queue/process" and isinstance(res_json, dict):
        facts.append(
            f"Queue Worker: processed=`{res_json.get('processed')}`, ai_evaluated=`{res_json.get('ai_evaluated')}`, "
            f"dm_sent=`{res_json.get('dm_sent')}`, failed=`{res_json.get('failed_or_blocked')}`"
        )
    elif path.endswith("/reply") and isinstance(res_json, dict):
        ledger = res_json.get("ledger", res_json)
        observed_states.append("REPLIED")
        facts.append(
            f"Reply Recorded: `{ledger.get('outreach_id')}` -> `REPLIED`, "
            f"`needs_attention={ledger.get('needs_attention')}`"
        )
    elif path.endswith("/handled") and isinstance(res_json, dict):
        ledger = res_json.get("ledger", res_json)
        facts.append(
            f"Marked Handled: `{ledger.get('outreach_id')}` -> `needs_attention={ledger.get('needs_attention')}`"
        )
    elif path == "/api/candidates/state-summary" and isinstance(res_json, dict):
        is_noisy_read = True
        nz = {k: v for k, v in (res_json.get("state_counts") or {}).items() if v > 0}
        observed_states.extend(nz.keys())
        facts.append(f"Summary: total=`{res_json.get('total_candidates')}` `{nz}`")
    elif path == "/api/candidates" and isinstance(res_json, dict):
        is_noisy_read = True
        facts.append(f"List Candidates: total=`{res_json.get('total')}`")
    elif path == "/api/ledger" and isinstance(res_json, dict):
        is_noisy_read = True
        facts.append(f"List Ledger: total=`{res_json.get('total')}`, counts=`{res_json.get('counts')}`")
    elif path == "/api/ledger/calibration" and isinstance(res_json, dict):
        is_noisy_read = True
        kpi = res_json.get("kpi", {})
        facts.append(
            f"Calibration KPI: aligned=`{kpi.get('alignment_accuracy')}%` "
            f"({kpi.get('aligned_count')}/{kpi.get('unique_benchmarked')}), "
            f"safety_blocks=`{kpi.get('safety_blocks_verified')}/{kpi.get('safety_blocks_total')}`, "
            f"mean_delta=`{kpi.get('mean_score_delta')}`"
        )

    return {
        "facts": facts,
        "guard": guard_msg,
        "states": observed_states,
        "is_noisy_read": is_noisy_read,
    }


def record_http_trace(
    *,
    testcase_id: str,
    method: str,
    path: str,
    query: str,
    status_code: int,
    duration_ms: float,
    req_bytes: bytes,
    res_bytes: bytes,
    db_snapshot: Optional[Dict[str, Any]] = None,
    source: str = "http",
) -> None:
    """Emit concise terminal trace, append raw JSONL, and append semantic Flow Contract line to <TC>.md."""
    now_iso = datetime.now(timezone.utc).isoformat()
    safe_id = sanitize_testcase_id(testcase_id)
    req_json = _safe_json(req_bytes)
    res_json = _safe_json(res_bytes)
    contract_keys = extract_contract_keys(res_json)
    sem = _summarize_semantic_event(method, path, status_code, req_json, res_json)

    full_path = f"{path}?{query}" if query else path
    trace_dir = get_trace_output_dir()
    state = _load_tc_state(trace_dir, safe_id)
    state["api_count"] = int(state.get("api_count", 0)) + 1

    # Always write full telemetry into raw JSONL for deep debugging
    raw_entry = {
        "timestamp": now_iso,
        "testcase": safe_id,
        "source": source,
        "method": method,
        "path": full_path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "contract_keys": contract_keys,
        "semantic_facts": sem["facts"],
        "request": req_json,
        "response": res_json,
    }
    with (trace_dir / "raw" / "all-traces.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(raw_entry, ensure_ascii=False) + "\n")

    for st in sem["states"]:
        if st not in state["observed_states"]:
            state["observed_states"].append(st)
    if sem["guard"] and sem["guard"] not in state["guards_triggered"]:
        state["guards_triggered"].append(sem["guard"])

    diff = _diff_snapshots(state.get("last_db_snapshot"), db_snapshot) if db_snapshot else {"transitions": [], "summary": ""}
    if db_snapshot:
        for tr in diff["transitions"]:
            if tr not in state["transitions"]:
                state["transitions"].append(tr)
        for st in db_snapshot.get("non_zero_states", {}).keys():
            if st not in state["observed_states"]:
                state["observed_states"].append(st)
        state["last_db_snapshot"] = db_snapshot

    # Deduplicate repetitive unchanged GET UI polls in the human-readable <TC>.md flow file
    sig = f"{method}:{full_path}:{status_code}:{'|'.join(sem['facts'])}"
    if sem["is_noisy_read"] and state.get("last_read_sig") == sig and not diff["transitions"]:
        state["read_repeat_count"] = int(state.get("read_repeat_count", 0)) + 1
        _save_tc_state(trace_dir, state)
        return

    state["last_read_sig"] = sig if sem["is_noisy_read"] else None
    state["read_repeat_count"] = 0
    _save_tc_state(trace_dir, state)

    icon = "🛡" if status_code >= 400 else ("🔹" if sem["is_noisy_read"] else "⚡")
    md_lines = [f"- {icon} **`{method} {full_path}`** $\\rightarrow$ **`{status_code}`** ({duration_ms:.1f}ms)"]
    for f in sem["facts"]:
        md_lines.append(f"  - {f}")
    if diff["transitions"]:
        md_lines.append(f"  - **DB Transitions:** {', '.join(diff['transitions'][:8])}")
    if db_snapshot and not sem["is_noisy_read"] and not diff["transitions"]:
        md_lines.append(f"  - **DB Check:** {diff['summary']}")
    if not sem["is_noisy_read"] and contract_keys:
        md_lines.append(f"  - Contract keys: `{contract_keys[:12]}{'...' if len(contract_keys) > 12 else ''}`")

    _append_md(trace_dir, safe_id, "\n".join(md_lines) + "\n")

    short_fact = sem["facts"][0] if sem["facts"] else f"keys={contract_keys[:6]}"
    logger.info("[TRACE][%s] %s %s -> %s | %s", safe_id, method, full_path, status_code, short_fact)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build _FLOW_COVERAGE_REPORT.md from trace outputs.")
    parser.add_argument("--build-report", action="store_true")
    args = parser.parse_args()
    if args.build_report:
        out = generate_flow_coverage_report()
        print(f"[tracing] Generated flow coverage report at {out}")
