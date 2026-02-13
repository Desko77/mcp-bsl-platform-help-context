"""Tests for EmbeddingProvider abstraction and factory."""

import pytest

from mcp_bsl_context.config import EmbeddingsConfig
from mcp_bsl_context.infrastructure.embeddings.provider import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    create_embedding_provider,
)


class TestEmbeddingProviderInterface:
    def test_abc_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_local_provider_requires_sentence_transformers(self, monkeypatch):
        """If sentence-transformers is not installed, ImportError is raised."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="sentence-transformers"):
            LocalEmbeddingProvider()


class TestOpenAICompatibleProvider:
    def test_stores_config(self):
        provider = OpenAICompatibleEmbeddingProvider(
            api_url="http://localhost:1234/v1",
            model="test-model",
            api_key="test-key",
        )
        assert provider._api_url == "http://localhost:1234/v1"
        assert provider._model == "test-model"
        assert provider._api_key == "test-key"

    def test_strips_trailing_slash(self):
        provider = OpenAICompatibleEmbeddingProvider(
            api_url="http://localhost:1234/v1/",
            model="test",
        )
        assert provider._api_url == "http://localhost:1234/v1"


class TestCreateEmbeddingProvider:
    def test_factory_local_raises_without_deps(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        config = EmbeddingsConfig(provider="local")
        with pytest.raises(ImportError):
            create_embedding_provider(config)

    def test_factory_api_requires_url(self):
        config = EmbeddingsConfig(provider="openai-compatible", api_url=None)
        with pytest.raises(ValueError, match="api_url is required"):
            create_embedding_provider(config)

    def test_factory_api_creates_provider(self):
        config = EmbeddingsConfig(
            provider="openai-compatible",
            model="test-model",
            api_url="http://localhost:1234/v1",
            api_key="key",
        )
        provider = create_embedding_provider(config)
        assert isinstance(provider, OpenAICompatibleEmbeddingProvider)

    def test_factory_unknown_provider_raises(self):
        config = EmbeddingsConfig(provider="unknown")
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            create_embedding_provider(config)
