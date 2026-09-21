"""Tests for the Markdown formatter."""

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)
from mcp_bsl_context.presentation.formatter import MarkdownFormatter


class TestMarkdownFormatter:
    def setup_method(self):
        self.formatter = MarkdownFormatter()

    def test_empty_results(self):
        result = self.formatter.format_search_results([])
        assert "Ничего не найдено" in result

    def test_single_method_result(self):
        method = MethodDefinition(
            name="Найти",
            description="Поиск значения",
            return_type="Произвольный",
        )
        result = self.formatter.format_search_results([method])
        assert "Найти" in result
        assert "Поиск значения" in result

    def test_multiple_results_compact(self):
        methods = [
            MethodDefinition(name=f"Method{i}", description=f"Description {i}")
            for i in range(3)
        ]
        result = self.formatter.format_search_results(methods)
        assert "Найдено результатов: 3" in result
        assert "Method0" in result
        assert "Method1" in result
        assert "Method2" in result

    def test_many_results_table(self):
        methods = [
            MethodDefinition(name=f"Method{i}", description=f"Desc {i}")
            for i in range(10)
        ]
        result = self.formatter.format_search_results(methods)
        assert "показаны первые 5" in result
        assert "| #" in result

    def test_format_type(self):
        t = PlatformTypeDefinition(
            name="ТаблицаЗначений",
            description="Описание",
            methods=[MethodDefinition(name="Добавить", description="")],
            properties=[PropertyDefinition(name="Колонки", description="")],
            constructors=[Signature(name="По умолчанию", parameters=[], description="")],
        )
        result = self.formatter.format_member(t)
        assert "ТаблицаЗначений" in result
        assert "Методы (1)" in result
        assert "Свойства (1)" in result
        assert "Конструкторы (1)" in result
        assert "- По умолчанию" in result

    def test_format_method_with_params(self):
        method = MethodDefinition(
            name="Func",
            description="A function",
            signatures=[
                Signature(
                    name="Func",
                    parameters=[
                        ParameterDefinition(name="a", type="int", description="param", required=True),
                    ],
                    description="",
                )
            ],
        )
        result = self.formatter.format_member(method)
        assert "Func" in result
        assert "Параметры" in result
        assert "- `a` (обязательный) - Тип: int. param" in result
        assert "```\nFunc(<a>)\n```" in result

    def test_format_method_syntax_line_and_markers(self):
        method = MethodDefinition(
            name="Найти",
            description="Поиск значения",
            return_type="СтрокаТаблицыЗначений, Неопределено",
            signatures=[
                Signature(
                    name="Найти",
                    parameters=[
                        ParameterDefinition(
                            name="Значение", type="Произвольный", description="Искомое значение.", required=True
                        ),
                        ParameterDefinition(
                            name="Колонки",
                            type="Строка",
                            description="Список имен колонок.\nЕсли не указан, поиск по всей таблице.",
                            required=False,
                            default_value="Пустая строка",
                        ),
                    ],
                    description="",
                    syntax="Найти(<Значение>, <Колонки>)",
                )
            ],
        )
        result = self.formatter.format_member(method)
        assert "```\nНайти(<Значение>, <Колонки>)\n```" in result
        assert "- `Значение` (обязательный) - Тип: Произвольный. Искомое значение." in result
        assert (
            "- `Колонки` (необязательный) - Тип: Строка. Список имен колонок. "
            "Если не указан, поиск по всей таблице. Значение по умолчанию: Пустая строка."
        ) in result
        assert "**Возвращаемое значение:** Тип: СтрокаТаблицыЗначений, Неопределено." in result

    def test_format_method_return_description(self):
        method = MethodDefinition(
            name="Вычислить",
            description="",
            return_type="",
            return_description="Результат вычисления выражения.",
        )
        result = self.formatter.format_member(method)
        assert "**Возвращаемое значение:** Результат вычисления выражения." in result

    def test_format_method_unknown_requirement_has_no_marker(self):
        method = MethodDefinition(
            name="Func",
            description="",
            signatures=[
                Signature(
                    name="Func",
                    parameters=[ParameterDefinition(name="a", type="", description="param")],
                    description="",
                )
            ],
        )
        result = self.formatter.format_member(method)
        assert "- `a` - param" in result
        assert "обязательный" not in result

    def test_format_method_without_parameters(self):
        method = MethodDefinition(
            name="Очистить",
            description="Очищает таблицу",
            signatures=[Signature(name="Очистить", parameters=[], description="", syntax="Очистить()")],
        )
        result = self.formatter.format_member(method)
        assert "```\nОчистить()\n```" in result
        assert "Параметры" not in result

    def test_format_method_without_signatures(self):
        method = MethodDefinition(name="Очистить", description="Очищает таблицу")
        result = self.formatter.format_member(method)
        assert "```\nОчистить()\n```" in result

    def test_format_method_syntax_variants(self):
        method = MethodDefinition(
            name="ОткрытьФорму",
            description="Открывает форму",
            signatures=[
                Signature(
                    name="По имени",
                    parameters=[ParameterDefinition(name="ИмяФормы", type="Строка", description="", required=True)],
                    description="Открывает форму по имени.",
                    syntax="ОткрытьФорму(<ИмяФормы>)",
                ),
                Signature(
                    name="По форме",
                    parameters=[ParameterDefinition(name="Форма", type="Форма", description="", required=True)],
                    description="",
                    syntax="ОткрытьФорму(<Форма>)",
                ),
            ],
        )
        result = self.formatter.format_member(method)
        assert "**Вариант синтаксиса: По имени**" in result
        assert "**Вариант синтаксиса: По форме**" in result
        assert "Открывает форму по имени." in result
        assert result.index("ОткрытьФорму(<ИмяФормы>)") < result.index("ОткрытьФорму(<Форма>)")

    def test_format_property(self):
        prop = PropertyDefinition(
            name="ТекущаяДата",
            description="Дата",
            property_type="Дата",
            is_read_only=True,
        )
        result = self.formatter.format_member(prop)
        assert "ТекущаяДата" in result
        assert "**Тип:** Дата" in result
        assert "Только чтение" in result

    def test_format_constructors(self):
        ctors = [
            Signature(
                name="Новый",
                parameters=[
                    ParameterDefinition(name="Размер", type="Число", description="Размер"),
                ],
                description="Создает массив",
            )
        ]
        result = self.formatter.format_constructors(ctors, "Массив")
        assert "Конструкторы Массив" in result
        assert "```\nНовый Массив(<Размер>)\n```" in result
        assert "- `Размер` - Тип: Число. Размер" in result

    def test_format_constructors_with_syntax(self):
        ctors = [
            Signature(
                name="По количеству элементов",
                parameters=[
                    ParameterDefinition(
                        name="КоличествоЭлементов1,...,КоличествоЭлементовN",
                        type="Число",
                        description="Количество элементов.",
                        required=False,
                    ),
                ],
                description="Создает массив из указанного количества элементов.",
                syntax="Новый Массив(<КоличествоЭлементов1>,...,<КоличествоЭлементовN>)",
            )
        ]
        result = self.formatter.format_constructors(ctors, "Массив")
        assert "### По количеству элементов" in result
        assert "```\nНовый Массив(<КоличествоЭлементов1>,...,<КоличествоЭлементовN>)\n```" in result
        assert "(необязательный)" in result

    def test_format_constructors_empty(self):
        result = self.formatter.format_constructors([], "Тип")
        assert "нет конструкторов" in result

    def test_format_type_members(self):
        members = [
            MethodDefinition(name="M1", description="method"),
            PropertyDefinition(name="P1", description="property", is_read_only=True),
        ]
        result = self.formatter.format_type_members(members)
        assert "## Методы" in result
        assert "## Свойства" in result
        assert "M1" in result
        assert "**P1** *(только чтение)*" in result

    def test_format_error(self):
        result = self.formatter.format_error(Exception("test error"))
        assert "Ошибка" in result
        assert "test error" in result

    def test_format_query(self):
        result = self.formatter.format_query("Найти")
        assert "Найти" in result
