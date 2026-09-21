"""Tests for TOC bracket file parser."""

from __future__ import annotations

import pytest

from mcp_bsl_context.infrastructure.hbk.toc.toc_parser import (
    TokenIterator,
    _strip_quotes,
    parse_content,
)


class TestStripQuotes:
    def test_quoted_string(self):
        assert _strip_quotes('"hello"') == "hello"

    def test_unquoted_string(self):
        assert _strip_quotes("hello") == "hello"

    def test_empty_quoted(self):
        assert _strip_quotes('""') == ""

    def test_single_quote_not_stripped(self):
        assert _strip_quotes('"hello') == '"hello'

    def test_empty_string(self):
        assert _strip_quotes("") == ""


class TestTokenIterator:
    def test_basic_iteration(self):
        it = TokenIterator(["a", "b", "c"])
        assert it.has_next()
        assert it.peek() == "a"
        assert it.next() == "a"
        assert it.next() == "b"
        assert it.next() == "c"
        assert not it.has_next()

    def test_peek_does_not_advance(self):
        it = TokenIterator(["x", "y"])
        assert it.peek() == "x"
        assert it.peek() == "x"
        assert it.next() == "x"

    def test_peek_empty(self):
        it = TokenIterator([])
        assert it.peek() is None

    def test_expect_success(self):
        it = TokenIterator(["{", "1", "}"])
        it.expect("{")
        assert it.next() == "1"

    def test_expect_failure(self):
        it = TokenIterator(["{", "1"])
        with pytest.raises(ValueError, match="Expected '}'"):
            it.expect("}")


class TestParseContentOldFormat:
    """Old format uses numeric language codes: '1' for Russian, '2' for English."""

    def _make_toc_bytes(self, content: str) -> bytes:
        return content.encode("utf-8")

    def test_single_chunk_numeric_lang(self):
        # One chunk with id=1, parent=0, 0 children, name in Russian (code "1")
        # Format: {count {id parent child_count {num1 num2 {cnum1 cnum2 {lang name}...} "path"}}}
        toc = '{1 {1 0 0 {0 0 {1 0 {1 "Имя"} {2 "Name"}} "page.html"}}}'
        chunks = parse_content(self._make_toc_bytes(toc))

        assert len(chunks) == 1
        assert chunks[0].id == 1
        assert chunks[0].parent_id == 0
        assert chunks[0].names[0].ru == "Имя"
        assert chunks[0].names[0].en == "Name"
        assert chunks[0].html_path == "page.html"

    def test_multiple_chunks(self):
        # Two chunks: parent(id=1) and child(id=2, parent=1)
        toc = (
            '{2 '
            '{1 0 1 2 {0 0 {1 0 {1 "Родитель"} {2 "Parent"}} "parent.html"}} '
            '{2 1 0 {0 0 {1 0 {1 "Потомок"} {2 "Child"}} "child.html"}}}'
        )
        chunks = parse_content(self._make_toc_bytes(toc))

        assert len(chunks) == 2
        assert chunks[0].id == 1
        assert chunks[0].child_ids == [2]
        assert chunks[1].id == 2
        assert chunks[1].parent_id == 1

    def test_html_path_extraction(self):
        toc = '{1 {1 0 0 {0 0 {1 0 {1 "T"}} "docs/api/page.htm"}}}'
        chunks = parse_content(self._make_toc_bytes(toc))

        assert len(chunks) == 1
        assert chunks[0].html_path == "docs/api/page.htm"


class TestParseContentNewFormat:
    """New 8.3.27 format uses quoted language codes: 'ru', 'en', '#'."""

    def _make_toc_bytes(self, content: str) -> bytes:
        return content.encode("utf-8")

    def test_quoted_lang_codes(self):
        toc = '{1 {1 0 0 {0 0 {1 0 {"ru" "Тест"} {"en" "Test"}} "test.html"}}}'
        chunks = parse_content(self._make_toc_bytes(toc))

        assert len(chunks) == 1
        assert chunks[0].names[0].ru == "Тест"
        assert chunks[0].names[0].en == "Test"

    def test_hash_lang_code(self):
        toc = '{1 {1 0 0 {0 0 {1 0 {"#" "Раздел"}} "section.html"}}}'
        chunks = parse_content(self._make_toc_bytes(toc))

        assert len(chunks) == 1
        assert chunks[0].names[0].ru == "Раздел"

    def test_empty_content(self):
        chunks = parse_content(b"")
        assert chunks == []

    def test_zero_chunks(self):
        chunks = parse_content(b"{0}")
        assert chunks == []
