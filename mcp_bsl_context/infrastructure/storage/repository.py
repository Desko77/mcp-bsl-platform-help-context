"""Platform context repository — facade over search engine."""

from __future__ import annotations

from mcp_bsl_context.domain.entities import (
    Definition,
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.domain.value_objects import SearchQuery
from mcp_bsl_context.infrastructure.search.engine import SearchEngine


class PlatformRepository:
    """High-level data access facade delegating to the search engine."""

    def __init__(self, engine: SearchEngine) -> None:
        self._engine = engine

    def search(self, query: SearchQuery) -> list[Definition]:
        return self._engine.search(query)

    def find_type(self, name: str) -> PlatformTypeDefinition | None:
        return self._engine.find_type(name)

    def find_method(self, name: str) -> MethodDefinition | None:
        return self._engine.find_method(name)

    def find_property(self, name: str) -> PropertyDefinition | None:
        return self._engine.find_property(name)

    def find_type_member(self, type_name: str, member_name: str) -> Definition | None:
        return self._engine.find_type_member(type_name, member_name)
