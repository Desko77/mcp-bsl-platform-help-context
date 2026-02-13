"""Tests for search indexes."""

from mcp_bsl_context.domain.entities import MethodDefinition
from mcp_bsl_context.infrastructure.search.indexes import HashIndex, StartWithIndex


class TestHashIndex:
    def test_exact_lookup(self):
        idx = HashIndex[MethodDefinition]()
        items = [
            MethodDefinition(name="Найти", description="find"),
            MethodDefinition(name="Добавить", description="add"),
        ]
        idx.load(items, lambda m: m.name)

        result = idx.get("Найти")
        assert len(result) == 1
        assert result[0].name == "Найти"

    def test_case_insensitive(self):
        idx = HashIndex[MethodDefinition]()
        items = [MethodDefinition(name="FindByRef", description="")]
        idx.load(items, lambda m: m.name)

        result = idx.get("findbyref")
        assert len(result) == 1
        assert result[0].name == "FindByRef"

    def test_not_found(self):
        idx = HashIndex[MethodDefinition]()
        idx.load([], lambda m: m.name)
        assert idx.get("anything") == []

    def test_size(self):
        idx = HashIndex[MethodDefinition]()
        items = [
            MethodDefinition(name="A", description=""),
            MethodDefinition(name="B", description=""),
        ]
        idx.load(items, lambda m: m.name)
        assert idx.size == 2
        assert idx.is_empty() is False


class TestStartWithIndex:
    def test_prefix_search(self):
        idx = StartWithIndex[MethodDefinition]()
        items = [
            MethodDefinition(name="НайтиПоСсылке", description=""),
            MethodDefinition(name="НайтиПоКоду", description=""),
            MethodDefinition(name="НайтиПоНаименованию", description=""),
            MethodDefinition(name="Добавить", description=""),
        ]
        idx.load(items, lambda m: m.name)

        result = idx.get("Найти")
        assert len(result) == 3
        names = {r.name for r in result}
        assert "НайтиПоСсылке" in names
        assert "НайтиПоКоду" in names
        assert "НайтиПоНаименованию" in names

    def test_case_insensitive_prefix(self):
        idx = StartWithIndex[MethodDefinition]()
        items = [MethodDefinition(name="FindByRef", description="")]
        idx.load(items, lambda m: m.name)

        result = idx.get("find")
        assert len(result) == 1

    def test_empty_prefix(self):
        idx = StartWithIndex[MethodDefinition]()
        items = [
            MethodDefinition(name="A", description=""),
            MethodDefinition(name="B", description=""),
        ]
        idx.load(items, lambda m: m.name)
        result = idx.get("")
        assert len(result) == 2

    def test_no_match(self):
        idx = StartWithIndex[MethodDefinition]()
        items = [MethodDefinition(name="Abc", description="")]
        idx.load(items, lambda m: m.name)
        assert idx.get("xyz") == []
