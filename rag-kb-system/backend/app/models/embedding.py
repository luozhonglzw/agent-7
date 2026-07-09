"""EmbeddingRecord SQLAlchemy model.

Tracks embedding vectors stored in Qdrant for each document chunk.
The actual vectors live in Qdrant; this table provides a relational
index for management and cleanup.

Table:
    embedding_records: Metadata about vectors stored in Qdrant.
"""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class EmbeddingRecord(BaseModel):
    """Embedding vector metadata.

    Records which chunks have been embedded and where their
    vectors are stored in Qdrant.

    Attributes:
        chunk_id: Foreign key to document_chunks table.
        document_id: Foreign key to documents table (denormalized for queries).
        user_id: Foreign key to users table (for permission filtering).
        qdrant_point_id: Qdrant point UUID.
        embedding_model: Model used for embedding (e.g., BAAI/bge-m3).
        embedding_dim: Dimension of the embedding vector.
        status: Embedding status (pending/completed/failed).
    """

    __tablename__ = "embedding_records"
    __table_args__ = (
        Index("ix_embedding_records_doc", "document_id"),
        Index("ix_embedding_records_user", "user_id"),
        Index("ix_embedding_records_chunk", "chunk_id"),
        {"comment": "Embedding vector metadata"},
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Chunk ID",
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Document ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owner user ID",
    )
    qdrant_point_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Qdrant point UUID",
    )
    embedding_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Embedding model name",
    )
    embedding_dim: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Embedding dimension",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="completed",
        nullable=False,
        comment="Status: pending, completed, failed",
    )

    def __repr__(self) -> str:
        return (
            f"<EmbeddingRecord(id={self.id}, chunk_id={self.chunk_id}, "
            f"status='{self.status}')>"
        )
