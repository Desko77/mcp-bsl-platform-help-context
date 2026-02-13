# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server (Python) that gives AI assistants access to 1C:Enterprise platform API documentation. Reads binary `.hbk` help files or pre-exported JSON, parses HTML pages into structured domain entities, and exposes MCP tools for fuzzy, semantic, and hybrid search. Python port of [mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) (Kotlin).

## Commands

```bash
pip install -e .              # Install in dev mode
pip install -e ".[dev]"       # Install with pytest
pip install -e ".[local]"     # Install with local embedding models (sentence-transformers, torch)

pytest -v                     # Run all tests (189+)
pytest -v tests/test_search_engine.py           # Single test module
pytest -v tests/test_search_engine.py::test_name  # Single test

# Run the server — YAML config (recommended)
mcp-bsl-context -c config.yml                                  # Full config from YAML
mcp-bsl-context -c config.yml -p /opt/1cv8/x86_64              # YAML + CLI override

# Run the server — CLI options (env vars MCP_BSL_* also work)
mcp-bsl-context -p /opt/1cv8/x86_64                            # Auto-detect latest version
mcp-bsl-context -p /opt/1cv8/x86_64 --platform-version 8.3.20  # Closest to 8.3.20
mcp-bsl-context -p /path -m streamable-http --port 8080         # Streamable HTTP transport
mcp-bsl-context -p /path --data-source json --json-path /path   # JSON source

# Docker
docker compose up                      # CPU + API providers
docker compose --profile gpu up        # GPU + local models
docker compose --profile json up       # JSON data source
```

## Configuration

YAML config file (`config.yml`) is the primary configuration method. See `config.example.yml` for all options.

**Priority:** YAML < env vars (`MCP_BSL_*`) < CLI arguments.

Key sections: `server`, `platform`, `search`, `embeddings`, `reranker`, `storage`, `index`.

## Architecture

Layered DDD structure: `config.py` -> `domain` -> `infrastructure` -> `presentation` -> `server.py`.

**Config** (`config.py`) — `AppConfig` dataclass tree, `load_config()` merges YAML + env + CLI.

**Domain** (`domain/`) — pure business logic, all dataclasses are `frozen=True`:
- `entities.py`: `Definition`, `MethodDefinition`, `PropertyDefinition`, `PlatformTypeDefinition`, `Signature`, `ParameterDefinition`
- `enums.py`: `ApiType` enum (METHOD, PROPERTY, TYPE, CONSTRUCTOR)
- `value_objects.py`: `SearchQuery`, `SearchOptions`, `PlatformVersion`, `find_closest_version()`
- `services.py`: `ContextSearchService` — orchestrates search and validation
- `exceptions.py`: `DomainException` hierarchy

**Infrastructure** (`infrastructure/`):
- `hbk/` — binary HBK file parsing: `container_reader.py` -> `content_reader.py` -> `context_reader.py` -> `pages_visitor.py`. Sub-packages: `toc/`, `parsers/`
- `json_loader/` — alternative data source from pre-exported JSON files
- `search/` — `engine.py` (keyword `SimpleSearchEngine`), `semantic_engine.py` (Qdrant + embeddings), `hybrid_engine.py` (RRF merge + reranker), `indexes.py`, `strategies.py`
- `embeddings/` — `provider.py` (`EmbeddingProvider` ABC, local/API), `reranker.py` (`Reranker` ABC, local/API), `document_builder.py` (entities -> embeddable text + Qdrant payload)
- `storage/` — `storage.py` (thread-safe lazy-loading), `repository.py` (facade), `loader.py`, `mapper.py`, `version_discovery.py` (`VersionDiscovery`)

**Presentation** (`presentation/formatter.py`) — `MarkdownFormatter` for MCP tool output.

**Server** (`server.py`) — `create_server(config)` wires dependencies, discovers platform versions, registers 6 MCP tools. `_LazySemanticState` defers ML model loading until first semantic/hybrid search request.

**Entry point** (`__main__.py`) — Click CLI with `--config`/`-c` for YAML, plus individual CLI overrides.

## Search Modes

The `search` tool supports three modes via the `mode` parameter (default from `config.search.default_mode`):

| Mode | Engine | Description |
|------|--------|-------------|
| `keyword` | `SimpleSearchEngine` | 4-strategy keyword search (hash, prefix, compound, word-order) |
| `semantic` | `SemanticSearchEngine` | Embed query -> Qdrant ANN -> optional cross-encoder rerank |
| `hybrid` | `HybridSearchEngine` | Keyword + semantic in parallel -> RRF merge (k=60) -> rerank |

**RAG pipeline:** `DocumentBuilder` -> `EmbeddingProvider` -> Qdrant embedded -> `Reranker`

**Default models:** `ai-forever/ru-en-RoSBERTa` (embedder), `DiTy/cross-encoder-russian-msmarco` (reranker)

**Providers:** `local` (sentence-transformers) or `openai-compatible` (any OpenAI-format API)

## Key Design Decisions

- **YAML-first config**: `config.py` loads YAML -> env vars -> CLI overrides in priority order
- **Multi-version support**: `VersionDiscovery` scans for version subdirectories (8.X.X.X pattern), resolves to closest match or latest. Single-version paths still work transparently.
- **Lazy semantic init**: ML models and Qdrant are only loaded on first semantic/hybrid search, not at startup. Keyword-only usage incurs no overhead.
- **Thread safety**: `RLock` in storage and search engine for MCP's async context
- **Lazy loading**: platform context loaded on first search, not at startup
- **Bilingual API names**: supports both Russian (PascalCase) and English; search is case-insensitive with CamelCase word splitting
- **HBK format**: proprietary binary container with ZIP-compressed TOC (bracket format) and ZIP archive of HTML docs; content encoded UTF-16LE
- **HBK version differences**: 8.3.27+ uses multi-page data chains in container, TOC language codes `"ru"`/`"en"` (quoted) instead of `"1"`/`"2"`, `"#"` for section headers, multiple root nodes (10), CSS classes `V8SH_heading`/`V8SH_chapter` in HTML. TOC paths have leading `/` but ZIP entries don't — stripped in `content_reader.py`.
- **Docker**: multi-stage build, non-root `mcpuser`, Qdrant data and model cache mounted on host for persistence. GPU Dockerfile uses venv (not `--prefix`) to avoid Ubuntu system pip issues with pyproject.toml packages.
- **Qdrant embedded**: vector DB runs in-process, persists to `storage.qdrant_path`. Deterministic UUID5 point IDs ensure stability across restarts.
- **Host binding**: `MCP_BSL_HOST` env var / `server.host` config controls bind address. Docker sets `0.0.0.0`; local default is `127.0.0.1`.
