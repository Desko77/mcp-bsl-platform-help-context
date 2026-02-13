"""Application configuration with YAML + env vars + CLI override support."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    mode: str = "stdio"
    port: int = 8080
    verbose: bool = False


@dataclass
class PlatformConfig:
    path: str = ""
    version: str | None = None
    data_source: str = "hbk"
    json_path: str | None = None


@dataclass
class SearchConfig:
    default_mode: str = "hybrid"  # hybrid | semantic | keyword


@dataclass
class EmbeddingsConfig:
    provider: str = "local"  # local | openai-compatible
    model: str = "ai-forever/ru-en-RoSBERTa"
    api_url: str | None = None
    api_key: str | None = None


@dataclass
class RerankerConfig:
    enabled: bool = True
    provider: str = "local"  # local | openai-compatible
    model: str = "DiTy/cross-encoder-russian-msmarco"
    api_url: str | None = None
    api_key: str | None = None


@dataclass
class StorageConfig:
    qdrant_path: str = "./data/qdrant"
    models_cache: str = "./data/models"


@dataclass
class IndexConfig:
    reindex: bool = False
    reset_cache: bool = False


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    embeddings: EmbeddingsConfig = field(default_factory=EmbeddingsConfig)
    reranker: RerankerConfig = field(default_factory=RerankerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    index: IndexConfig = field(default_factory=IndexConfig)


# Mapping: env var name -> (section, field)
_ENV_MAPPING: dict[str, tuple[str, str]] = {
    "MCP_BSL_PLATFORM_PATH": ("platform", "path"),
    "MCP_BSL_PLATFORM_VERSION": ("platform", "version"),
    "MCP_BSL_MODE": ("server", "mode"),
    "MCP_BSL_PORT": ("server", "port"),
    "MCP_BSL_DATA_SOURCE": ("platform", "data_source"),
    "MCP_BSL_JSON_PATH": ("platform", "json_path"),
    "MCP_BSL_VERBOSE": ("server", "verbose"),
}


def load_config(
    config_path: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> AppConfig:
    """Load configuration with priority: YAML < env vars < CLI overrides.

    Args:
        config_path: Path to YAML config file. None to skip.
        cli_overrides: Dict of CLI overrides in format {"section.field": value}.
            None values are skipped (means CLI option was not provided).
    """
    config = AppConfig()

    # 1. Load from YAML
    if config_path:
        _apply_yaml(config, config_path)

    # 2. Apply env vars
    _apply_env_vars(config)

    # 3. Apply CLI overrides
    if cli_overrides:
        _apply_overrides(config, cli_overrides)

    return config


def _apply_yaml(config: AppConfig, config_path: str) -> None:
    """Load YAML file and apply values to config."""
    path = Path(config_path)
    if not path.is_file():
        logger.warning("Config file not found: %s, using defaults", config_path)
        return

    try:
        import yaml
    except ImportError:
        logger.error("pyyaml not installed. Install with: pip install pyyaml")
        return

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        logger.warning("Config file is not a valid YAML mapping: %s", config_path)
        return

    for section_name, section_data in data.items():
        if not isinstance(section_data, dict):
            continue
        section = getattr(config, section_name, None)
        if section is None:
            logger.debug("Unknown config section: %s", section_name)
            continue
        _set_section_fields(section, section_data)

    logger.info("Loaded config from %s", config_path)


def _apply_env_vars(config: AppConfig) -> None:
    """Apply environment variables to config."""
    for env_name, (section_name, field_name) in _ENV_MAPPING.items():
        value = os.environ.get(env_name)
        if value is None:
            continue
        section = getattr(config, section_name, None)
        if section is None:
            continue
        _set_field_value(section, field_name, value)


def _apply_overrides(config: AppConfig, overrides: dict[str, Any]) -> None:
    """Apply CLI overrides in format {'section.field': value}."""
    for key, value in overrides.items():
        if value is None:
            continue
        parts = key.split(".", 1)
        if len(parts) != 2:
            continue
        section_name, field_name = parts
        section = getattr(config, section_name, None)
        if section is None:
            continue
        _set_field_value(section, field_name, value)


def _set_section_fields(section: Any, data: dict[str, Any]) -> None:
    """Set fields on a section dataclass from a dict."""
    section_fields = {f.name: f for f in fields(section)}
    for key, value in data.items():
        if key in section_fields and value is not None:
            _set_field_value(section, key, value)


def _set_field_value(obj: Any, field_name: str, value: Any) -> None:
    """Set a field on a dataclass, coercing the value to the correct type."""
    field_info = {f.name: f for f in fields(obj)}.get(field_name)
    if field_info is None:
        return

    coerced = _coerce_value(value, field_info.type)
    object.__setattr__(obj, field_name, coerced)


def _coerce_value(value: Any, type_hint: str | type | None) -> Any:
    """Coerce a value to match the target type hint."""
    if value is None:
        return None

    type_str = str(type_hint) if type_hint else ""

    if "bool" in type_str:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    if "int" in type_str and "None" not in type_str:
        return int(value)

    if "int" in type_str and "None" in type_str:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    return value
