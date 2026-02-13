"""Embedding providers for semantic search."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

from mcp_bsl_context.config import EmbeddingsConfig

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document texts.

        Args:
            texts: List of document strings to embed.

        Returns:
            List of embedding vectors (same order as input).
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text.

        Args:
            text: Query string.

        Returns:
            Embedding vector.
        """
        ...

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding using sentence-transformers.

    Default model: ai-forever/ru-en-RoSBERTa
    Requires: pip install sentence-transformers torch
    """

    def __init__(
        self,
        model_name: str = "ai-forever/ru-en-RoSBERTa",
        cache_dir: str | None = None,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install 'mcp-bsl-context[local]'"
            ) from e

        if cache_dir:
            os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", cache_dir)

        logger.info("Loading embedding model: %s", model_name)
        self._model = SentenceTransformer(model_name, cache_folder=cache_dir)
        self._dim: int = self._model.get_sentence_embedding_dimension()
        logger.info("Embedding model loaded, dimension: %d", self._dim)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(
            texts, convert_to_numpy=True, show_progress_bar=len(texts) > 100
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def dimension(self) -> int:
        return self._dim


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible embedding API (OpenRouter, LM Studio, etc.).

    Expects a POST /v1/embeddings endpoint with standard OpenAI format.
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
        self._dim: int | None = None

    def _post_embeddings(self, texts: list[str]) -> list[list[float]]:
        import httpx

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = httpx.post(
            f"{self._api_url}/embeddings",
            json={"input": texts, "model": self._model},
            headers=headers,
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            all_embeddings.extend(self._post_embeddings(batch))
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        results = self._post_embeddings([text])
        return results[0]

    def dimension(self) -> int:
        if self._dim is None:
            sample = self.embed_query("dimension probe")
            self._dim = len(sample)
        return self._dim


def create_embedding_provider(
    config: EmbeddingsConfig,
    cache_dir: str | None = None,
) -> EmbeddingProvider:
    """Factory: create an EmbeddingProvider from config.

    Args:
        config: Embeddings configuration section.
        cache_dir: Directory for caching downloaded models.
    """
    if config.provider == "local":
        return LocalEmbeddingProvider(
            model_name=config.model, cache_dir=cache_dir
        )
    if config.provider == "openai-compatible":
        if not config.api_url:
            raise ValueError(
                "embeddings.api_url is required for openai-compatible provider"
            )
        return OpenAICompatibleEmbeddingProvider(
            api_url=config.api_url,
            model=config.model,
            api_key=config.api_key,
        )
    raise ValueError(f"Unknown embedding provider: {config.provider}")
