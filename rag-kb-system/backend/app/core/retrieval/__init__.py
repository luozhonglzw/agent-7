"""Retrieval engines for search and Q&A.

Provides vector search, sparse search, and hybrid retrieval.

Components:
    DenseRetriever: Vector similarity search via Qdrant
    BM25Retriever: Sparse keyword search via rank-bm25
    HybridRetriever: Combined dense + sparse with RRF fusion
    Reranker: Cross-encoder reranking (BGE-Reranker)
"""
