"""Tests for DocumentBuilder — entity-to-embedding-text conversion."""

import pytest

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)
from mcp_bsl_context.infrastructure.embeddings.document_builder import (
    DocumentBuilder,
    EmbeddingDocument,
    _make_id,
)


@pytest.fixture
def builder():
    return DocumentBuilder()


class TestMethodDocument:
    def test_global_method(self, builder):
        method = MethodDefinition(
            name="Сообщить",
            description="Выводит сообщение пользователю.",
            return_type="",
        )
        doc = builder.build_from_method(method)
        assert isinstance(doc, EmbeddingDocument)
        assert "Сообщить" in doc.text
        assert "Выводит сообщение" in doc.text
        assert doc.metadata["name"] == "Сообщить"
        assert doc.metadata["api_type"] == "method"
        assert doc.metadata["type_name"] == ""

    def test_type_method_includes_type_prefix(self, builder):
        method = MethodDefinition(
            name="Добавить",
            description="Добавляет строку.",
            return_type="СтрокаТаблицыЗначений",
        )
        doc = builder.build_from_method(method, type_name="ТаблицаЗначений")
        assert "ТаблицаЗначений.Добавить" in doc.text
        assert "Возвращает: СтрокаТаблицыЗначений" in doc.text
        assert doc.metadata["type_name"] == "ТаблицаЗначений"

    def test_method_with_parameters(self, builder):
        method = MethodDefinition(
            name="Найти",
            description="Поиск строки.",
            signatures=[
                Signature(
                    name="Найти",
                    description="",
                    parameters=[
                        ParameterDefinition(
                            name="Значение",
                            type="Произвольный",
                            description="Искомое значение",
                        ),
                        ParameterDefinition(
                            name="Колонки",
                            type="Строка",
                            description="Колонки поиска",
                        ),
                    ],
                )
            ],
        )
        doc = builder.build_from_method(method)
        assert "Параметры: Значение, Колонки" in doc.text

    def test_method_without_description(self, builder):
        method = MethodDefinition(name="Тест", description="")
        doc = builder.build_from_method(method)
        assert doc.text == "Тест"


class TestPropertyDocument:
    def test_global_property(self, builder):
        prop = PropertyDefinition(
            name="ТекущаяДата",
            description="Возвращает текущую дату.",
            property_type="Дата",
        )
        doc = builder.build_from_property(prop)
        assert "ТекущаяДата" in doc.text
        assert "Тип: Дата" in doc.text
        assert doc.metadata["api_type"] == "property"

    def test_read_only_property(self, builder):
        prop = PropertyDefinition(
            name="Ссылка",
            description="Ссылка на объект.",
            is_read_only=True,
        )
        doc = builder.build_from_property(prop, type_name="ДокументОбъект")
        assert "Только чтение" in doc.text
        assert "ДокументОбъект.Ссылка" in doc.text

    def test_property_without_type(self, builder):
        prop = PropertyDefinition(name="Имя", description="Имя элемента.")
        doc = builder.build_from_property(prop)
        assert "Тип:" not in doc.text


class TestTypeDocument:
    def test_type_with_methods_and_properties(self, builder):
        type_def = PlatformTypeDefinition(
            name="ТаблицаЗначений",
            description="Объект для хранения данных.",
            methods=[
                MethodDefinition(name="Добавить", description=""),
                MethodDefinition(name="Удалить", description=""),
            ],
            properties=[
                PropertyDefinition(name="Колонки", description=""),
            ],
        )
        doc = builder.build_from_type(type_def)
        assert "ТаблицаЗначений" in doc.text
        assert "Объект для хранения данных" in doc.text
        assert "Методы: Добавить, Удалить" in doc.text
        assert "Свойства: Колонки" in doc.text
        assert doc.metadata["api_type"] == "type"

    def test_type_truncates_long_member_lists(self, builder):
        methods = [
            MethodDefinition(name=f"Метод{i}", description="")
            for i in range(25)
        ]
        type_def = PlatformTypeDefinition(
            name="БольшойТип", description="", methods=methods
        )
        doc = builder.build_from_type(type_def)
        assert "...и ещё 5" in doc.text

    def test_empty_type(self, builder):
        type_def = PlatformTypeDefinition(name="ПустойТип", description="")
        doc = builder.build_from_type(type_def)
        assert doc.text == "ПустойТип"


class TestBuildAll:
    def test_builds_global_and_type_members(self, builder):
        class FakeStorage:
            methods = [MethodDefinition(name="ГлобМетод", description="")]
            properties = [PropertyDefinition(name="ГлобСвойство", description="")]
            types = [
                PlatformTypeDefinition(
                    name="Тип1",
                    description="",
                    methods=[MethodDefinition(name="ЧленМетод", description="")],
                    properties=[PropertyDefinition(name="ЧленСвойство", description="")],
                )
            ]

        docs = builder.build_all(FakeStorage())
        # 1 global method + 1 global property + 1 type + 1 type method + 1 type property
        assert len(docs) == 5

        names = [d.metadata["name"] for d in docs]
        assert "ГлобМетод" in names
        assert "ГлобСвойство" in names
        assert "Тип1" in names
        assert "ЧленМетод" in names
        assert "ЧленСвойство" in names

    def test_empty_storage(self, builder):
        class EmptyStorage:
            methods = []
            properties = []
            types = []

        docs = builder.build_all(EmptyStorage())
        assert docs == []


class TestBuildText:
    def test_method_text(self, builder):
        method = MethodDefinition(name="Тест", description="Описание")
        text = builder.build_text(method)
        assert "Тест" in text
        assert "Описание" in text

    def test_property_text(self, builder):
        prop = PropertyDefinition(name="Свойство", description="Описание свойства")
        text = builder.build_text(prop)
        assert "Свойство" in text

    def test_type_text(self, builder):
        type_def = PlatformTypeDefinition(name="МойТип", description="Описание типа")
        text = builder.build_text(type_def)
        assert "МойТип" in text


class TestMakeId:
    def test_deterministic(self):
        id1 = _make_id("method", "Test", "Type1")
        id2 = _make_id("method", "Test", "Type1")
        assert id1 == id2

    def test_different_for_different_inputs(self):
        id1 = _make_id("method", "Test", "Type1")
        id2 = _make_id("property", "Test", "Type1")
        assert id1 != id2

    def test_different_with_and_without_type(self):
        id1 = _make_id("method", "Test", None)
        id2 = _make_id("method", "Test", "Type1")
        assert id1 != id2

    def test_returns_valid_uuid_string(self):
        import uuid

        id_str = _make_id("method", "Test", None)
        uuid.UUID(id_str)  # Should not raise


class TestEmbeddingDocumentMetadata:
    def test_metadata_contains_text_field(self, builder):
        method = MethodDefinition(name="Тест", description="Описание")
        doc = builder.build_from_method(method)
        assert "text" in doc.metadata
        assert doc.metadata["text"] == doc.text
