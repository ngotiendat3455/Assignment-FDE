from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SendOutreachRequest(BaseModel):
    custom_message: Optional[str] = Field(None, description="Optional edited message overriding the AI draft")
    idempotency_key: Optional[str] = Field(None, description="Client idempotency key to prevent double clicks")


class RecordReplyRequest(BaseModel):
    reply_text: str = Field(..., min_length=1, description="Content of recipient's reply")


class OutreachLedgerResponse(BaseModel):
    id: int
    candidate_id: int
    handle: str
    idempotency_key: str
    sent_message: str
    dispatch_mode: str
    external_dm_id: Optional[str] = None
    sent_by_user_id: Optional[int] = None
    sent_at: Optional[str] = None
    replied_at: Optional[str] = None
    reply_text: Optional[str] = None
    needs_attention: bool
    status: str
    candidate_name: Optional[str] = None
    candidate_location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

