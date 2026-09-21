"""HTML page block extraction using BeautifulSoup.

Extracts structured blocks from 1C platform documentation HTML pages.
Blocks include: Name, Syntax, Parameters, Description, Return Value, Example, etc.

Page layout of the platform help (both the 8.3.10-era ``div`` markup and the
8.3.24+ ``p`` markup)::

    <h1 class="V8SH_pagetitle">Тип.Метод (Type.Method)</h1>
    <p class="V8SH_title">Тип (Type)</p>              -> owner
    <p class="V8SH_heading">Метод (Method)</p>        -> name
    <div class="__SINCE_SHOW_STYLE__">...</div>       -> since
    <div class="__DEPRECATED_SHOW_STYLE__">...</div>  -> deprecated
    <p class="V8SH_chapter">Вариант синтаксиса: X</p> -> variant (repeated per variant)
    <p class="V8SH_chapter">Синтаксис:</p>Метод(<А>)  -> syntax (bare text!)
    <p class="V8SH_chapter">Параметры:</p>
      <div class="V8SH_rubric"><А> (обязательный)</div>Тип: Строка.<br>Описание -> items
    <p class="V8SH_chapter">Возвращаемое значение:</p>Тип: Число.<br>Описание
    <p class="V8SH_chapter">Описание:</p><p>...</p>
    <HR>  -> end of content (external link follows)

Most of the content is bare text between tags, so the walker processes text
nodes as well as elements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

try:
    from bs4 import BeautifulSoup, Comment, NavigableString, Tag
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    Comment = None  # type: ignore[assignment,misc]
    NavigableString = None  # type: ignore[assignment,misc]
    Tag = None  # type: ignore[assignment,misc]

# Block title mapping (Russian titles found in 1C documentation)
BLOCK_TITLES = {
    "Имя": "name",
    "Name": "name",
    "Синтаксис": "syntax",
    "Syntax": "syntax",
    "Вариант синтаксиса": "variant",
    "Syntax variant": "variant",
    "Параметры": "parameters",
    "Parameters": "parameters",
    "Описание": "description",
    "Description": "description",
    "Описание варианта метода": "variant_description",
    "Method variant description": "variant_description",
    "Возвращаемое значение": "return_value",
    "Return value": "return_value",
    "Значение": "value",
    "Value": "value",
    "Использование": "usage",
    "Usage": "usage",
    "Пример": "example",
    "Example": "example",
    "Доступность": "availability",
    "Availability": "availability",
    "Замечание": "note",
    "Примечание": "note",
    "Note": "note",
    "См. также": "see_also",
    "See also": "see_also",
    "Конструкторы": "constructors",
    "Constructors": "constructors",
    "Методы": "methods",
    "Methods": "methods",
    "Свойства": "properties",
    "Properties": "properties",
    "Элементы коллекции": "collection_items",
    "Collection items": "collection_items",
    "Использование в версии": "version_info",
    "Version usage": "version_info",
}

# CSS classes of the platform help markup
CLASS_PAGE_TITLE = "V8SH_pagetitle"
CLASS_OWNER = "V8SH_title"
CLASS_HEADING = "V8SH_heading"
CLASS_CHAPTER = "V8SH_chapter"
CLASS_RUBRIC = "V8SH_rubric"
CLASS_SINCE = "__SINCE_SHOW_STYLE__"
# Other banners before the first chapter: __DEPRECATED_SHOW_STYLE__,
# __INTERFACE_DEPRECATED_SHOW_STYLE__ ("Не рекомендуется использовать...")
BANNER_CLASS_SUFFIX = "_SHOW_STYLE__"

# Blocks that describe the page rather than its content
_META_BLOCK_TYPES = {"name", "owner", "since", "deprecated", "intro"}

_BLOCK_LEVEL_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
    "tr", "blockquote", "section", "article", "dd", "dt", "dl",
}
_SKIPPED_TAGS = {"script", "style", "head", "title", "meta", "link"}

# Markers around text whose indentation must survive normalization
VERBATIM_START = "\x02"
VERBATIM_END = "\x03"


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

    def get_blocks(self, block_type: str) -> list[ParsedBlock]:
        return [b for b in self.blocks if b.block_type == block_type]

    def get_block_content(self, block_type: str) -> str:
        block = self.get_block(block_type)
        return block.content if block else ""


class _BlockCollector:
    """Accumulates text and rubric items for the block being parsed."""

    def __init__(self, block: ParsedBlock | None) -> None:
        self.block = block
        self._parts: list[str] = []
        self._item: ParsedBlock | None = None
        self._item_parts: list[str] = []

    def add_text(self, text: str) -> None:
        if not text:
            return
        self._parts.append(text)
        if self._item is not None:
            self._item_parts.append(text)

    def start_item(self, title: str) -> None:
        self._flush_item()
        self._item = ParsedBlock(title=title, block_type="item")
        self._parts.append("\n" + title + "\n")

    def finish(self) -> ParsedBlock | None:
        """Return the finished block (None if there is no block and no content)."""
        self._flush_item()
        content = normalize_text("".join(self._parts))
        if self.block is None:
            if not content:
                return None
            self.block = ParsedBlock(title="Intro", block_type="intro")
        if self.block.content and content:
            self.block.content = normalize_text(self.block.content + "\n" + content)
        elif content:
            self.block.content = content
        return self.block

    def _flush_item(self) -> None:
        if self._item is None:
            return
        self._item.content = normalize_text("".join(self._item_parts))
        if self.block is not None:
            self.block.items.append(self._item)
        self._item = None
        self._item_parts = []


def parse_html_page(html: str) -> ParsedPage:
    """Parse an HTML documentation page into structured blocks."""
    if BeautifulSoup is None:
        raise ImportError("beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")

    soup = BeautifulSoup(html, "lxml")
    page = ParsedPage()

    title_tag = soup.find("title")
    if title_tag:
        page.title = title_tag.get_text(strip=True)

    body = soup.find("body")
    if body is None:
        return page

    collector = _BlockCollector(None)

    def close_block() -> None:
        nonlocal collector
        block = collector.finish()
        if block is not None:
            page.blocks.append(block)

    def open_block(block: ParsedBlock | None) -> None:
        nonlocal collector
        close_block()
        collector = _BlockCollector(block)

    for element in body.children:
        if isinstance(element, NavigableString):
            if isinstance(element, Comment):
                continue
            collector.add_text(str(element))
            continue
        if not isinstance(element, Tag):
            continue

        name = element.name.lower()
        if name in _SKIPPED_TAGS:
            continue

        # Everything after the trailing <hr> is the external "Методическая информация" link
        if name == "hr":
            break

        if name == "br":
            collector.add_text("\n")
            continue

        text = normalize_text(element_text(element))

        # Page title "Тип.Метод (Type.Method)": the caller names pages after the TOC
        if _has_css_class(element, CLASS_PAGE_TITLE):
            continue

        if _has_css_class(element, CLASS_HEADING):
            open_block(None)
            page.blocks.append(ParsedBlock(title="name", block_type="name", content=text))
            continue

        if _has_css_class(element, CLASS_OWNER):
            open_block(None)
            page.blocks.append(ParsedBlock(title="owner", block_type="owner", content=text))
            continue

        # Banners "Доступен, начиная с версии X" / "Не рекомендуется использовать..."
        # precede the first chapter; inside a chapter they are noise and are dropped
        banner_type = _banner_type(element)
        if banner_type is not None:
            if collector.block is None:
                open_block(None)
                if text:
                    page.blocks.append(ParsedBlock(title=banner_type, block_type=banner_type, content=text))
            continue

        if _has_css_class(element, CLASS_RUBRIC):
            if collector.block is None:
                open_block(ParsedBlock(title="Description", block_type="description"))
            collector.start_item(text)
            continue

        if not text:
            # Empty element: block-level ones still separate lines
            if name in _BLOCK_LEVEL_TAGS:
                collector.add_text("\n")
            continue

        block = _detect_block_title(element, text)
        if block is not None:
            open_block(block)
            continue

        collector.add_text(element_text(element))

    close_block()

    # A page without chapters (catalog page, query table field) is all description
    if all(b.block_type in _META_BLOCK_TYPES for b in page.blocks):
        for block in page.blocks:
            if block.block_type == "intro":
                block.block_type = "description"
                block.title = "Description"

    return page


def _banner_type(element: Tag) -> str | None:  # type: ignore[name-defined]
    """Block type of a metadata banner div, None for ordinary elements."""
    if _has_css_class(element, CLASS_SINCE):
        return "since"
    css_class = element.get("class", [])
    classes = css_class if isinstance(css_class, list) else str(css_class).split()
    if any(cls.endswith(BANNER_CLASS_SUFFIX) for cls in classes):
        return "deprecated"
    return None


def element_text(element: Tag) -> str:  # type: ignore[name-defined]
    """Extract text from an element preserving line structure.

    ``<br>`` and block-level elements become line breaks, list items get a
    ``- `` prefix, tables are rendered row by row with ``|`` separators
    (a single-cell table, used by the help for code samples, is returned as-is).
    Inline elements (``a``, ``span``, ``font``...) are concatenated without
    separators, exactly as the browser renders them.
    """
    parts: list[str] = []
    _collect_text(element, parts)
    return "".join(parts)


def _collect_text(node, parts: list[str]) -> None:
    if isinstance(node, NavigableString):
        if not isinstance(node, Comment):
            parts.append(str(node))
        return
    if not isinstance(node, Tag):
        return

    name = node.name.lower()
    if name in _SKIPPED_TAGS:
        return
    if name == "br":
        parts.append("\n")
        return
    if name == "pre":
        parts.append("\n" + VERBATIM_START + node.get_text() + VERBATIM_END + "\n")
        return
    if name in ("ul", "ol"):
        parts.append("\n")
        for li in node.find_all("li", recursive=False):
            item_parts: list[str] = []
            for child in li.children:
                _collect_text(child, item_parts)
            parts.append("- " + normalize_text("".join(item_parts)).replace("\n", " ") + "\n")
        return
    if name == "table":
        parts.append("\n" + _parse_table(node) + "\n")
        return

    is_block = name in _BLOCK_LEVEL_TAGS or name == "li"
    if is_block:
        parts.append("\n")
    for child in node.children:
        _collect_text(child, parts)
    if is_block:
        parts.append("\n")


def normalize_text(text: str) -> str:
    """Collapse whitespace: NBSP to space, runs of spaces to one, no blank lines.

    Verbatim regions (``<pre>`` and code samples) marked with VERBATIM_START /
    VERBATIM_END keep their indentation; only trailing spaces are removed.
    """
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\r", "")
    lines: list[str] = []
    verbatim = False
    for chunk in re.split(f"([{VERBATIM_START}{VERBATIM_END}])", text):
        if chunk == VERBATIM_START:
            verbatim = True
            continue
        if chunk == VERBATIM_END:
            verbatim = False
            continue
        for line in chunk.split("\n"):
            if verbatim:
                lines.append(line.rstrip())
            else:
                lines.append(re.sub(r"[ \t\f\v]+", " ", line).strip())
    return "\n".join(line for line in lines if line)


def _detect_block_title(element: Tag, text: str) -> ParsedBlock | None:  # type: ignore[name-defined]
    """Detect if an element is a block title and return the new (empty) block.

    A title may carry a value after the colon ("Вариант синтаксиса: По имени");
    the value becomes the initial content of the block.
    """
    key, value = _split_title(text)

    if _has_css_class(element, CLASS_CHAPTER):
        return _make_block(text, BLOCK_TITLES.get(key, "unknown"), value)

    # Check heading tags
    if element.name in ("h1", "h2", "h3", "h4"):
        return _make_block(text, BLOCK_TITLES.get(key, "unknown"), value)

    if element.name == "p":
        css_class = element.get("class", [])
        class_str = " ".join(css_class) if isinstance(css_class, list) else str(css_class)
        if "head" in class_str or "title" in class_str:
            return _make_block(text, BLOCK_TITLES.get(key, "unknown"), value)

    # Check bold text that matches known block titles
    if element.name in ("p", "div"):
        bold = element.find(["b", "strong"])
        if bold and bold.get_text(strip=True) == text:
            block_type = BLOCK_TITLES.get(key)
            if block_type is not None:
                return _make_block(text, block_type, value)

    return None


def _split_title(text: str) -> tuple[str, str]:
    """Split "Заголовок: значение" into ("Заголовок", "значение")."""
    if ":" in text:
        key, value = text.split(":", 1)
        return key.strip(), value.strip()
    return text.strip(), ""


def _make_block(title: str, block_type: str, value: str) -> ParsedBlock:
    block = ParsedBlock(title=title, block_type=block_type)
    if value and block_type == "variant":
        block.content = value
    return block


def _has_css_class(element: Tag, cls: str) -> bool:  # type: ignore[name-defined]
    """Check if an element has a specific CSS class."""
    css_class = element.get("class", [])
    if isinstance(css_class, list):
        return cls in css_class
    return cls in str(css_class)


def _parse_table(table: Tag) -> str:  # type: ignore[name-defined]
    """Convert an HTML table to a simple text representation."""
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells: list[str] = []
        for td in tr.find_all(["td", "th"]):
            cell_parts: list[str] = []
            for child in td.children:
                _collect_text(child, cell_parts)
            cells.append(_normalize_cell("".join(cell_parts)))
        if cells:
            rows.append(cells)

    # A code sample is a single-cell table: keep its lines and indentation
    if len(rows) == 1 and len(rows[0]) == 1:
        return VERBATIM_START + rows[0][0] + VERBATIM_END

    return "\n".join(" | ".join(cell.replace("\n", " ") for cell in row) for row in rows)


def _normalize_cell(text: str) -> str:
    """Normalize a table cell keeping the indentation of code samples."""
    text = text.replace("\xa0", " ").replace("\r", "")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line.strip())
