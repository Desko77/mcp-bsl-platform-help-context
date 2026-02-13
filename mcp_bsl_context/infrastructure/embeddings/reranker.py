"""Reranker implementations for search result refinement."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from mcp_bsl_context.config import RerankerConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RankedResult:
    """A single reranked result with original index and relevance score."""

    index: int
    score: float
    text: str


class Reranker(ABC):
    """Abstract base for rerankers."""

    @abstractmethod
    def rerank(
        self, query: str, documents: list[str], top_k: int = 10
    ) -> list[RankedResult]:
        """Rerank documents by relevance to the query.

        Args:
            query: The search query.
            documents: List of document texts to rerank.
            top_k: Maximum number of results to return.

        Returns:
            Reranked results sorted by score descending.
        """
        ...


class LocalReranker(Reranker):
    """Cross-encoder reranker using sentence-transformers.

    Default model: DiTy/cross-encoder-russian-msmarco
    Requires: pip install sentence-transformers torch
    """

    def __init__(
        self,
        model_name: str = "DiTy/cross-encoder-russian-msmarco",
        cache_dir: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for local reranking. "
                "Install with: pip install 'mcp-bsl-context[local]'"
            ) from e

        if cache_dir:
            os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", cache_dir)
            os.environ.setdefault("HF_HOME", cache_dir)

        logger.info("Loading reranker model: %s", model_name)
        self._model = CrossEncoder(model_name, max_length=512)
        logger.info("Reranker model loaded")

    def rerank(
        self, query: str, documents: list[str], top_k: int = 10
    ) -> list[RankedResult]:
        if not documents:
            return []

        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)

        results = [
            RankedResult(index=i, score=float(s), text=documents[i])
            for i, s in enumerate(scores)
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


class OpenAICompatibleReranker(Reranker):
    """Reranker using a reranking API (Cohere, Jina, etc.).

    Expects a POST /rerank endpoint with:
      Request:  {"model": ..., "query": ..., "documents": [...], "top_n": N}
      Response: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
    """

    def __init__(
        self,
        api_url: str,
        model: str,
        api_key: str | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._model = model
        self._api_key = api_key

    def rerank(
        self, query: str, documents: list[str], top_k: int = 10
    ) -> list[RankedResult]:
        if not documents:
            return []

        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = httpx.post(
            f"{self._api_url}/rerank",
            json={
                "model": self._model,
                "query": query,
                "documents": documents,
                "top_n": top_k,
            },
            headers=headers,
            timeout=60.0,
        )
        response.raise_for_status()
        data = response.json()

        results: list[RankedResult] = []
        for item in data.get("results", []):
            idx = item["index"]
            score = float(
                item.get("relevance_score", item.get("score", 0.0))
            )
            results.append(
                RankedResult(index=idx, score=score, text=documents[idx])
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]


def create_reranker(
    config: RerankerConfig,
    cache_dir: str | None = None,
) -> Reranker | None:
    """Factory: create a Reranker from config, or None if disabled.

    Args:
        config: Reranker configuration section.
        cache_dir: Directory for caching downloaded models.
    """
    if not config.enabled:
        return None

    if config.provider == "local":
        return LocalReranker(model_name=config.model, cache_dir=cache_dir)
    if config.provider == "openai-compatible":
        if not config.api_url:
            raise ValueError(
                "reranker.api_url is required for openai-compatible provider"
            )
        return OpenAICompatibleReranker(
            api_url=config.api_url,
            model=config.model,
            api_key=config.api_key,
        )
    raise ValueError(f"Unknown reranker provider: {config.provider}")
