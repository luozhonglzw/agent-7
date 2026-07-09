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
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import settings

logger = logging.getLogger(__name__)

# Sync engine for Celery workers (cannot use async in Celery tasks).
_sync_engine = None
_SyncSessionLocal = None


def _get_sync_session() -> Session:
    """Get a synchronous database session for Celery tasks.

    Returns:
        SQLAlchemy sync session.
    """
    global _sync_engine, _SyncSessionLocal  # noqa: PLW0603
    if _sync_engine is None:
        _sync_engine = create_engine(settings.db.sync_url, pool_pre_ping=True)
        _SyncSessionLocal = sessionmaker(bind=_sync_engine)
    return _SyncSessionLocal()


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
        Dictionary with processing results.

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
        parsed_doc = _parse_document(file_path, file_type)
        logger.info(
            "Parsed document %s: %d pages, %d chars, title='%s'",
            document_id, parsed_doc.page_count, parsed_doc.char_count, parsed_doc.title,
        )

        # Update title from parsed content if not already set
        _update_document_title(document_id, parsed_doc.title)

        # Update status to CHUNKING
        _update_document_status(document_id, "chunking")

        # Stage 2: Split into chunks
        chunks = _chunk_content(parsed_doc.full_text)
        logger.info("Chunked document %s: %d chunks", document_id, len(chunks))

        # Stage 3: Store chunks in PostgreSQL
        _store_chunks(document_id, chunks)

        # Update status to EMBEDDING
        _update_document_status(document_id, "embedding")

        # Stage 4: Generate embeddings (stub — Phase 4)
        # embeddings = _generate_embeddings(chunks)

        # Update status to INDEXING
        _update_document_status(document_id, "indexing")

        # Stage 5: Store in Qdrant (stub — Phase 4)
        # _store_vectors(document_id, chunks, embeddings)

        # Stage 6: Update document status to READY
        token_count = sum(len(c.split()) for c in chunks)
        _update_document_status(
            document_id,
            "ready",
            chunk_count=len(chunks),
            token_count=token_count,
        )

        result = {
            "document_id": document_id,
            "chunk_count": len(chunks),
            "token_count": token_count,
            "status": "ready",
        }
        logger.info("Document processing complete: %s", result)
        return result

    except Exception as exc:
        logger.exception(
            "Document processing failed: doc_id=%s, error=%s",
            document_id, str(exc),
        )
        _update_document_status(document_id, "failed", error_message=str(exc)[:500])

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

    Args:
        document_id: UUID of the document to reprocess.

    Returns:
        Dictionary with processing results.
    """
    logger.info("Reprocessing document: %s", document_id)

    session = _get_sync_session()
    try:
        from app.models.document import Document

        doc = session.query(Document).filter(Document.id == uuid.UUID(document_id)).first()
        if doc is None:
            return {"document_id": document_id, "status": "failed", "error": "Document not found"}

        # Delete existing chunks
        from app.models.document import DocumentChunk
        session.query(DocumentChunk).filter(
            DocumentChunk.document_id == uuid.UUID(document_id)
        ).delete()
        session.commit()

        # Run the full pipeline
        return process_document.apply_async(
            args=[document_id, doc.file_path, doc.file_type],
            task_id=document_id,
        ).get(timeout=600)

    except Exception as exc:
        logger.exception("Reprocessing failed: doc_id=%s", document_id)
        return {"document_id": document_id, "status": "failed", "error": str(exc)}
    finally:
        session.close()


# ── Internal Helpers ───────────────────────────────────────────


def _update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    token_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update document processing status in database (sync).

    Args:
        document_id: Document UUID.
        status: New status value.
        chunk_count: Optional chunk count to update.
        token_count: Optional token count to update.
        error_message: Optional error message.
    """
    from app.models.document import Document, DocumentStatus

    session = _get_sync_session()
    try:
        doc = session.query(Document).filter(
            Document.id == uuid.UUID(document_id)
        ).first()
        if doc is None:
            logger.warning("Document not found for status update: %s", document_id)
            return

        doc.status = DocumentStatus(status)
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        if token_count is not None:
            doc.token_count = token_count
        if error_message is not None:
            doc.error_message = error_message
        if status == "ready":
            doc.processed_at = datetime.now(timezone.utc)

        session.commit()
        logger.debug("Document %s status -> %s", document_id, status)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _update_document_title(document_id: str, title: str) -> None:
    """Update document title from parsed content.

    Args:
        document_id: Document UUID.
        title: Extracted title.
    """
    if not title:
        return

    from app.models.document import Document

    session = _get_sync_session()
    try:
        doc = session.query(Document).filter(
            Document.id == uuid.UUID(document_id)
        ).first()
        if doc and not doc.title:
            doc.title = title[:500]
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def _parse_document(file_path: str, file_type: str):
    """Parse document content from file.

    Args:
        file_path: Path to the document file.
        file_type: File extension.

    Returns:
        ParsedDocument instance.
    """
    from app.core.parsers import parse_file

    return parse_file(Path(file_path))


def _chunk_content(content: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split content into overlapping chunks.

    Uses a simple word-boundary approach.  Phase 3 will add
    recursive and semantic chunking strategies.

    Args:
        content: Full document text.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between adjacent chunks in characters.

    Returns:
        List of text chunks.
    """
    if not content.strip():
        return []

    chunks: list[str] = []
    start = 0
    content_len = len(content)

    while start < content_len:
        end = min(start + chunk_size, content_len)

        # Try to break at a sentence or word boundary
        if end < content_len:
            # Look for sentence boundary
            for sep in (". ", "。", "\n\n", "\n"):
                last_sep = content.rfind(sep, start + chunk_size // 2, end)
                if last_sep > start:
                    end = last_sep + len(sep)
                    break
            else:
                # Fall back to word boundary
                last_space = content.rfind(" ", start + chunk_size // 2, end)
                if last_space > start:
                    end = last_space + 1

        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, end - overlap)

    return chunks


def _store_chunks(document_id: str, chunks: list[str]) -> None:
    """Store parsed chunks in PostgreSQL (sync).

    Args:
        document_id: Document UUID.
        chunks: List of text chunks.
    """
    from app.models.document import DocumentChunk

    session = _get_sync_session()
    try:
        doc_uuid = uuid.UUID(document_id)
        for i, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc_uuid,
                chunk_index=i,
                content=chunk_text,
                token_count=len(chunk_text.split()),
            )
            session.add(chunk)
        session.commit()
        logger.debug("Stored %d chunks for document %s", len(chunks), document_id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
