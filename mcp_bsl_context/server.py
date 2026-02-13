"""FastMCP server with 5 platform context tools."""

from __future__ import annotations

import logging
from pathlib import Path

from mcp_bsl_context.domain.exceptions import DomainException
from mcp_bsl_context.domain.services import ContextSearchService
from mcp_bsl_context.infrastructure.search.engine import SimpleSearchEngine
from mcp_bsl_context.infrastructure.storage.loader import PlatformContextLoader
from mcp_bsl_context.infrastructure.storage.repository import PlatformRepository
from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage
from mcp_bsl_context.presentation.formatter import MarkdownFormatter

logger = logging.getLogger(__name__)


def create_server(
    platform_path: str,
    data_source: str = "hbk",
    json_path: str | None = None,
):
    """Create and configure the MCP server.

    Args:
        platform_path: Path to 1C platform installation directory.
        data_source: "hbk" for direct HBK reading, "json" for pre-exported JSON.
        json_path: Path to JSON directory (required when data_source="json").
    """
    from fastmcp import FastMCP

    mcp = FastMCP("mcp-bsl-context")

    # Wire dependencies
    loader = PlatformContextLoader()

    if data_source == "json" and json_path:
        storage = _create_json_storage(json_path)
    else:
        storage = PlatformContextStorage(loader, Path(platform_path))

    engine = SimpleSearchEngine(storage)
    repository = PlatformRepository(engine)
    service = ContextSearchService(repository)
    formatter = MarkdownFormatter()

    @mcp.tool()
    def search(query: str, type: str | None = None, limit: int | None = None) -> str:
        """Search 1C platform API documentation.

        Fuzzy search across methods, properties, types.
        Use specific 1C terms (Russian or English) for best results.

        Args:
            query: Search term (e.g., 'НайтиПоСсылке', 'FindByRef')
            type: Filter by element type: 'method', 'property', or 'type'
            limit: Maximum results to return (1-50, default 10)
        """
        try:
            results = service.search_all(query, type, limit)
            return formatter.format_query(query) + formatter.format_search_results(results)
        except DomainException as e:
            return formatter.format_error(e)

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

    return mcp


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
