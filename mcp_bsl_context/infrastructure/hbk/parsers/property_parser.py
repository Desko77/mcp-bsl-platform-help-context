"""Parser for property documentation pages."""

from __future__ import annotations

import re

from ..models import PropertyInfo
from .base import PageParser
from .html_handler import ParsedPage
from .params import split_type_prefix


class PropertyPageParser(PageParser):
    """Parses property documentation HTML pages into PropertyInfo."""

    def _build_result(self, page: ParsedPage) -> PropertyInfo:
        info = PropertyInfo()

        # Name
        name_content = page.get_block_content("name")
        if name_content:
            names = _parse_bilingual_name(name_content)
            info.name_ru = names[0]
            info.name_en = names[1] if len(names) > 1 else ""
        elif page.title:
            info.name_ru = page.title

        # Description starts with the type line "Тип: Строка." followed by the text
        property_type, description = split_type_prefix(page.get_block_content("description"))
        deprecated = [block.content for block in page.get_blocks("deprecated") if block.content]
        info.description = "\n".join(deprecated + ([description] if description else []))
        info.property_type = property_type

        # Type (explicit value block wins over the description prefix)
        value_content = page.get_block_content("value")
        if value_content:
            info.property_type = value_content

        # Read-only marker: "Использование: Только чтение."
        access_content = page.get_block_content("usage") or page.get_block_content("availability")
        if access_content:
            lower = access_content.lower()
            info.is_read_only = "только чтение" in lower or "read only" in lower or "read-only" in lower

        return info


def _parse_bilingual_name(text: str) -> list[str]:
    if " / " in text:
        return [p.strip() for p in text.split(" / ", 1)]
    match = re.match(r"(.+?)\s*\((.+?)\)", text)
    if match:
        return [match.group(1).strip(), match.group(2).strip()]
    return [text.strip()]
