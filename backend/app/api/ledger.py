from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.services.ledger_service import (
    get_calibration_matrix,
    list_ledger_entries,
    mark_ledger_handled,
    record_ledger_reply,
    sync_x_dm_replies,
)

router = APIRouter(prefix="/ledger", tags=["ledger"])


class LedgerReplyRequest(BaseModel):
    reply_text: str = Field(..., min_length=1, description="Founder reply text to record")
    needs_attention: bool = Field(
        default=True,
        description="Whether this reply requires immediate Partner attention",
    )


@router.get("", response_model=Dict[str, Any])
def get_ledger(
    filter_tab: str = Query(
        default="all",
        description="Filter pill: all | needs_attention | replied | sent | blocked",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search by handle, name, outreach_id, or message content",
    ),
    db: Session = Depends(get_db),
):
    """
    List immutable outreach ledger entries with KPI metrics and filter counts.
    """
    return list_ledger_entries(db=db, filter_tab=filter_tab, search=search)


@router.get("/calibration", response_model=Dict[str, Any])
def get_calibration(db: Session = Depends(get_db)):
    """
    Retrieve the Partner Calibration Matrix comparing AI Scorer output against
    X-Scout AI's reference benchmark dataset.
    """
    return get_calibration_matrix(db=db)


@router.post("/sync-replies", response_model=Dict[str, Any])
def post_sync_x_replies(
    db: Session = Depends(get_db),
):
    """
    Poll X API v2 (`GET /2/dm_events`) using OAuth 1.0a User Context (`dm.read`)
    to sync incoming candidate DM replies into the Outreach Ledger.
    """
    return sync_x_dm_replies(db=db)


@router.post("/{ledger_id}/reply", response_model=Dict[str, Any])
def post_ledger_reply(
    ledger_id: int,
    payload: LedgerReplyRequest,
    db: Session = Depends(get_db),
):
    """
    Simulate or record a founder reply on a ledger entry (sets status=REPLIED and needs_attention=True).
    """
    return record_ledger_reply(
        db=db,
        ledger_id=ledger_id,
        reply_text=payload.reply_text,
        needs_attention=payload.needs_attention,
    )


@router.post("/{ledger_id}/handled", response_model=Dict[str, Any])
def post_ledger_handled(
    ledger_id: int,
    db: Session = Depends(get_db),
):
    """
    Mark a replied ledger entry as handled (clears needs_attention flag).
    """
    return mark_ledger_handled(db=db, ledger_id=ledger_id)

