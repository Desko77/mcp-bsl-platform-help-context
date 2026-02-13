"""Parser for constructor documentation pages."""

from __future__ import annotations

import re

from ..models import ParameterInfo, SignatureInfo
from .base import PageParser
from .html_handler import ParsedPage


class ConstructorPageParser(PageParser):
    """Parses constructor documentation HTML pages into SignatureInfo."""

    def _build_result(self, page: ParsedPage) -> SignatureInfo:
        info = SignatureInfo()

        name_content = page.get_block_content("name")
        if name_content:
            info.name = name_content.split("/")[0].strip()
        elif page.title:
            info.name = page.title

        # Syntax block
        syntax = page.get_block_content("syntax")
        if syntax:
            info.description = syntax

        # Parameters
        params_content = page.get_block_content("parameters")
        if params_content:
            info.parameters = _parse_parameters(params_content)

        return info


def _parse_parameters(text: str) -> list[ParameterInfo]:
    """Parse parameter descriptions from text."""
    params: list[ParameterInfo] = []
    lines = text.strip().split("\n")

    current_name = ""
    current_desc_parts: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        param_match = re.match(r"^<(.+?)>\s*[-–]\s*(.*)", line)
        if param_match:
            if current_name:
                params.append(
                    ParameterInfo(
                        name=current_name,
                        description="\n".join(current_desc_parts).strip(),
                    )
                )
            current_name = param_match.group(1).strip()
            current_desc_parts = [param_match.group(2).strip()] if param_match.group(2) else []
        else:
            simple_match = re.match(r"^(\w+)\s*[-–]\s*(.*)", line)
            if simple_match and not current_name:
                current_name = simple_match.group(1).strip()
                current_desc_parts = [simple_match.group(2).strip()] if simple_match.group(2) else []
            elif current_name:
                current_desc_parts.append(line)

    if current_name:
        params.append(
            ParameterInfo(
                name=current_name,
                description="\n".join(current_desc_parts).strip(),
            )
        )

    return params
