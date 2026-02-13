"""FastMCP server with platform context tools."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from mcp_bsl_context.config import AppConfig
from mcp_bsl_context.domain.entities import Definition
from mcp_bsl_context.domain.exceptions import DomainException, PlatformContextLoadException
from mcp_bsl_context.domain.services import ContextSearchService
from mcp_bsl_context.domain.value_objects import PlatformVersion, find_closest_version
from mcp_bsl_context.infrastructure.search.engine import SimpleSearchEngine
from mcp_bsl_context.infrastructure.storage.loader import PlatformContextLoader
from mcp_bsl_context.infrastructure.storage.repository import PlatformRepository
from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage
from mcp_bsl_context.infrastructure.storage.version_discovery import (
    PlatformVersionInfo,
    VersionDiscovery,
)
from mcp_bsl_context.presentation.formatter import MarkdownFormatter

logger = logging.getLogger(__name__)

MIN_LIMIT = 1
MAX_LIMIT = 50
DEFAULT_LIMIT = 10
VALID_MODES = {"keyword", "semantic", "hybrid"}


class _LazySemanticState:
    """Lazy-loaded semantic/hybrid search components.

    Models and Qdrant are not initialized until the first
    semantic or hybrid search request.  This avoids loading
    heavy ML models when only keyword search is used.
    """

    def __init__(
        self,
        config: AppConfig,
        storage: PlatformContextStorage,
        keyword_engine: SimpleSearchEngine,
    ) -> None:
        self._config = config
        self._storage = storage
        self._keyword_engine = keyword_engine
        self._semantic_engine = None
        self._hybrid_engine = None
        self._lock = threading.Lock()
        self._initialized = False
        self._init_error: str | None = None

    def _ensure_initialized(self) -> None:
        if self._initialized:
            if self._init_error:
                raise RuntimeError(self._init_error)
            return
        with self._lock:
            if self._initialized:
                if self._init_error:
                    raise RuntimeError(self._init_error)
                return
            try:
                self._do_init()
            except Exception as exc:
                self._init_error = (
                    f"Failed to initialize semantic search: {exc}. "
                    "Use mode='keyword' or install dependencies: "
                    "pip install 'mcp-bsl-context[local]'"
                )
                self._initialized = True
                raise RuntimeError(self._init_error) from exc
            self._initialized = True

    def _do_init(self) -> None:
        from mcp_bsl_context.infrastructure.embeddings.provider import (
            create_embedding_provider,
        )
        from mcp_bsl_context.infrastructure.embeddings.reranker import (
            create_reranker,
        )
        from mcp_bsl_context.infrastructure.search.hybrid_engine import (
            HybridSearchEngine,
        )
        from mcp_bsl_context.infrastructure.search.semantic_engine import (
            SemanticSearchEngine,
        )

        cache_dir = self._config.storage.models_cache
        logger.info("Initializing semantic search components...")

        embedder = create_embedding_provider(
            self._config.embeddings, cache_dir=cache_dir
        )
        reranker = create_reranker(
            self._config.reranker, cache_dir=cache_dir
        )

        self._semantic_engine = SemanticSearchEngine(
            embedding_provider=embedder,
            qdrant_path=self._config.storage.qdrant_path,
            reranker=reranker,
        )

        # Force reindex if configured
        self._semantic_engine.ensure_ready(
            self._storage,
            force_reindex=self._config.index.reindex,
        )

        self._hybrid_engine = HybridSearchEngine(
            keyword_engine=self._keyword_engine,
            semantic_engine=self._semantic_engine,
            reranker=reranker,
        )
        logger.info("Semantic search components ready")

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        type_filter: str | None = None,
    ) -> list[Definition]:
        self._ensure_initialized()
        return self._semantic_engine.search(
            query, self._storage, limit=limit, type_filter=type_filter
        )

    def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        type_filter: str | None = None,
    ) -> list[Definition]:
        self._ensure_initialized()
        return self._hybrid_engine.search(
            query, self._storage, limit=limit, type_filter=type_filter
        )


def create_server(config: AppConfig):
    """Create and configure the MCP server.

    Args:
        config: Application configuration (YAML + env + CLI merged).
    """
    from fastmcp import FastMCP

    mcp = FastMCP("mcp-bsl-context")

    # Wire dependencies
    loader = PlatformContextLoader()

    if config.platform.data_source == "json" and config.platform.json_path:
        storage = _create_json_storage(config.platform.json_path)
        version_info = PlatformVersionInfo(
            active_version=None,
            active_hbk_path=Path(),
            available_versions=[],
        )
    else:
        storage, version_info = _create_hbk_storage(loader, config)

    keyword_engine = SimpleSearchEngine(storage)
    repository = PlatformRepository(keyword_engine)
    service = ContextSearchService(repository)
    formatter = MarkdownFormatter()

    # Lazy-loaded semantic/hybrid components
    semantic_state = _LazySemanticState(config, storage, keyword_engine)

    @mcp.tool()
    def search(
        query: str,
        mode: str | None = None,
        type: str | None = None,
        limit: int | None = None,
    ) -> str:
        """Search 1C platform API documentation.

        Supports keyword, semantic (embeddings), and hybrid (both + RRF merge) modes.
        Use specific 1C terms (Russian or English) for best results.

        Args:
            query: Search term (e.g., 'НайтиПоСсылке', 'FindByRef',
                   or natural language: 'добавить строку в таблицу значений')
            mode: Search mode — 'keyword', 'semantic', or 'hybrid' (default from config)
            type: Filter by element type: 'method', 'property', or 'type'
            limit: Maximum results to return (1-50, default 10)
        """
        effective_mode = mode or config.search.default_mode
        if effective_mode not in VALID_MODES:
            return formatter.format_error(
                ValueError(
                    f"Invalid search mode: '{effective_mode}'. "
                    f"Use: {', '.join(sorted(VALID_MODES))}"
                )
            )

        effective_limit = DEFAULT_LIMIT
        if limit is not None:
            effective_limit = max(MIN_LIMIT, min(limit, MAX_LIMIT))

        try:
            if effective_mode == "keyword":
                results = service.search_all(query, type, effective_limit)
            elif effective_mode == "semantic":
                results = semantic_state.semantic_search(
                    query, limit=effective_limit, type_filter=type
                )
            else:  # hybrid
                results = semantic_state.hybrid_search(
                    query, limit=effective_limit, type_filter=type
                )
            return (
                formatter.format_query(query)
                + formatter.format_search_results(results)
            )
        except DomainException as e:
            return formatter.format_error(e)
        except RuntimeError as e:
            return f"**Error:** {e}"

    @mcp.tool()
    def info(name: str, type: str) -> str:
        """Get detailed information about a specific 1C platform API element.

        Args:
            name: Exact element name (e.g., 'НайтиПоСсылке')
            type: Element type: 'method', 'property', or 'type'
        """
        try:
            definition = service.get_info(name, type)
            return formatter.format_member(definition)
        except DomainException as e:
            return formatter.format_error(e)

    @mcp.tool()
    def get_member(type_name: str, member_name: str) -> str:
        """Get information about a method or property of a specific 1C type.

        Args:
            type_name: Type name (e.g., 'СправочникСсылка', 'CatalogRef')
            member_name: Method or property name within the type
        """
        try:
            definition = service.find_member_by_type_and_name(type_name, member_name)
            return formatter.format_member(definition)
        except DomainException as e:
            return formatter.format_error(e)

    @mcp.tool()
    def get_members(type_name: str) -> str:
        """Get full list of methods and properties for a 1C platform type.

        Args:
            type_name: Type name (e.g., 'ТаблицаЗначений', 'ValueTable')
        """
        try:
            members = service.find_type_members(type_name)
            return formatter.format_type_members(members)
        except DomainException as e:
            return formatter.format_error(e)

    @mcp.tool()
    def get_constructors(type_name: str) -> str:
        """Get constructor signatures for creating instances of a 1C platform type.

        Args:
            type_name: Type name (e.g., 'ТаблицаЗначений', 'ValueTable')
        """
        try:
            constructors = service.find_constructors(type_name)
            return formatter.format_constructors(constructors, type_name)
        except DomainException as e:
            return formatter.format_error(e)

    @mcp.tool()
    def get_platform_info() -> str:
        """Get information about the active platform version and list available versions.

        Returns the currently loaded version, HBK file path,
        and all discovered platform versions.
        """
        parts: list[str] = []

        if version_info.active_version:
            parts.append(f"**Active version:** {version_info.active_version}")
        else:
            parts.append("**Active version:** unknown")

        if version_info.active_hbk_path and str(version_info.active_hbk_path):
            parts.append(f"**HBK path:** `{version_info.active_hbk_path}`")

        if version_info.available_versions:
            sorted_versions = sorted(version_info.available_versions, reverse=True)
            parts.append(f"\n**Available versions ({len(sorted_versions)}):**")
            for v in sorted_versions:
                marker = " **(active)**" if v == version_info.active_version else ""
                parts.append(f"- {v}{marker}")
        else:
            parts.append("\n*Single-version mode — no other versions discovered.*")

        return "\n".join(parts)

    return mcp


def _create_hbk_storage(
    loader: PlatformContextLoader,
    config: AppConfig,
) -> tuple[PlatformContextStorage, PlatformVersionInfo]:
    """Discover versions, resolve the active one, create storage."""
    platform_path = Path(config.platform.path)

    discovery = VersionDiscovery()
    discovered = discovery.discover(platform_path)

    if not discovered:
        raise PlatformContextLoadException(
            f"No HBK files found in '{platform_path}'"
        )

    # Separate versioned and unversioned discoveries
    versioned = [d for d in discovered if d.version is not None]

    if config.platform.version:
        # User requested a specific version — find closest match
        target = PlatformVersion.parse(config.platform.version)
        if target is None:
            raise PlatformContextLoadException(
                f"Invalid version format: '{config.platform.version}'. Expected: 8.X.X"
            )
        if versioned:
            closest = find_closest_version(target, [d.version for d in versioned])
            resolved = next(d for d in versioned if d.version == closest)
            logger.info("Requested version %s, resolved to %s", target, closest)
        else:
            resolved = discovered[0]
            logger.warning(
                "Version %s requested but no version info available, using single HBK",
                target,
            )
    else:
        # Default: pick maximum version
        if versioned:
            resolved = max(versioned, key=lambda d: d.version)
            logger.info("Auto-selected latest version: %s", resolved.version)
        else:
            resolved = discovered[0]

    storage = PlatformContextStorage(loader, resolved.platform_dir)
    version_info_result = PlatformVersionInfo(
        active_version=resolved.version,
        active_hbk_path=resolved.hbk_path,
        available_versions=[d.version for d in versioned],
    )

    return storage, version_info_result


def _create_json_storage(json_path: str) -> PlatformContextStorage:
    """Create a storage pre-loaded from JSON files."""
    from mcp_bsl_context.infrastructure.json_loader.json_context_loader import JsonContextLoader

    json_loader = JsonContextLoader()
    methods, properties, types = json_loader.load_all(Path(json_path))

    # Create a dummy storage and populate it directly
    storage = PlatformContextStorage.__new__(PlatformContextStorage)
    storage.methods = methods
    storage.properties = properties
    storage.types = types
    storage._loaded = True
    storage._lock = __import__("threading").RLock()
    return storage
