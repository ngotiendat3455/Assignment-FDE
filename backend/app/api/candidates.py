from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.candidate import Candidate
from backend.app.models.ledger import OutreachLedger, OutreachStatus
from backend.app.schemas.ledger import SendOutreachRequest, RecordReplyRequest
from backend.app.services.state_machine import (
    approve_and_send_candidate,
    reject_candidate,
    retry_candidate_ai_evaluation,
    record_candidate_reply,
    mark_ledger_handled,
    get_state_machine_summary,
    DoubleMessageConflictError,
    SendBlockedError,
    StateTransitionError,
)

router = APIRouter(prefix="/candidates", tags=["Candidates & State Machine"])


class RejectCandidateRequest(BaseModel):
    reason: Optional[str] = None


def _enrich_candidate_with_ledger(
    cand: Candidate,
    ledger_map: Dict[int, OutreachLedger],
) -> Dict[str, Any]:
    data = cand.to_dict()
    ledger = ledger_map.get(cand.id)
    if ledger:
        data["already_contacted"] = ledger.status in (
            OutreachStatus.SENT.value,
            OutreachStatus.REPLIED.value,
        )
        data["ledger_status"] = ledger.status
        data["needs_attention"] = ledger.needs_attention
        data["sent_message"] = ledger.sent_message
        data["reply_text"] = ledger.reply_text
        data["sent_at"] = ledger.sent_at.isoformat() if ledger.sent_at else None
        data["replied_at"] = ledger.replied_at.isoformat() if ledger.replied_at else None
    else:
        data["already_contacted"] = False
        data["ledger_status"] = None
        data["needs_attention"] = False
        data["sent_message"] = None
        data["reply_text"] = None
        data["sent_at"] = None
        data["replied_at"] = None
    return data


@router.get("/state-summary")
def read_state_machine_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return counts across all 9 lifecycle states and Outreach Ledger protection gates."""
    return get_state_machine_summary(db)


@router.get("")
def list_candidates(
    status: Optional[str] = Query(None, description="Filter by lifecycle status"),
    search: Optional[str] = Query(None, description="Search by handle, name, bio, or segment"),
    min_score: Optional[int] = Query(None, ge=1, le=4, description="Minimum AI fit score"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List candidates with their current 9-state lifecycle status and Outreach Ledger lock flags."""
    query = db.query(Candidate)

    if status and status.upper() != "ALL":
        query = query.filter(Candidate.status == status.upper())

    if min_score is not None:
        query = query.filter(Candidate.fit_score >= min_score)

    if search and search.strip():
        q = f"%{search.strip()}%"
        query = query.filter(
            (Candidate.handle.ilike(q))
            | (Candidate.name.ilike(q))
            | (Candidate.bio.ilike(q))
            | (Candidate.segment.ilike(q))
        )

    candidates = query.order_by(Candidate.id.asc()).all()
    ledgers = db.query(OutreachLedger).all()
    ledger_map = {l.candidate_id: l for l in ledgers}

    items: List[Dict[str, Any]] = [
        _enrich_candidate_with_ledger(c, ledger_map) for c in candidates
    ]
    return {
        "total": len(items),
        "items": items,
    }


@router.get("/{candidate_id}")
def get_candidate_detail(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve a single candidate and its immutable Outreach Ledger trail."""
    cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")

    ledger = (
        db.query(OutreachLedger)
        .filter(OutreachLedger.candidate_id == cand.id)
        .first()
    )
    ledger_map = {cand.id: ledger} if ledger else {}
    return _enrich_candidate_with_ledger(cand, ledger_map)


@router.post("/{candidate_id}/send")
def send_candidate_dm(
    candidate_id: int,
    payload: SendOutreachRequest = SendOutreachRequest(),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Approve & Send DM with Two-Tier Zero Double-Messaging Protection.
    Returns 409 Conflict if candidate was already messaged or on duplicate idempotency_key.
    Returns 422 Unprocessable Entity if candidate has DMs closed (can_dm=false).
    """
    try:
        return approve_and_send_candidate(
            db=db,
            candidate_id=candidate_id,
            custom_message=payload.custom_message,
            idempotency_key=payload.idempotency_key,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DoubleMessageConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SendBlockedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{candidate_id}/reject")
def reject_candidate_endpoint(
    candidate_id: int,
    payload: RejectCandidateRequest = RejectCandidateRequest(),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Transition candidate to REJECTED."""
    try:
        cand = reject_candidate(db, candidate_id, reason=payload.reason)
        return cand.to_dict()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DoubleMessageConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StateTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/retry")
def retry_candidate_ai_endpoint(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retry AI evaluation for an AI_FAILED or INSUFFICIENT_EVIDENCE candidate."""
    try:
        cand = retry_candidate_ai_evaluation(db, candidate_id)
        return cand.to_dict()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DoubleMessageConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except StateTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/reply")
def record_reply_endpoint(
    candidate_id: int,
    payload: RecordReplyRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Record a founder reply (SENT -> REPLIED) and turn on NEEDS ATTENTION."""
    try:
        return record_candidate_reply(db, candidate_id, payload.reply_text)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StateTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{candidate_id}/handled")
def mark_handled_endpoint(
    candidate_id: int,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Resolve and clear NEEDS ATTENTION flag after Partner follow-up."""
    try:
        return mark_ledger_handled(db, candidate_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

