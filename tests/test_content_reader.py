"""Tests for HBK content reader: HbkContext and inflate logic."""

from __future__ import annotations

import io
import zipfile

import pytest

from mcp_bsl_context.infrastructure.hbk.content_reader import HbkContentReader, HbkContext
from mcp_bsl_context.infrastructure.hbk.toc.toc import Toc
from mcp_bsl_context.infrastructure.hbk.models import Chunk, DoubleLanguageString


def make_zip_bytes(files: dict[str, str]) -> bytes:
    """Create an in-memory ZIP archive from a {name: content} dict."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def make_hbk_context(files: dict[str, str]) -> HbkContext:
    """Create an HbkContext backed by an in-memory ZIP."""
    zip_bytes = make_zip_bytes(files)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    # Minimal TOC with no pages
    toc = Toc._build_tree([])
    return HbkContext(toc, zf)


class TestHbkContextReadPage:
    def test_exact_match(self):
        ctx = make_hbk_context({"dir/page.htm": "<html>OK</html>"})
        result = ctx.read_page("dir/page.htm")
        assert result == "<html>OK</html>"

    def test_leading_slash_stripped(self):
        ctx = make_hbk_context({"dir/page.htm": "content"})
        result = ctx.read_page("/dir/page.htm")
        assert result == "content"

    def test_backslash_normalized(self):
        ctx = make_hbk_context({"dir/page.htm": "data"})
        result = ctx.read_page("dir\\page.htm")
        assert result == "data"

    def test_case_insensitive(self):
        ctx = make_hbk_context({"dir/page.htm": "found"})
        result = ctx.read_page("DIR/PAGE.HTM")
        assert result == "found"

    def test_missing_path(self):
        ctx = make_hbk_context({"dir/page.htm": "x"})
        result = ctx.read_page("other/missing.htm")
        assert result is None

    def test_empty_path(self):
        ctx = make_hbk_context({"dir/page.htm": "x"})
        result = ctx.read_page("")
        assert result is None

    def test_multiple_leading_slashes(self):
        ctx = make_hbk_context({"dir/page.htm": "ok"})
        result = ctx.read_page("///dir/page.htm")
        assert result == "ok"


class TestInflatePackBlock:
    def test_decompress(self):
        toc_content = "{1 {1 0 0 {}}}"
        zip_data = make_zip_bytes({"toc.txt": toc_content})

        result = HbkContentReader._inflate_pack_block(zip_data)
        assert result == toc_content.encode("utf-8")

    def test_empty_zip(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w"):
            pass  # empty ZIP
        with pytest.raises(ValueError, match="empty"):
            HbkContentReader._inflate_pack_block(buf.getvalue())


class TestHbkContextNameCaching:
    def test_name_set_cached(self):
        ctx = make_hbk_context({"a.htm": "A", "b.htm": "B"})
        assert ctx._name_set is None
        ctx.read_page("a.htm")
        assert ctx._name_set is not None
        # Second call uses cache
        cached = ctx._name_set
        ctx.read_page("b.htm")
        assert ctx._name_set is cached

    def test_multiple_reads(self):
        files = {f"page{i}.htm": f"content{i}" for i in range(5)}
        ctx = make_hbk_context(files)

        for name, expected in files.items():
            assert ctx.read_page(name) == expected

    def test_bad_zip_returns_none(self):
        """A valid HbkContext with a file that can't be read returns None."""
        ctx = make_hbk_context({"good.htm": "ok"})
        # Reading a non-existent path returns None
        assert ctx.read_page("nonexistent.htm") is None
