"""Base classes for page parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .html_handler import ParsedPage, parse_html_page


def page_description(page: ParsedPage) -> str:
    """Description of the page, prefixed with its deprecation banners
    ("Не рекомендуется использовать, начиная с версии X. Рекомендуется использовать: Y")."""
    parts = [block.content for block in page.get_blocks("deprecated") if block.content]
    description = page.get_block_content("description")
    if description:
        parts.append(description)
    return "\n".join(parts)


class PageParser(ABC):
    """Base class for parsing HTML documentation pages into domain models."""

    def parse(self, html_content: str) -> Any:
        """Parse HTML content and return a domain model."""
        page = parse_html_page(html_content)
        return self._build_result(page)

    @abstractmethod
    def _build_result(self, page: ParsedPage) -> Any:
        """Build a domain model from parsed blocks."""
        ...
