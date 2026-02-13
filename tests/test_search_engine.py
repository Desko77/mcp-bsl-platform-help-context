"""Tests for the search engine."""

import threading

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)
from mcp_bsl_context.domain.enums import ApiType
from mcp_bsl_context.domain.value_objects import SearchQuery
from mcp_bsl_context.infrastructure.search.engine import SimpleSearchEngine


class FakeStorage:
    """Fake storage for testing the search engine."""

    def __init__(self, methods, properties, types):
        self.methods = methods
        self.properties = properties
        self.types = types
        self._loaded = True
        self._lock = threading.RLock()

    def ensure_loaded(self):
        pass


class TestSimpleSearchEngine:
    def _make_engine(self, methods=None, properties=None, types=None):
        storage = FakeStorage(
            methods=methods or [],
            properties=properties or [],
            types=types or [],
        )
        return SimpleSearchEngine(storage)

    def test_search_methods_by_prefix(self, sample_methods):
        engine = self._make_engine(methods=sample_methods)
        results = engine.search(SearchQuery(query="Найти"))
        names = [r.name for r in results]
        assert "НайтиПоСсылке" in names
        assert "НайтиПоКоду" in names
        assert "НайтиПоНаименованию" in names

    def test_search_with_type_filter(self, sample_methods, sample_properties):
        engine = self._make_engine(methods=sample_methods, properties=sample_properties)
        results = engine.search(SearchQuery(query="Текущая", type=ApiType.PROPERTY))
        assert all(isinstance(r, PropertyDefinition) for r in results)

    def test_search_with_limit(self, sample_methods):
        engine = self._make_engine(methods=sample_methods)
        results = engine.search(SearchQuery(query="Найти", limit=1))
        assert len(results) <= 1

    def test_find_type(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type("ТаблицаЗначений")
        assert result is not None
        assert result.name == "ТаблицаЗначений"

    def test_find_type_case_insensitive(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type("таблицазначений")
        assert result is not None

    def test_find_type_not_found(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type("НесуществующийТип")
        assert result is None

    def test_find_method(self, sample_methods):
        engine = self._make_engine(methods=sample_methods)
        result = engine.find_method("Сообщить")
        assert result is not None
        assert result.name == "Сообщить"

    def test_find_property(self, sample_properties):
        engine = self._make_engine(properties=sample_properties)
        result = engine.find_property("ТекущаяДата")
        assert result is not None

    def test_find_type_member(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type_member("ТаблицаЗначений", "Добавить")
        assert result is not None
        assert result.name == "Добавить"

    def test_find_type_member_property(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type_member("ТаблицаЗначений", "Колонки")
        assert result is not None
        assert isinstance(result, PropertyDefinition)

    def test_find_type_member_not_found(self, sample_types):
        engine = self._make_engine(types=sample_types)
        result = engine.find_type_member("ТаблицаЗначений", "Неизвестный")
        assert result is None

    def test_empty_search(self):
        engine = self._make_engine()
        results = engine.search(SearchQuery(query="anything"))
        assert results == []

    def test_compound_type_search(self, sample_types):
        engine = self._make_engine(types=sample_types)
        results = engine.search(SearchQuery(query="Справочник Объект"))
        names = [r.name for r in results]
        assert "СправочникОбъект" in names

    def test_word_based_search(self, sample_methods):
        engine = self._make_engine(methods=sample_methods)
        results = engine.search(SearchQuery(query="Ссылке"))
        names = [r.name for r in results]
        assert "НайтиПоСсылке" in names
