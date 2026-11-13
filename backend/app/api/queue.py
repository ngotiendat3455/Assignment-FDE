from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.user import User
from backend.app.services.dispatcher import (
    dispatch_candidate_dm,
    RateLimitExceededError,
)
from backend.app.services.queue_worker import (
    evaluate_candidate_by_id,
    enqueue_send_dm_job,
    process_send_dm_job,
    process_pending_jobs,
    get_dual_queue_status,
)
from backend.app.services.state_machine import (
    DoubleMessageConflictError,
    SendBlockedError,
)
from backend.app.services.x_client import (
    XApiDispatchError,
    XApiRateLimitError,
)

router = APIRouter(
    prefix="/queue",
    tags=["Dual Queue & AI Send Engine"],
    dependencies=[Depends(get_current_user)],
)


class ProcessQueueRequest(BaseModel):
    job_type: Optional[str] = Field(
        default=None,
        description="Optional filter: 'AI_EVALUATE' or 'SEND_DM'",
    )
    limit: int = Field(default=50, ge=1, le=200)


class EvaluateCandidateRequest(BaseModel):
    simulate_failure: bool = Field(
        default=False,
        description="Simulate an external LLM API outage to verify AI_FAILED state isolation",
    )


class DispatchCandidateRequest(BaseModel):
    custom_message: Optional[str] = None
    idempotency_key: Optional[str] = None
    dispatch_mode: Optional[str] = Field(
        default=None,
        description="Override dispatch mode ('SANDBOX' or 'LIVE_X')",
    )
    allowed_test_handles: Optional[List[str]] = Field(
        default=None,
        description="Optional override for ALLOWED_TEST_HANDLES whitelist in LIVE_X mode",
    )
    simulate_rate_limit: bool = Field(
        default=False,
        description="Simulate X API HTTP 429 rate limit to verify Token Bucket circuit breaker",
    )
    use_queue_job: bool = Field(
        default=False,
        description="If True, enqueue a SEND_DM job in job_queue and process via Queue 2 worker",
    )


@router.get("/status")
def read_dual_queue_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return real-time observability metrics for Queue 1 (AI_EVALUATE) and Queue 2 (SEND_DM)."""
    return get_dual_queue_status(db)


@router.post("/process")
def trigger_queue_processing(
    payload: ProcessQueueRequest = ProcessQueueRequest(),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Process pending jobs in Queue 1 (AI_EVALUATE) and/or Queue 2 (SEND_DM)."""
    return process_pending_jobs(
        db=db,
        job_type=payload.job_type,
        limit=payload.limit,
    )


@router.post("/evaluate/{candidate_id}")
def trigger_candidate_ai_evaluation(
    candidate_id: int,
    payload: EvaluateCandidateRequest = EvaluateCandidateRequest(),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Run Tri-Guard AI Evaluation (Queue 1) for a specific candidate."""
    try:
        return evaluate_candidate_by_id(
            db=db,
            candidate_id=candidate_id,
            simulate_failure=payload.simulate_failure,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/dispatch/{candidate_id}")
def trigger_candidate_dm_dispatch(
    candidate_id: int,
    payload: DispatchCandidateRequest = DispatchCandidateRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Run Dual-Mode Safe Send Dispatcher (Queue 2) for a candidate.
    Enforces Closed DM block (`can_dm=false`), Live X Whitelist (`ALLOWED_TEST_HANDLES`),
    Token Bucket Rate Limiter, and Two-Tier Zero Double-Messaging Gate.
    """
    if payload.use_queue_job:
        try:
            job = enqueue_send_dm_job(
                db=db,
                candidate_id=candidate_id,
                custom_message=payload.custom_message,
                idempotency_key=payload.idempotency_key,
                dispatch_mode=payload.dispatch_mode,
                sent_by_user_id=current_user.id,
                allowed_test_handles=payload.allowed_test_handles,
                simulate_rate_limit=payload.simulate_rate_limit,
            )
            return process_send_dm_job(db=db, job=job)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        return dispatch_candidate_dm(
            db=db,
            candidate_id=candidate_id,
            custom_message=payload.custom_message,
            idempotency_key=payload.idempotency_key,
            dispatch_mode=payload.dispatch_mode,
            sent_by_user_id=current_user.id,
            allowed_test_handles=payload.allowed_test_handles,
            simulate_rate_limit=payload.simulate_rate_limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DoubleMessageConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SendBlockedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (RateLimitExceededError, XApiRateLimitError) as exc:
        retry_sec = getattr(exc, "retry_after_seconds", 60.0)
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(int(retry_sec))},
        ) from exc
    except XApiDispatchError as exc:
        status_code = 503 if str(exc).startswith("[LIVE_PRODUCTION]") else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

