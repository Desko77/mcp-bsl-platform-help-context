"""Base classes for page parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .html_handler import ParsedPage, parse_html_page


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
