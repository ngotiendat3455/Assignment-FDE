import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.candidate import Candidate, CandidateStatus
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.models.queue import JobQueue, JobStatus


class StateTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""
    pass


class DoubleMessageConflictError(Exception):
    """Raised (HTTP 409) when attempting to message a candidate who was already contacted."""
    pass


class SendBlockedError(Exception):
    """Raised when attempting to dispatch a DM to a candidate with closed DMs or insufficient evidence."""
    pass


# Formal 9-State Lifecycle Transition Matrix
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    CandidateStatus.QUEUED_FOR_AI.value: {
        CandidateStatus.PENDING_REVIEW.value,
        CandidateStatus.INSUFFICIENT_EVIDENCE.value,
        CandidateStatus.AI_FAILED.value,
        CandidateStatus.REJECTED.value,
    },
    CandidateStatus.AI_FAILED.value: {
        CandidateStatus.QUEUED_FOR_AI.value,
        CandidateStatus.REJECTED.value,
    },
    CandidateStatus.INSUFFICIENT_EVIDENCE.value: {
        CandidateStatus.QUEUED_FOR_AI.value,
        CandidateStatus.PENDING_REVIEW.value,
        CandidateStatus.REJECTED.value,
    },
    CandidateStatus.PENDING_REVIEW.value: {
        CandidateStatus.REJECTED.value,
        CandidateStatus.APPROVED_QUEUED.value,
        CandidateStatus.SEND_BLOCKED.value,
        CandidateStatus.SENT.value,
        CandidateStatus.QUEUED_FOR_AI.value,
    },
    CandidateStatus.APPROVED_QUEUED.value: {
        CandidateStatus.SEND_BLOCKED.value,
        CandidateStatus.SENT.value,
        CandidateStatus.REJECTED.value,
    },
    CandidateStatus.SEND_BLOCKED.value: {
        CandidateStatus.REJECTED.value,
    },
    CandidateStatus.REJECTED.value: {
        CandidateStatus.QUEUED_FOR_AI.value,
        CandidateStatus.PENDING_REVIEW.value,
    },
    # Terminal / Protected Outreach States: Never regress to pre-send states
    CandidateStatus.SENT.value: {
        CandidateStatus.REPLIED.value,
    },
    CandidateStatus.REPLIED.value: set(),
}


def validate_transition(current_status: str, target_status: str) -> bool:
    """Check if transitioning from current_status to target_status is permitted."""
    if current_status == target_status:
        return True
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    return target_status in allowed


def transition_candidate_state(
    db: Session,
    candidate: Candidate,
    target_status: CandidateStatus,
    error_message: Optional[str] = None,
) -> Candidate:
    """Validate and execute an atomic state transition on a Candidate."""
    current = candidate.status
    target = target_status.value

    if current in (CandidateStatus.SENT.value, CandidateStatus.REPLIED.value) and target not in (
        CandidateStatus.SENT.value,
        CandidateStatus.REPLIED.value,
    ):
        raise DoubleMessageConflictError(
            f"Candidate @{candidate.handle} is already in terminal outreach state '{current}' and cannot regress to '{target}'."
        )

    if not validate_transition(current, target):
        raise StateTransitionError(
            f"Invalid state transition for @{candidate.handle}: '{current}' -> '{target}'."
        )

    candidate.status = target
    if error_message is not None:
        candidate.error_message = error_message
    candidate.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(candidate)
    return candidate


