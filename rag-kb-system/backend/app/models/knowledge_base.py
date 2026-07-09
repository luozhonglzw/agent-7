"""Knowledge Base and document association models.

Defines the knowledge base table for grouping documents and
the many-to-many association between knowledge bases and documents.

Tables:
    knowledge_bases: Knowledge base metadata and ownership.
    kb_documents: Many-to-many association between KBs and documents.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModel


class KBVisibility(str, Enum):
    """Knowledge base visibility levels.

    Controls who can see and access the knowledge base.
    """

    PUBLIC = "public"    # Everyone can read
    PRIVATE = "private"  # Only owner can read
    DEPT = "dept"        # Same department can read


class KnowledgeBase(BaseModel):
    """Knowledge base model.

    A knowledge base groups related documents together and controls
    their visibility through the ``visibility`` field.

    Attributes:
        name: Knowledge base name.
        description: Optional description.
        owner_id: Foreign key to the creating user.
        visibility: Access level (public/private/dept).
        owner: Related user who created the KB.
        documents: Associated documents via many-to-many.
    """

    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("ix_kb_owner", "owner_id"),
        Index("ix_kb_visibility", "visibility"),
        {"comment": "Knowledge bases for document grouping"},
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Knowledge base name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Knowledge base description",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner user ID",
    )
    visibility: Mapped[KBVisibility] = mapped_column(
        SAEnum(KBVisibility, name="kb_visibility"),
        default=KBVisibility.PRIVATE,
        nullable=False,
        comment="Access level: public, private, dept",
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        lazy="selectin",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        secondary="kb_documents",
        back_populates="knowledge_bases",
        lazy="selectin",
    )

    @property
    def is_public(self) -> bool:
        """Check if KB is publicly visible.

        Returns:
            True if visibility is PUBLIC.
        """
        return self.visibility == KBVisibility.PUBLIC

    @property
    def document_count(self) -> int:
        """Number of associated documents.

        Returns:
            Count of documents in this KB.
        """
        return len(self.documents)

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBase(id={self.id}, name='{self.name}', "
            f"visibility={self.visibility.value})>"
        )


class KBDocument(Base):
    """Many-to-many association between knowledge bases and documents.

    This is an association table with its own primary key so that
    future metadata (e.g. added_at, added_by) can be attached.

    Attributes:
        id: Surrogate primary key.
        kb_id: Foreign key to knowledge_bases.
        document_id: Foreign key to documents.
        added_at: Timestamp when the document was added.
    """

    __tablename__ = "kb_documents"
    __table_args__ = (
        Index("ix_kb_doc_kb", "kb_id"),
        Index("ix_kb_doc_doc", "document_id"),
        Index("ix_kb_doc_unique", "kb_id", "document_id", unique=True),
        {"comment": "Knowledge base ↔ document association"},
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    kb_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Knowledge base ID",
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Document ID",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the document was added to the KB",
    )

    def __repr__(self) -> str:
        return (
            f"<KBDocument(kb_id={self.kb_id}, doc_id={self.document_id})>"
        )
