from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from backend.app.core.database import Base


class CandidateChunk(Base):
    """
    Trạm 1 & Trạm 2 (Module 03 - RAG & Verify Gate 2):
    Stores semantic chunks of candidate profiles (bio, individual X posts, technical Markdown/PDF docs)
    with preserved provenance metadata (`chunk_id`, `post_id`, `created_at_source`) and vector embeddings.
    """

    __tablename__ = "candidate_chunks"
    __table_args__ = (
        Index(
            "idx_chunks_handle_source",
            "candidate_handle",
            "source_type",
            "post_id",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String(128), unique=True, index=True, nullable=False)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    candidate_handle = Column(String(64), index=True, nullable=False)
    source_type = Column(String(32), default="x_post", nullable=False)
    post_id = Column(String(64), index=True, nullable=False)
    created_at_source = Column(String(64), nullable=True)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Dynamic transient attributes populated during Trạm 3 & Trạm 4 retrieval/reranking
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: float = 0.0

    def to_dict(self):
        return {
            "id": self.id,
            "chunk_id": self.chunk_id,
            "candidate_id": self.candidate_id,
            "candidate_handle": self.candidate_handle,
            "source_type": self.source_type,
            "post_id": self.post_id,
            "created_at": self.created_at_source,
            "text": self.text,
            "token_count": self.token_count,
            "bm25_score": round(getattr(self, "bm25_score", 0.0), 4),
            "vector_score": round(getattr(self, "vector_score", 0.0), 4),
            "rrf_score": round(getattr(self, "rrf_score", 0.0), 4),
            "rerank_score": round(getattr(self, "rerank_score", 0.0), 4),
        }
