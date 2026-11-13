"""
X (Twitter) API v2 Real Client & OAuth 1.0a Helpers (Sub-task 7.2).

Uses Python stdlib (`hmac`, `hashlib`, `base64`, `urllib.parse`) + `httpx`
so no extra OAuth dependencies are required in `requirements.txt`.
"""

import base64
import hashlib
import hmac
import logging
import secrets
import time
import urllib.parse
from typing import Any, Dict, Optional

import httpx

from backend.app.core.config import settings

logger = logging.getLogger("genai_fund.x_client")

DEFAULT_X_API_BASE = "https://api.twitter.com/2"


def get_x_api_base() -> str:
    """Return active X API v2 base URL (real api.twitter.com/2 or local dev simulator)."""
    raw = (getattr(settings, "X_API_BASE_URL", "") or DEFAULT_X_API_BASE).strip()
    return (raw or DEFAULT_X_API_BASE).rstrip("/")


def is_local_x_simulator() -> bool:
    """True when X_API_BASE_URL points to a local HTTP simulator rather than api.twitter.com/x.com."""
    base = get_x_api_base().lower()
    return "127.0.0.1" in base or "localhost" in base or "0.0.0.0" in base


def extract_x_api_error_detail(resp: httpx.Response) -> str:
    """Parse human-readable problem detail from an X API v2 JSON/text response."""
    try:
        payload = resp.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        title = str(payload.get("title") or "").strip()
        detail = str(payload.get("detail") or payload.get("error") or "").strip()
        if not detail and isinstance(payload.get("errors"), list) and payload["errors"]:
            first = payload["errors"][0]
            if isinstance(first, dict):
                detail = str(first.get("detail") or first.get("message") or first.get("title") or "").strip()
                if not title:
                    title = str(first.get("title") or "").strip()
        if title and detail and title.lower() not in detail.lower():
            return f"{title} — {detail}"
        if detail:
            return detail
        if title:
            return title

    raw_text = (resp.text or "").strip()
    return raw_text[:240] if raw_text else f"HTTP {resp.status_code}"


class XApiRateLimitError(RuntimeError):
    """Raised when live X API v2 responds with HTTP 429 Too Many Requests."""

    def __init__(self, message: str, retry_after_seconds: float = 60.0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class XApiDispatchError(RuntimeError):
    """Raised when live X API v2 returns a non-retryable client/server error."""


def _is_configured(value: str) -> bool:
    v = (value or "").strip()
    return bool(v and not v.startswith("your_"))


def has_x_bearer_token() -> bool:
    return _is_configured(settings.X_BEARER_TOKEN)


def has_x_oauth_credentials() -> bool:
    return all(
        _is_configured(val)
        for val in (
            settings.X_API_KEY,
            settings.X_API_SECRET,
            settings.X_ACCESS_TOKEN,
            settings.X_ACCESS_TOKEN_SECRET,
        )
    )


def _percent_encode(val: str) -> str:
    return urllib.parse.quote(str(val), safe="")


def build_oauth1_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
    nonce: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> str:
    """Build an RFC 5849 OAuth 1.0a HMAC-SHA1 Authorization header."""
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    parsed = urllib.parse.urlsplit(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)

    all_params = sorted([(k, v) for k, v in query_pairs] + list(oauth_params.items()))
    param_str = "&".join(f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in all_params)
    signature_base = "&".join(
        [
            method.upper(),
            _percent_encode(base_url),
            _percent_encode(param_str),
        ]
    )
    signing_key = f"{_percent_encode(consumer_secret)}&{_percent_encode(access_token_secret)}"
    digest = hmac.new(
        signing_key.encode("utf-8"),
        signature_base.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    oauth_params["oauth_signature"] = base64.b64encode(digest).decode("ascii")

    header_parts = ", ".join(
        f'{_percent_encode(k)}="{_percent_encode(v)}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


def resolve_x_user_id(handle: str, timeout: float = 8.0) -> Optional[str]:
    """Resolve numeric X user ID from handle via X API v2 Bearer or OAuth 1.0a."""
    clean_handle = handle.strip().lstrip("@")
    url = f"{get_x_api_base()}/users/by/username/{clean_handle}"

    headers: Dict[str, str] = {}
    if has_x_bearer_token():
        headers["Authorization"] = f"Bearer {settings.X_BEARER_TOKEN.strip()}"
    elif has_x_oauth_credentials():
        headers["Authorization"] = build_oauth1_header(
            method="GET",
            url=url,
            consumer_key=settings.X_API_KEY.strip(),
            consumer_secret=settings.X_API_SECRET.strip(),
            access_token=settings.X_ACCESS_TOKEN.strip(),
            access_token_secret=settings.X_ACCESS_TOKEN_SECRET.strip(),
        )
    else:
        return None

    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params={"user.fields": "id,username"}, headers=headers)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "60"))
            raise XApiRateLimitError(
                f"X API user lookup rate-limited for @{clean_handle}",
                retry_after_seconds=retry_after,
            )
        if resp.status_code != 200:
            raise XApiDispatchError(
                f"X API failed resolving @{clean_handle} (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        return resp.json().get("data", {}).get("id")


def send_x_dm(
    handle: str,
    message: str,
    x_user_id: Optional[str] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Send a real Direct Message via X API v2 (`POST /2/dm_conversations/with/{id}/messages`).
    Requires all 4 OAuth 1.0a User Context credentials configured in settings.
    """
    if not has_x_oauth_credentials():
        raise XApiDispatchError("X OAuth 1.0a credentials are not fully configured.")

    participant_id = (x_user_id or "").strip()
    if not participant_id.isdigit():
        participant_id = resolve_x_user_id(handle, timeout=timeout) or ""

    if not participant_id or not participant_id.isdigit():
        raise XApiDispatchError(
            f"Unable to resolve numeric X participant_id for @{handle}."
        )

    url = f"{get_x_api_base()}/dm_conversations/with/{participant_id}/messages"
    auth_header = build_oauth1_header(
        method="POST",
        url=url,
        consumer_key=settings.X_API_KEY.strip(),
        consumer_secret=settings.X_API_SECRET.strip(),
        access_token=settings.X_ACCESS_TOKEN.strip(),
        access_token_secret=settings.X_ACCESS_TOKEN_SECRET.strip(),
    )
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, headers=headers, json={"text": message})
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "60"))
            raise XApiRateLimitError(
                f"X API DM dispatch rate-limited (HTTP 429) for @{handle}",
                retry_after_seconds=retry_after,
            )
        if resp.status_code not in (200, 201):
            raise XApiDispatchError(
                f"X API DM dispatch failed (HTTP {resp.status_code}) for @{handle}: {resp.text[:240]}"
            )

        data = resp.json().get("data", {})
        return {
            "dm_event_id": data.get("dm_event_id") or data.get("id") or f"x_dm_{participant_id}",
            "dm_conversation_id": data.get("dm_conversation_id"),
            "participant_id": participant_id,
        }

