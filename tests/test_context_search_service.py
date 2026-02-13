"""Tests for the ContextSearchService."""

import threading

import pytest

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)
from mcp_bsl_context.domain.exceptions import (
    InvalidSearchQueryException,
    PlatformTypeNotFoundException,
    TypeMemberNotFoundException,
)
from mcp_bsl_context.domain.services import ContextSearchService
from mcp_bsl_context.infrastructure.search.engine import SimpleSearchEngine
from mcp_bsl_context.infrastructure.storage.repository import PlatformRepository


class FakeStorage:
    def __init__(self, methods, properties, types):
        self.methods = methods
        self.properties = properties
        self.types = types
        self._loaded = True
        self._lock = threading.RLock()

    def ensure_loaded(self):
        pass


def _make_service(methods=None, properties=None, types=None):
    storage = FakeStorage(methods or [], properties or [], types or [])
    engine = SimpleSearchEngine(storage)
    repo = PlatformRepository(engine)
    return ContextSearchService(repo)


class TestSearchAll:
    def test_basic_search(self, sample_methods):
        svc = _make_service(methods=sample_methods)
        results = svc.search_all("Найти")
        assert len(results) > 0

    def test_empty_query_raises(self):
        svc = _make_service()
        with pytest.raises(InvalidSearchQueryException):
            svc.search_all("")

    def test_blank_query_raises(self):
        svc = _make_service()
        with pytest.raises(InvalidSearchQueryException):
            svc.search_all("   ")

    def test_limit_clamped(self, sample_methods):
        svc = _make_service(methods=sample_methods)
        results = svc.search_all("Найти", limit=100)
        assert len(results) <= 50

    def test_type_filter(self, sample_methods, sample_properties):
        svc = _make_service(methods=sample_methods, properties=sample_properties)
        results = svc.search_all("Текущая", type_str="property")
        assert all(isinstance(r, PropertyDefinition) for r in results)


class TestGetInfo:
    def test_get_method(self, sample_methods):
        svc = _make_service(methods=sample_methods)
        result = svc.get_info("Сообщить", "method")
        assert result.name == "Сообщить"

    def test_get_type(self, sample_types):
        svc = _make_service(types=sample_types)
        result = svc.get_info("ТаблицаЗначений", "type")
        assert result.name == "ТаблицаЗначений"

    def test_not_found(self, sample_methods):
        svc = _make_service(methods=sample_methods)
        with pytest.raises(PlatformTypeNotFoundException):
            svc.get_info("Несуществующий", "method")

    def test_empty_name_raises(self):
        svc = _make_service()
        with pytest.raises(InvalidSearchQueryException):
            svc.get_info("", "method")

    def test_unknown_type_raises(self):
        svc = _make_service()
        with pytest.raises(InvalidSearchQueryException):
            svc.get_info("Test", "unknown_type")


class TestFindMember:
    def test_find_method_member(self, sample_types):
        svc = _make_service(types=sample_types)
        result = svc.find_member_by_type_and_name("ТаблицаЗначений", "Добавить")
        assert result.name == "Добавить"

    def test_find_property_member(self, sample_types):
        svc = _make_service(types=sample_types)
        result = svc.find_member_by_type_and_name("ТаблицаЗначений", "Колонки")
        assert result.name == "Колонки"

    def test_type_not_found(self, sample_types):
        svc = _make_service(types=sample_types)
        with pytest.raises(PlatformTypeNotFoundException):
            svc.find_member_by_type_and_name("Несуществующий", "Метод")

    def test_member_not_found(self, sample_types):
        svc = _make_service(types=sample_types)
        with pytest.raises(TypeMemberNotFoundException):
            svc.find_member_by_type_and_name("ТаблицаЗначений", "Несуществующий")


class TestFindTypeMembers:
    def test_returns_all_members(self, sample_types):
        svc = _make_service(types=sample_types)
        members = svc.find_type_members("ТаблицаЗначений")
        assert len(members) == 5  # 3 methods + 2 properties

    def test_type_not_found(self, sample_types):
        svc = _make_service(types=sample_types)
        with pytest.raises(PlatformTypeNotFoundException):
            svc.find_type_members("Несуществующий")


class TestFindConstructors:
    def test_returns_constructors(self, sample_types):
        svc = _make_service(types=sample_types)
        ctors = svc.find_constructors("ТаблицаЗначений")
        assert len(ctors) == 1

    def test_empty_constructors(self, sample_types):
        svc = _make_service(types=sample_types)
        ctors = svc.find_constructors("Массив")
        assert len(ctors) == 0
