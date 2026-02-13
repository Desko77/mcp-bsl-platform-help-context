"""Search query value objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import ApiType


@dataclass(frozen=True)
class SearchOptions:
    case_sensitive: bool = False
    exact_match: bool = False


@dataclass(frozen=True)
class SearchQuery:
    query: str
    type: ApiType | None = None
    limit: int = 10
    options: SearchOptions = field(default_factory=SearchOptions)
