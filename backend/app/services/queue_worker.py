import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.core.langfuse_tracing import flush_langfuse
from backend.app.core.runtime_gateway import RuntimeGateway
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.queue import JobQueue, JobStatus
from backend.app.services.ai_evaluator import (
    evaluate_candidate_profile,
    regenerate_candidate_dm_draft,
    AIEvaluationServiceError,
    DMGenerationBlockedError,
)
from backend.app.services.dispatcher import (
    dispatch_candidate_dm,
    send_rate_limiter,
    RateLimitExceededError,
)
from backend.app.services.state_machine import (
    DoubleMessageConflictError,
    SendBlockedError,
)
from backend.app.services.x_client import (
    XApiDispatchError,
    XApiRateLimitError,
)


def evaluate_candidate_by_id(
    db: Session,
    candidate_id: int,
    simulate_failure: bool = False,
) -> Dict[str, Any]:
    """
    Execute Queue 1 (AI Evaluation) for a single candidate and persist results in SQLite.
    - Never overwrites terminal outreach states (SENT / REPLIED).
    - Transitions QUEUED_FOR_AI -> PENDING_REVIEW or INSUFFICIENT_EVIDENCE.
    - On LLM error, transitions to AI_FAILED (never assigning a fake low score).
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    if candidate.status in (CandidateStatus.SENT.value, CandidateStatus.REPLIED.value):
        return {
            "candidate_id": candidate.id,
            "handle": candidate.handle,
            "status": candidate.status,
            "skipped": True,
            "reason": "Terminal outreach state protected",
        }

    pending_jobs = (
        db.query(JobQueue)
        .filter(
            JobQueue.candidate_id == candidate.id,
            JobQueue.job_type == "AI_EVALUATE",
            JobQueue.status.in_([JobStatus.PENDING.value, JobStatus.PROCESSING.value]),
        )
        .all()
    )
    for j in pending_jobs:
        j.status = JobStatus.PROCESSING.value
        j.attempts = (j.attempts or 0) + 1
    db.commit()

    ai_plan = RuntimeGateway.resolve_ai_plan()

    try:
        eval_result = evaluate_candidate_profile(
            candidate,
            simulate_failure=simulate_failure,
            db=db,
        )

        candidate.is_match = eval_result.is_match
        candidate.fit_score = eval_result.fit_score
        candidate.fit_reason = eval_result.fit_reason
        candidate.evidence_snippet = eval_result.evidence_snippet
        candidate.draft_dm = eval_result.draft_dm
        candidate.insufficient_evidence = eval_result.insufficient_evidence
        candidate.error_message = None
        candidate.updated_at = datetime.now(timezone.utc)

        if eval_result.insufficient_evidence:
            candidate.status = CandidateStatus.INSUFFICIENT_EVIDENCE.value
        else:
            candidate.status = CandidateStatus.PENDING_REVIEW.value

        now = datetime.now(timezone.utc)
        for j in pending_jobs:
            j.status = JobStatus.COMPLETED.value
            j.last_error = None
            j.completed_at = now

        db.commit()
        db.refresh(candidate)
        flush_langfuse()
        return {
            "candidate_id": candidate.id,
            "handle": candidate.handle,
            "status": candidate.status,
            "evaluation": eval_result.model_dump(),
            "execution_meta": ai_plan.to_meta(),
            "candidate": candidate.to_dict(),
        }

    except AIEvaluationServiceError as exc:
        candidate.status = CandidateStatus.AI_FAILED.value
        candidate.error_message = str(exc)
        candidate.updated_at = datetime.now(timezone.utc)
        for j in pending_jobs:
            j.status = JobStatus.FAILED.value
            j.last_error = str(exc)
        db.commit()
        db.refresh(candidate)
        flush_langfuse()
        return {
            "candidate_id": candidate.id,
            "handle": candidate.handle,
            "status": candidate.status,
            "error": str(exc),
            "execution_meta": ai_plan.to_meta(),
            "candidate": candidate.to_dict(),
        }


def regenerate_candidate_dm_by_id(
    db: Session,
    candidate_id: int,
    current_dm: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Regenerate ONLY the personalized DM draft for a candidate inside the Composer modal.
    Preserves existing fit_score, fit_reason ('AI Fit Assessment'), and is_match,
    and clears stale edited_dm so the UI displays the fresh draft_dm immediately.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    if candidate.status in (CandidateStatus.SENT.value, CandidateStatus.REPLIED.value):
        raise DoubleMessageConflictError(
            f"Candidate @{candidate.handle} is already in terminal state ({candidate.status}); DM cannot be regenerated."
        )

    ai_plan = RuntimeGateway.resolve_ai_plan()
    previous = current_dm if current_dm is not None else (candidate.edited_dm or candidate.draft_dm or "")
    new_draft, evidence = regenerate_candidate_dm_draft(candidate, previous_dm=previous)

    candidate.draft_dm = new_draft
    candidate.edited_dm = None
    if not candidate.evidence_snippet and evidence:
        candidate.evidence_snippet = evidence
    candidate.error_message = None
    candidate.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(candidate)
    return {
        "candidate_id": candidate.id,
        "handle": candidate.handle,
        "draft_dm": new_draft,
        "execution_meta": ai_plan.to_meta(),
        "candidate": candidate.to_dict(),
    }


def enqueue_send_dm_job(
    db: Session,
    candidate_id: int,
    custom_message: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    dispatch_mode: Optional[str] = None,
    sent_by_user_id: Optional[int] = None,
    allowed_test_handles: Optional[List[str]] = None,
    simulate_rate_limit: bool = False,
) -> JobQueue:
    """
    Create a persistent Queue 2 (SEND_DM) job in SQLite and move candidate to APPROVED_QUEUED.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    if custom_message:
        candidate.edited_dm = custom_message

    if candidate.status == CandidateStatus.PENDING_REVIEW.value:
        candidate.status = CandidateStatus.APPROVED_QUEUED.value
        candidate.updated_at = datetime.now(timezone.utc)

    payload_data = {
        "candidate_id": candidate.id,
        "handle": candidate.handle,
        "custom_message": custom_message,
        "idempotency_key": idempotency_key or f"q2-{candidate.id}-{uuid.uuid4().hex[:10]}",
        "dispatch_mode": (dispatch_mode or settings.DISPATCH_MODE or "SANDBOX").upper(),
        "sent_by_user_id": sent_by_user_id,
        "allowed_test_handles": allowed_test_handles,
        "simulate_rate_limit": simulate_rate_limit,
    }

    job = JobQueue(
        job_type="SEND_DM",
        candidate_id=candidate.id,
        payload=json.dumps(payload_data),
        status=JobStatus.PENDING.value,
        attempts=0,
        max_attempts=3,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_send_dm_job(db: Session, job: JobQueue) -> Dict[str, Any]:
    """Execute a single Queue 2 (SEND_DM) job from the persistent job_queue table."""
    job.status = JobStatus.PROCESSING.value
    job.attempts = (job.attempts or 0) + 1
    db.commit()

    payload: Dict[str, Any] = {}
    if job.payload:
        try:
            payload = json.loads(job.payload)
        except Exception:
            payload = {}

    candidate_id = job.candidate_id or payload.get("candidate_id")
    if not candidate_id:
        job.status = JobStatus.FAILED.value
        job.last_error = "Missing candidate_id in SEND_DM job."
        db.commit()
        return {"job_id": job.id, "status": "FAILED", "error": job.last_error}

    try:
        dispatch_res = dispatch_candidate_dm(
            db=db,
            candidate_id=int(candidate_id),
            custom_message=payload.get("custom_message"),
            idempotency_key=payload.get("idempotency_key"),
            dispatch_mode=payload.get("dispatch_mode"),
            sent_by_user_id=payload.get("sent_by_user_id"),
            allowed_test_handles=payload.get("allowed_test_handles"),
            simulate_rate_limit=bool(payload.get("simulate_rate_limit", False)),
        )
        job.status = JobStatus.COMPLETED.value
        job.last_error = None
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "job_id": job.id,
            "job_type": "SEND_DM",
            "status": JobStatus.COMPLETED.value,
            "candidate_id": candidate_id,
            "result": dispatch_res,
        }
    except (RateLimitExceededError, XApiRateLimitError) as exc:
        job.status = JobStatus.RATE_LIMITED.value
        job.last_error = str(exc)
        db.commit()
        return {
            "job_id": job.id,
            "job_type": "SEND_DM",
            "status": JobStatus.RATE_LIMITED.value,
            "candidate_id": candidate_id,
            "error": str(exc),
            "retry_after_seconds": getattr(exc, "retry_after_seconds", 60.0),
        }
    except (SendBlockedError, DoubleMessageConflictError, LookupError, XApiDispatchError) as exc:
        job.status = JobStatus.FAILED.value
        job.last_error = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "job_id": job.id,
            "job_type": "SEND_DM",
            "status": JobStatus.FAILED.value,
            "candidate_id": candidate_id,
            "error": str(exc),
        }


