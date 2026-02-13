"""Search strategies for the platform context search engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mcp_bsl_context.domain.entities import (
    Definition,
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.domain.enums import ApiType

if TYPE_CHECKING:
    from .indexes import Indexes


@dataclass
class SearchResult:
    item: Definition
    priority: int
    words_matched: int = 0


def _split_words(text: str) -> list[str]:
    """Split camelCase/PascalCase and space-separated words."""
    # Split by spaces first
    parts = text.strip().split()
    words: list[str] = []
    for part in parts:
        # Split camelCase/PascalCase
        tokens = re.findall(r"[А-ЯA-Z][а-яa-z]*|[а-яa-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)", part)
        if tokens:
            words.extend(tokens)
        else:
            words.append(part)
    return [w.lower() for w in words if w]


class CompoundTypeSearch:
    """Priority 1: Multi-word type queries — joins words into compound type names."""

    priority = 1

    def search(
        self,
        query: str,
        hash_indexes: Indexes,
        prefix_indexes: Indexes,
        api_type: ApiType | None,
    ) -> list[SearchResult]:
        words = query.strip().split()
        if len(words) < 2:
            return []

        if api_type is not None and api_type != ApiType.TYPE:
            return []

        results: list[SearchResult] = []
        seen: set[str] = set()

        # Generate compound variants
        variants = self._generate_variants(words)
        for variant, word_count in variants:
            for item in prefix_indexes.types.get(variant):
                key = item.name.lower()
                if key not in seen:
                    seen.add(key)
                    results.append(SearchResult(item, self.priority, word_count))

        return results

    @staticmethod
    def _generate_variants(words: list[str]) -> list[tuple[str, int]]:
        """Generate compound word variants from a list of words."""
        variants: list[tuple[str, int]] = []
        # All words joined
        variants.append(("".join(words), len(words)))
        # Adjacent pairs
        for i in range(len(words) - 1):
            variants.append(("".join(words[i : i + 2]), 2))
        # First + last (if 3+ words)
        if len(words) >= 3:
            variants.append((words[0] + words[-1], 2))
        return variants


class TypeMemberSearch:
    """Priority 2: Type.Member pattern queries."""

    priority = 2

    def search(
        self,
        query: str,
        hash_indexes: Indexes,
        prefix_indexes: Indexes,
        api_type: ApiType | None,
    ) -> list[SearchResult]:
        words = query.strip().split()
        if len(words) < 2:
            return []

        results: list[SearchResult] = []
        seen: set[str] = set()

        # Try splitting at each position: words[:i] as type, words[i:] as member
        for split_pos in range(1, len(words)):
            type_name = "".join(words[:split_pos])
            member_name = "".join(words[split_pos:])

            type_matches = hash_indexes.types.get(type_name)
            if not type_matches:
                type_matches = prefix_indexes.types.get(type_name)

            for type_def in type_matches:
                if not isinstance(type_def, PlatformTypeDefinition):
                    continue
                member_lower = member_name.lower()
                for method in type_def.methods:
                    if method.name.lower().startswith(member_lower):
                        key = f"{type_def.name}.{method.name}".lower()
                        if key not in seen:
                            seen.add(key)
                            results.append(SearchResult(method, self.priority, split_pos + 1))
                for prop in type_def.properties:
                    if prop.name.lower().startswith(member_lower):
                        key = f"{type_def.name}.{prop.name}".lower()
                        if key not in seen:
                            seen.add(key)
                            results.append(SearchResult(prop, self.priority, split_pos + 1))

        return results


class RegularSearch:
    """Priority 3: Direct index lookup."""

    priority = 3

    def search(
        self,
        query: str,
        hash_indexes: Indexes,
        prefix_indexes: Indexes,
        api_type: ApiType | None,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen: set[str] = set()
        q = query.strip()

        def _add(items: list, priority: int = self.priority) -> None:
            for item in items:
                key = item.name.lower()
                if key not in seen:
                    seen.add(key)
                    results.append(SearchResult(item, priority))

        if api_type is None or api_type == ApiType.METHOD:
            _add(hash_indexes.methods.get(q))
            _add(prefix_indexes.methods.get(q))

        if api_type is None or api_type == ApiType.PROPERTY:
            _add(hash_indexes.properties.get(q))
            _add(prefix_indexes.properties.get(q))

        if api_type is None or api_type == ApiType.TYPE:
            _add(hash_indexes.types.get(q))
            _add(prefix_indexes.types.get(q))

        return results


class WordOrderSearch:
    """Priority 4: Word-based substring matching across all definitions."""

    priority = 4

    def search(
        self,
        query: str,
        all_methods: list[MethodDefinition],
        all_properties: list[PropertyDefinition],
        all_types: list[PlatformTypeDefinition],
        api_type: ApiType | None,
    ) -> list[SearchResult]:
        words = _split_words(query)
        if not words:
            return []

        results: list[SearchResult] = []
        seen: set[str] = set()

        def _check(items: list, expected_type: ApiType | None = None) -> None:
            if api_type is not None and expected_type is not None and api_type != expected_type:
                return
            for item in items:
                name_lower = item.name.lower()
                matched = sum(1 for w in words if w in name_lower)
                if matched > 0:
                    key = name_lower
                    if key not in seen:
                        seen.add(key)
                        results.append(SearchResult(item, self.priority, matched))

        _check(all_methods, ApiType.METHOD)
        _check(all_properties, ApiType.PROPERTY)
        _check(all_types, ApiType.TYPE)

        return results
