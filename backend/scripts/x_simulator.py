"""
Local X API v2 HTTP Simulator for $0 Dev & E2E Testing.

Implements authentic X API v2 endpoints over localhost HTTP so developers can
exercise real `httpx` requests, Bearer/OAuth 1.0a headers, and error codes
(401 / 402 / 403 / 404 / 429) without paying for X API credits:

    - GET  /health
    - GET  /2/users/by/username/{username}
    - GET  /2/users/{user_id}/tweets
    - POST /2/dm_conversations/with/{participant_id}/messages
    - GET  /2/dm_events/sent

Special test handles/tokens for negative HTTP path testing:
    - Token containing `invalid` or `bad_token`   -> HTTP 401 Unauthorized
    - Token containing `depleted` / @credits_depleted -> HTTP 402 Payment Required
    - Token containing `forbidden` / @forbidden_handle -> HTTP 403 Forbidden
    - Handle `@rate_limit`                         -> HTTP 429 Too Many Requests
    - Handle `@missing_user` / `@not_found_user`   -> HTTP 404 Not Found

Run standalone:
    python -m backend.scripts.x_simulator --host 127.0.0.1 --port 8099
"""

import argparse
import csv
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_CSV_PATH = PROJECT_ROOT / "genai-outreach-pack" / "candidates_seed.csv"

simulator_app = FastAPI(
    title="Local X API v2 Simulator",
    description="Zero-cost local HTTP simulator matching X API v2 response envelopes.",
    version="1.0.0",
)

_DM_LEDGER: List[Dict[str, Any]] = []


def _parse_bool(raw: Optional[str], default: bool = True) -> bool:
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y"}


def _deterministic_user_id(handle: str) -> str:
    digest = hashlib.sha256(handle.encode("utf-8")).hexdigest()
    numeric_tail = str(int(digest[:12], 16)).zfill(9)[-9:]
    return f"9{numeric_tail}"


