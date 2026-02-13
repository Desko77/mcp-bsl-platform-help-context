"""Coordinator for page parsers — dispatches to specific parsers by page type."""

from __future__ import annotations

from typing import Any

from ..models import (
    EnumInfo,
    EnumValueInfo,
    MethodInfo,
    ObjectInfo,
    PropertyInfo,
    SignatureInfo,
)
from .constructor_parser import ConstructorPageParser
from .enum_parser import EnumPageParser
from .enum_value_parser import EnumValuePageParser
from .method_parser import MethodPageParser
from .object_parser import ObjectPageParser
from .property_parser import PropertyPageParser


class PlatformContextPagesParser:
    """Dispatches HTML page content to the appropriate parser."""

    def __init__(self) -> None:
        self._method_parser = MethodPageParser()
        self._property_parser = PropertyPageParser()
        self._object_parser = ObjectPageParser()
        self._enum_parser = EnumPageParser()
        self._enum_value_parser = EnumValuePageParser()
        self._constructor_parser = ConstructorPageParser()

    def parse_method(self, html: str) -> MethodInfo:
        return self._method_parser.parse(html)

    def parse_property(self, html: str) -> PropertyInfo:
        return self._property_parser.parse(html)

    def parse_object(self, html: str) -> ObjectInfo:
        return self._object_parser.parse(html)

    def parse_enum(self, html: str) -> EnumInfo:
        return self._enum_parser.parse(html)

    def parse_enum_value(self, html: str) -> EnumValueInfo:
        return self._enum_value_parser.parse(html)

    def parse_constructor(self, html: str) -> SignatureInfo:
        return self._constructor_parser.parse(html)
