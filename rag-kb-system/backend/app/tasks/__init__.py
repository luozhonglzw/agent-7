"""Celery tasks for the RAG Knowledge Base System.

This package contains async tasks for document processing,
embedding generation, and other background operations.

Tasks:
    document.process_document: Parse and chunk uploaded documents.
    embedding.generate_embeddings: Generate embeddings for text chunks.
    embedding.batch_embed: Batch embedding generation for multiple chunks.
"""

from app.tasks.document import process_document, reprocess_document
from app.tasks.embedding import generate_embeddings, batch_embed

__all__ = [
    "process_document",
    "reprocess_document",
    "generate_embeddings",
    "batch_embed",
]
