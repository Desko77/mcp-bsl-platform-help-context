"""Parser for method documentation pages."""

from __future__ import annotations

import re

from ..models import MethodInfo, ParameterInfo, ReturnValueInfo, SignatureInfo
from .base import PageParser
from .html_handler import ParsedPage


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
        info.description = page.get_block_content("description")

        # Syntax
        info.syntax = page.get_block_content("syntax")

        # Parameters
        params_content = page.get_block_content("parameters")
        if params_content:
            info.signatures = [
                SignatureInfo(
                    name=info.name_ru,
                    parameters=_parse_parameters(params_content),
                    description="",
                )
            ]

        # Return value
        rv_content = page.get_block_content("return_value")
        if rv_content:
            info.return_value = ReturnValueInfo(description=rv_content)

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


def _parse_parameters(text: str) -> list[ParameterInfo]:
    """Parse parameter descriptions from text."""
    params: list[ParameterInfo] = []
    lines = text.strip().split("\n")

    current_name = ""
    current_desc_parts: list[str] = []
    current_type = ""
    current_required = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line starts a new parameter (e.g., "ParamName - description" or "ParamName | type")
        param_match = re.match(r"^<(.+?)>\s*[-–]\s*(.*)", line)
        if param_match:
            # Save previous parameter
            if current_name:
                params.append(
                    ParameterInfo(
                        name=current_name,
                        type=current_type,
                        description="\n".join(current_desc_parts).strip(),
                        required=current_required,
                    )
                )

            current_name = param_match.group(1).strip()
            current_desc_parts = [param_match.group(2).strip()] if param_match.group(2) else []
            current_type = ""
            current_required = False
        else:
            # Try simple "Name - Description" format
            simple_match = re.match(r"^(\w+)\s*[-–]\s*(.*)", line)
            if simple_match and not current_name:
                current_name = simple_match.group(1).strip()
                current_desc_parts = [simple_match.group(2).strip()] if simple_match.group(2) else []
            elif current_name:
                current_desc_parts.append(line)

    # Save last parameter
    if current_name:
        params.append(
            ParameterInfo(
                name=current_name,
                type=current_type,
                description="\n".join(current_desc_parts).strip(),
                required=current_required,
            )
        )

    return params
