"""Tests for HBK page tree visitor: classification, subcatalog detection, traversal."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock

from mcp_bsl_context.infrastructure.hbk.content_reader import HbkContext
from mcp_bsl_context.infrastructure.hbk.models import Page
from mcp_bsl_context.infrastructure.hbk.pages_visitor import (
    PageType,
    PlatformContextPagesVisitor,
)
from mcp_bsl_context.infrastructure.hbk.toc.toc import Toc


def make_page(
    id: int = 0,
    name_ru: str = "",
    name_en: str = "",
    path: str = "",
    children: list[Page] | None = None,
) -> Page:
    page = Page(id=id, name_ru=name_ru, name_en=name_en, path=path)
    if children:
        for child in children:
            child.parent = page
            page.children.append(child)
    return page


def make_hbk_context(root: Page) -> HbkContext:
    """Create a minimal HbkContext with the given page tree and empty ZIP."""
    toc = Toc(root)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    zf = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    return HbkContext(toc, zf)


class TestClassifyPage:
    def _classify(self, page: Page) -> str:
        ctx = make_hbk_context(make_page(id=0))
        visitor = PlatformContextPagesVisitor(ctx)
        return visitor._classify_page(page)

    def test_properties_by_path(self):
        page = make_page(path="/type/properties/prop1.htm")
        assert self._classify(page) == PageType.PROPERTIES

    def test_methods_by_path(self):
        page = make_page(path="/type/methods/method1.htm")
        assert self._classify(page) == PageType.METHODS

    def test_constructors_by_path(self):
        page = make_page(path="/type/ctors/ctor1.htm")
        assert self._classify(page) == PageType.CONSTRUCTORS

    def test_properties_by_name(self):
        page = make_page(name_ru="Свойства")
        assert self._classify(page) == PageType.PROPERTIES

    def test_methods_by_name(self):
        page = make_page(name_ru="Методы")
        assert self._classify(page) == PageType.METHODS

    def test_constructors_by_name(self):
        page = make_page(name_ru="Конструкторы")
        assert self._classify(page) == PageType.CONSTRUCTORS

    def test_unknown(self):
        page = make_page(name_ru="Введение", path="/intro.htm")
        assert self._classify(page) == PageType.UNKNOWN


class TestClassifyRootPage:
    def _classify_root(self, page: Page) -> str:
        ctx = make_hbk_context(make_page(id=0))
        visitor = PlatformContextPagesVisitor(ctx)
        return visitor._classify_root_page(page)

    def test_global_context(self):
        page = make_page(path="/root/Global context/index.htm")
        assert self._classify_root(page) == PageType.GLOBAL_CONTEXT

    def test_enum_catalog_syst_perechisl(self):
        page = make_page(name_ru="Системные перечисления")
        assert self._classify_root(page) == PageType.ENUM_CATALOG

    def test_enum_catalog_syst_nabory(self):
        page = make_page(name_ru="Системные наборы значений")
        assert self._classify_root(page) == PageType.ENUM_CATALOG

    def test_type_catalog(self):
        page = make_page(name_ru="Общие объекты")
        assert self._classify_root(page) == PageType.TYPE_CATALOG


class TestIsSubcatalog:
    def _is_subcatalog(self, page: Page) -> bool:
        ctx = make_hbk_context(make_page(id=0))
        visitor = PlatformContextPagesVisitor(ctx)
        return visitor._is_subcatalog(page)

    def test_leaf_page(self):
        page = make_page(name_ru="Leaf")
        assert not self._is_subcatalog(page)

    def test_page_with_method_children(self):
        """A type page has children classified as methods/properties — not a subcatalog."""
        methods_child = make_page(name_ru="Методы", path="/methods/")
        page = make_page(name_ru="SomeType", children=[methods_child])
        assert not self._is_subcatalog(page)

    def test_page_with_grandchildren(self):
        """A subcatalog has children that themselves have children (i.e., types)."""
        grandchild = make_page(name_ru="Методы", path="/methods/")
        type_child = make_page(name_ru="ТипОбъекта", children=[grandchild])
        page = make_page(name_ru="Подкаталог", children=[type_child])
        assert self._is_subcatalog(page)

    def test_page_with_childless_children(self):
        """Children without their own children and not classified as members → not a subcatalog."""
        child1 = make_page(name_ru="Что-то")
        child2 = make_page(name_ru="Ещё что-то")
        page = make_page(name_ru="Группа", children=[child1, child2])
        assert not self._is_subcatalog(page)


class TestFindGlobalContextPage:
    def _find(self, root: Page) -> Page | None:
        ctx = make_hbk_context(root)
        visitor = PlatformContextPagesVisitor(ctx)
        return visitor._find_global_context_page()

    def test_found_by_path(self):
        gc = make_page(id=2, path="/docs/Global context/index.htm")
        root = make_page(id=1, children=[gc])

        result = self._find(root)
        assert result is not None
        assert result.id == 2

    def test_found_by_name_en(self):
        gc = make_page(id=3, name_en="Global context")
        root = make_page(id=1, children=[gc])

        result = self._find(root)
        assert result is not None
        assert result.id == 3

    def test_found_by_name_ru(self):
        gc = make_page(id=4, name_ru="Глобальный контекст")
        root = make_page(id=1, children=[gc])

        result = self._find(root)
        assert result is not None
        assert result.id == 4

    def test_not_found(self):
        child = make_page(id=2, name_ru="Общие объекты")
        root = make_page(id=1, children=[child])

        result = self._find(root)
        assert result is None


class TestVisitTypeCatalog:
    def test_recurse_into_subcatalog(self):
        """Subcatalogs (e.g., grouped categories) are recursed into."""
        # Build: catalog -> subcatalog -> type_page (with methods child)
        method_page = make_page(id=10, name_ru="Добавить", path="/method.htm")
        methods_section = make_page(
            id=5, name_ru="Методы", path="/methods/", children=[method_page]
        )
        type_page = make_page(
            id=3, name_ru="СписокЗначений", path="/list.htm", children=[methods_section]
        )
        subcatalog = make_page(id=2, name_ru="Подгруппа", children=[type_page])
        catalog = make_page(id=1, name_ru="Каталог", children=[subcatalog])

        # Create context with proper HTML for the type page
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "list.htm",
                "<html><body><h2>Описание</h2><p>Коллекция</p></body></html>",
            )
            zf.writestr(
                "method.htm",
                "<html><body><h2>Описание</h2><p>Добавляет элемент</p></body></html>",
            )
        zip_data = buf.getvalue()
        zf = zipfile.ZipFile(io.BytesIO(zip_data))
        toc = Toc(catalog)
        ctx = HbkContext(toc, zf)
        visitor = PlatformContextPagesVisitor(ctx)

        types = list(visitor._visit_type_catalog(catalog))

        assert len(types) == 1
        assert types[0].name_ru == "СписокЗначений"

    def test_direct_type_children(self):
        """Types directly under catalog (no subcatalog) are parsed."""
        methods_section = make_page(id=5, name_ru="Методы", path="/methods/")
        type_page = make_page(
            id=2, name_ru="Массив", path="/array.htm", children=[methods_section]
        )
        catalog = make_page(id=1, name_ru="Каталог", children=[type_page])

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "array.htm",
                "<html><body><h2>Описание</h2><p>Массив значений</p></body></html>",
            )
        zf_obj = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
        toc = Toc(catalog)
        ctx = HbkContext(toc, zf_obj)
        visitor = PlatformContextPagesVisitor(ctx)

        types = list(visitor._visit_type_catalog(catalog))

        assert len(types) == 1
        assert types[0].name_ru == "Массив"
