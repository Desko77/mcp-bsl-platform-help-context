"""Tests for the bracket file tokenizer."""

from mcp_bsl_context.infrastructure.hbk.toc.tokenizer import tokenize


class TestTokenizer:
    def test_empty_string(self):
        assert tokenize("") == []

    def test_simple_numbers(self):
        tokens = tokenize("{3 1 2 3}")
        assert tokens == ["{", "3", "1", "2", "3", "}"]

    def test_quoted_strings(self):
        tokens = tokenize('"hello" "world"')
        assert tokens == ['"hello"', '"world"']

    def test_escaped_quotes(self):
        tokens = tokenize('"he""llo"')
        assert tokens == ['"he"llo"']

    def test_braces(self):
        tokens = tokenize("{a {b c} d}")
        assert tokens == ["{", "a", "{", "b", "c", "}", "d", "}"]

    def test_commas_ignored(self):
        tokens = tokenize("a, b, c")
        assert tokens == ["a", "b", "c"]

    def test_bom_stripped(self):
        tokens = tokenize("\ufeff{1}")
        assert tokens == ["{", "1", "}"]

    def test_whitespace_handling(self):
        tokens = tokenize("  a   b   c  ")
        assert tokens == ["a", "b", "c"]

    def test_nested_structure(self):
        content = '{2 {1 0 0 {0 0 {1 0 {1 "Name"}} "page.html"}} {2 1 0 {0 0 {1 0 {1 "Other"}} "other.html"}}}'
        tokens = tokenize(content)
        assert tokens[0] == "{"
        assert tokens[-1] == "}"
        assert '"Name"' in tokens
        assert '"Other"' in tokens
        assert '"page.html"' in tokens

    def test_mixed_content(self):
        tokens = tokenize('{1 "hello world" 42}')
        assert tokens == ["{", "1", '"hello world"', "42", "}"]
