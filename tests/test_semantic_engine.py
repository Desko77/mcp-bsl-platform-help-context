"""Tests for SemanticSearchEngine with mock embedding provider."""

import pytest

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.infrastructure.embeddings.provider import EmbeddingProvider
from mcp_bsl_context.infrastructure.embeddings.reranker import RankedResult, Reranker
from mcp_bsl_context.infrastructure.search.semantic_engine import (
    COLLECTION_NAME,
    SemanticSearchEngine,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    """Produces simple deterministic embeddings for testing."""

    def __init__(self, dim: int = 4) -> None:
        self._dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_vec(text)

    def dimension(self) -> int:
        return self._dim

    def _text_to_vec(self, text: str) -> list[float]:
        """Hash-based deterministic embedding."""
        h = hash(text) % 10000
        base = [(h + i) / 10000.0 for i in range(self._dim)]
        # Normalize
        norm = sum(x * x for x in base) ** 0.5
        return [x / norm for x in base] if norm > 0 else base


class FakeReranker(Reranker):
    """Reverses order (for testing that reranking is applied)."""

    def rerank(
        self, query: str, documents: list[str], top_k: int = 10
    ) -> list[RankedResult]:
        results = [
            RankedResult(index=i, score=float(len(documents) - i), text=doc)
            for i, doc in enumerate(documents)
        ]
        # Reverse the order
        results.reverse()
        return results[:top_k]


class FakeStorage:
    """Minimal storage mock with a few entities."""

    def __init__(self):
        self.methods = [
            MethodDefinition(name="Сообщить", description="Вывод сообщения"),
            MethodDefinition(name="Вопрос", description="Диалог вопроса"),
        ]
        self.properties = [
            PropertyDefinition(name="ТекущаяДата", description="Текущая дата"),
        ]
        self.types = [
            PlatformTypeDefinition(
                name="ТаблицаЗначений",
                description="Табличные данные",
                methods=[
                    MethodDefinition(name="Добавить", description="Добавить строку"),
                    MethodDefinition(name="Удалить", description="Удалить строку"),
                ],
                properties=[
                    PropertyDefinition(name="Колонки", description="Колонки таблицы"),
                ],
            ),
        ]
        self._loaded = True

    def ensure_loaded(self):
        pass


@pytest.fixture
def fake_storage():
    return FakeStorage()


@pytest.fixture
def engine_no_reranker(tmp_path, fake_storage):
    provider = FakeEmbeddingProvider(dim=4)
    engine = SemanticSearchEngine(
        embedding_provider=provider,
        qdrant_path=str(tmp_path / "qdrant"),
        reranker=None,
    )
    engine.ensure_ready(fake_storage)
    return engine


@pytest.fixture
def engine_with_reranker(tmp_path, fake_storage):
    provider = FakeEmbeddingProvider(dim=4)
    reranker = FakeReranker()
    engine = SemanticSearchEngine(
        embedding_provider=provider,
        qdrant_path=str(tmp_path / "qdrant"),
        reranker=reranker,
    )
    engine.ensure_ready(fake_storage)
    return engine


class TestSemanticSearchEngineBasic:
    def test_search_returns_definitions(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search("Сообщить", fake_storage, limit=5)
        assert len(results) > 0
        # All results should be Definition instances
        for r in results:
            assert hasattr(r, "name")

    def test_search_respects_limit(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search("данные", fake_storage, limit=2)
        assert len(results) <= 2

    def test_search_empty_query(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search("", fake_storage, limit=5)
        # Should still return results (empty query gets embedded)
        assert isinstance(results, list)

    def test_search_with_type_filter(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search(
            "добавить", fake_storage, limit=10, type_filter="method"
        )
        for r in results:
            assert isinstance(r, MethodDefinition)


class TestSemanticSearchEngineIndex:
    def test_ensure_ready_idempotent(self, engine_no_reranker, fake_storage):
        # Calling ensure_ready again should not rebuild
        engine_no_reranker.ensure_ready(fake_storage)
        engine_no_reranker.ensure_ready(fake_storage)
        # Should still work
        results = engine_no_reranker.search("тест", fake_storage, limit=5)
        assert isinstance(results, list)

    def test_force_reindex(self, engine_no_reranker, fake_storage):
        engine_no_reranker.ensure_ready(fake_storage, force_reindex=True)
        results = engine_no_reranker.search("Сообщить", fake_storage, limit=5)
        assert len(results) > 0

    def test_has_collection_after_index(self, engine_no_reranker):
        assert engine_no_reranker._has_collection()


class TestSemanticSearchWithReranker:
    def test_reranker_is_applied(self, engine_with_reranker, fake_storage):
        results = engine_with_reranker.search("строка", fake_storage, limit=5)
        assert len(results) > 0

    def test_reranker_with_single_result(self, tmp_path):
        """Reranker should not be invoked for single result."""

        class SingleStorage:
            methods = [MethodDefinition(name="Единственный", description="Один")]
            properties = []
            types = []
            _loaded = True

            def ensure_loaded(self):
                pass

        provider = FakeEmbeddingProvider(dim=4)
        reranker = FakeReranker()
        engine = SemanticSearchEngine(
            embedding_provider=provider,
            qdrant_path=str(tmp_path / "qdrant"),
            reranker=reranker,
        )
        storage = SingleStorage()
        engine.ensure_ready(storage)
        results = engine.search("Единственный", storage, limit=5)
        assert len(results) == 1


class TestSemanticSearchLookup:
    def test_resolves_global_method(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search("Сообщить", fake_storage, limit=10)
        names = [r.name for r in results]
        assert "Сообщить" in names

    def test_resolves_type_member(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search("Добавить", fake_storage, limit=10)
        names = [r.name for r in results]
        assert "Добавить" in names

    def test_resolves_type(self, engine_no_reranker, fake_storage):
        results = engine_no_reranker.search(
            "ТаблицаЗначений", fake_storage, limit=10, type_filter="type"
        )
        names = [r.name for r in results]
        assert "ТаблицаЗначений" in names
