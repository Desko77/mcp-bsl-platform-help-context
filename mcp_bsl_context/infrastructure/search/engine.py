"""Search engine with multi-strategy approach."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Protocol

from mcp_bsl_context.domain.entities import (
    Definition,
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.domain.value_objects import SearchQuery

from .indexes import HashIndex, Indexes, StartWithIndex
from .strategies import (
    CompoundTypeSearch,
    RegularSearch,
    SearchResult,
    TypeMemberSearch,
    WordOrderSearch,
)

if TYPE_CHECKING:
    from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage

logger = logging.getLogger(__name__)

MAX_RESULTS = 50


class SearchEngine(Protocol):
    def search(self, query: SearchQuery) -> list[Definition]: ...
    def find_type(self, name: str) -> PlatformTypeDefinition | None: ...
    def find_property(self, name: str) -> PropertyDefinition | None: ...
    def find_method(self, name: str) -> MethodDefinition | None: ...
    def find_type_member(self, type_name: str, member_name: str) -> Definition | None: ...


class SimpleSearchEngine:
    def __init__(self, storage: PlatformContextStorage) -> None:
        self._storage = storage
        self._hash_indexes = Indexes(
            properties=HashIndex[PropertyDefinition](),
            methods=HashIndex[MethodDefinition](),
            types=HashIndex[PlatformTypeDefinition](),
        )
        self._prefix_indexes = Indexes(
            properties=StartWithIndex[PropertyDefinition](),
            methods=StartWithIndex[MethodDefinition](),
            types=StartWithIndex[PlatformTypeDefinition](),
        )
        self._initialized = False
        self._lock = threading.Lock()

        self._compound_search = CompoundTypeSearch()
        self._type_member_search = TypeMemberSearch()
        self._regular_search = RegularSearch()
        self._word_search = WordOrderSearch()

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._storage.ensure_loaded()
            self._load_indexes()
            self._initialized = True

    def _load_indexes(self) -> None:
        name_fn = lambda item: item.name

        self._hash_indexes.methods.load(self._storage.methods, name_fn)
        self._hash_indexes.properties.load(self._storage.properties, name_fn)
        self._hash_indexes.types.load(self._storage.types, name_fn)

        self._prefix_indexes.methods.load(self._storage.methods, name_fn)
        self._prefix_indexes.properties.load(self._storage.properties, name_fn)
        self._prefix_indexes.types.load(self._storage.types, name_fn)

        logger.info(
            "Indexes loaded: %d methods, %d properties, %d types",
            self._hash_indexes.methods.size,
            self._hash_indexes.properties.size,
            self._hash_indexes.types.size,
        )

    def search(self, query: SearchQuery) -> list[Definition]:
        self._ensure_initialized()

        all_results: list[SearchResult] = []

        # Strategy 1: Compound type search
        all_results.extend(
            self._compound_search.search(
                query.query, self._hash_indexes, self._prefix_indexes, query.type
            )
        )

        # Strategy 2: Type member search
        all_results.extend(
            self._type_member_search.search(
                query.query, self._hash_indexes, self._prefix_indexes, query.type
            )
        )

        # Strategy 3: Regular search
        all_results.extend(
            self._regular_search.search(
                query.query, self._hash_indexes, self._prefix_indexes, query.type
            )
        )

        # Strategy 4: Word-based search
        all_results.extend(
            self._word_search.search(
                query.query,
                self._storage.methods,
                self._storage.properties,
                self._storage.types,
                query.type,
            )
        )

        # Deduplicate
        seen: set[str] = set()
        unique: list[SearchResult] = []
        for r in all_results:
            key = r.item.name.lower()
            if key not in seen:
                seen.add(key)
                unique.append(r)

        # Sort: lower priority number first, then more words matched
        unique.sort(key=lambda r: (r.priority, -r.words_matched))

        limit = min(query.limit, MAX_RESULTS)
        return [r.item for r in unique[:limit]]

    def find_type(self, name: str) -> PlatformTypeDefinition | None:
        self._ensure_initialized()
        results = self._hash_indexes.types.get(name)
        return results[0] if results else None

    def find_property(self, name: str) -> PropertyDefinition | None:
        self._ensure_initialized()
        results = self._hash_indexes.properties.get(name)
        return results[0] if results else None

    def find_method(self, name: str) -> MethodDefinition | None:
        self._ensure_initialized()
        results = self._hash_indexes.methods.get(name)
        return results[0] if results else None

    def find_type_member(self, type_name: str, member_name: str) -> Definition | None:
        self._ensure_initialized()
        type_def = self.find_type(type_name)
        if type_def is None:
            return None
        member_lower = member_name.lower()
        for method in type_def.methods:
            if method.name.lower() == member_lower:
                return method
        for prop in type_def.properties:
            if prop.name.lower() == member_lower:
                return prop
        return None
