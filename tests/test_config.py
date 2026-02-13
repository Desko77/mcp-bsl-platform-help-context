"""Tests for AppConfig loading (YAML, env vars, CLI overrides)."""

import os

import pytest

from mcp_bsl_context.config import AppConfig, load_config


class TestDefaults:
    def test_default_config(self):
        config = load_config()
        assert config.server.mode == "stdio"
        assert config.server.port == 8080
        assert config.server.verbose is False
        assert config.platform.path == ""
        assert config.platform.version is None
        assert config.platform.data_source == "hbk"
        assert config.search.default_mode == "hybrid"
        assert config.embeddings.provider == "local"
        assert config.embeddings.model == "ai-forever/ru-en-RoSBERTa"
        assert config.reranker.enabled is True
        assert config.reranker.model == "DiTy/cross-encoder-russian-msmarco"
        assert config.storage.qdrant_path == "./data/qdrant"
        assert config.index.reindex is False


class TestYamlLoading:
    def test_load_from_yaml(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "server:\n"
            "  mode: sse\n"
            "  port: 9090\n"
            "platform:\n"
            '  path: "/opt/1cv8"\n'
            '  version: "8.3.22"\n'
            "search:\n"
            "  default_mode: keyword\n",
            encoding="utf-8",
        )

        config = load_config(config_path=str(config_file))
        assert config.server.mode == "sse"
        assert config.server.port == 9090
        assert config.platform.path == "/opt/1cv8"
        assert config.platform.version == "8.3.22"
        assert config.search.default_mode == "keyword"

    def test_missing_yaml_uses_defaults(self):
        config = load_config(config_path="/nonexistent/config.yml")
        assert config.server.mode == "stdio"

    def test_partial_yaml_preserves_defaults(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text("server:\n  port: 3000\n", encoding="utf-8")

        config = load_config(config_path=str(config_file))
        assert config.server.port == 3000
        assert config.server.mode == "stdio"  # default preserved

    def test_unknown_section_ignored(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            "unknown_section:\n  foo: bar\nserver:\n  port: 3000\n",
            encoding="utf-8",
        )

        config = load_config(config_path=str(config_file))
        assert config.server.port == 3000


class TestEnvVars:
    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yml"
        config_file.write_text("server:\n  port: 3000\n", encoding="utf-8")

        monkeypatch.setenv("MCP_BSL_PORT", "5000")
        config = load_config(config_path=str(config_file))
        assert config.server.port == 5000

    def test_env_platform_path(self, monkeypatch):
        monkeypatch.setenv("MCP_BSL_PLATFORM_PATH", "/custom/path")
        config = load_config()
        assert config.platform.path == "/custom/path"

    def test_env_verbose_true(self, monkeypatch):
        monkeypatch.setenv("MCP_BSL_VERBOSE", "true")
        config = load_config()
        assert config.server.verbose is True

    def test_env_verbose_false(self, monkeypatch):
        monkeypatch.setenv("MCP_BSL_VERBOSE", "false")
        config = load_config()
        assert config.server.verbose is False


class TestCliOverrides:
    def test_cli_overrides_env(self, monkeypatch):
        monkeypatch.setenv("MCP_BSL_PORT", "5000")
        config = load_config(cli_overrides={"server.port": 7000})
        assert config.server.port == 7000

    def test_cli_overrides_yaml(self, tmp_path):
        config_file = tmp_path / "config.yml"
        config_file.write_text("server:\n  mode: sse\n", encoding="utf-8")

        config = load_config(
            config_path=str(config_file),
            cli_overrides={"server.mode": "streamable-http"},
        )
        assert config.server.mode == "streamable-http"

    def test_none_cli_values_are_skipped(self):
        config = load_config(cli_overrides={"server.port": None})
        assert config.server.port == 8080  # default

    def test_platform_version_override(self):
        config = load_config(cli_overrides={"platform.version": "8.3.20"})
        assert config.platform.version == "8.3.20"


class TestPriority:
    def test_full_priority_chain(self, tmp_path, monkeypatch):
        """YAML < env < CLI."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("server:\n  port: 1000\n", encoding="utf-8")

        monkeypatch.setenv("MCP_BSL_PORT", "2000")

        config = load_config(
            config_path=str(config_file),
            cli_overrides={"server.port": 3000},
        )
        assert config.server.port == 3000

    def test_env_over_yaml(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.yml"
        config_file.write_text("server:\n  port: 1000\n", encoding="utf-8")

        monkeypatch.setenv("MCP_BSL_PORT", "2000")

        config = load_config(config_path=str(config_file))
        assert config.server.port == 2000