def process_pending_jobs(
    db: Session,
    job_type: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Drain pending jobs from SQLite `job_queue` (Queue 1: AI_EVALUATE and Queue 2: SEND_DM).
    Also evaluates any candidates stuck in `QUEUED_FOR_AI` without an explicit job row.
    """
    query = db.query(JobQueue).filter(
        JobQueue.status.in_([JobStatus.PENDING.value, JobStatus.RATE_LIMITED.value])
    )
    if job_type:
        query = query.filter(JobQueue.job_type == job_type.upper())

    jobs = query.order_by(JobQueue.scheduled_at.asc(), JobQueue.id.asc()).limit(limit).all()

    ai_evaluated_count = 0
    dm_sent_count = 0
    failed_or_blocked_count = 0
    rate_limited_count = 0
    details: List[Dict[str, Any]] = []
    evaluated_candidate_ids = set()

    for job in jobs:
        if job.job_type == "AI_EVALUATE" and job.candidate_id:
            evaluated_candidate_ids.add(job.candidate_id)
            res = evaluate_candidate_by_id(db, job.candidate_id)
            if res.get("status") == CandidateStatus.AI_FAILED.value:
                failed_or_blocked_count += 1
            else:
                ai_evaluated_count += 1
            details.append(res)
        elif job.job_type == "SEND_DM":
            res = process_send_dm_job(db, job)
            if res.get("status") == JobStatus.COMPLETED.value:
                dm_sent_count += 1
            elif res.get("status") == JobStatus.RATE_LIMITED.value:
                rate_limited_count += 1
            else:
                failed_or_blocked_count += 1
            details.append(res)

    # Also evaluate any candidate in QUEUED_FOR_AI that didn't have a PENDING job row
    if job_type is None or job_type.upper() == "AI_EVALUATE":
        remaining_queued = (
            db.query(Candidate)
            .filter(Candidate.status == CandidateStatus.QUEUED_FOR_AI.value)
            .limit(limit)
            .all()
        )
        for cand in remaining_queued:
            if cand.id not in evaluated_candidate_ids:
                res = evaluate_candidate_by_id(db, cand.id)
                if res.get("status") == CandidateStatus.AI_FAILED.value:
                    failed_or_blocked_count += 1
                else:
                    ai_evaluated_count += 1
                details.append(res)

    return {
        "processed": len(details),
        "ai_evaluated": ai_evaluated_count,
        "dm_sent": dm_sent_count,
        "failed_or_blocked": failed_or_blocked_count,
        "rate_limited": rate_limited_count,
        "execution_meta": RuntimeGateway.resolve_ai_plan().to_meta(),
        "rate_limiter": send_rate_limiter.get_status(),
        "details": details,
    }


def run_background_queue_drain(
    job_type: Optional[str] = None,
    limit: int = 50,
) -> None:
    """Background task helper using its own SQLite session to drain pending jobs asynchronously."""
    db = SessionLocal()
    try:
        process_pending_jobs(db, job_type=job_type, limit=limit)
    finally:
        db.close()


def get_dual_queue_status(db: Session) -> Dict[str, Any]:
    """Return real-time observability metrics for Queue 1 (AI_EVALUATE) and Queue 2 (SEND_DM)."""
    all_jobs = db.query(JobQueue).all()

    q1_counts = {s.value: 0 for s in JobStatus}
    q2_counts = {s.value: 0 for s in JobStatus}

    for j in all_jobs:
        if j.job_type == "AI_EVALUATE":
            q1_counts[j.status] = q1_counts.get(j.status, 0) + 1
        elif j.job_type == "SEND_DM":
            q2_counts[j.status] = q2_counts.get(j.status, 0) + 1

    queued_for_ai_candidates = (
        db.query(Candidate)
        .filter(Candidate.status == CandidateStatus.QUEUED_FOR_AI.value)
        .count()
    )

    return {
        "runtime_profile": RuntimeGateway.get_active_profile(),
        "runtime_gateway": RuntimeGateway.get_runtime_status_summary(),
        "dispatch_mode": settings.DISPATCH_MODE,
        "allowed_test_handles": settings.ALLOWED_TEST_HANDLES,
        "ai_evaluation_queue": {
            "job_type": "AI_EVALUATE",
            "counts": q1_counts,
            "candidates_waiting_in_queued_for_ai": queued_for_ai_candidates,
        },
        "safe_send_queue": {
            "job_type": "SEND_DM",
            "counts": q2_counts,
            "rate_limiter": send_rate_limiter.get_status(),
        },
    }

