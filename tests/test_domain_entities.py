"""Tests for domain entities."""

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)
from mcp_bsl_context.domain.enums import ApiType
from mcp_bsl_context.domain.value_objects import SearchOptions, SearchQuery


class TestEntities:
    def test_method_definition_frozen(self):
        m = MethodDefinition(name="Test", description="desc")
        assert m.name == "Test"
        assert m.description == "desc"
        assert m.return_type == ""
        assert m.signatures == []

    def test_property_definition(self):
        p = PropertyDefinition(
            name="Prop", description="desc", property_type="String", is_read_only=True
        )
        assert p.is_read_only is True
        assert p.property_type == "String"

    def test_platform_type_has_methods(self):
        t = PlatformTypeDefinition(
            name="Type",
            description="desc",
            methods=[MethodDefinition(name="M", description="")],
        )
        assert t.has_methods() is True
        assert t.has_properties() is False

    def test_signature_with_parameters(self):
        s = Signature(
            name="Func",
            parameters=[
                ParameterDefinition(name="a", type="int", description="param a", required=True),
                ParameterDefinition(name="b", type="str", description="param b"),
            ],
            description="A function",
        )
        assert len(s.parameters) == 2
        assert s.parameters[0].required is True
        assert s.parameters[1].required is False


class TestApiType:
    def test_from_string_russian(self):
        assert ApiType.from_string("метод") == ApiType.METHOD
        assert ApiType.from_string("свойство") == ApiType.PROPERTY
        assert ApiType.from_string("тип") == ApiType.TYPE

    def test_from_string_english(self):
        assert ApiType.from_string("method") == ApiType.METHOD
        assert ApiType.from_string("property") == ApiType.PROPERTY
        assert ApiType.from_string("type") == ApiType.TYPE

    def test_from_string_case_insensitive(self):
        assert ApiType.from_string("METHOD") == ApiType.METHOD
        assert ApiType.from_string("Property") == ApiType.PROPERTY

    def test_from_string_unknown(self):
        assert ApiType.from_string("unknown") is None

    def test_display_name(self):
        assert ApiType.METHOD.get_display_name() == "Метод"
        assert ApiType.TYPE.get_display_name() == "Тип"


class TestSearchQuery:
    def test_defaults(self):
        q = SearchQuery(query="test")
        assert q.limit == 10
        assert q.type is None
        assert q.options.case_sensitive is False

    def test_custom_options(self):
        q = SearchQuery(
            query="test",
            type=ApiType.METHOD,
            limit=5,
            options=SearchOptions(exact_match=True),
        )
        assert q.type == ApiType.METHOD
        assert q.limit == 5
        assert q.options.exact_match is True
