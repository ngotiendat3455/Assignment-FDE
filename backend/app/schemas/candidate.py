from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CandidateBase(BaseModel):
    handle: str = Field(..., description="X handle (e.g. minh_quant)")
    name: str = Field(..., description="Full name or display name")
    bio: str = Field(..., description="Profile bio text")
    recent_tweets: str = Field(..., description="Raw recent tweets string or JSON")
    location: Optional[str] = "Southeast Asia"
    can_dm: bool = True
    segment: Optional[str] = "SEA AI & Robotics Ecosystem"
    x_user_id: Optional[str] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    edited_dm: Optional[str] = None
    status: Optional[str] = None
    fit_score: Optional[int] = None
    fit_reason: Optional[str] = None


class CandidateResponse(CandidateBase):
    id: int
    is_match: Optional[bool] = None
    fit_score: Optional[int] = None
    fit_reason: Optional[str] = None
    evidence_snippet: Optional[str] = None
    draft_dm: Optional[str] = None
    edited_dm: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AIEvaluationResult(BaseModel):
    is_match: bool = Field(description="True if builder/researcher in SEA AI or Robotics with real technical signal")
    fit_score: int = Field(ge=1, le=4, description="1 to 4 rubric score")
    fit_reason: str = Field(description="1-2 sentences explaining fit or lack thereof")
    evidence_snippet: str = Field(default="", description="Verbatim quote from candidate bio or recent tweets")
    draft_dm: str = Field(default="", description="Warm peer-to-peer DM draft under 500 chars citing the evidence")
    insufficient_evidence: bool = Field(default=False, description="True if profile is too sparse to evaluate or draft genuine DM")


class SeedIngestRequest(BaseModel):
    segment: Optional[str] = "SEA AI & Robotics Ecosystem"


class CsvPreflightRequest(BaseModel):
    csv_content: str = Field(..., description="Raw CSV file content")


class CsvPreviewRow(BaseModel):
    line_number: int
    handle: str
    name: str
    bio: str
    recent_tweets: str
    location: Optional[str] = None
    can_dm: bool = True
    is_valid: bool = True
    validation_note: str = "Valid"


class CsvPreflightResponse(BaseModel):
    valid: bool
    total_rows: int
    missing_columns: List[str]
    detected_columns: List[str]
    preview_rows: List[CsvPreviewRow]
    error_message: Optional[str] = None


class CsvIngestRequest(BaseModel):
    csv_content: str = Field(..., description="Raw CSV file content")
    default_segment: Optional[str] = "SEA AI & Robotics Ecosystem"
    skip_ledger_collisions: bool = True


class CollisionDetail(BaseModel):
    handle: str
    status: str


class IngestionAuditReport(BaseModel):
    total_rows: int
    imported: int
    queued_for_ai_count: int
    in_batch_duplicates_skipped: int
    already_in_db_skipped: int
    already_contacted_in_ledger: int
    duplicate_handles: List[str]
    collision_details: List[CollisionDetail]
    details: List[Dict[str, Any]]


class LiveXLookupResponse(BaseModel):
    handle: str
    name: str
    location: str
    bio: str
    recent_tweets: List[str]
    raw_tweets_text: str
    can_dm: bool
    segment: str
    x_user_id: Optional[str] = None
    source_mode: str
    api_connected: bool
    already_contacted: bool = False
    existing_ledger_status: Optional[str] = None
