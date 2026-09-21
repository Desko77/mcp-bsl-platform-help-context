"""Parser for constructor documentation pages."""

from __future__ import annotations

from ..models import SignatureInfo
from .base import PageParser, page_description
from .html_handler import ParsedPage
from .params import parse_signatures


class ConstructorPageParser(PageParser):
    """Parses constructor documentation HTML pages into SignatureInfo.

    A constructor page describes one constructor variant ("По умолчанию",
    "По количеству элементов"...): its syntax line ``Новый Тип(<Параметр>)``,
    parameters and description.
    """

    def _build_result(self, page: ParsedPage) -> SignatureInfo:
        name = ""
        name_content = page.get_block_content("name")
        if name_content:
            name = name_content.split("/")[0].strip()
        elif page.title:
            name = page.title

        signatures = parse_signatures(page, name)
        info = signatures[0] if signatures else SignatureInfo()
        info.name = name
        info.description = page_description(page)

        return info
