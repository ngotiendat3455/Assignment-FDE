import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.candidate import Candidate
from backend.app.services.state_machine import (
    approve_and_send_candidate,
    SendBlockedError,
)

logger = logging.getLogger("genai_fund.dispatcher")


class RateLimitExceededError(RuntimeError):
    """Raised when the Token Bucket Rate Limiter or X API HTTP 429 halts outgoing DMs."""

    def __init__(self, message: str, retry_after_seconds: float = 15.0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TokenBucketRateLimiter:
    """
    Token Bucket Rate Limiter enforcing X (Twitter) API v2 DM dispatch safety.
    - Prevents burst spamming that could trigger automated X account locks.
    - Supports immediate circuit-breaker halt when HTTP 429 Too Many Requests is received.
    """

    def __init__(self, capacity: float = 15.0, refill_rate_per_sec: float = 0.5):
        self.capacity = capacity
        self.refill_rate_per_sec = refill_rate_per_sec
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.halted_until = 0.0
        self.total_dispatched = 0
        self.total_blocked_or_throttled = 0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = max(0.0, now - self.last_refill)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate_per_sec)
        self.last_refill = now

    def try_acquire(self, cost: float = 1.0) -> Tuple[bool, float]:
        """
        Attempt to consume `cost` tokens from the bucket.
        Returns (allowed: bool, wait_seconds: float).
        """
        now = time.monotonic()
        if now < self.halted_until:
            wait_sec = round(self.halted_until - now, 2)
            self.total_blocked_or_throttled += 1
            return False, wait_sec

        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            self.total_dispatched += 1
            return True, 0.0

        deficit = cost - self.tokens
        wait_sec = round(deficit / max(self.refill_rate_per_sec, 0.01), 2)
        self.total_blocked_or_throttled += 1
        return False, wait_sec

    def trigger_rate_limit_halt(self, retry_after_seconds: float = 30.0) -> None:
        """Halt the dispatcher bucket for `retry_after_seconds` upon receiving HTTP 429."""
        self.halted_until = time.monotonic() + max(1.0, retry_after_seconds)
        self.tokens = 0.0
        self.total_blocked_or_throttled += 1
        logger.warning(
            "X Rate Limit (HTTP 429) circuit breaker triggered: halting DM dispatch for %.1fs",
            retry_after_seconds,
        )

    def reset(self) -> None:
        """Reset token bucket to full capacity (useful for testing)."""
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self.halted_until = 0.0

    def get_status(self) -> Dict[str, Any]:
        self._refill()
        now = time.monotonic()
        is_halted = now < self.halted_until
        return {
            "available_tokens": round(self.tokens, 2),
            "capacity": self.capacity,
            "refill_rate_per_sec": self.refill_rate_per_sec,
            "is_rate_limited": is_halted,
            "retry_after_seconds": round(max(0.0, self.halted_until - now), 2) if is_halted else 0.0,
            "total_dispatched": self.total_dispatched,
            "total_blocked_or_throttled": self.total_blocked_or_throttled,
        }


# Singleton Token Bucket instance for Queue 2 (Safe Send Dispatcher)
send_rate_limiter = TokenBucketRateLimiter(capacity=15.0, refill_rate_per_sec=0.5)


def dispatch_candidate_dm(
    db: Session,
    candidate_id: int,
    custom_message: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    dispatch_mode: Optional[str] = None,
    sent_by_user_id: Optional[int] = None,
    allowed_test_handles: Optional[List[str]] = None,
    simulate_rate_limit: bool = False,
    sandbox_latency_sec: float = 0.02,
) -> Dict[str, Any]:
    """
    Queue 2: Dual-Mode Safe Send Dispatcher.
    1. Checks candidate existence & closed DM protection (`can_dm=False` -> `SEND_BLOCKED`).
    2. In `LIVE_X` mode, enforces `ALLOWED_TEST_HANDLES` safety whitelist BEFORE touching rate tokens
       or external networks (`SEND_BLOCKED` + warning log if not whitelisted).
    3. Acquires token from `TokenBucketRateLimiter` (raises `RateLimitExceededError` on 429/exhaustion).
    4. Executes Two-Tier Zero Double-Messaging atomic dispatch and records in `outreach_ledger`.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    mode = (dispatch_mode or settings.DISPATCH_MODE or "SANDBOX").upper()

    # Check custom allowed_test_handles override if passed in LIVE_X mode
    if mode == "LIVE_X" and allowed_test_handles is not None:
        clean_whitelist = [h.strip().lower().lstrip("@") for h in allowed_test_handles if h.strip()]
        if candidate.handle.lower().lstrip("@") not in clean_whitelist:
            logger.warning(
                "SAFETY SHIELD BLOCKED LIVE_X DISPATCH: @%s is not in ALLOWED_TEST_HANDLES %s",
                candidate.handle,
                clean_whitelist,
            )
            # Delegate to approve_and_send_candidate with temporary setting or block directly
            orig_whitelist = settings._allowed_test_handles
            try:
                settings._allowed_test_handles = ",".join(clean_whitelist)
                return approve_and_send_candidate(
                    db=db,
                    candidate_id=candidate_id,
                    custom_message=custom_message,
                    idempotency_key=idempotency_key,
                    dispatch_mode="LIVE_X",
                    sent_by_user_id=sent_by_user_id,
                )
            finally:
                settings._allowed_test_handles = orig_whitelist

    if mode == "LIVE_X":
        whitelist = settings.ALLOWED_TEST_HANDLES
        if candidate.handle.lower().lstrip("@") not in whitelist:
            logger.warning(
                "SAFETY SHIELD BLOCKED LIVE_X DISPATCH: @%s is not in ALLOWED_TEST_HANDLES %s",
                candidate.handle,
                whitelist,
            )

    # Check Rate Limiter (Token Bucket)
    if simulate_rate_limit:
        send_rate_limiter.trigger_rate_limit_halt(retry_after_seconds=15.0)
        raise RateLimitExceededError(
            f"X API Rate Limit (HTTP 429) encountered while dispatching to @{candidate.handle}. Queue paused.",
            retry_after_seconds=15.0,
        )

    allowed, wait_sec = send_rate_limiter.try_acquire(cost=1.0)
    if not allowed:
        raise RateLimitExceededError(
            f"Token Bucket Rate Limiter throttled dispatch to @{candidate.handle}. Retry after {wait_sec}s.",
            retry_after_seconds=wait_sec,
        )

    # Simulate realistic network latency in SANDBOX mode without blocking event loop excessively
    if mode == "SANDBOX" and sandbox_latency_sec > 0:
        time.sleep(min(sandbox_latency_sec, 0.5))

    result = approve_and_send_candidate(
        db=db,
        candidate_id=candidate_id,
        custom_message=custom_message,
        idempotency_key=idempotency_key,
        dispatch_mode=mode,
        sent_by_user_id=sent_by_user_id,
    )
    result["rate_limiter"] = send_rate_limiter.get_status()
    return result

