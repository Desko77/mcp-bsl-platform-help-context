"""Hybrid search engine — merges keyword and semantic results via RRF."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mcp_bsl_context.domain.entities import Definition
from mcp_bsl_context.domain.value_objects import SearchQuery
from mcp_bsl_context.infrastructure.embeddings.document_builder import DocumentBuilder
from mcp_bsl_context.infrastructure.embeddings.reranker import Reranker
from mcp_bsl_context.infrastructure.search.engine import SimpleSearchEngine
from mcp_bsl_context.infrastructure.search.semantic_engine import SemanticSearchEngine

if TYPE_CHECKING:
    from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage

logger = logging.getLogger(__name__)

# Standard RRF constant from the original paper (Cormack et al., 2009).
RRF_K = 60


class HybridSearchEngine:
    """Reciprocal Rank Fusion (RRF) merge of keyword + semantic search.

    Algorithm:
      1. Run keyword search → ranked list A
      2. Run semantic search → ranked list B
      3. For each document d, score(d) = Σ 1/(k + rank_i(d))
      4. Deduplicate by name
      5. Optionally rerank top candidates with cross-encoder
      6. Return top-limit results

    RRF is scale-invariant — it doesn't depend on score magnitudes from
    either engine, only on the rank positions.  Documents found by both
    engines naturally receive higher fused scores.
    """

    def __init__(
        self,
        keyword_engine: SimpleSearchEngine,
        semantic_engine: SemanticSearchEngine,
        reranker: Reranker | None = None,
    ) -> None:
        self._keyword = keyword_engine
        self._semantic = semantic_engine
        self._reranker = reranker
        self._builder = DocumentBuilder()

    def search(
        self,
        query: str,
        storage: PlatformContextStorage,
        limit: int = 10,
        type_filter: str | None = None,
    ) -> list[Definition]:
        """Run hybrid search: keyword + semantic → RRF merge → optional rerank.

        Args:
            query: Search query string.
            storage: Platform context storage.
            limit: Maximum results to return.
            type_filter: Optional API type filter ("method"/"property"/"type").
        """
        fetch_limit = limit * 3

        # 1. Keyword search
        from mcp_bsl_context.domain.enums import ApiType

        api_type = ApiType.from_string(type_filter) if type_filter else None
        keyword_query = SearchQuery(query=query, type=api_type, limit=fetch_limit)
        keyword_results = self._keyword.search(keyword_query)

        # 2. Semantic search
        semantic_results = self._semantic.search(
            query, storage, limit=fetch_limit, type_filter=type_filter
        )

        # 3. RRF merge
        merged = self._rrf_merge(keyword_results, semantic_results)

        # 4. Optional rerank
        if self._reranker and len(merged) > 1:
            rerank_candidates = merged[: limit * 2]
            texts = [self._builder.build_text(d) for d in rerank_candidates]
            reranked = self._reranker.rerank(query, texts, top_k=limit)
            return [rerank_candidates[r.index] for r in reranked]

        return merged[:limit]

    @staticmethod
    def _rrf_merge(
        list_a: list[Definition],
        list_b: list[Definition],
    ) -> list[Definition]:
        """Merge two ranked lists using Reciprocal Rank Fusion.

        Each document receives score = Σ 1/(RRF_K + rank) from each list
        where it appears.  Results are sorted by fused score descending
        and deduplicated by element name.
        """
        scores: dict[str, float] = {}
        items: dict[str, Definition] = {}

        for rank, defn in enumerate(list_a):
            key = _definition_key(defn)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            items.setdefault(key, defn)

        for rank, defn in enumerate(list_b):
            key = _definition_key(defn)
            scores[key] = scores.get(key, 0.0) + 1.0 / (RRF_K + rank + 1)
            items.setdefault(key, defn)

        # Sort by fused score descending
        sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
        return [items[k] for k in sorted_keys]


def _definition_key(defn: Definition) -> str:
    """Unique key for deduplication based on definition type and name."""
    type_prefix = type(defn).__name__
    return f"{type_prefix}:{defn.name}"
