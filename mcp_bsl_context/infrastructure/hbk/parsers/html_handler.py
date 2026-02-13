"""HTML page block extraction using BeautifulSoup.

Extracts structured blocks from 1C platform documentation HTML pages.
Blocks include: Name, Syntax, Parameters, Description, Return Value, Example, etc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    Tag = None  # type: ignore[assignment,misc]

# Block title mapping (Russian titles found in 1C documentation)
BLOCK_TITLES = {
    "Имя": "name",
    "Name": "name",
    "Синтаксис": "syntax",
    "Syntax": "syntax",
    "Параметры": "parameters",
    "Parameters": "parameters",
    "Описание": "description",
    "Description": "description",
    "Возвращаемое значение": "return_value",
    "Return value": "return_value",
    "Значение": "value",
    "Value": "value",
    "Пример": "example",
    "Example": "example",
    "Доступность": "availability",
    "Availability": "availability",
    "Замечание": "note",
    "Note": "note",
    "См. также": "see_also",
    "See also": "see_also",
    "Конструкторы": "constructors",
    "Constructors": "constructors",
    "Методы": "methods",
    "Methods": "methods",
    "Свойства": "properties",
    "Properties": "properties",
}


@dataclass
class ParsedBlock:
    title: str
    block_type: str
    content: str = ""
    items: list[ParsedBlock] = field(default_factory=list)


@dataclass
class ParsedPage:
    title: str = ""
    blocks: list[ParsedBlock] = field(default_factory=list)

    def get_block(self, block_type: str) -> ParsedBlock | None:
        for b in self.blocks:
            if b.block_type == block_type:
                return b
        return None

    def get_block_content(self, block_type: str) -> str:
        block = self.get_block(block_type)
        return block.content if block else ""


def parse_html_page(html: str) -> ParsedPage:
    """Parse an HTML documentation page into structured blocks."""
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "lxml")
    page = ParsedPage()

    # Extract title
    title_tag = soup.find("title")
    if title_tag:
        page.title = title_tag.get_text(strip=True)

    body = soup.find("body")
    if body is None:
        return page

    # Find all header-like elements that serve as block titles
    current_block: ParsedBlock | None = None
    content_parts: list[str] = []

    for element in body.children:
        if not isinstance(element, Tag):
            continue

        text = element.get_text(strip=True)
        if not text:
            continue

        # Check if this element is a block title
        block_type = _detect_block_title(element, text)
        if block_type is not None:
            # Save previous block
            if current_block is not None:
                current_block.content = "\n".join(content_parts).strip()
                page.blocks.append(current_block)
                content_parts.clear()

            current_block = ParsedBlock(title=text, block_type=block_type)
        else:
            # Accumulate content
            if element.name == "pre":
                content_parts.append(element.get_text())
            elif element.name == "table":
                content_parts.append(_parse_table(element))
            elif element.name in ("ul", "ol"):
                content_parts.append(_parse_list(element))
            else:
                content_parts.append(text)

    # Save last block
    if current_block is not None:
        current_block.content = "\n".join(content_parts).strip()
        page.blocks.append(current_block)
    elif content_parts:
        # No blocks detected — put everything in description
        page.blocks.append(
            ParsedBlock(
                title="Description",
                block_type="description",
                content="\n".join(content_parts).strip(),
            )
        )

    return page


def _detect_block_title(element: Tag, text: str) -> str | None:  # type: ignore[name-defined]
    """Detect if an element is a block title and return its type."""
    # Check heading tags
    if element.name in ("h1", "h2", "h3", "h4"):
        return BLOCK_TITLES.get(text, "unknown")

    # Check paragraph with specific CSS classes used in 1C docs
    if element.name == "p":
        css_class = element.get("class", [])
        if isinstance(css_class, list):
            class_str = " ".join(css_class)
        else:
            class_str = str(css_class)

        if "head" in class_str or "title" in class_str:
            return BLOCK_TITLES.get(text, "unknown")

    # Check bold text that matches known block titles
    if element.name in ("p", "div"):
        bold = element.find(["b", "strong"])
        if bold and bold.get_text(strip=True) == text:
            return BLOCK_TITLES.get(text)

    return None


def _parse_table(table: Tag) -> str:  # type: ignore[name-defined]
    """Convert an HTML table to a simple text representation."""
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def _parse_list(list_element: Tag) -> str:  # type: ignore[name-defined]
    """Convert an HTML list to text."""
    items: list[str] = []
    for li in list_element.find_all("li", recursive=False):
        items.append(f"- {li.get_text(strip=True)}")
    return "\n".join(items)
