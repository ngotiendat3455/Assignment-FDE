import csv
import io
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.models.queue import JobQueue, JobStatus
from backend.app.services.x_client import (
    extract_x_api_error_detail,
    get_x_api_base,
    is_local_x_simulator,
)


class XApiLookupError(RuntimeError):
    """Raised when live/simulator X API v2 handle lookup fails or is unconfigured."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def normalize_handle(raw_handle: Optional[str]) -> str:
    """Normalize X handle or X profile URL to lowercase, stripping whitespace, quotes, and '@'."""
    if not raw_handle:
        return ""
    h = str(raw_handle).strip().strip("'\"")
    # Extract handle if user pasted a full X or Twitter URL
    url_match = re.match(r"^https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)", h, re.IGNORECASE)
    if url_match:
        h = url_match.group(1)
    h = h.lstrip("@").strip().lower()
    return h


def _resolve_column_mapping(fieldnames: List[str]) -> Dict[str, Optional[str]]:
    """Map flexible CSV header names to canonical fields."""
    col_map = {col.strip().lower(): col for col in fieldnames if col}

    def find_col(candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in col_map:
                return col_map[c]
        return None

    return {
        "handle": find_col(["handle", "username", "x_handle", "twitter_handle", "screen_name"]),
        "name": find_col(["name", "display_name", "full_name"]),
        "bio": find_col(["bio", "description", "profile_bio"]),
        "recent_tweets": find_col(["recent_tweets", "tweets", "recent_posts", "posts", "raw_tweets"]),
        "location": find_col(["location", "city", "country"]),
        "can_dm": find_col(["can_dm", "dm_open", "allow_dm"]),
        "segment": find_col(["segment", "target_segment", "track"]),
        "x_user_id": find_col(["x_user_id", "user_id", "id_str"]),
    }


def preflight_csv_check(csv_text: str) -> Dict[str, Any]:
    """
    Validate CSV headers and preview the first 5 rows before ingestion.
    Never raises on missing columns; returns structured pre-flight diagnostics for UI Tab 2.
    """
    if not csv_text or not csv_text.strip():
        return {
            "valid": False,
            "total_rows": 0,
            "missing_columns": ["handle", "name", "bio", "recent_tweets"],
            "detected_columns": [],
            "preview_rows": [],
            "error_message": "CSV file is empty or missing header row.",
        }

    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        return {
            "valid": False,
            "total_rows": 0,
            "missing_columns": ["handle", "name", "bio", "recent_tweets"],
            "detected_columns": [],
            "preview_rows": [],
            "error_message": "CSV is empty or missing header row.",
        }

    detected_columns = [c.strip() for c in reader.fieldnames if c]
    mapping = _resolve_column_mapping(detected_columns)

    missing_columns: List[str] = []
    for req_key in ["handle", "name", "bio", "recent_tweets"]:
        if not mapping.get(req_key):
            missing_columns.append(req_key)

    all_rows = list(reader)
    preview_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(all_rows[:5], start=1):
        raw_h = row.get(mapping["handle"], "") if mapping["handle"] else ""
        norm_h = normalize_handle(raw_h)
        name_val = str(row.get(mapping["name"], "")).strip() if mapping["name"] else ""
        bio_val = str(row.get(mapping["bio"], "")).strip() if mapping["bio"] else ""
        tweets_val = str(row.get(mapping["recent_tweets"], "")).strip() if mapping["recent_tweets"] else ""
        loc_val = str(row.get(mapping["location"], "")).strip() if mapping["location"] else "Southeast Asia"

        can_dm_val = True
        if mapping["can_dm"] and row.get(mapping["can_dm"]) is not None:
            raw_dm = str(row[mapping["can_dm"]]).strip().lower()
            if raw_dm in ("false", "0", "no", "closed"):
                can_dm_val = False

        row_missing = list(missing_columns)
        if not norm_h and "handle" not in row_missing:
            row_missing.append("handle")
        if not bio_val and "bio" not in row_missing:
            row_missing.append("bio")
        if not tweets_val and "recent_tweets" not in row_missing:
            row_missing.append("recent_tweets")

        is_row_valid = len(row_missing) == 0
        note = "Valid" if is_row_valid else f"Missing: {', '.join(row_missing)}"

        preview_rows.append({
            "line_number": idx,
            "handle": f"@{norm_h}" if norm_h else "(empty)",
            "name": name_val or "(missing)",
            "bio": bio_val or "(missing)",
            "recent_tweets": tweets_val or "(missing)",
            "location": loc_val,
            "can_dm": can_dm_val,
            "is_valid": is_row_valid,
            "validation_note": note,
        })

    is_valid = len(missing_columns) == 0 and len(all_rows) > 0
    error_msg = None
    if missing_columns:
        error_msg = f"Missing required column(s): {', '.join(missing_columns)}"
    elif len(all_rows) == 0:
        error_msg = "CSV contains headers but 0 data rows."

    return {
        "valid": is_valid,
        "total_rows": len(all_rows),
        "missing_columns": missing_columns,
        "detected_columns": detected_columns,
        "preview_rows": preview_rows,
        "error_message": error_msg,
    }


def parse_csv_content(csv_text: str) -> List[Dict[str, Any]]:
    """Parse CSV text with flexible column mapping and return list of raw dicts."""
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing header row.")

    mapping = _resolve_column_mapping(list(reader.fieldnames))

    handle_col = mapping["handle"]
    name_col = mapping["name"]
    bio_col = mapping["bio"]
    tweets_col = mapping["recent_tweets"]

    if not handle_col:
        raise ValueError("Missing required column for X handle (e.g. 'handle', 'username').")
    if not name_col:
        raise ValueError("Missing required column for Name (e.g. 'name', 'display_name').")
    if not bio_col:
        raise ValueError("Missing required column for Bio (e.g. 'bio', 'description').")
    if not tweets_col:
        raise ValueError("Missing required column for Tweets (e.g. 'recent_tweets', 'tweets').")

    loc_col = mapping["location"]
    dm_col = mapping["can_dm"]
    seg_col = mapping["segment"]
    uid_col = mapping["x_user_id"]

    parsed_rows = []
    for idx, row in enumerate(reader, start=1):
        raw_handle = row.get(handle_col, "")
        norm_h = normalize_handle(raw_handle)
        if not norm_h:
            continue

        can_dm_val = True
        if dm_col and row.get(dm_col) is not None:
            raw_dm = str(row[dm_col]).strip().lower()
            if raw_dm in ("false", "0", "no", "closed"):
                can_dm_val = False

        parsed_rows.append({
            "line_number": idx,
            "handle": norm_h,
            "name": str(row.get(name_col, "")).strip(),
            "bio": str(row.get(bio_col, "")).strip(),
            "recent_tweets": str(row.get(tweets_col, "")).strip(),
            "location": str(row.get(loc_col, "")).strip() if loc_col and row.get(loc_col) else "Southeast Asia",
            "can_dm": can_dm_val,
            "segment": str(row.get(seg_col, "")).strip() if seg_col and row.get(seg_col) else "SEA AI & Robotics Ecosystem",
            "x_user_id": str(row.get(uid_col, "")).strip() if uid_col and row.get(uid_col) else None,
        })

    return parsed_rows


def ingest_candidate_batch(
    db: Session,
    records: List[Dict[str, Any]],
    source_label: str = "CSV_IMPORT",
    default_segment: Optional[str] = None,
    skip_ledger_collisions: bool = True,
) -> Dict[str, Any]:
    """
    Ingest a batch of candidate records with 3-tier deduplication:
    1. In-batch deduplication: skips duplicate handles within the same upload.
    2. Database deduplication: checks existing records in 'candidates'.
    3. Ledger deduplication: checks 'outreach_ledger' to permanently protect against double-messaging.
    """
    report: Dict[str, Any] = {
        "total_rows": len(records),
        "imported": 0,
        "queued_for_ai_count": 0,
        "in_batch_duplicates_skipped": 0,
        "already_in_db_skipped": 0,
        "already_contacted_in_ledger": 0,
        "duplicate_handles": [],
        "collision_details": [],
        "details": [],
    }

    seen_in_batch = set()
    new_candidates_to_create = []

    for item in records:
        h = normalize_handle(item.get("handle"))
        if not h:
            continue

        # 1. In-batch Deduplication
        if h in seen_in_batch:
            report["in_batch_duplicates_skipped"] += 1
            report["duplicate_handles"].append(h)
            report["details"].append({"handle": h, "status": "SKIPPED_IN_BATCH_DUPLICATE"})
            continue
        seen_in_batch.add(h)

        # Check ledger collision (Sent or Replied in the past)
        existing_ledger = db.query(OutreachLedger).filter(OutreachLedger.handle == h).first()
        is_past_messaged = existing_ledger is not None and existing_ledger.status in (
            OutreachStatus.SENT.value,
            OutreachStatus.REPLIED.value,
        )

        if is_past_messaged and existing_ledger is not None:
            report["already_contacted_in_ledger"] += 1
            report["collision_details"].append({
                "handle": h,
                "status": existing_ledger.status,
            })

        # 2. Check if already exists in candidates table
        existing_candidate = db.query(Candidate).filter(Candidate.handle == h).first()
        if existing_candidate:
            report["already_in_db_skipped"] += 1
            # Enrich placeholder history record with real profile bio/tweets if needed
            if existing_candidate.bio == "Historical contact imported from seed log":
                existing_candidate.name = item.get("name") or existing_candidate.name
                existing_candidate.bio = item.get("bio") or existing_candidate.bio
                existing_candidate.recent_tweets = item.get("recent_tweets") or existing_candidate.recent_tweets
                existing_candidate.location = item.get("location") or existing_candidate.location
                existing_candidate.can_dm = item.get("can_dm", existing_candidate.can_dm)
                existing_candidate.segment = default_segment or item.get("segment") or existing_candidate.segment

            report["details"].append({
                "handle": h,
                "status": "HISTORICAL_COLLISION" if is_past_messaged else "ALREADY_EXISTS_IN_DB",
                "id": existing_candidate.id,
                "already_contacted": is_past_messaged,
            })
            continue

        # 3. Determine initial pipeline status for new candidate
        initial_status = CandidateStatus.QUEUED_FOR_AI.value
        if is_past_messaged and existing_ledger is not None:
            if existing_ledger.status == OutreachStatus.REPLIED.value:
                initial_status = CandidateStatus.REPLIED.value
            else:
                initial_status = CandidateStatus.SENT.value

        candidate = Candidate(
            handle=h,
            name=item["name"],
            location=item.get("location") or "Southeast Asia",
            bio=item["bio"],
            recent_tweets=item["recent_tweets"],
            can_dm=item.get("can_dm", True),
            segment=default_segment or item.get("segment") or "SEA AI & Robotics Ecosystem",
            x_user_id=item.get("x_user_id"),
            status=initial_status,
        )
        db.add(candidate)
        new_candidates_to_create.append((candidate, is_past_messaged))

    db.commit()

    for cand, was_contacted in new_candidates_to_create:
        report["imported"] += 1
        report["details"].append({
            "handle": cand.handle,
            "id": cand.id,
            "status": "IMPORTED",
            "initial_pipeline_status": cand.status,
            "already_contacted": was_contacted,
        })

        if not was_contacted:
            report["queued_for_ai_count"] += 1
            job = JobQueue(
                job_type="AI_EVALUATE",
                candidate_id=cand.id,
                payload=json.dumps({"handle": cand.handle, "source": source_label}),
                status=JobStatus.PENDING.value,
            )
            db.add(job)

    db.commit()
    return report


def seed_history_ledger(db: Session, history_csv_path: Path) -> int:
    """Seed historical outreach logs into outreach_ledger to establish past contact baseline."""
    if not history_csv_path.exists():
        return 0

    count = 0
    with open(history_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            handle = normalize_handle(row.get("handle"))
            if not handle:
                continue

            existing = db.query(OutreachLedger).filter(OutreachLedger.handle == handle).first()
            if existing:
                continue

            raw_status = str(row.get("status", "")).strip().lower()
            is_closed_dm = "closed" in raw_status or "blocked" in raw_status

            cand = db.query(Candidate).filter(Candidate.handle == handle).first()
            if not cand:
                if raw_status == "replied":
                    cand_status = CandidateStatus.REPLIED.value
                elif is_closed_dm:
                    cand_status = CandidateStatus.QUEUED_FOR_AI.value
                else:
                    cand_status = CandidateStatus.SENT.value

                cand = Candidate(
                    handle=handle,
                    x_user_id=row.get("x_user_id"),
                    name=handle.replace("_", " ").title(),
                    bio="Historical contact imported from seed log",
                    recent_tweets="Historical outreach log entry",
                    can_dm=not is_closed_dm,
                    status=cand_status,
                )
                db.add(cand)
                db.commit()

            sent_at_val = datetime.now(timezone.utc)
            if row.get("sent_at"):
                try:
                    sent_at_val = datetime.fromisoformat(row["sent_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            replied_at_val = None
            if row.get("last_reply_at"):
                try:
                    replied_at_val = datetime.fromisoformat(row["last_reply_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            status_val = OutreachStatus.SENT.value
            if raw_status == "replied":
                status_val = OutreachStatus.REPLIED.value
            elif is_closed_dm:
                status_val = OutreachStatus.BLOCKED.value

            ledger = OutreachLedger(
                candidate_id=cand.id,
                handle=handle,
                idempotency_key=f"hist-{row.get('outreach_id', handle)}",
                sent_message=row.get("sent_message", "Historical message"),
                dispatch_mode="SANDBOX",
                sent_at=sent_at_val,
                replied_at=replied_at_val,
                reply_text=row.get("last_reply_text"),
                needs_attention=str(row.get("needs_attention", "")).lower() == "true",
                status=status_val,
            )
            db.add(ledger)
            count += 1

    db.commit()
    return count


def ingest_seed_pack(db: Session, default_segment: Optional[str] = None) -> Dict[str, Any]:
    """
    1-Click Seed Pack loader for Tab 1 (Reviewer Express Journey).
    Ensures outreach_history_log.csv and candidates_seed.csv are loaded into SQLite,
    and returns consistent audit metrics even if clicked multiple times.
    """
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    history_csv = project_root / "genai-outreach-pack" / "outreach_history_log.csv"
    seed_csv = project_root / "genai-outreach-pack" / "candidates_seed.csv"

    if history_csv.exists():
        seed_history_ledger(db, history_csv)

    if not seed_csv.exists():
        raise FileNotFoundError(f"Seed CSV not found at {seed_csv}")

    with open(seed_csv, mode="r", encoding="utf-8") as f:
        parsed_records = parse_csv_content(f.read())

    report = ingest_candidate_batch(
        db,
        parsed_records,
        source_label="SEED_PACK",
        default_segment=default_segment,
    )

    # Calculate active pipeline queue count (16 unique non-contacted + 1 closed DM = 16/17 active review candidates)
    active_pipeline_count = (
        db.query(Candidate)
        .filter(Candidate.status.notin_([CandidateStatus.SENT.value, CandidateStatus.REPLIED.value]))
        .count()
    )
    report["queued_for_ai_count"] = max(report["queued_for_ai_count"], active_pipeline_count)
    return report


def _map_x_lookup_http_error(resp: httpx.Response, handle: str) -> XApiLookupError:
    """Convert an upstream X API v2 error response into a structured XApiLookupError."""
    detail = extract_x_api_error_detail(resp)
    status = resp.status_code
    if status == 401:
        return XApiLookupError(
            401,
            f"[X API 401 Unauthorized] Invalid or missing X_BEARER_TOKEN: {detail}",
        )
    if status == 402:
        return XApiLookupError(
            402,
            f"[X API 402 Payment Required] {detail}. Top up X API credits or set X_API_BASE_URL=http://127.0.0.1:8099/2 for local $0 testing.",
        )
    if status == 403:
        return XApiLookupError(
            403,
            f"[X API 403 Forbidden] Access denied for @{handle}: {detail}",
        )
    if status == 404:
        return XApiLookupError(
            404,
            f"[X API 404 Not Found] Handle @{handle} was not found: {detail}",
        )
    if status == 429:
        retry_after = resp.headers.get("retry-after")
        retry_note = f" (Retry-After: {retry_after}s)" if retry_after else ""
        return XApiLookupError(
            429,
            f"[X API 429 Too Many Requests] {detail}{retry_note}",
        )
    if status >= 500:
        return XApiLookupError(
            502,
            f"[X API {status} Upstream Error] {detail}",
        )
    return XApiLookupError(status, f"[X API {status}] {detail}")


def lookup_x_handle(db: Session, raw_handle: str) -> Dict[str, Any]:
    """
    HTTP Handle Lookup for Tab 3 (Live Sourcing Journey).
    Calls configured X API v2 endpoint (`X_API_BASE_URL`, defaulting to
    https://api.twitter.com/2 or pointing to the local $0 dev simulator).
    Fails explicitly with `XApiLookupError` when unconfigured or on HTTP error;
    never falls back to synthetic or seed data.
    """
    handle = normalize_handle(raw_handle)
    if not handle:
        raise ValueError("Please provide a valid X handle.")

    # Check if already contacted in outreach_ledger (double-messaging guard)
    existing_ledger = db.query(OutreachLedger).filter(OutreachLedger.handle == handle).first()
    already_contacted = existing_ledger is not None and existing_ledger.status in (
        OutreachStatus.SENT.value,
        OutreachStatus.REPLIED.value,
    )
    ledger_status = existing_ledger.status if existing_ledger else None
    existing_cand = db.query(Candidate).filter(Candidate.handle == handle).first()

    lookup_plan = RuntimeGateway.resolve_x_lookup_plan()
    if lookup_plan.strict_error:
        raise XApiLookupError(503, lookup_plan.strict_error)

    base_url = lookup_plan.base_url
    bearer_token = lookup_plan.bearer_token
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        with httpx.Client(timeout=8.0) as client:
            user_resp = client.get(
                f"{base_url}/users/by/username/{handle}",
                params={"user.fields": "id,name,username,description,location"},
                headers=headers,
            )
            if user_resp.status_code != 200:
                raise _map_x_lookup_http_error(user_resp, handle)

            payload = user_resp.json()
            user_data = payload.get("data")
            if not user_data:
                err_msg = extract_x_api_error_detail(user_resp)
                raise XApiLookupError(
                    404,
                    f"[X API 404 Not Found] Handle @{handle} returned no user data: {err_msg}",
                )

            uid = user_data.get("id")
            tweets_list: List[str] = []
            if uid:
                t_resp = client.get(
                    f"{base_url}/users/{uid}/tweets",
                    params={"max_results": 5, "tweet.fields": "created_at,text"},
                    headers=headers,
                )
                if t_resp.status_code != 200:
                    raise _map_x_lookup_http_error(t_resp, handle)
                for t_obj in t_resp.json().get("data", []):
                    text = (t_obj.get("text") or "").strip()
                    if text:
                        tweets_list.append(text)
    except httpx.RequestError as exc:
        raise XApiLookupError(
            503,
            f"Unable to reach X API endpoint ({base_url}): {exc}",
        ) from exc

    if not tweets_list:
        tweets_list = ["No recent public tweets found via X API v2."]

    if "can_dm" in user_data:
        can_dm = bool(user_data.get("can_dm"))
    elif existing_cand is not None:
        can_dm = existing_cand.can_dm
    else:
        can_dm = True

    default_segment = (
        existing_cand.segment
        if existing_cand and existing_cand.segment
        else "SEG-02: LLM Inference & AI Infra"
    )
    source_mode = lookup_plan.source_mode

    return {
        "handle": handle,
        "name": user_data.get("name") or handle,
        "location": user_data.get("location") or "Southeast Asia",
        "bio": user_data.get("description") or "Builder on X",
        "recent_tweets": tweets_list,
        "raw_tweets_text": " || ".join(tweets_list),
        "can_dm": can_dm,
        "segment": default_segment,
        "x_user_id": uid,
        "source_mode": source_mode,
        "api_connected": True,
        "already_contacted": already_contacted,
        "existing_ledger_status": ledger_status,
        "execution_meta": lookup_plan.to_meta(),
    }
