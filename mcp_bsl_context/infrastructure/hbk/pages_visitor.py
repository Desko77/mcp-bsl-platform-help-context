"""Visitor for HBK page tree — classifies and traverses pages."""

from __future__ import annotations

import logging
from typing import Iterator

from .content_reader import HbkContext
from .models import (
    EnumInfo,
    MethodInfo,
    ObjectInfo,
    PropertyInfo,
    SignatureInfo,
    Page,
)
from .parsers.pages_parser import PlatformContextPagesParser

logger = logging.getLogger(__name__)

# Page classification constants
GLOBAL_CONTEXT_MARKER = "Global context"
ENUM_CATALOG_TITLES = {"Системные наборы значений", "Системные перечисления"}
PROPERTIES_PATH_MARKER = "/properties/"
METHODS_PATH_MARKER = "/methods/"
CONSTRUCTORS_PATH_MARKER = "/ctors/"


class PageType:
    GLOBAL_CONTEXT = "global_context"
    ENUM_CATALOG = "enum_catalog"
    TYPE_CATALOG = "type_catalog"
    PROPERTIES = "properties"
    METHODS = "methods"
    CONSTRUCTORS = "constructors"
    UNKNOWN = "unknown"


class PlatformContextPagesVisitor:
    """Traverses the page tree and extracts platform context data."""

    def __init__(self, ctx: HbkContext) -> None:
        self._ctx = ctx
        self._parser = PlatformContextPagesParser()

    def collect_global_methods(self) -> list[MethodInfo]:
        """Collect global context methods."""
        methods: list[MethodInfo] = []
        global_page = self._find_global_context_page()
        if global_page is None:
            logger.warning("Global context page not found")
            return methods

        for child in global_page.children:
            page_type = self._classify_page(child)
            if page_type == PageType.METHODS:
                methods.extend(self._visit_methods_page(child))
        return methods

    def collect_global_properties(self) -> list[PropertyInfo]:
        """Collect global context properties."""
        properties: list[PropertyInfo] = []
        global_page = self._find_global_context_page()
        if global_page is None:
            return properties

        for child in global_page.children:
            page_type = self._classify_page(child)
            if page_type == PageType.PROPERTIES:
                properties.extend(self._visit_properties_page(child))
        return properties

    def collect_types(self) -> list[ObjectInfo]:
        """Collect all type/object definitions."""
        types: list[ObjectInfo] = []
        root = self._ctx.toc.root

        for child in root.children:
            page_type = self._classify_root_page(child)
            if page_type == PageType.TYPE_CATALOG:
                types.extend(self._visit_type_catalog(child))
        return types

    def collect_enums(self) -> list[EnumInfo]:
        """Collect all enum definitions."""
        enums: list[EnumInfo] = []
        root = self._ctx.toc.root

        for child in root.children:
            page_type = self._classify_root_page(child)
            if page_type == PageType.ENUM_CATALOG:
                enums.extend(self._visit_enum_catalog(child))
        return enums

    def _find_global_context_page(self) -> Page | None:
        """Find the global context page in the tree."""
        for page in self._ctx.toc.all_pages:
            if page.path and GLOBAL_CONTEXT_MARKER in page.path:
                return page
            if page.name_en and "Global context" in page.name_en:
                return page
            if page.name_ru and "Глобальный контекст" in page.name_ru:
                return page
        return None

    def _classify_root_page(self, page: Page) -> str:
        """Classify a root-level page."""
        if page.path and GLOBAL_CONTEXT_MARKER in page.path:
            return PageType.GLOBAL_CONTEXT
        if page.name_ru in ENUM_CATALOG_TITLES:
            return PageType.ENUM_CATALOG
        return PageType.TYPE_CATALOG

    def _classify_page(self, page: Page) -> str:
        """Classify a page by its path or name."""
        path = (page.path or "").lower()
        name = (page.name_ru or "").lower()

        if PROPERTIES_PATH_MARKER in path or "свойства" in name:
            return PageType.PROPERTIES
        if METHODS_PATH_MARKER in path or "методы" in name:
            return PageType.METHODS
        if CONSTRUCTORS_PATH_MARKER in path or "конструкторы" in name:
            return PageType.CONSTRUCTORS
        return PageType.UNKNOWN

    def _visit_methods_page(self, page: Page) -> Iterator[MethodInfo]:
        """Visit a methods container page and parse each child method."""
        for child in page.children:
            html = self._ctx.read_page(child.path)
            if html:
                try:
                    method = self._parser.parse_method(html)
                    if not method.name_ru and child.name_ru:
                        method.name_ru = child.name_ru
                    if not method.name_en and child.name_en:
                        method.name_en = child.name_en
                    yield method
                except Exception as e:
                    logger.warning("Failed to parse method page '%s': %s", child.path, e)

    def _visit_properties_page(self, page: Page) -> Iterator[PropertyInfo]:
        """Visit a properties container page and parse each child property."""
        for child in page.children:
            html = self._ctx.read_page(child.path)
            if html:
                try:
                    prop = self._parser.parse_property(html)
                    if not prop.name_ru and child.name_ru:
                        prop.name_ru = child.name_ru
                    if not prop.name_en and child.name_en:
                        prop.name_en = child.name_en
                    yield prop
                except Exception as e:
                    logger.warning("Failed to parse property page '%s': %s", child.path, e)

    def _visit_constructors_page(self, page: Page) -> list[SignatureInfo]:
        """Visit constructors page and parse constructor signatures."""
        constructors: list[SignatureInfo] = []
        for child in page.children:
            html = self._ctx.read_page(child.path)
            if html:
                try:
                    ctor = self._parser.parse_constructor(html)
                    constructors.append(ctor)
                except Exception as e:
                    logger.warning("Failed to parse constructor page '%s': %s", child.path, e)
        return constructors

    def _visit_type_catalog(self, page: Page) -> Iterator[ObjectInfo]:
        """Visit a type catalog and parse each type with its members."""
        for type_page in page.children:
            html = self._ctx.read_page(type_page.path)
            if html is None:
                continue

            try:
                obj = self._parser.parse_object(html)
                if not obj.name_ru and type_page.name_ru:
                    obj.name_ru = type_page.name_ru
                if not obj.name_en and type_page.name_en:
                    obj.name_en = type_page.name_en

                # Parse members from child pages
                for child in type_page.children:
                    child_type = self._classify_page(child)
                    if child_type == PageType.METHODS:
                        obj.methods.extend(self._visit_methods_page(child))
                    elif child_type == PageType.PROPERTIES:
                        obj.properties.extend(self._visit_properties_page(child))
                    elif child_type == PageType.CONSTRUCTORS:
                        obj.constructors.extend(self._visit_constructors_page(child))

                yield obj
            except Exception as e:
                logger.warning("Failed to parse type page '%s': %s", type_page.path, e)

    def _visit_enum_catalog(self, page: Page) -> Iterator[EnumInfo]:
        """Visit an enum catalog and parse each enum."""
        for enum_page in page.children:
            html = self._ctx.read_page(enum_page.path)
            if html:
                try:
                    enum = self._parser.parse_enum(html)
                    if not enum.name_ru and enum_page.name_ru:
                        enum.name_ru = enum_page.name_ru
                    if not enum.name_en and enum_page.name_en:
                        enum.name_en = enum_page.name_en

                    # Parse enum values from children
                    for child in enum_page.children:
                        child_html = self._ctx.read_page(child.path)
                        if child_html:
                            try:
                                value = self._parser.parse_enum_value(child_html)
                                enum.values.append(value)
                            except Exception as e:
                                logger.warning("Failed to parse enum value '%s': %s", child.path, e)

                    yield enum
                except Exception as e:
                    logger.warning("Failed to parse enum page '%s': %s", enum_page.path, e)
