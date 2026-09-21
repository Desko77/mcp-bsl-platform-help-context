"""Tests for TOC tree builder."""

from __future__ import annotations

from mcp_bsl_context.infrastructure.hbk.models import Chunk, DoubleLanguageString
from mcp_bsl_context.infrastructure.hbk.toc.toc import Toc


def make_chunk(
    id: int,
    parent_id: int = 0,
    child_ids: list[int] | None = None,
    name_ru: str = "",
    name_en: str = "",
    html_path: str = "",
) -> Chunk:
    chunk = Chunk(
        id=id,
        parent_id=parent_id,
        child_ids=child_ids or [],
    )
    if name_ru or name_en:
        chunk.names.append(DoubleLanguageString(ru=name_ru, en=name_en))
    chunk.html_path = html_path
    return chunk


class TestBuildTreeSingleRoot:
    def test_single_root(self):
        chunks = [make_chunk(id=1, name_ru="Корень")]
        toc = Toc._build_tree(chunks)

        assert toc.root.id == 1
        assert toc.root.name_ru == "Корень"
        assert toc.root.parent is None

    def test_parent_child(self):
        chunks = [
            make_chunk(id=1, child_ids=[2], name_ru="Родитель"),
            make_chunk(id=2, parent_id=1, name_ru="Потомок"),
        ]
        toc = Toc._build_tree(chunks)

        assert toc.root.id == 1
        assert len(toc.root.children) == 1
        assert toc.root.children[0].id == 2
        assert toc.root.children[0].parent is toc.root

    def test_three_levels(self):
        chunks = [
            make_chunk(id=1, child_ids=[2], name_ru="A"),
            make_chunk(id=2, parent_id=1, child_ids=[3], name_ru="B"),
            make_chunk(id=3, parent_id=2, name_ru="C"),
        ]
        toc = Toc._build_tree(chunks)

        leaf = toc.root.children[0].children[0]
        assert leaf.id == 3
        assert leaf.parent.id == 2
        assert leaf.parent.parent.id == 1


class TestBuildTreeMultipleRoots:
    def test_virtual_root_created(self):
        chunks = [
            make_chunk(id=1, name_ru="Root1"),
            make_chunk(id=2, name_ru="Root2"),
        ]
        toc = Toc._build_tree(chunks)

        assert toc.root.id == 0
        assert toc.root.name_ru == "root"

    def test_virtual_root_children(self):
        chunks = [
            make_chunk(id=1, name_ru="Root1"),
            make_chunk(id=2, name_ru="Root2"),
            make_chunk(id=3, name_ru="Root3"),
        ]
        toc = Toc._build_tree(chunks)

        child_ids = [c.id for c in toc.root.children]
        assert child_ids == [1, 2, 3]

    def test_original_roots_have_parent(self):
        chunks = [
            make_chunk(id=1, name_ru="R1"),
            make_chunk(id=2, name_ru="R2"),
        ]
        toc = Toc._build_tree(chunks)

        for child in toc.root.children:
            assert child.parent is toc.root


class TestBuildTreeEmpty:
    def test_empty_chunks(self):
        toc = Toc._build_tree([])

        assert toc.root.id == 0
        assert toc.root.name_ru == "root"
        assert toc.root.children == []


class TestGetPage:
    def test_existing_page(self):
        chunks = [
            make_chunk(id=1, child_ids=[2], name_ru="Parent"),
            make_chunk(id=2, parent_id=1, name_ru="Child"),
        ]
        toc = Toc._build_tree(chunks)

        page = toc.get_page(2)
        assert page is not None
        assert page.name_ru == "Child"

    def test_missing_page(self):
        chunks = [make_chunk(id=1, name_ru="Only")]
        toc = Toc._build_tree(chunks)

        assert toc.get_page(999) is None


class TestAllPages:
    def test_returns_all(self):
        chunks = [
            make_chunk(id=1, child_ids=[2, 3], name_ru="Root"),
            make_chunk(id=2, parent_id=1, name_ru="A"),
            make_chunk(id=3, parent_id=1, name_ru="B"),
        ]
        toc = Toc._build_tree(chunks)

        assert len(toc.all_pages) == 3

    def test_includes_virtual_root(self):
        chunks = [
            make_chunk(id=1, name_ru="R1"),
            make_chunk(id=2, name_ru="R2"),
        ]
        toc = Toc._build_tree(chunks)

        ids = {p.id for p in toc.all_pages}
        assert 0 in ids  # virtual root
        assert 1 in ids
        assert 2 in ids

    def test_single_page(self):
        chunks = [make_chunk(id=5, name_ru="Solo")]
        toc = Toc._build_tree(chunks)

        assert len(toc.all_pages) == 1
        assert toc.all_pages[0].id == 5
