"""Search indexes for fast lookup."""

from __future__ import annotations

from bisect import bisect_left
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class HashIndex(Generic[T]):
    """Case-insensitive exact lookup using a dict."""

    def __init__(self) -> None:
        self._data: dict[str, T] = {}

    def load(self, items: list[T], key_fn: Callable[[T], str]) -> None:
        self._data = {key_fn(item).lower(): item for item in items}

    def get(self, key: str) -> list[T]:
        val = self._data.get(key.lower())
        return [val] if val is not None else []

    @property
    def size(self) -> int:
        return len(self._data)

    def is_empty(self) -> bool:
        return len(self._data) == 0


class StartWithIndex(Generic[T]):
    """Prefix-based search using a sorted list + bisect."""

    def __init__(self) -> None:
        self._keys: list[str] = []
        self._values: list[T] = []

    def load(self, items: list[T], key_fn: Callable[[T], str]) -> None:
        pairs = sorted(
            ((key_fn(item).lower(), item) for item in items),
            key=lambda x: x[0],
        )
        self._keys = [p[0] for p in pairs]
        self._values = [p[1] for p in pairs]

    def get(self, prefix: str) -> list[T]:
        prefix = prefix.lower()
        left = bisect_left(self._keys, prefix)
        results: list[T] = []
        for i in range(left, len(self._keys)):
            if self._keys[i].startswith(prefix):
                results.append(self._values[i])
            else:
                break
        return results

    @property
    def size(self) -> int:
        return len(self._keys)

    def is_empty(self) -> bool:
        return len(self._keys) == 0


class Indexes:
    """Composite index manager holding property/method/type indexes."""

    def __init__(
        self,
        properties: HashIndex | StartWithIndex,
        methods: HashIndex | StartWithIndex,
        types: HashIndex | StartWithIndex,
    ) -> None:
        self.properties = properties
        self.methods = methods
        self.types = types