def approve_and_send_candidate(
    db: Session,
    candidate_id: int,
    custom_message: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    dispatch_mode: str = "SANDBOX",
    sent_by_user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Two-Tier Idempotency & Zero Double-Messaging Gate:
    - Tier 1 (Application Guard): Verifies candidate status, existing outreach_ledger records,
      and idempotency_key before attempting dispatch.
    - Closed DM Guard: Blocks candidates with can_dm=False and transitions to SEND_BLOCKED.
    - Tier 2 (Database Unique Constraint): Atomically inserts into outreach_ledger catching
      IntegrityError on race-condition double clicks -> raises DoubleMessageConflictError (409).
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    # --- TIER 1A: Application Status Check ---
    if candidate.status in (CandidateStatus.SENT.value, CandidateStatus.REPLIED.value):
        raise DoubleMessageConflictError(
            f"Zero Double-Messaging Guard: @{candidate.handle} has already been contacted (status: {candidate.status})."
        )

    # --- TIER 1B: Idempotency Key Collision Check ---
    if idempotency_key:
        existing_key = (
            db.query(OutreachLedger)
            .filter(OutreachLedger.idempotency_key == idempotency_key)
            .first()
        )
        if existing_key:
            raise DoubleMessageConflictError(
                f"Duplicate request blocked by idempotency_key '{idempotency_key}' for @{existing_key.handle}."
            )

    # --- TIER 1C: Outreach Ledger Handle / Candidate ID Check ---
    existing_ledger = (
        db.query(OutreachLedger)
        .filter(
            (OutreachLedger.candidate_id == candidate.id)
            | (OutreachLedger.handle == candidate.handle)
        )
        .first()
    )
    if existing_ledger and existing_ledger.status in (
        OutreachStatus.SENT.value,
        OutreachStatus.REPLIED.value,
    ):
        # Synchronize candidate status if needed
        candidate.status = existing_ledger.status
        db.commit()
        raise DoubleMessageConflictError(
            f"Zero Double-Messaging Guard: @{candidate.handle} already exists in Outreach Ledger ({existing_ledger.status})."
        )

    # --- SAFETY GUARD: Sparse / Insufficient Evidence Check ---
    if candidate.status == CandidateStatus.INSUFFICIENT_EVIDENCE.value and not custom_message:
        raise SendBlockedError(
            f"Cannot auto-send to @{candidate.handle}: profile has INSUFFICIENT_EVIDENCE."
        )

    # --- SAFETY GUARD: Closed DM Check (can_dm = False) ---
    if not candidate.can_dm:
        candidate.status = CandidateStatus.SEND_BLOCKED.value
        candidate.error_message = (
            f"Dispatch blocked: @{candidate.handle} has DMs closed on X (can_dm=false)."
        )
        candidate.updated_at = datetime.now(timezone.utc)
        if not existing_ledger:
            blocked_ledger = OutreachLedger(
                candidate_id=candidate.id,
                handle=candidate.handle,
                idempotency_key=idempotency_key or f"blocked-{candidate.handle}-{uuid.uuid4().hex[:8]}",
                sent_message=custom_message or candidate.edited_dm or candidate.draft_dm or "(blocked before send)",
                dispatch_mode=dispatch_mode,
                sent_by_user_id=sent_by_user_id,
                status=OutreachStatus.BLOCKED.value,
                needs_attention=False,
            )
            db.add(blocked_ledger)
        db.commit()
        raise SendBlockedError(
            f"Cannot send DM to @{candidate.handle}: Recipient has DMs closed (can_dm=false). Status set to SEND_BLOCKED."
        )

    # --- SAFETY GUARD: Live X Whitelist Check (ALLOWED_TEST_HANDLES) ---
    normalized_mode = (dispatch_mode or settings.DISPATCH_MODE or "SANDBOX").upper()
    if normalized_mode == "LIVE_X":
        allowed_handles = settings.ALLOWED_TEST_HANDLES
        if candidate.handle.lower().lstrip("@") not in allowed_handles:
            candidate.status = CandidateStatus.SEND_BLOCKED.value
            candidate.error_message = (
                f"Safety Whitelist Guard: @{candidate.handle} is not in ALLOWED_TEST_HANDLES "
                f"({', '.join(allowed_handles)}) for LIVE_X dispatch. Status set to SEND_BLOCKED."
            )
            candidate.updated_at = datetime.now(timezone.utc)
            if not existing_ledger:
                blocked_ledger = OutreachLedger(
                    candidate_id=candidate.id,
                    handle=candidate.handle,
                    idempotency_key=idempotency_key or f"blocked-live-{candidate.handle}-{uuid.uuid4().hex[:8]}",
                    sent_message=custom_message or candidate.edited_dm or candidate.draft_dm or "(blocked by LIVE_X safety whitelist)",
                    dispatch_mode="LIVE_X",
                    sent_by_user_id=sent_by_user_id,
                    status=OutreachStatus.BLOCKED.value,
                    needs_attention=False,
                )
                db.add(blocked_ledger)
            db.commit()
            raise SendBlockedError(candidate.error_message)

    # --- Prepare Final Message ---
    final_message = (
        custom_message
        or candidate.edited_dm
        or candidate.draft_dm
        or f"Hi {candidate.name}, impressed by your AI/Robotics work in SEA (@{candidate.handle})!"
    ).strip()

    if custom_message:
        candidate.edited_dm = custom_message

    final_idem_key = idempotency_key or f"dm-{candidate.id}-{uuid.uuid4().hex}"

    # --- TIER 2: Atomic Database Transaction with Unique Constraints ---
    try:
        # Transition through APPROVED_QUEUED -> SENT
        candidate.status = CandidateStatus.SENT.value
        candidate.error_message = None
        candidate.updated_at = datetime.now(timezone.utc)

        ledger_entry = OutreachLedger(
            candidate_id=candidate.id,
            handle=candidate.handle,
            idempotency_key=final_idem_key,
            sent_message=final_message,
            dispatch_mode=dispatch_mode,
            external_dm_id=f"sim_dm_{candidate.id}_{uuid.uuid4().hex[:6]}",
            sent_by_user_id=sent_by_user_id,
            sent_at=datetime.now(timezone.utc),
            status=OutreachStatus.SENT.value,
            needs_attention=False,
        )
        db.add(ledger_entry)
        db.commit()
        db.refresh(candidate)
        db.refresh(ledger_entry)
    except IntegrityError as exc:
        db.rollback()
        raise DoubleMessageConflictError(
            f"Database-level UNIQUE constraint prevented duplicate DM to @{candidate.handle}."
        ) from exc

    return {
        "candidate": candidate.to_dict(),
        "ledger": ledger_entry.to_dict(),
    }


def reject_candidate(
    db: Session,
    candidate_id: int,
    reason: Optional[str] = None,
) -> Candidate:
    """Transition a candidate to REJECTED (unless already SENT or REPLIED)."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    return transition_candidate_state(
        db,
        candidate,
        CandidateStatus.REJECTED,
        error_message=reason,
    )


def retry_candidate_ai_evaluation(
    db: Session,
    candidate_id: int,
) -> Candidate:
    """Transition an AI_FAILED or INSUFFICIENT_EVIDENCE candidate back to QUEUED_FOR_AI and enqueue job."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    updated = transition_candidate_state(
        db,
        candidate,
        CandidateStatus.QUEUED_FOR_AI,
        error_message=None,
    )

    job = JobQueue(
        job_type="AI_EVALUATE",
        candidate_id=updated.id,
        payload=json.dumps({"handle": updated.handle, "source": "MANUAL_RETRY"}),
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    return updated


def record_candidate_reply(
    db: Session,
    candidate_id: int,
    reply_text: str,
) -> Dict[str, Any]:
    """
    Transition a SENT candidate to REPLIED and activate the urgent 'needs_attention' flag
    in outreach_ledger so a Partner can take over the conversation.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    ledger = (
        db.query(OutreachLedger)
        .filter(
            (OutreachLedger.candidate_id == candidate.id)
            | (OutreachLedger.handle == candidate.handle)
        )
        .first()
    )
    if not ledger:
        raise StateTransitionError(
            f"Cannot record reply for @{candidate.handle}: no sent DM exists in Outreach Ledger."
        )

    candidate.status = CandidateStatus.REPLIED.value
    candidate.updated_at = datetime.now(timezone.utc)

    ledger.status = OutreachStatus.REPLIED.value
    ledger.reply_text = reply_text.strip()
    ledger.replied_at = datetime.now(timezone.utc)
    ledger.needs_attention = True

    db.commit()
    db.refresh(candidate)
    db.refresh(ledger)

    return {
        "candidate": candidate.to_dict(),
        "ledger": ledger.to_dict(),
    }


def mark_ledger_handled(
    db: Session,
    candidate_id: int,
) -> Dict[str, Any]:
    """Clear the 'needs_attention' flag after a Partner handles the founder's reply."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise LookupError(f"Candidate with ID {candidate_id} not found.")

    ledger = (
        db.query(OutreachLedger)
        .filter(
            (OutreachLedger.candidate_id == candidate.id)
            | (OutreachLedger.handle == candidate.handle)
        )
        .first()
    )
    if not ledger:
        raise LookupError(f"Outreach Ledger entry for candidate {candidate_id} not found.")

    ledger.needs_attention = False
    db.commit()
    db.refresh(ledger)

    return {
        "candidate": candidate.to_dict(),
        "ledger": ledger.to_dict(),
    }


def get_state_machine_summary(db: Session) -> Dict[str, Any]:
    """Return real-time counts across all 9 candidate states and outreach ledger safety gates."""
    state_counts: Dict[str, int] = {s.value: 0 for s in CandidateStatus}
    all_candidates = db.query(Candidate).all()
    for c in all_candidates:
        state_counts[c.status] = state_counts.get(c.status, 0) + 1

    all_ledgers = db.query(OutreachLedger).all()
    sent_count = sum(
        1
        for l in all_ledgers
        if l.status in (OutreachStatus.SENT.value, OutreachStatus.REPLIED.value)
    )
    replied_count = sum(
        1 for l in all_ledgers if l.status == OutreachStatus.REPLIED.value
    )
    blocked_count = sum(
        1 for l in all_ledgers if l.status == OutreachStatus.BLOCKED.value
    )
    needs_attention_count = sum(1 for l in all_ledgers if l.needs_attention)

    return {
        "total_candidates": len(all_candidates),
        "state_counts": state_counts,
        "ledger_summary": {
            "total_dispatched": sent_count,
            "total_replied": replied_count,
            "total_blocked": blocked_count,
            "needs_attention_count": needs_attention_count,
        },
    }

