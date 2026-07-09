"""Document processing Celery tasks.

Handles asynchronous document parsing, chunking, and indexing.
Documents are processed in the background to avoid blocking API requests.

Tasks:
    process_document: Full document processing pipeline.
    reprocess_document: Re-process a failed or updated document.
"""

import logging
import uuid
from datetime import datetime, timezone

from celery import shared_task

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.document.process_document",
    max_retries=3,
    default_retry_delay=30,
    queue="documents",
    acks_late=True,
)
def process_document(self, document_id: str, file_path: str, file_type: str) -> dict:
    """Process an uploaded document through the full pipeline.

    Pipeline stages:
    1. Parse document content (PDF, DOCX, MD, etc.)
    2. Split into chunks with overlap
    3. Generate embeddings for each chunk
    4. Store chunks in PostgreSQL
    5. Store vectors in Qdrant
    6. Update document status to READY

    Args:
        document_id: UUID of the document to process.
        file_path: Path to the uploaded file.
        file_type: File extension (pdf, docx, md, etc.).

    Returns:
        Dictionary with processing results:
        - document_id: Processed document ID
        - chunk_count: Number of chunks created
        - token_count: Total tokens across all chunks
        - status: Final status (ready/failed)

    Raises:
        Retry: If processing fails and retries remain.
    """
    logger.info(
        "Starting document processing: doc_id=%s, file=%s, type=%s",
        document_id, file_path, file_type,
    )

    try:
        # Update status to PARSING
        _update_document_status(document_id, "parsing")

        # Stage 1: Parse document
        # TODO: Implement in Phase 3 with core.parsers
        content = _parse_document(file_path, file_type)
        logger.info("Parsed document %s: %d chars", document_id, len(content))

        # Update status to CHUNKING
        _update_document_status(document_id, "chunking")

        # Stage 2: Split into chunks
        # TODO: Implement in Phase 3 with core.chunking
        chunks = _chunk_content(content)
        logger.info("Chunked document %s: %d chunks", document_id, len(chunks))

        # Update status to EMBEDDING
        _update_document_status(document_id, "embedding")

        # Stage 3: Generate embeddings
        # TODO: Implement in Phase 4 with core.retrieval
        embeddings = _generate_embeddings(chunks)
        logger.info("Embedded document %s: %d vectors", document_id, len(embeddings))

        # Update status to INDEXING
        _update_document_status(document_id, "indexing")

        # Stage 4: Store in Qdrant
        # TODO: Implement in Phase 4 with core.retrieval
        _store_vectors(document_id, chunks, embeddings)

        # Stage 5: Update document status to READY
        _update_document_status(
            document_id,
            "ready",
            chunk_count=len(chunks),
            token_count=sum(len(c.split()) for c in chunks),
        )

        result = {
            "document_id": document_id,
            "chunk_count": len(chunks),
            "status": "ready",
        }
        logger.info("Document processing complete: %s", result)
        return result

    except Exception as exc:
        logger.exception(
            "Document processing failed: doc_id=%s, error=%s",
            document_id, str(exc),
        )
        _update_document_status(document_id, "failed", error_message=str(exc))

        # Retry if we have retries left
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc

        return {
            "document_id": document_id,
            "status": "failed",
            "error": str(exc),
        }


@celery_app.task(
    bind=True,
    name="app.tasks.document.reprocess_document",
    max_retries=2,
    default_retry_delay=60,
    queue="documents",
)
def reprocess_document(self, document_id: str) -> dict:
    """Re-process a document that failed or needs updating.

    Deletes existing chunks and vectors before re-processing.

    Args:
        document_id: UUID of the document to reprocess.

    Returns:
        Dictionary with processing results.
    """
    logger.info("Reprocessing document: %s", document_id)

    try:
        # TODO: Implement cleanup of existing chunks/vectors
        # Then run the full pipeline
        return process_document.apply_async(
            args=[document_id, "", ""],
        ).get(timeout=600)

    except Exception as exc:
        logger.exception("Reprocessing failed: doc_id=%s", document_id)
        return {
            "document_id": document_id,
            "status": "failed",
            "error": str(exc),
        }


# ── Internal Helpers ───────────────────────────────────────────

def _update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    token_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update document processing status in database.

    Args:
        document_id: Document UUID.
        status: New status value.
        chunk_count: Optional chunk count to update.
        token_count: Optional token count to update.
        error_message: Optional error message.
    """
    # TODO: Implement database update in Phase 3
    logger.info(
        "Document %s status -> %s (chunks=%s, tokens=%s, error=%s)",
        document_id, status, chunk_count, token_count, error_message,
    )


def _parse_document(file_path: str, file_type: str) -> str:
    """Parse document content from file.

    Args:
        file_path: Path to the document file.
        file_type: File extension.

    Returns:
        Extracted text content.

    Raises:
        ValueError: If file type is not supported.
    """
    # TODO: Implement in Phase 3 with core.parsers
    raise NotImplementedError("Document parsing not yet implemented")


def _chunk_content(content: str) -> list[str]:
    """Split content into overlapping chunks.

    Args:
        content: Full document text.

    Returns:
        List of text chunks.
    """
    # TODO: Implement in Phase 3 with core.chunking
    raise NotImplementedError("Chunking not yet implemented")


def _generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Generate embeddings for text chunks.

    Args:
        chunks: List of text chunks.

    Returns:
        List of embedding vectors.
    """
    # TODO: Implement in Phase 4 with core.retrieval
    raise NotImplementedError("Embedding generation not yet implemented")


def _store_vectors(
    document_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    """Store vectors in Qdrant.

    Args:
        document_id: Document UUID.
        chunks: Text chunks.
        embeddings: Embedding vectors.
    """
    # TODO: Implement in Phase 4 with core.retrieval
    raise NotImplementedError("Vector storage not yet implemented")