def _load_seed_profiles() -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Load seed candidate records from candidates_seed.csv indexed by handle & numeric id."""
    by_handle: Dict[str, Dict[str, Any]] = {}
    by_id: Dict[str, Dict[str, Any]] = {}
    if not SEED_CSV_PATH.exists():
        return by_handle, by_id

    with open(SEED_CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            handle = (row.get("handle") or "").strip().lstrip("@").lower()
            if not handle:
                continue
            raw_uid = (row.get("x_user_id") or "").strip()
            uid = raw_uid if raw_uid.isdigit() else _deterministic_user_id(handle)
            tweets = [
                t.strip()
                for t in (row.get("recent_tweets") or "").split("||")
                if t.strip()
            ]
            profile = {
                "id": uid,
                "name": (row.get("name") or handle).strip(),
                "username": handle,
                "description": (row.get("bio") or f"Builder @{handle}").strip(),
                "location": (row.get("location") or "Southeast Asia").strip(),
                "can_dm": _parse_bool(row.get("can_dm"), default=True),
                "tweets": tweets or [f"Shipping AI infrastructure updates from @{handle}."],
            }
            by_handle[handle] = profile
            by_id[uid] = profile
    return by_handle, by_id


_SEED_BY_HANDLE, _SEED_BY_ID = _load_seed_profiles()
_DYNAMIC_BY_ID: Dict[str, Dict[str, Any]] = {}


def _synthesize_profile(handle: str) -> Dict[str, Any]:
    uid = _deterministic_user_id(handle)
    display_name = handle.replace("_", " ").replace(".", " ").title()
    profile = {
        "id": uid,
        "name": display_name,
        "username": handle,
        "description": (
            f"Founder & AI Engineer @{handle}. Building frontier AI infrastructure "
            "and autonomous systems in Southeast Asia."
        ),
        "location": "Singapore / Southeast Asia",
        "can_dm": True,
        "tweets": [
            f"[2026-11-10] Benchmarking low-latency inference kernels on edge GPUs (@{handle}).",
            "[2026-11-04] Shipping production multi-agent tooling for SEA enterprise teams.",
        ],
    }
    _DYNAMIC_BY_ID[uid] = profile
    return profile


def _resolve_profile_by_handle(handle: str) -> Dict[str, Any]:
    return _SEED_BY_HANDLE.get(handle) or _synthesize_profile(handle)


def _resolve_profile_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return _SEED_BY_ID.get(user_id) or _DYNAMIC_BY_ID.get(user_id)


def _problem_response(
    status: int,
    title: str,
    detail: str,
    problem_type: str = "about:blank",
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "title": title,
            "detail": detail,
            "status": status,
            "type": problem_type,
        },
        headers=headers or {},
    )


def _validate_auth_header(
    authorization: Optional[str],
    require_oauth1: bool = False,
) -> tuple[Optional[JSONResponse], str]:
    """Validate Bearer or OAuth 1.0a header and enforce negative test token rules."""
    auth = (authorization or "").strip()
    if not auth:
        return (
            _problem_response(
                401,
                "Unauthorized",
                "Missing Authorization header.",
            ),
            "",
        )

    if require_oauth1:
        if not auth.startswith("OAuth "):
            return (
                _problem_response(
                    403,
                    "Forbidden",
                    "OAuth 1.0a User Context Authorization header required for DM creation.",
                ),
                "",
            )
        required_fields = ("oauth_consumer_key=", "oauth_token=", "oauth_signature=")
        if not all(field in auth for field in required_fields):
            return (
                _problem_response(
                    401,
                    "Unauthorized",
                    "Malformed OAuth 1.0a signature header.",
                ),
                "",
            )
        lowered = auth.lower()
        if "invalid" in lowered:
            return _problem_response(401, "Unauthorized", "Invalid OAuth 1.0a token."), ""
        if "depleted" in lowered:
            return (
                _problem_response(
                    402,
                    "Payment Required",
                    "credits depleted",
                    problem_type="https://api.x.com/2/problems/credits-depleted",
                ),
                "",
            )
        return None, auth

    if auth.startswith("Bearer "):
        token = auth[len("Bearer ") :].strip()
        if not token:
            return _problem_response(401, "Unauthorized", "Empty X Bearer Token."), ""
        lowered = token.lower()
        if "invalid" in lowered or lowered == "bad_token":
            return (
                _problem_response(401, "Unauthorized", "Invalid or revoked X Bearer Token."),
                "",
            )
        if "depleted" in lowered:
            return (
                _problem_response(
                    402,
                    "Payment Required",
                    "credits depleted",
                    problem_type="https://api.x.com/2/problems/credits-depleted",
                ),
                "",
            )
        if "forbidden" in lowered:
            return (
                _problem_response(403, "Forbidden", "Client app lacks read scope."),
                "",
            )
        return None, token

    if auth.startswith("OAuth "):
        return None, auth

    return (
        _problem_response(
            401,
            "Unauthorized",
            "Unsupported Authorization scheme (expected Bearer or OAuth).",
        ),
        "",
    )


def _check_handle_fault_trigger(handle: str) -> Optional[JSONResponse]:
    if handle in {"credits_depleted", "sim_402"}:
        return _problem_response(
            402,
            "Payment Required",
            "credits depleted",
            problem_type="https://api.x.com/2/problems/credits-depleted",
        )
    if handle in {"invalid_auth", "sim_401"}:
        return _problem_response(401, "Unauthorized", "Unauthorized simulated user lookup.")
    if handle in {"forbidden_handle", "sim_403"}:
        return _problem_response(403, "Forbidden", "Access denied to protected X account.")
    if handle in {"rate_limit", "sim_429"}:
        return _problem_response(
            429,
            "Too Many Requests",
            "Rate limit exceeded on /2/users/by/username.",
            headers={"Retry-After": "30"},
        )
    if handle in {"missing_user", "not_found_user", "sim_404"}:
        return _problem_response(
            404,
            "Not Found Error",
            f"Could not find user with username: [{handle}].",
        )
    return None


@simulator_app.get("/health")
def simulator_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "local-x-api-v2-simulator",
        "loaded_seed_profiles": len(_SEED_BY_HANDLE),
        "dms_sent_count": len(_DM_LEDGER),
    }


@simulator_app.get("/2/users/by")
def sim_get_users_by_usernames(
    usernames: str = Query(..., description="Comma-separated usernames (up to 100)"),
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=False)
    if auth_err is not None:
        return auth_err

    handles = [
        h.strip().lstrip("@").lower()
        for h in (usernames or "").split(",")
        if h.strip().lstrip("@")
    ][:100]
    data: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    import re

    for h in handles:
        if not re.fullmatch(r"[A-Za-z0-9_]{1,30}", h):
            return JSONResponse(
                status_code=400,
                content={
                    "title": "Invalid Request",
                    "detail": "One or more parameters to your request was invalid.",
                },
            )
        fault = _check_handle_fault_trigger(h)
        if fault is not None:
            if fault.status_code == 404:
                errors.append(
                    {
                        "value": h,
                        "detail": f"Could not find user with username: [{h}].",
                        "title": "Not Found Error",
                    }
                )
                continue
            return fault
        prof = _resolve_profile_by_handle(h)
        data.append(
            {
                "id": prof["id"],
                "name": prof["name"],
                "username": prof["username"],
                "description": prof["description"],
                "location": prof["location"],
                "can_dm": prof["can_dm"],
                "public_metrics": {"followers_count": 1240},
            }
        )

    body: Dict[str, Any] = {"data": data}
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=200, content=body)


@simulator_app.get("/2/users/by/username/{username}")
def sim_get_user_by_username(
    username: str,
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=False)
    if auth_err is not None:
        return auth_err

    clean_handle = username.strip().lstrip("@").lower()
    fault = _check_handle_fault_trigger(clean_handle)
    if fault is not None:
        return fault

    profile = _resolve_profile_by_handle(clean_handle)
    return JSONResponse(
        status_code=200,
        content={
            "data": {
                "id": profile["id"],
                "name": profile["name"],
                "username": profile["username"],
                "description": profile["description"],
                "location": profile["location"],
                "can_dm": profile["can_dm"],
            }
        },
    )


@simulator_app.get("/2/users/{user_id}/tweets")
def sim_get_user_tweets(
    user_id: str,
    max_results: int = Query(default=5, ge=1, le=100),
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=False)
    if auth_err is not None:
        return auth_err

    profile = _resolve_profile_by_id(user_id)
    if profile is None:
        return _problem_response(
            404,
            "Not Found Error",
            f"Could not find user with id: [{user_id}].",
        )

    tweets = profile["tweets"][:max_results]
    data = [
        {
            "id": f"{user_id}0{idx + 1}",
            "text": text,
            "created_at": f"2026-11-{max(1, 10 - idx):02d}T09:00:00.000Z",
        }
        for idx, text in enumerate(tweets)
    ]
    return JSONResponse(
        status_code=200,
        content={"data": data, "meta": {"result_count": len(data)}},
    )


class DmCreateRequest(BaseModel):
    text: str


@simulator_app.post("/2/dm_conversations/with/{participant_id}/messages")
async def sim_create_dm(
    participant_id: str,
    payload: DmCreateRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=True)
    if auth_err is not None:
        return auth_err

    profile = _resolve_profile_by_id(participant_id)
    if profile is not None and not profile.get("can_dm", True):
        return _problem_response(
            403,
            "Forbidden",
            f"You cannot send messages to @{profile['username']} (DMs disabled).",
        )

    if participant_id == "9999990429":
        return _problem_response(
            429,
            "Too Many Requests",
            "DM rate limit exceeded.",
            headers={"Retry-After": "45"},
        )

    seq = len(_DM_LEDGER) + 1
    dm_event = {
        "dm_conversation_id": f"{participant_id}-sim-conv",
        "dm_event_id": f"sim_dm_{seq:04d}",
        "participant_id": participant_id,
        "text": payload.text,
        "path": str(request.url.path),
    }
    _DM_LEDGER.append(dm_event)
    return JSONResponse(
        status_code=201,
        content={
            "data": {
                "dm_conversation_id": dm_event["dm_conversation_id"],
                "dm_event_id": dm_event["dm_event_id"],
            }
        },
    )


@simulator_app.get("/2/dm_events/sent")
def sim_list_sent_dms() -> Dict[str, Any]:
    return {"count": len(_DM_LEDGER), "events": list(_DM_LEDGER)}


@simulator_app.get("/2/dm_events")
def sim_get_dm_events(
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=True)
    if auth_err is not None:
        return auth_err
    return JSONResponse(status_code=200, content={"data": list(_DM_LEDGER), "meta": {"result_count": len(_DM_LEDGER)}})


@simulator_app.get("/2/dm_conversations/with/{participant_id}/dm_events")
def sim_get_conversation_dm_events(
    participant_id: str,
    authorization: Optional[str] = Header(default=None),
) -> JSONResponse:
    auth_err, _ = _validate_auth_header(authorization, require_oauth1=True)
    if auth_err is not None:
        return auth_err
    events = [ev for ev in _DM_LEDGER if str(ev.get("participant_id")) == str(participant_id)]
    return JSONResponse(status_code=200, content={"data": events, "meta": {"result_count": len(events)}})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Local X API v2 Simulator ($0 HTTP dev server)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8099)
    args = parser.parse_args()
    uvicorn.run(simulator_app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
