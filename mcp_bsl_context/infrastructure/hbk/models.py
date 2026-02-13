"""HBK data models for parsed platform context."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DoubleLanguageString:
    ru: str = ""
    en: str = ""


@dataclass
class Page:
    id: int = 0
    name_ru: str = ""
    name_en: str = ""
    path: str = ""
    children: list[Page] = field(default_factory=list)
    parent: Page | None = None

    def __repr__(self) -> str:
        return f"Page(id={self.id}, name='{self.name_ru}', path='{self.path}', children={len(self.children)})"


@dataclass
class Chunk:
    """Raw TOC chunk parsed from bracket file."""
    id: int = 0
    parent_id: int = 0
    child_ids: list[int] = field(default_factory=list)
    names: list[DoubleLanguageString] = field(default_factory=list)
    html_path: str = ""


@dataclass
class ParameterInfo:
    name: str = ""
    type: str = ""
    description: str = ""
    required: bool = False
    default_value: str | None = None


@dataclass
class ReturnValueInfo:
    type: str = ""
    description: str = ""


@dataclass
class SignatureInfo:
    name: str = ""
    parameters: list[ParameterInfo] = field(default_factory=list)
    description: str = ""


@dataclass
class MethodInfo:
    name_ru: str = ""
    name_en: str = ""
    description: str = ""
    return_value: ReturnValueInfo | None = None
    signatures: list[SignatureInfo] = field(default_factory=list)
    syntax: str = ""


@dataclass
class PropertyInfo:
    name_ru: str = ""
    name_en: str = ""
    description: str = ""
    property_type: str = ""
    is_read_only: bool = False


@dataclass
class ObjectInfo:
    name_ru: str = ""
    name_en: str = ""
    description: str = ""
    methods: list[MethodInfo] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    constructors: list[SignatureInfo] = field(default_factory=list)


@dataclass
class EnumValueInfo:
    name_ru: str = ""
    name_en: str = ""
    description: str = ""


@dataclass
class EnumInfo:
    name_ru: str = ""
    name_en: str = ""
    description: str = ""
    values: list[EnumValueInfo] = field(default_factory=list)
