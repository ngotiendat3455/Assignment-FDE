from enum import Enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class OutreachStatus(str, Enum):
    SENT = "SENT"
    REPLIED = "REPLIED"
    BLOCKED = "BLOCKED"


class OutreachLedger(Base):
    __tablename__ = "outreach_ledger"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), unique=True, nullable=False, index=True)
    handle = Column(String(64), unique=True, index=True, nullable=False)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)

    sent_message = Column(Text, nullable=False)
    dispatch_mode = Column(String(32), nullable=False)  # 'SANDBOX' | 'LIVE_X'
    external_dm_id = Column(String(128), nullable=True)

    sent_by_user_id = Column(Integer, nullable=True)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    replied_at = Column(DateTime, nullable=True)
    reply_text = Column(Text, nullable=True)
    needs_attention = Column(Boolean, default=False, index=True, nullable=False)
    status = Column(String(32), default=OutreachStatus.SENT.value, index=True, nullable=False)

    candidate = relationship("Candidate", backref="ledger_entry")

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "handle": self.handle,
            "idempotency_key": self.idempotency_key,
            "sent_message": self.sent_message,
            "dispatch_mode": self.dispatch_mode,
            "external_dm_id": self.external_dm_id,
            "sent_by_user_id": self.sent_by_user_id,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "replied_at": self.replied_at.isoformat() if self.replied_at else None,
            "reply_text": self.reply_text,
            "needs_attention": self.needs_attention,
            "status": self.status,
            "candidate_name": self.candidate.name if self.candidate else None,
            "candidate_location": self.candidate.location if self.candidate else None,
        }

