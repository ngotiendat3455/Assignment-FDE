from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from backend.app.core.database import Base


class CandidateStatus(str, Enum):
    QUEUED_FOR_AI = "QUEUED_FOR_AI"
    PENDING_REVIEW = "PENDING_REVIEW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AI_FAILED = "AI_FAILED"
    REJECTED = "REJECTED"
    APPROVED_QUEUED = "APPROVED_QUEUED"
    SENT = "SENT"
    SEND_BLOCKED = "SEND_BLOCKED"
    REPLIED = "REPLIED"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    x_user_id = Column(String(64), unique=True, index=True, nullable=True)
    handle = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    location = Column(String(128), nullable=True)
    bio = Column(Text, nullable=False)
    recent_tweets = Column(Text, nullable=False)
    can_dm = Column(Boolean, default=True, nullable=False)
    segment = Column(String(128), nullable=True)

    # AI Evaluation Fields
    is_match = Column(Boolean, nullable=True)
    fit_score = Column(Integer, nullable=True)
    fit_reason = Column(Text, nullable=True)
    evidence_snippet = Column(Text, nullable=True)
    draft_dm = Column(Text, nullable=True)
    edited_dm = Column(Text, nullable=True)

    # Pipeline State Machine
    status = Column(String(32), default=CandidateStatus.QUEUED_FOR_AI.value, index=True, nullable=False)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def insufficient_evidence(self) -> bool:
        return self.status == CandidateStatus.INSUFFICIENT_EVIDENCE.value

    @insufficient_evidence.setter
    def insufficient_evidence(self, value: bool) -> None:
        if value:
            self.status = CandidateStatus.INSUFFICIENT_EVIDENCE.value

    def to_dict(self):
        return {
            "id": self.id,
            "x_user_id": self.x_user_id,
            "handle": self.handle,
            "name": self.name,
            "location": self.location,
            "bio": self.bio,
            "recent_tweets": self.recent_tweets,
            "can_dm": self.can_dm,
            "segment": self.segment,
            "is_match": self.is_match,
            "fit_score": self.fit_score,
            "fit_reason": self.fit_reason,
            "evidence_snippet": self.evidence_snippet,
            "draft_dm": self.draft_dm,
            "edited_dm": self.edited_dm,
            "insufficient_evidence": self.insufficient_evidence,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

