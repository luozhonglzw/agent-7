"""Search and Q&A Pydantic schemas.

Defines request/response models for search and Q&A endpoints.

Schemas:
    SearchRequest: Search query input
    SearchResponse: Search results
    QARequest: Question input
    QAResponse: Answer with citations
    SourceChunk: Retrieved chunk with metadata
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request.

    Attributes:
        query: Search query text.
        top_k: Number of results to return.
        document_ids: Optional filter by document IDs.
        file_types: Optional filter by file types.
        use_reranker: Whether to apply reranking.
        score_threshold: Minimum relevance score.
    """

    query: str = Field(
        ..., min_length=1, max_length=2000, description="Search query"
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Result count")
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Filter by document IDs"
    )
    file_types: list[str] | None = Field(
        default=None, description="Filter by file types"
    )
    use_reranker: bool = Field(default=True, description="Apply reranking")
    score_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Min score threshold"
    )


class SourceChunk(BaseModel):
    """Retrieved source chunk with relevance information.

    Attributes:
        chunk_id: Chunk UUID.
        document_id: Source document UUID.
        document_title: Source document title.
        content: Chunk text content.
        score: Relevance score (0-1).
        page_number: Source page number.
        heading: Section heading.
    """

    chunk_id: uuid.UUID = Field(..., description="Chunk UUID")
    document_id: uuid.UUID = Field(..., description="Document UUID")
    document_title: str = Field(..., description="Document title")
    content: str = Field(..., description="Chunk text content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    page_number: int | None = Field(default=None, description="Page number")
    heading: str | None = Field(default=None, description="Section heading")


class SearchResponse(BaseModel):
    """Search results response.

    Attributes:
        query: Original search query.
        results: List of matching chunks.
        total: Total matching chunks found.
        search_time_ms: Search duration in milliseconds.
    """

    query: str = Field(..., description="Search query")
    results: list[SourceChunk] = Field(
        default_factory=list, description="Search results"
    )
    total: int = Field(..., ge=0, description="Total results")
    search_time_ms: float = Field(
        ..., ge=0, description="Search time in ms"
    )


class QARequest(BaseModel):
    """Q&A request.

    Attributes:
        question: User question.
        top_k: Number of context chunks to retrieve.
        document_ids: Optional filter by document IDs.
        stream: Whether to stream the response.
        max_tokens: Maximum answer length in tokens.
    """

    question: str = Field(
        ..., min_length=1, max_length=5000, description="User question"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Context chunks")
    document_ids: list[uuid.UUID] | None = Field(
        default=None, description="Filter by document IDs"
    )
    stream: bool = Field(default=True, description="Stream response")
    max_tokens: int = Field(
        default=2048, ge=1, le=8192, description="Max answer tokens"
    )


class QAResponse(BaseModel):
    """Q&A response with citations.

    Attributes:
        question: Original question.
        answer: LLM-generated answer.
        sources: Source chunks used for the answer.
        model: LLM model used.
        tokens_used: Total tokens consumed.
        response_time_ms: Response duration in milliseconds.
    """

    question: str = Field(..., description="Original question")
    answer: str = Field(..., description="Generated answer")
    sources: list[SourceChunk] = Field(
        default_factory=list, description="Source citations"
    )
    model: str = Field(..., description="LLM model used")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    response_time_ms: float = Field(
        ..., ge=0, description="Response time in ms"
    )
