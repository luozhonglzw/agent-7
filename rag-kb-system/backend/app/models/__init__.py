"""SQLAlchemy ORM models for the RAG Knowledge Base System.

This package contains all database models organized by domain:
- base: Base model with common fields
- user: User and session models
- document: Document and chunk models
- knowledge_base: Knowledge base and document association
- embedding: Embedding metadata models
- audit: Audit log model
- casbin_rule: Casbin RBAC rule model
"""

from app.models.audit import AuditLog
from app.models.base import Base, BaseModel
from app.models.casbin_rule import CasbinRule
from app.models.document import Document, DocumentChunk
from app.models.embedding import EmbeddingRecord
from app.models.knowledge_base import KBDocument, KBVisibility, KnowledgeBase
from app.models.user import User, UserSession

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "UserSession",
    "Document",
    "DocumentChunk",
    "KnowledgeBase",
    "KBDocument",
    "KBVisibility",
    "EmbeddingRecord",
    "AuditLog",
    "CasbinRule",
]
