"""Parser for method documentation pages."""

from __future__ import annotations

import re

from ..models import MethodInfo, ReturnValueInfo
from .base import PageParser, page_description
from .html_handler import ParsedPage
from .params import parse_signatures, split_type_prefix


class MethodPageParser(PageParser):
    """Parses method documentation HTML pages into MethodInfo."""

    def _build_result(self, page: ParsedPage) -> MethodInfo:
        info = MethodInfo()

        # Name
        name_content = page.get_block_content("name")
        if name_content:
            names = _parse_bilingual_name(name_content)
            info.name_ru = names[0]
            info.name_en = names[1] if len(names) > 1 else ""
        elif page.title:
            info.name_ru = page.title

        # Description
        info.description = page_description(page)

        # Syntax variants with their parameters
        info.signatures = parse_signatures(page, info.name_ru)
        info.syntax = info.signatures[0].syntax if info.signatures else ""

        # Return value: type line "Тип: X." followed by the description
        rv_content = page.get_block_content("return_value")
        if rv_content:
            rv_type, rv_description = split_type_prefix(rv_content)
            info.return_value = ReturnValueInfo(type=rv_type, description=rv_description)

        return info


def _parse_bilingual_name(text: str) -> list[str]:
    """Parse 'RussianName / EnglishName' or 'RussianName (EnglishName)' format."""
    # Try "Name / Name" format
    if " / " in text:
        return [p.strip() for p in text.split(" / ", 1)]
    # Try "Name (Name)" format
    match = re.match(r"(.+?)\s*\((.+?)\)", text)
    if match:
        return [match.group(1).strip(), match.group(2).strip()]
    return [text.strip()]
