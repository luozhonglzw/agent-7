"""LLM abstraction layer.

Provides unified interface for LLM interactions with support
for streaming, retries, and error handling.

Components:
    LLMClient: Base LLM client with Anthropic-compatible API
    EmbeddingService: Embedding model management (BGE-M3)
    RerankerService: Reranker model management (BGE-Reranker)
"""
