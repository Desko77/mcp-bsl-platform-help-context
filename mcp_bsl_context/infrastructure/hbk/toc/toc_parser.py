"""Recursive descent parser for TOC bracket file."""

from __future__ import annotations

from typing import Iterator

from ..models import Chunk, DoubleLanguageString
from .tokenizer import tokenize


class TokenIterator:
    """Iterator over tokens with peek support."""

    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens
        self._pos = 0

    def has_next(self) -> bool:
        return self._pos < len(self._tokens)

    def next(self) -> str:
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def peek(self) -> str | None:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def expect(self, expected: str) -> None:
        token = self.next()
        if token != expected:
            raise ValueError(f"Expected '{expected}', got '{token}' at position {self._pos - 1}")


def parse_content(data: bytes) -> list[Chunk]:
    """Parse TOC bracket file content into chunks."""
    content = data.decode("utf-8")
    tokens = tokenize(content)
    it = TokenIterator(tokens)
    return list(_parse_table_of_content(it))


def _parse_table_of_content(it: TokenIterator) -> Iterator[Chunk]:
    """Parse the top-level table of content block."""
    if not it.has_next():
        return

    it.expect("{")

    # Read chunk count
    count_str = it.next()
    try:
        count = int(count_str)
    except ValueError:
        return

    for _ in range(count):
        chunk = _parse_chunk(it)
        if chunk is not None:
            yield chunk

    # Read closing brace
    if it.has_next() and it.peek() == "}":
        it.next()


def _parse_chunk(it: TokenIterator) -> Chunk | None:
    """Parse a single chunk: {id parentId childCount childId1..N {properties}}."""
    if not it.has_next():
        return None

    it.expect("{")

    chunk = Chunk()
    chunk.id = int(it.next())
    chunk.parent_id = int(it.next())

    child_count = int(it.next())
    for _ in range(child_count):
        chunk.child_ids.append(int(it.next()))

    # Parse properties block
    _parse_chunk_properties(it, chunk)

    it.expect("}")
    return chunk


def _parse_chunk_properties(it: TokenIterator, chunk: Chunk) -> None:
    """Parse the properties block inside a chunk."""
    if not it.has_next() or it.peek() != "{":
        return

    it.expect("{")

    # Read two numbers (number1, number2)
    if it.has_next() and it.peek() != "{":
        it.next()  # number1
    if it.has_next() and it.peek() != "{":
        it.next()  # number2

    # Parse name containers
    if it.has_next() and it.peek() == "{":
        _parse_name_containers(it, chunk)

    # Read html path (quoted string)
    if it.has_next() and it.peek() not in ("{", "}"):
        token = it.next()
        # Strip quotes
        if token.startswith('"') and token.endswith('"'):
            chunk.html_path = token[1:-1]
        else:
            chunk.html_path = token

    # Skip remaining tokens until closing brace
    depth = 1
    while it.has_next() and depth > 0:
        token = it.next()
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1


def _parse_name_containers(it: TokenIterator, chunk: Chunk) -> None:
    """Parse name container blocks with language-specific names."""
    while it.has_next() and it.peek() == "{":
        it.expect("{")

        name = DoubleLanguageString()

        # Read container numbers
        if it.has_next() and it.peek() != "{":
            it.next()
        if it.has_next() and it.peek() != "{":
            it.next()

        # Parse language entries
        while it.has_next() and it.peek() == "{":
            it.expect("{")
            lang_code = it.next()
            name_token = it.next()
            # Strip quotes from name
            if name_token.startswith('"') and name_token.endswith('"'):
                name_value = name_token[1:-1]
            else:
                name_value = name_token

            if lang_code == "1":  # Russian
                name.ru = name_value
            elif lang_code == "2":  # English
                name.en = name_value

            it.expect("}")

        chunk.names.append(name)
        it.expect("}")
