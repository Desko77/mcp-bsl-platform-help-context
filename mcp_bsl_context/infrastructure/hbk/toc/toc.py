"""Table of Contents tree builder."""

from __future__ import annotations

import logging

from ..models import Chunk, Page
from .toc_parser import parse_content

logger = logging.getLogger(__name__)


class Toc:
    """Builds and provides access to a page tree from parsed TOC data."""

    def __init__(self, root: Page) -> None:
        self.root = root
        self._pages_by_id: dict[int, Page] = {}
        self._index_pages(root)

    def _index_pages(self, page: Page) -> None:
        self._pages_by_id[page.id] = page
        for child in page.children:
            self._index_pages(child)

    def get_page(self, page_id: int) -> Page | None:
        return self._pages_by_id.get(page_id)

    @property
    def all_pages(self) -> list[Page]:
        return list(self._pages_by_id.values())

    @classmethod
    def parse(cls, data: bytes) -> Toc:
        """Parse TOC data and build the page tree."""
        chunks = parse_content(data)
        return cls._build_tree(chunks)

    @classmethod
    def _build_tree(cls, chunks: list[Chunk]) -> Toc:
        """Build a page tree from flat chunks."""
        chunk_map: dict[int, Chunk] = {c.id: c for c in chunks}
        page_map: dict[int, Page] = {}

        # Create all pages
        for chunk in chunks:
            name_ru = ""
            name_en = ""
            if chunk.names:
                name_ru = chunk.names[0].ru
                name_en = chunk.names[0].en

            page = Page(
                id=chunk.id,
                name_ru=name_ru,
                name_en=name_en,
                path=chunk.html_path,
            )
            page_map[chunk.id] = page

        # Build parent-child relationships
        for chunk in chunks:
            page = page_map[chunk.id]
            for child_id in chunk.child_ids:
                child_page = page_map.get(child_id)
                if child_page is not None:
                    child_page.parent = page
                    page.children.append(child_page)

        # Find all root pages (pages without a parent)
        roots = [page_map[c.id] for c in chunks if page_map[c.id].parent is None]

        if len(roots) == 1:
            root = roots[0]
        elif roots:
            # Multiple roots — create a virtual root containing all of them
            root = Page(id=0, name_ru="root")
            for r in roots:
                r.parent = root
                root.children.append(r)
        else:
            root = Page(id=0, name_ru="root")

        logger.debug("TOC tree built: %d pages", len(page_map))
        return cls(root)
