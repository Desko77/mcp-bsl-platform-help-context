"""Tests for Reranker abstraction and factory."""

import pytest

from mcp_bsl_context.config import RerankerConfig
from mcp_bsl_context.infrastructure.embeddings.reranker import (
    LocalReranker,
    OpenAICompatibleReranker,
    RankedResult,
    Reranker,
    create_reranker,
)


class TestRerankerInterface:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            Reranker()


class TestRankedResult:
    def test_frozen_dataclass(self):
        r = RankedResult(index=0, score=0.95, text="test")
        assert r.index == 0
        assert r.score == 0.95
        assert r.text == "test"
        with pytest.raises(AttributeError):
            r.score = 0.5


class TestOpenAICompatibleReranker:
    def test_stores_config(self):
        reranker = OpenAICompatibleReranker(
            api_url="http://localhost:8080/v1",
            model="test-reranker",
            api_key="key123",
        )
        assert reranker._api_url == "http://localhost:8080/v1"
        assert reranker._model == "test-reranker"
        assert reranker._api_key == "key123"

    def test_empty_documents_returns_empty(self):
        reranker = OpenAICompatibleReranker(
            api_url="http://localhost:8080/v1",
            model="test",
        )
        result = reranker.rerank("query", [], top_k=5)
        assert result == []


class TestLocalRerankerImport:
    def test_requires_sentence_transformers(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="sentence-transformers"):
            LocalReranker()


class TestCreateReranker:
    def test_disabled_returns_none(self):
        config = RerankerConfig(enabled=False)
        assert create_reranker(config) is None

    def test_api_requires_url(self):
        config = RerankerConfig(
            enabled=True, provider="openai-compatible", api_url=None
        )
        with pytest.raises(ValueError, match="api_url is required"):
            create_reranker(config)

    def test_api_creates_reranker(self):
        config = RerankerConfig(
            enabled=True,
            provider="openai-compatible",
            model="test-model",
            api_url="http://localhost:8080/v1",
        )
        reranker = create_reranker(config)
        assert isinstance(reranker, OpenAICompatibleReranker)

    def test_unknown_provider_raises(self):
        config = RerankerConfig(enabled=True, provider="unknown")
        with pytest.raises(ValueError, match="Unknown reranker provider"):
            create_reranker(config)
