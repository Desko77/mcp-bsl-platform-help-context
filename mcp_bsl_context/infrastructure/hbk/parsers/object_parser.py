"""Parser for object/type documentation pages."""

from __future__ import annotations

import re

from ..models import ObjectInfo
from .base import PageParser
from .html_handler import ParsedPage


class ObjectPageParser(PageParser):
    """Parses type/object documentation HTML pages into ObjectInfo."""

    def _build_result(self, page: ParsedPage) -> ObjectInfo:
        info = ObjectInfo()

        # Name
        name_content = page.get_block_content("name")
        if name_content:
            names = _parse_bilingual_name(name_content)
            info.name_ru = names[0]
            info.name_en = names[1] if len(names) > 1 else ""
        elif page.title:
            info.name_ru = page.title

        # Description
        info.description = page.get_block_content("description")

        return info


def _parse_bilingual_name(text: str) -> list[str]:
    if " / " in text:
        return [p.strip() for p in text.split(" / ", 1)]
    match = re.match(r"(.+?)\s*\((.+?)\)", text)
    if match:
        return [match.group(1).strip(), match.group(2).strip()]
    return [text.strip()]
