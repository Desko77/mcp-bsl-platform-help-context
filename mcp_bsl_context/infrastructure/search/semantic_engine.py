"""Semantic search engine using Qdrant vector database."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from mcp_bsl_context.domain.entities import Definition
from mcp_bsl_context.infrastructure.embeddings.document_builder import DocumentBuilder
from mcp_bsl_context.infrastructure.embeddings.provider import EmbeddingProvider
from mcp_bsl_context.infrastructure.embeddings.reranker import Reranker

if TYPE_CHECKING:
    from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage

logger = logging.getLogger(__name__)

COLLECTION_NAME = "platform_context"
UPSERT_BATCH_SIZE = 100


class SemanticSearchEngine:
    """Vector-based search using embeddings + Qdrant + optional reranker.

    Lifecycle:
      1. ``ensure_ready(storage)`` — builds lookup dict, creates index if missing.
      2. ``search(query, storage, ...)`` — embed query → Qdrant ANN → rerank → Definitions.

    The Qdrant collection is persisted on disk (``qdrant_path``) and reused across
    restarts.  The in-memory lookup dict is rebuilt from storage on each startup.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        qdrant_path: str,
        reranker: Reranker | None = None,
    ) -> None:
        from qdrant_client import QdrantClient

        self._embedder = embedding_provider
        self._reranker = reranker
        self._client = QdrantClient(path=qdrant_path)
        self._builder = DocumentBuilder()
        self._lookup: dict[tuple[str, str, str], Definition] = {}
        self._ready = False
        self._lock = threading.Lock()

    def ensure_ready(
        self,
        storage: PlatformContextStorage,
        force_reindex: bool = False,
    ) -> None:
        """Prepare the engine: build lookup dict and index if needed.

        Args:
            storage: Loaded platform context storage.
            force_reindex: If True, rebuild the vector index from scratch.
        """
        if self._ready and not force_reindex:
            return
        with self._lock:
            if self._ready and not force_reindex:
                return
            storage.ensure_loaded()
            self._build_lookup(storage)
            if force_reindex or not self._has_collection():
                self._build_index(storage)
            self._ready = True

    def search(
        self,
        query: str,
        storage: PlatformContextStorage,
        limit: int = 10,
        type_filter: str | None = None,
    ) -> list[Definition]:
        """Semantic search: embed query -> Qdrant ANN -> optional rerank.

        Args:
            query: Natural-language search query.
            storage: Platform context storage (for lazy init).
            limit: Maximum results to return.
            type_filter: Optional filter by api_type ("method"/"property"/"type").

        Returns:
            Ordered list of Definition objects (most relevant first).
        """
        self.ensure_ready(storage)

        search_limit = limit * 3 if self._reranker else limit
        query_vector = self._embedder.embed_query(query)

        qdrant_filter = None
        if type_filter:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="api_type", match=MatchValue(value=type_filter)
                    )
                ]
            )

        response = self._client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=search_limit,
            query_filter=qdrant_filter,
        )
        results = response.points

        if not results:
            return []

        # Rerank candidates if reranker is available
        if self._reranker and len(results) > 1:
            texts = [hit.payload.get("text", "") for hit in results]
            reranked = self._reranker.rerank(query, texts, top_k=limit)
            definitions: list[Definition] = []
            for ranked in reranked:
                payload = results[ranked.index].payload
                defn = self._resolve_definition(payload)
                if defn is not None and defn not in definitions:
                    definitions.append(defn)
            return definitions[:limit]

        # Without reranker — map Qdrant results directly
        definitions: list[Definition] = []
        for hit in results[:limit]:
            defn = self._resolve_definition(hit.payload)
            if defn is not None and defn not in definitions:
                definitions.append(defn)
        return definitions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_collection(self) -> bool:
        """Check if the Qdrant collection exists and contains points."""
        try:
            collections = self._client.get_collections().collections
            for col in collections:
                if col.name == COLLECTION_NAME:
                    info = self._client.get_collection(COLLECTION_NAME)
                    return info.points_count > 0
        except Exception:
            pass
        return False

    def _build_index(self, storage: PlatformContextStorage) -> None:
        """Build the vector index from all entities in storage."""
        from qdrant_client.models import Distance, PointStruct, VectorParams

        logger.info("Building semantic index...")
        docs = self._builder.build_all(storage)
        if not docs:
            logger.warning("No documents to index")
            return

        texts = [doc.text for doc in docs]
        logger.info("Embedding %d documents...", len(texts))
        vectors = self._embedder.embed_documents(texts)

        # Recreate collection
        try:
            self._client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        self._client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=self._embedder.dimension(),
                distance=Distance.COSINE,
            ),
        )

        # Upsert in batches
        for i in range(0, len(docs), UPSERT_BATCH_SIZE):
            batch_docs = docs[i : i + UPSERT_BATCH_SIZE]
            batch_vectors = vectors[i : i + UPSERT_BATCH_SIZE]
            points = [
                PointStruct(id=doc.id, vector=vec, payload=doc.metadata)
                for doc, vec in zip(batch_docs, batch_vectors)
            ]
            self._client.upsert(
                collection_name=COLLECTION_NAME, points=points
            )

        logger.info("Semantic index built: %d documents indexed", len(docs))

    def _build_lookup(self, storage: PlatformContextStorage) -> None:
        """Build in-memory lookup dict for resolving Qdrant results to Definitions."""
        lookup: dict[tuple[str, str, str], Definition] = {}

        for method in storage.methods:
            lookup[("method", "", method.name)] = method

        for prop in storage.properties:
            lookup[("property", "", prop.name)] = prop

        for type_def in storage.types:
            lookup[("type", "", type_def.name)] = type_def
            for method in type_def.methods:
                lookup[("method", type_def.name, method.name)] = method
            for prop in type_def.properties:
                lookup[("property", type_def.name, prop.name)] = prop

        self._lookup = lookup
        logger.debug("Lookup table built: %d entries", len(lookup))

    def _resolve_definition(self, payload: dict) -> Definition | None:
        """Resolve a Qdrant payload back to a Definition object."""
        key = (
            payload.get("api_type", ""),
            payload.get("type_name", ""),
            payload.get("name", ""),
        )
        return self._lookup.get(key)
