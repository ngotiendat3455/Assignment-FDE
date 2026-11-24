import csv
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from sqlalchemy.orm import Session

MAX_CSV_X_VERIFY_BATCH = 25
X_TWEETS_CONCURRENCY = 3

from backend.app.core.config import settings
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.models.queue import JobQueue, JobStatus
from backend.app.services.rag_retriever import sync_candidate_chunks
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


def is_valid_x_username(handle: Optional[str]) -> bool:
    """
    Validate X API v2 username syntax (`A-Z`, `a-z`, `0-9`, `_`).
    Enforces X's strict 15-character limit against real X API v2, while allowing up to 30 chars
    on local X simulator handles (e.g. `@credits_depleted`, `@forbidden_handle`).
    """
    if not handle:
        return False
    max_len = 30 if is_local_x_simulator() and RuntimeGateway.get_active_profile() != "LIVE_PRODUCTION" else 15
    return bool(re.fullmatch(rf"[A-Za-z0-9_]{{1,{max_len}}}", handle))


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


def preflight_csv_check(
    csv_text: str,
    verify_with_x_api: bool = False,
    fetch_x_preview: bool = False,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Validate CSV headers and preview rows before ingestion.
    When `verify_with_x_api=True`, only the `handle` column is required (up to 25 rows/batch),
    performs $0 local deduplication inspection, and optionally runs 1 batch `GET /2/users/by`
    lookup when `fetch_x_preview=True`.
    Never raises on missing columns; preserves exact legacy schema when `verify_with_x_api=False`.
    """
    required_cols = ["handle"] if verify_with_x_api else ["handle", "name", "bio", "recent_tweets"]
    cleaned_csv = (csv_text or "").lstrip("\ufeff").strip()

    if not cleaned_csv:
        return {
            "valid": False,
            "total_rows": 0,
            "missing_columns": required_cols,
            "detected_columns": [],
            "preview_rows": [],
            "error_message": "CSV file is empty or missing header row.",
        }

    reader = csv.DictReader(io.StringIO(cleaned_csv))
    if not reader.fieldnames:
        return {
            "valid": False,
            "total_rows": 0,
            "missing_columns": required_cols,
            "detected_columns": [],
            "preview_rows": [],
            "error_message": "CSV is empty or missing header row.",
        }

    detected_columns = [c.strip().lstrip("\ufeff") for c in reader.fieldnames if c]
    mapping = _resolve_column_mapping(detected_columns)

    missing_columns: List[str] = []
    for req_key in required_cols:
        if not mapping.get(req_key):
            missing_columns.append(req_key)

    # Ignore completely blank trailing/separator lines (e.g. from Excel saves)
    all_rows = [
        row
        for row in reader
        if any(str(v or "").strip() for k, v in row.items() if k is not None)
    ]

    is_enhanced_mode = verify_with_x_api or fetch_x_preview
    batch_exceeded = verify_with_x_api and len(all_rows) > MAX_CSV_X_VERIFY_BATCH

    # Zero-cost local DB/Ledger/in-batch dedup inspection for Live X preflight mode
    existing_db_handles: set[str] = set()
    blocked_ledger_handles: set[str] = set()
    if is_enhanced_mode and db is not None:
        normalized_all = [
            normalize_handle(r.get(mapping["handle"], "") if mapping["handle"] else "")
            for r in all_rows
        ]
        unique_lookup = list({h for h in normalized_all if h})
        if unique_lookup:
            existing_db_handles = {
                h
                for (h,) in db.query(Candidate.handle)
                .filter(Candidate.handle.in_(unique_lookup))
                .all()
            }
            blocked_ledger_handles = {
                h
                for (h,) in db.query(OutreachLedger.handle)
                .filter(
                    OutreachLedger.handle.in_(unique_lookup),
                    OutreachLedger.status.in_([OutreachStatus.SENT, OutreachStatus.REPLIED]),
                )
                .all()
            }

    seen_in_csv: set[str] = set()
    row_dedup_statuses: List[str] = []
    local_dedup_summary = {
        "new_handles": 0,
        "in_batch_duplicates": 0,
        "already_in_db": 0,
        "already_contacted": 0,
    }
    if is_enhanced_mode:
        for row in all_rows:
            raw_h = row.get(mapping["handle"], "") if mapping["handle"] else ""
            norm_h = normalize_handle(raw_h)
            if not norm_h or (verify_with_x_api and not is_valid_x_username(norm_h)):
                row_dedup_statuses.append("INVALID")
                continue
            if norm_h in seen_in_csv:
                row_dedup_statuses.append("IN_BATCH_DUPLICATE")
                local_dedup_summary["in_batch_duplicates"] += 1
                continue
            seen_in_csv.add(norm_h)
            if norm_h in blocked_ledger_handles:
                row_dedup_statuses.append("ALREADY_CONTACTED")
                local_dedup_summary["already_contacted"] += 1
            elif norm_h in existing_db_handles:
                row_dedup_statuses.append("ALREADY_IN_DB")
                local_dedup_summary["already_in_db"] += 1
            else:
                row_dedup_statuses.append("NEW")
                local_dedup_summary["new_handles"] += 1

    live_profiles_by_handle: Dict[str, Dict[str, Any]] = {}
    if fetch_x_preview and not missing_columns and all_rows and not batch_exceeded:
        net_new_handles: List[str] = []
        for idx, row in enumerate(all_rows):
            if row_dedup_statuses[idx] != "NEW":
                continue
            norm_h = normalize_handle(row.get(mapping["handle"], "") if mapping["handle"] else "")
            if norm_h and norm_h not in net_new_handles:
                net_new_handles.append(norm_h)
        if net_new_handles:
            live_profiles_by_handle = _batch_fetch_x_user_profiles(net_new_handles[:MAX_CSV_X_VERIFY_BATCH])

    preview_limit = MAX_CSV_X_VERIFY_BATCH if verify_with_x_api else 5
    preview_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(all_rows[:preview_limit], start=1):
        raw_h = row.get(mapping["handle"], "") if mapping["handle"] else ""
        norm_h = normalize_handle(raw_h)
        name_val = str(row.get(mapping["name"], "")).strip() if mapping["name"] and row.get(mapping["name"]) else ""
        bio_val = str(row.get(mapping["bio"], "")).strip() if mapping["bio"] and row.get(mapping["bio"]) else ""
        tweets_val = str(row.get(mapping["recent_tweets"], "")).strip() if mapping["recent_tweets"] and row.get(mapping["recent_tweets"]) else ""
        loc_val = str(row.get(mapping["location"], "")).strip() if mapping["location"] and row.get(mapping["location"]) else "Southeast Asia"
        seg_val = str(row.get(mapping["segment"], "")).strip() if mapping["segment"] and row.get(mapping["segment"]) else ""

        can_dm_val = True
        if mapping["can_dm"] and row.get(mapping["can_dm"]) is not None:
            raw_dm = str(row[mapping["can_dm"]]).strip().lower()
            if raw_dm in ("false", "0", "no", "closed"):
                can_dm_val = False

        row_missing = list(missing_columns)
        if not norm_h and "handle" not in row_missing:
            row_missing.append("handle")
        if not verify_with_x_api:
            if not bio_val and "bio" not in row_missing:
                row_missing.append("bio")
            if not tweets_val and "recent_tweets" not in row_missing:
                row_missing.append("recent_tweets")

        is_row_valid = len(row_missing) == 0
        if not is_enhanced_mode:
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
            continue

        dedup_status = row_dedup_statuses[idx - 1]
        followers_count: Optional[int] = None
        if not is_row_valid or dedup_status == "INVALID":
            x_preview_status = "INVALID"
            is_row_valid = False
            if row_missing:
                note = f"Missing: {', '.join(row_missing)}"
            else:
                note = "Invalid X handle (A-Z, 0-9, _ only, max 15 chars)"
        elif dedup_status != "NEW":
            x_preview_status = "SKIPPED_DEDUP"
            dedup_notes = {
                "IN_BATCH_DUPLICATE": "Duplicate in CSV (skipped)",
                "ALREADY_IN_DB": "Already in DB (skipped)",
                "ALREADY_CONTACTED": "Already contacted in Ledger (blocked)",
            }
            note = dedup_notes.get(dedup_status, "Skipped")
        elif fetch_x_preview:
            live_prof = live_profiles_by_handle.get(norm_h)
            if live_prof:
                name_val = live_prof.get("name") or name_val or norm_h
                bio_val = live_prof.get("bio") or bio_val or f"Builder @{norm_h}"
                loc_val = live_prof.get("location") or loc_val
                followers_count = live_prof.get("followers_count")
                if live_prof.get("can_dm") is False:
                    can_dm_val = False
                x_preview_status = "FOUND"
                note = "Verified on Live X"
            else:
                x_preview_status = "NOT_FOUND"
                is_row_valid = False
                note = "Not found on X (404)"
        else:
            x_preview_status = "PENDING_SYNC"
            note = "Ready (Live X Sync)"

        preview_rows.append({
            "line_number": idx,
            "handle": f"@{norm_h}" if norm_h else "(empty)",
            "name": name_val or "Pending X API sync",
            "bio": bio_val or "Syncs bio & 5 recent tweets on Import",
            "recent_tweets": tweets_val or "Syncs up to 5 posts on Import",
            "location": loc_val,
            "can_dm": can_dm_val,
            "is_valid": is_row_valid,
            "validation_note": note,
            "segment": seg_val or "Auto / Default Segment",
            "dedup_status": dedup_status,
            "x_preview_status": x_preview_status,
            "followers_count": followers_count,
        })

    is_valid = len(missing_columns) == 0 and len(all_rows) > 0 and not batch_exceeded
    error_msg = None
    if missing_columns:
        error_msg = f"Missing required column(s): {', '.join(missing_columns)}"
    elif len(all_rows) == 0:
        error_msg = "CSV contains headers but 0 data rows."
    elif batch_exceeded:
        error_msg = (
            f"Live X API sync is capped at {MAX_CSV_X_VERIFY_BATCH} rows per CSV upload "
            f"(detected {len(all_rows)} rows) to protect X API rate limits and credits."
        )

    result: Dict[str, Any] = {
        "valid": is_valid,
        "total_rows": len(all_rows),
        "missing_columns": missing_columns,
        "detected_columns": detected_columns,
        "preview_rows": preview_rows,
        "error_message": error_msg,
    }
    if is_enhanced_mode:
        result["local_dedup_summary"] = local_dedup_summary
    return result


def parse_csv_content(csv_text: str, verify_with_x_api: bool = False) -> List[Dict[str, Any]]:
    """Parse CSV text with flexible column mapping and return list of raw dicts."""
    cleaned_csv = (csv_text or "").lstrip("\ufeff").strip()
    reader = csv.DictReader(io.StringIO(cleaned_csv))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or missing header row.")

    mapping = _resolve_column_mapping(list(reader.fieldnames))

    handle_col = mapping["handle"]
    name_col = mapping["name"]
    bio_col = mapping["bio"]
    tweets_col = mapping["recent_tweets"]

    if not handle_col:
        raise ValueError("Missing required column for X handle (e.g. 'handle', 'username').")
    if not verify_with_x_api:
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
            "name": str(row.get(name_col, "")).strip() if name_col and row.get(name_col) else "",
            "bio": str(row.get(bio_col, "")).strip() if bio_col and row.get(bio_col) else "",
            "recent_tweets": str(row.get(tweets_col, "")).strip() if tweets_col and row.get(tweets_col) else "",
            "location": str(row.get(loc_col, "")).strip() if loc_col and row.get(loc_col) else "Southeast Asia",
            "can_dm": can_dm_val,
            "segment": str(row.get(seg_col, "")).strip() if seg_col and row.get(seg_col) else "SEA AI & Robotics Ecosystem",
            "x_user_id": str(row.get(uid_col, "")).strip() if uid_col and row.get(uid_col) else None,
        })

    return parsed_rows


def _batch_fetch_x_user_profiles(
    handles: List[str],
    client: Optional[httpx.Client] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Batch-verify up to MAX_CSV_X_VERIFY_BATCH handles against X API v2 using
    a SINGLE `GET /2/users/by?usernames=h1,h2,...` HTTP request (no tweets fetched).
    """
    valid_handles = [h for h in handles if is_valid_x_username(h)]
    if not valid_handles:
        return {}
    if len(valid_handles) > MAX_CSV_X_VERIFY_BATCH:
        raise ValueError(
            f"Live X API batch sync is capped at {MAX_CSV_X_VERIFY_BATCH} net-new handles per upload "
            f"(got {len(valid_handles)})."
        )

    lookup_plan = RuntimeGateway.resolve_x_lookup_plan()
    if lookup_plan.strict_error:
        raise XApiLookupError(503, lookup_plan.strict_error)

    base_url = lookup_plan.base_url
    headers = {"Authorization": f"Bearer {lookup_plan.bearer_token}"}
    enriched: Dict[str, Dict[str, Any]] = {}

    def _run_lookup(http_client: httpx.Client) -> None:
        users_resp = http_client.get(
            f"{base_url}/users/by",
            params={
                "usernames": ",".join(valid_handles),
                "user.fields": "id,name,username,description,location,public_metrics",
            },
            headers=headers,
        )
        if users_resp.status_code != 200:
            raise _map_x_lookup_http_error(users_resp, valid_handles[0])

        users_data = users_resp.json().get("data") or []
        for u in users_data:
            uname = normalize_handle(u.get("username"))
            uid = str(u.get("id") or "").strip()
            if not uname or not uid:
                continue
            metrics = u.get("public_metrics") if isinstance(u.get("public_metrics"), dict) else {}
            raw_followers = metrics.get("followers_count")
            enriched[uname] = {
                "handle": uname,
                "x_user_id": uid,
                "name": (u.get("name") or uname).strip(),
                "bio": (u.get("description") or f"Builder @{uname}").strip(),
                "location": (u.get("location") or "Global / Unspecified").strip(),
                "followers_count": int(raw_followers) if isinstance(raw_followers, (int, float)) else None,
                "can_dm": bool(u.get("can_dm", True)) if "can_dm" in u else None,
                "recent_tweets": "",
            }

    try:
        if client is not None:
            _run_lookup(client)
        else:
            with httpx.Client(timeout=10.0) as local_client:
                _run_lookup(local_client)
    except httpx.RequestError as exc:
        raise XApiLookupError(
            503,
            f"Unable to reach X API endpoint ({base_url}) during batch CSV sync: {exc}",
        ) from exc

    return enriched


def _fetch_x_user_tweets_paginated(
    client: httpx.Client,
    base_url: str,
    uid: str,
    headers: Dict[str, str],
    max_tweets: Optional[int] = None,
) -> List[str]:
    """
    Fetch up to `max_tweets` recent public tweets for a user via X API v2 `/2/users/{uid}/tweets`.
    Uses up to 100 tweets per page (X API v2 single-page max), applies `X_TWEETS_EXCLUDE`
    (default `retweets,replies`) so RAG receives original authored technical posts instead of RT/reply noise,
    and falls back without `exclude` only if the user has zero original posts.
    """
    target_total = max(5, min(500, int(max_tweets or getattr(settings, "X_TWEETS_MAX_RESULTS", 50))))
    exclude_cfg = (getattr(settings, "X_TWEETS_EXCLUDE", "retweets,replies") or "").strip()

    def _run_fetch(use_exclude: Optional[str]) -> List[str]:
        collected: List[str] = []
        next_token: Optional[str] = None
        while len(collected) < target_total:
            remaining = target_total - len(collected)
            page_limit = max(5, min(100, remaining))
            params: Dict[str, Any] = {
                "max_results": page_limit,
                "tweet.fields": "created_at,text",
            }
            if use_exclude:
                params["exclude"] = use_exclude
            if next_token:
                params["pagination_token"] = next_token

            t_resp = client.get(
                f"{base_url}/users/{uid}/tweets",
                params=params,
                headers=headers,
            )
            if t_resp.status_code != 200:
                if not collected:
                    raise _map_x_lookup_http_error(t_resp, uid)
                break

            body = t_resp.json()
            page_items = body.get("data") or []
            if not page_items:
                break

            for t_obj in page_items:
                text = (t_obj.get("text") or "").strip()
                if text:
                    collected.append(text)
                if len(collected) >= target_total:
                    break

            next_token = (body.get("meta") or {}).get("next_token")
            if not next_token:
                break
        return collected

    result = _run_fetch(exclude_cfg or None)
    if not result and exclude_cfg:
        result = _run_fetch(None)
    return result


def _batch_fetch_x_profiles_and_tweets(handles: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Batch-verify and enrich up to MAX_CSV_X_VERIFY_BATCH handles against X API v2:
    1. Calls `GET /2/users/by?usernames=h1,h2,...` via `_batch_fetch_x_user_profiles`.
    2. Fetches `GET /2/users/{uid}/tweets?max_results=<X_TWEETS_MAX_RESULTS>` with bounded concurrency (`max_workers=3`).
    """
    if not handles:
        return {}

    lookup_plan = RuntimeGateway.resolve_x_lookup_plan()
    if lookup_plan.strict_error:
        raise XApiLookupError(503, lookup_plan.strict_error)

    base_url = lookup_plan.base_url
    headers = {"Authorization": f"Bearer {lookup_plan.bearer_token}"}
    enriched: Dict[str, Dict[str, Any]] = {}

    try:
        with httpx.Client(timeout=12.0) as client:
            enriched = _batch_fetch_x_user_profiles(handles, client=client)

            def _fetch_user_tweets(uname_and_uid: tuple[str, str]) -> tuple[str, str]:
                uname_key, uid_val = uname_and_uid
                try:
                    tweets_arr = _fetch_x_user_tweets_paginated(
                        client=client,
                        base_url=base_url,
                        uid=uid_val,
                        headers=headers,
                    )
                except XApiLookupError:
                    return uname_key, "No recent public tweets found via X API v2."
                return (
                    uname_key,
                    " || ".join(tweets_arr)
                    if tweets_arr
                    else "No recent public tweets found via X API v2.",
                )

            pairs = [(uname, info["x_user_id"]) for uname, info in enriched.items()]
            if pairs:
                with ThreadPoolExecutor(max_workers=min(X_TWEETS_CONCURRENCY, len(pairs))) as pool:
                    for uname_key, joined_tweets in pool.map(_fetch_user_tweets, pairs):
                        enriched[uname_key]["recent_tweets"] = joined_tweets
    except httpx.RequestError as exc:
        raise XApiLookupError(
            503,
            f"Unable to reach X API endpoint ({base_url}) during batch CSV sync: {exc}",
        ) from exc

    return enriched


def ingest_candidate_batch(
    db: Session,
    records: List[Dict[str, Any]],
    source_label: str = "CSV_IMPORT",
    default_segment: Optional[str] = None,
    skip_ledger_collisions: bool = True,
    verify_with_x_api: bool = False,
) -> Dict[str, Any]:
    """
    Ingest a batch of candidate records with 3-tier deduplication:
    1. In-batch deduplication: skips duplicate handles within the same upload.
    2. Database deduplication: checks existing records in 'candidates'.
    3. Ledger deduplication: checks 'outreach_ledger' to permanently protect against double-messaging.
    4. Optional Live X API v2 batch verification (`verify_with_x_api=True`) on net-new handles.
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
    pending_new_items: List[tuple[str, Dict[str, Any], bool, Optional[OutreachLedger]]] = []

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
                db.commit()
                sync_candidate_chunks(db, existing_candidate)

            report["details"].append({
                "handle": h,
                "status": "HISTORICAL_COLLISION" if is_past_messaged else "ALREADY_EXISTS_IN_DB",
                "id": existing_candidate.id,
                "already_contacted": is_past_messaged,
            })
            continue

        pending_new_items.append((h, item, is_past_messaged, existing_ledger))

    # Optional Step 2.5: Batch-sync net-new valid handles from X API v2 (1 `/users/by` call + bounded `/tweets`)
    x_enriched_map: Dict[str, Dict[str, Any]] = {}
    if verify_with_x_api and pending_new_items:
        net_new_handles = [
            h for h, _, _, _ in pending_new_items if is_valid_x_username(h)
        ]
        if net_new_handles:
            x_enriched_map = _batch_fetch_x_profiles_and_tweets(net_new_handles)

    new_candidates_to_create = []
    for h, item, is_past_messaged, existing_ledger in pending_new_items:
        if verify_with_x_api:
            if not is_valid_x_username(h):
                report["details"].append({
                    "handle": h,
                    "status": "SKIPPED_INVALID_X_HANDLE",
                    "already_contacted": is_past_messaged,
                })
                continue
            live_prof = x_enriched_map.get(h)
            if not live_prof:
                report["details"].append({
                    "handle": h,
                    "status": "SKIPPED_X_NOT_FOUND",
                    "already_contacted": is_past_messaged,
                })
                continue
            item = {
                **item,
                "name": live_prof["name"],
                "bio": live_prof["bio"],
                "recent_tweets": live_prof["recent_tweets"],
                "location": live_prof["location"] or item.get("location") or "Southeast Asia",
                "x_user_id": live_prof["x_user_id"],
                "can_dm": live_prof["can_dm"] if live_prof["can_dm"] is not None else item.get("can_dm", True),
            }

        # 3. Determine initial pipeline status for new candidate
        initial_status = CandidateStatus.QUEUED_FOR_AI.value
        if is_past_messaged and existing_ledger is not None:
            if existing_ledger.status == OutreachStatus.REPLIED.value:
                initial_status = CandidateStatus.REPLIED.value
            else:
                initial_status = CandidateStatus.SENT.value

        candidate = Candidate(
            handle=h,
            name=item["name"] or h,
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
        sync_candidate_chunks(db, cand)
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


def lookup_x_handle(
    db: Session,
    raw_handle: str,
    max_tweets: Optional[int] = None,
) -> Dict[str, Any]:
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
    if not is_valid_x_username(handle):
        raise ValueError(
            f"Invalid X handle '@{handle}': X usernames can only contain letters, numbers, and underscores (1–15 characters)."
        )

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
                tweets_list = _fetch_x_user_tweets_paginated(
                    client=client,
                    base_url=base_url,
                    uid=uid,
                    headers=headers,
                    max_tweets=max_tweets,
                )
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
        "location": user_data.get("location") or "Global / Unspecified",
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
