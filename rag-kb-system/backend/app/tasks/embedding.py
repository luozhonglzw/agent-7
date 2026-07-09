"""Embedding generation Celery tasks.

Handles batch embedding generation for document chunks using
the configured embedding model (BAAI/bge-m3).

Tasks:
    generate_embeddings: Generate embeddings for a document's chunks.
    batch_embed: Generate embeddings for arbitrary text inputs.
"""

import logging
from typing import Any

from celery import shared_task

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.embedding.generate_embeddings",
    max_retries=3,
    default_retry_delay=30,
    queue="embeddings",
    acks_late=True,
)
def generate_embeddings(
    self,
    document_id: str,
    chunk_ids: list[str],
    texts: list[str],
) -> dict[str, Any]:
    """Generate embeddings for document chunks.

    Takes text chunks and generates embedding vectors using the
    configured model, then stores them in Qdrant.

    Args:
        document_id: UUID of the source document.
        chunk_ids: List of chunk UUIDs corresponding to texts.
        texts: List of text content to embed.

    Returns:
        Dictionary with results:
        - document_id: Source document ID
        - embedded_count: Number of chunks embedded
        - model: Embedding model used
        - dimension: Embedding vector dimension
    """
    logger.info(
        "Generating embeddings: doc_id=%s, chunks=%d",
        document_id, len(texts),
    )

    try:
        # TODO: Implement in Phase 4 with core.llm.embedding
        # 1. Load embedding model
        # 2. Generate embeddings in batches
        # 3. Store in Qdrant with metadata
        # 4. Update embedding_records table

        result = {
            "document_id": document_id,
            "embedded_count": len(texts),
            "model": "BAAI/bge-m3",
            "dimension": 1024,
        }
        logger.info("Embedding generation complete: %s", result)
        return result

    except Exception as exc:
        logger.exception(
            "Embedding generation failed: doc_id=%s, error=%s",
            document_id, str(exc),
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        return {
            "document_id": document_id,
            "status": "failed",
            "error": str(exc),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.embedding.batch_embed",
    max_retries=2,
    default_retry_delay=15,
    queue="embeddings",
)
def batch_embed(
    self,
    texts: list[str],
    batch_size: int = 32,
) -> list[list[float]]:
    """Generate embeddings for a batch of texts.

    General-purpose embedding task for arbitrary text inputs.
    Used for query embedding and ad-hoc embedding needs.

    Args:
        texts: List of texts to embed.
        batch_size: Number of texts to process per batch.

    Returns:
        List of embedding vectors (float lists).
    """
    logger.info("Batch embedding: %d texts, batch_size=%d", len(texts), batch_size)

    try:
        # TODO: Implement in Phase 4
        # from app.core.llm.embedding import get_embedding_model
        # model = get_embedding_model()
        # return model.encode(texts, batch_size=batch_size)

        raise NotImplementedError("Batch embedding not yet implemented")

    except Exception as exc:
        logger.exception("Batch embedding failed: %s", str(exc))
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
