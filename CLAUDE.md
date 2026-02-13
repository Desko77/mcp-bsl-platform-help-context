# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP server (Python) that gives AI assistants access to 1C:Enterprise platform API documentation. Reads binary `.hbk` help files or pre-exported JSON, parses HTML pages into structured domain entities, and exposes 5 MCP tools for fuzzy search and navigation. Python port of [mcp-bsl-platform-context](https://github.com/alkoleft/mcp-bsl-platform-context) (Kotlin).

## Commands

```bash
pip install -e .           # Install in dev mode
pip install -e ".[dev]"    # Install with pytest

pytest -v                  # Run all tests (79+)
pytest -v tests/test_search_engine.py           # Single test module
pytest -v tests/test_search_engine.py::test_name  # Single test

# Run the server (CLI options or env vars MCP_BSL_*)
mcp-bsl-context -p /path/to/1cv8/8.3.25.1257              # HBK source, STDIO
mcp-bsl-context -p /path --data-source json --json-path /path/to/json  # JSON source
mcp-bsl-context -p /path -m sse --port 8080                # SSE transport
mcp-bsl-context -p /path -m streamable-http --port 8080    # Streamable HTTP transport
mcp-bsl-context -p /path -v                                # Debug logging

# Docker
docker compose up                      # HBK source (mount into ./platform-data/)
docker compose --profile json up       # JSON source (mount into ./json-data/)
```

## Architecture

Layered DDD structure: `domain` → `infrastructure` → `presentation` → `server.py`.

**Domain** (`domain/`) — pure business logic, all dataclasses are `frozen=True`:
- `entities.py`: `Definition`, `MethodDefinition`, `PropertyDefinition`, `PlatformTypeDefinition`, `Signature`, `ParameterDefinition`
- `enums.py`: `ApiType` enum (METHOD, PROPERTY, TYPE, CONSTRUCTOR)
- `value_objects.py`: immutable `SearchQuery`, `SearchOptions`
- `services.py`: `ContextSearchService` — orchestrates search and validation
- `exceptions.py`: `DomainException` hierarchy (`InvalidSearchQueryException`, `PlatformTypeNotFoundException`, etc.)

**Infrastructure** (`infrastructure/`):
- `hbk/` — binary HBK file parsing: `container_reader.py` (struct unpacking) → `content_reader.py` (ZIP extraction) → `context_reader.py` (orchestrator) → `pages_visitor.py` (visitor pattern over page tree). Sub-packages: `toc/` (bracket-format TOC tokenizer/parser), `parsers/` (BeautifulSoup HTML parsers for methods, properties, constructors, enums, objects)
- `json_loader/` — alternative data source from pre-exported JSON files
- `search/` — `engine.py` (`SimpleSearchEngine`), `indexes.py` (`HashIndex` exact match, `StartWithIndex` prefix), `strategies.py` (4 priority-ordered strategies: CompoundTypeSearch → TypeMemberSearch → RegularSearch → WordOrderSearch)
- `storage/` — `storage.py` (thread-safe lazy-loading via `RLock`), `repository.py` (facade), `loader.py` (finds/reads HBK), `mapper.py` (HBK models → domain entities)

**Presentation** (`presentation/formatter.py`) — `MarkdownFormatter` for MCP tool output.

**Server** (`server.py`) — `create_server()` wires dependencies, registers 5 FastMCP tools: `search`, `info`, `get_member`, `get_members`, `get_constructors`.

**Entry point** (`__main__.py`) — Click CLI with options for platform path, transport mode (stdio/sse/streamable-http), data source. All options also accept `MCP_BSL_*` environment variables.

## Key Design Decisions

- **Thread safety**: `RLock` in storage and search engine for MCP's async context
- **Lazy loading**: platform context loaded on first search, not at startup
- **Bilingual API names**: supports both Russian (PascalCase) and English; search is case-insensitive with CamelCase word splitting
- **Search deduplication**: results deduplicated by lowercased name, max 50 results
- **HBK format**: proprietary binary container with ZIP-compressed TOC (bracket format) and ZIP archive of HTML docs; content encoded UTF-16LE
- **Docker**: multi-stage build (builder + slim runtime), runs as non-root `mcpuser`, defaults to streamable-http on port 8080, data mounted at `/data/platform` or `/data/json`
