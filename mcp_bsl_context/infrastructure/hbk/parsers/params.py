"""Parsing of syntax variants, parameters and typed descriptions.

Shared by the method and constructor page parsers. Understands the layout of
the platform help:

* a parameter rubric ``<Имя> (обязательный)`` / ``<Имя> (необязательный)``,
  including variadic forms ``<Имя1>,...,<ИмяN>``;
* a description starting with a type line ``Тип: Строка, Число.``;
* a trailing ``Значение по умолчанию: Ложь.`` line;
* several syntax variants on one page, each introduced by
  ``Вариант синтаксиса: <название>``.

For pages without rubrics a plain-text fallback (``<Имя> - описание`` or
``Имя - описание`` lines) is used.
"""

from __future__ import annotations

import re

from ..models import ParameterInfo, SignatureInfo
from .html_handler import ParsedBlock, ParsedPage

# <Имя>, <Имя1>,...,<ИмяN>, <<разм0>,...,<размN-1>> followed by an optional
# (обязательный) marker and an optional "- описание" tail
_HEADER_RE = re.compile(
    r"^(?P<name><{1,2}[^<>]+>(?:\s*,\s*\.\.\.\s*,\s*<[^<>]+>{1,2})?)"
    r"\s*(?:\((?P<marker>[^()]*)\))?\s*(?:[-–:]\s*(?P<rest>.*))?$"
)
_SIMPLE_HEADER_RE = re.compile(r"^(?P<name>\w+)\s*[-–]\s*(?P<rest>.*)$")
_TYPE_LINE_RE = re.compile(r"^(?:Тип|Type)\s*:\s*(?P<value>.*)$", re.IGNORECASE)
_DEFAULT_LINE_RE = re.compile(
    r"^(?:Значение по умолчанию|Default value)\s*:\s*(?P<value>.+?)\.?$", re.IGNORECASE
)

_REQUIRED_MARKERS = {"обязательный", "required", "mandatory"}
_OPTIONAL_MARKERS = {"необязательный", "optional"}


def parse_signatures(page: ParsedPage, default_name: str) -> list[SignatureInfo]:
    """Collect syntax variants of a page in document order.

    Every ``Вариант синтаксиса`` block starts a new signature named after the
    variant; a ``Синтаксис`` block without a preceding variant starts an
    unnamed signature (``default_name``). ``Параметры`` and ``Описание
    варианта метода`` blocks are attached to the current signature.
    """
    signatures: list[SignatureInfo] = []
    current: SignatureInfo | None = None

    def start(name: str) -> SignatureInfo:
        signature = SignatureInfo(name=name)
        signatures.append(signature)
        return signature

    for block in page.blocks:
        if block.block_type == "variant":
            current = start(block.content or default_name)
        elif block.block_type == "syntax":
            if current is None or current.syntax:
                current = start(default_name)
            current.syntax = block.content
        elif block.block_type == "parameters":
            if current is None:
                current = start(default_name)
            current.parameters = parse_parameters(block)
        elif block.block_type == "variant_description":
            if current is not None:
                current.description = block.content

    return signatures


def parse_parameters(block: ParsedBlock | None) -> list[ParameterInfo]:
    """Parse the parameters block into ParameterInfo list."""
    if block is None:
        return []
    if block.items:
        return [_build_parameter(item.title, item.content) for item in block.items]
    return _parse_parameters_text(block.content)


def split_type_prefix(text: str) -> tuple[str, str]:
    """Split a typed description into (type, description).

    ``"Тип: Строка, Число.\\nОписание"`` -> ``("Строка, Число", "Описание")``.
    Text without a type line is returned as ``("", text)``.
    """
    text = text.strip()
    if not text:
        return "", ""
    first, _, remainder = text.partition("\n")
    match = _TYPE_LINE_RE.match(first.strip())
    if match is None:
        return "", text

    value = match.group("value").strip()
    same_line_rest = ""
    if ". " in value:
        value, same_line_rest = value.split(". ", 1)
    type_name = value.strip().rstrip(".").strip()

    rest_lines = [same_line_rest.strip(), remainder.strip()]
    description = "\n".join(line for line in rest_lines if line)
    return type_name, description


def _build_parameter(header: str, body: str) -> ParameterInfo:
    header = header.strip()
    match = _HEADER_RE.match(header) or _SIMPLE_HEADER_RE.match(header)
    if match:
        name = _clean_name(match.group("name"))
        required = _required_from_marker(match.groupdict().get("marker"))
        rest = (match.group("rest") or "").strip()
    else:
        name = _clean_name(header)
        required = None
        rest = ""

    # The type line opens the body ("Тип: Строка.") or, in the text fallback,
    # the header tail ("<Имя> - Тип: Строка. Описание")
    type_name, description = split_type_prefix(body)
    if rest:
        if not type_name:
            type_name, rest = split_type_prefix(rest)
        description = "\n".join(part for part in (rest, description) if part)
    default_value, description = _extract_default_value(description)

    return ParameterInfo(
        name=name,
        type=type_name,
        description=description,
        required=required,
        default_value=default_value,
    )


def _parse_parameters_text(text: str) -> list[ParameterInfo]:
    """Fallback for pages without rubrics: one parameter per header line."""
    params: list[ParameterInfo] = []
    header: str | None = None
    lines: list[str] = []

    def flush() -> None:
        if header is not None:
            params.append(_build_parameter(header, "\n".join(lines)))

    for raw_line in text.strip().split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if _HEADER_RE.match(line) or _SIMPLE_HEADER_RE.match(line):
            flush()
            header = line
            lines = []
        elif header is not None:
            lines.append(line)

    flush()
    return params


def _clean_name(raw: str) -> str:
    """``<Имя>`` -> ``Имя``, ``<Имя1>,...,<ИмяN>`` -> ``Имя1,...,ИмяN``."""
    name = re.sub(r"[<>]", "", raw)
    return re.sub(r"\s+", "", name) if "..." in name else name.strip()


def _required_from_marker(marker: str | None) -> bool | None:
    if not marker:
        return None
    normalized = marker.strip().lower()
    if normalized in _REQUIRED_MARKERS:
        return True
    if normalized in _OPTIONAL_MARKERS:
        return False
    return None


def _extract_default_value(description: str) -> tuple[str | None, str]:
    """Pull ``Значение по умолчанию: X`` lines out of the description."""
    values: list[str] = []
    kept: list[str] = []
    for line in description.split("\n"):
        match = _DEFAULT_LINE_RE.match(line.strip())
        if match:
            value = match.group("value").strip()
            if value and value not in values:
                values.append(value)
        else:
            kept.append(line)
    default_value = "; ".join(values) if values else None
    return default_value, "\n".join(kept).strip()
