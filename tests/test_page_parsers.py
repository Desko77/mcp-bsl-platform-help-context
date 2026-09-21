"""Tests for the page parsers on the real markup of the platform help.

Fixtures reproduce the HBK layout: bare text between tags, ``div.V8SH_rubric``
parameter headers with (обязательный)/(необязательный) markers, several syntax
variants, the 8.3.10 ``div``-based markup and the 8.3.24+ ``p``-based markup.
"""

from __future__ import annotations

from mcp_bsl_context.infrastructure.hbk.parsers.constructor_parser import ConstructorPageParser
from mcp_bsl_context.infrastructure.hbk.parsers.html_handler import ParsedBlock, parse_html_page
from mcp_bsl_context.infrastructure.hbk.parsers.method_parser import MethodPageParser
from mcp_bsl_context.infrastructure.hbk.parsers.object_parser import ObjectPageParser
from mcp_bsl_context.infrastructure.hbk.parsers.params import (
    parse_parameters,
    parse_signatures,
    split_type_prefix,
)
from mcp_bsl_context.infrastructure.hbk.parsers.property_parser import PropertyPageParser
from mcp_bsl_context.infrastructure.storage.mapper import method_info_to_entity, object_info_to_entity

HEAD = '<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"></head><body>'
TAIL = (
    '<HR><p>&nbsp;&nbsp;&nbsp;&nbsp; <a href=http://www.example.com/devlinks target="_blank">'
    "Методическая информация</a></p></body></html>"
)


def rubric(text: str) -> str:
    return f'<div class="V8SH_rubric"> <p style="margin-top: 2px; margin-bottom: 1px">{text}</div>'


def chapter(text: str) -> str:
    return f'<p class="V8SH_chapter">{text}</p>'


# ТаблицаЗначений.Найти, HBK 8.3.27
FIND_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">ТаблицаЗначений.Найти (ValueTable.Find)</h1>'
    '<p class="V8SH_title">ТаблицаЗначений (ValueTable)</p>'
    '<p class="V8SH_heading">Найти (Find)</p>'
    '<div class="__SINCE_SHOW_STYLE__"><p class="not_used">Доступен, начиная с версии 8.0.</p></div>'
    + chapter("Синтаксис:")
    + "Найти(&lt;Значение&gt;, &lt;Колонки&gt;)"
    + chapter("Параметры:")
    + rubric("&lt;Значение&gt; (обязательный)")
    + "Тип: Произвольный. <br>Искомое значение."
    + rubric("&lt;Колонки&gt; (необязательный)")
    + 'Тип: <a href="v8help://SyntaxHelperLanguage/def_String">Строка</a>. <br>'
    "Список имен колонок, разделенных запятыми, по которым производится поиск.<br>"
    "Если параметр не указан, поиск осуществляется по всей таблице значений.<br>"
    "Значение по умолчанию: Пустая строка."
    + chapter("Возвращаемое значение:")
    + 'Тип: <a href="v8help://x/ValueTableRow.html">СтрокаТаблицыЗначений</a>, '
    '<a href="v8help://SyntaxHelperLanguage/def_Undefined">Неопределено</a>. <br>'
    "Строка, в которой содержится искомое значение."
    + chapter("Описание:")
    + "<p>Осуществляет поиск значения в указанных колонках таблицы значений.</p>"
    + chapter("Доступность: ")
    + "<p>Сервер, толстый клиент.</p>"
    + chapter("Примечание:")
    + "Метод эффективно использовать для поиска уникальных значений."
    + chapter("Пример:")
    + '<TABLE width="100%"><TBODY><TR><TD><p class="V8SH_codesample"><font color="#0000ff">'
    "НайденнаяСтрока&nbsp;<font color=\"#ff0000\">=</font>&nbsp;ТаблицаЦен<font color=\"#ff0000\">.</font>"
    "Найти<font color=\"#ff0000\">(</font>ВыбТовар<font color=\"#ff0000\">)</font>;<BR>"
    "&nbsp;&nbsp;&nbsp;&nbsp;Предупреждение<font color=\"#ff0000\">(</font>1<font color=\"#ff0000\">)</font>;"
    "</font></p></TD></TR></TBODY></TABLE>"
    + chapter("Использование в версии:")
    + '<p class="V8SH_versionInfo">Доступен, начиная с версии 8.0.</p>'
    + TAIL
)

# ОткрытьФорму: two syntax variants, HBK 8.3.27
OPEN_FORM_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Глобальный контекст.ОткрытьФорму (Global context.OpenForm)</h1>'
    '<p class="V8SH_title">Глобальный контекст (Global context)</p>'
    '<p class="V8SH_heading">ОткрытьФорму (OpenForm)</p>'
    '<div class="__SINCE_SHOW_STYLE__"><p class="not_used">Доступен, начиная с версии 8.2.</p></div>'
    + chapter("Вариант синтаксиса: По имени")
    + chapter("Синтаксис:")
    + "ОткрытьФорму(&lt;ИмяФормы&gt;, &lt;Параметры&gt;)"
    + chapter("Параметры:")
    + rubric("&lt;ИмяФормы&gt; (обязательный)")
    + 'Тип: <a href="v8help://SyntaxHelperLanguage/def_String">Строка</a>. <br>Имя формы.'
    + rubric("&lt;Параметры&gt; (необязательный)")
    + 'Тип: <a href="v8help://x/Structure.html">Структура</a>. <br>Параметры формы.'
    + chapter("Описание варианта метода:")
    + "Открывает форму по имени."
    + chapter("Вариант синтаксиса: По форме")
    + chapter("Синтаксис:")
    + "ОткрытьФорму(&lt;Форма&gt;, &lt;Окно&gt;)"
    + chapter("Параметры:")
    + rubric("&lt;Форма&gt; (обязательный)")
    + 'Тип: <a href="v8help://x/Form.html">Форма</a>, <a href="v8help://x/CAF.html">ФормаКлиентскогоПриложения</a>. '
    "<br>Форма или форма клиентского приложения."
    + rubric("&lt;Окно&gt; (необязательный)")
    + "Тип: ОкноКлиентскогоПриложения. <br>Окно приложения."
    + chapter("Возвращаемое значение:")
    + 'Тип: <a href="v8help://x/Form.html">Форма</a>, '
    '<a href="v8help://x/CAF.html">ФормаКлиентскогоПриложения</a>. <br>'
    + chapter("Описание:")
    + "<p>Открывает и возвращает форму.<br>Для следующих форм владелец не учитывается:"
    "<ul><li>ФормаОбъекта,</li><li>ФормаЗаписи.</li></ul></p>"
    + TAIL
)

# Массив.По количеству элементов: variadic parameter, mixed escaping as in the HBK
ARRAY_CTOR_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Массив.По количеству элементов</h1>'
    '<p class="V8SH_title">Массив (Array)</p>'
    '<p class="V8SH_heading">По количеству элементов</p>'
    + chapter("Синтаксис:")
    + "Новый Массив(&lt;КоличествоЭлементов1>,...,<КоличествоЭлементовN&gt;)"
    + chapter("Параметры:")
    + rubric("&lt;КоличествоЭлементов1>,...,<КоличествоЭлементовN&gt; (необязательный)")
    + 'Тип: <a href="v8help://SyntaxHelperLanguage/def_Number">Число</a>. <br>'
    "Каждый параметр определяет количество элементов массива."
    + chapter("Описание:")
    + "<p>Создает массив из указанного количества элементов.</p>"
    + TAIL
)

# Соответствие.По умолчанию: constructor without parameters
MAP_CTOR_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Соответствие.По умолчанию</h1>'
    '<p class="V8SH_title">Соответствие (Map)</p>'
    '<p class="V8SH_heading">По умолчанию</p>'
    + chapter("Синтаксис:")
    + "Новый Соответствие()"
    + chapter("Описание:")
    + "<p>Создает пустое соответствие (без элементов).</p>"
    + TAIL
)

# Глобальный контекст.ПоказатьОповещениеПользователя, HBK 8.3.10 (div-based markup)
OLD_MARKUP_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Глобальный контекст.ПоказатьОповещениеПользователя'
    " (Global context.ShowUserNotification)</h1>"
    '<div class="V8SH_title">Глобальный контекст (Global context)</div>'
    '<div class="V8SH_heading">ПоказатьОповещениеПользователя (ShowUserNotification)</div>'
    '<div class="V8SH_chapter"> <p style="margin-top: 3px; margin-bottom: 1px">Синтаксис:</div>'
    "ПоказатьОповещениеПользователя(&lt;Текст&gt;, &lt;ДействиеПриНажатии&gt;)"
    '<div class="V8SH_chapter"> <p style="margin-top: 3px; margin-bottom: 1px">Параметры:</div>'
    + rubric("&lt;Текст&gt; (необязательный)")
    + 'Тип: <a href="v8help://SyntaxHelperLanguage/def_String">Строка</a>. <br>Текст оповещения.'
    + rubric("&lt;ДействиеПриНажатии&gt; (необязательный)")
    + 'Тип: <a href="v8help://SyntaxHelperLanguage/def_String">Строка</a>; '
    '<a href="v8help://x/NotifyDescription.html">ОписаниеОповещения</a>. <br>'
    "Если тип Строка, то она содержит навигационную ссылку."
    '<div class="V8SH_chapter"> <p style="margin-top: 3px; margin-bottom: 1px">Описание:</div>'
    "Показывает окно оповещения.<br>"
    '<div class="V8SH_chapter"> <p style="margin-top: 3px; margin-bottom: 1px">Доступность:</div>'
    "Тонкий клиент, веб-клиент.<br>" + TAIL
)

# Глобальный контекст.WebSocketКлиенты: read-only property
PROPERTY_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Глобальный контекст.WebSocketКлиенты (Global context.WebSocketClients)</h1>'
    '<p class="V8SH_title">Глобальный контекст (Global context)</p>'
    '<p class="V8SH_heading">WebSocketКлиенты (WebSocketClients)</p>'
    '<div class="__SINCE_SHOW_STYLE__"><p class="not_used">Доступен, начиная с версии 8.3.27.</p></div>'
    + chapter("Использование:")
    + "Только чтение."
    + chapter("Описание:")
    + 'Тип: <a href="v8help://x/WebSocketClientsManager.html">МенеджерWebSocketКлиентов</a>. <br>'
    "Предоставляет доступ к WebSocket-клиентам, описанным в конфигурации."
    + chapter("Доступность: ")
    + "<p>Сервер, толстый клиент, внешнее соединение.</p>"
    + TAIL
)

# ТаблицаЗначений: type page (no V8SH_heading)
TYPE_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">ТаблицаЗначений (ValueTable)</h1>'
    '<p class="V8SH_title">ТаблицаЗначений (ValueTable)</p>'
    + chapter("Свойства:")
    + '<a href="ValueTable/properties/Columns1030.html">Колонки (Columns)</a><br>'
    + chapter("Методы:")
    + '<a href="ValueTable/methods/Find602.html">Найти (Find)</a><br>'
    + chapter("Конструкторы:")
    + '<a href="ValueTable/ctors/ctor_Auto.html">По умолчанию</a><br>'
    + chapter("Описание:")
    + "<p>Таблица значений предназначена для хранения значений в табличном виде.</p>"
    + TAIL
)


# Глобальный контекст.НавигационнаяСсылкаЗапуска: deprecation banner before the first chapter
DEPRECATED_PROPERTY_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Глобальный контекст.НавигационнаяСсылкаЗапуска (Global context.LaunchURL)</h1>'
    '<p class="V8SH_title">Глобальный контекст (Global context)</p>'
    '<p class="V8SH_heading">НавигационнаяСсылкаЗапуска (LaunchURL)</p>'
    '<div class="__DEPRECATED_SHOW_STYLE__"><p class="not_used">Не рекомендуется использовать, начиная с версии 8.3.18.</p>'
    '<p class="__DEPRECATED_SHOW_STYLE__">Рекомендуется использовать:</p>'
    '<ul class="__DEPRECATED_SHOW_STYLE__"><li><a href="v8help://x/LaunchURLNavigationData13177.html">'
    "ДанныеПереходаПоНавигационнойСсылкеЗапуска</a></li></ul></div>"
    '<div class="__SINCE_SHOW_STYLE__"><p class="not_used">Доступен, начиная с версии 8.3.18.</p></div>'
    + chapter("Использование:")
    + "Только чтение."
    + chapter("Описание:")
    + 'Тип: <a href="v8help://x/URLNavigationData.html">ДанныеПереходаПоНавигационнойСсылке</a>, '
    '<a href="v8help://SyntaxHelperLanguage/def_Undefined">Неопределено</a>. <br>'
    "Используется для доступа к ссылке, по которой был произведен запуск приложения."
    + TAIL
)

# Catalog page: no chapters, free text after the title
CATALOG_PAGE = (
    HEAD
    + '<h1 class="V8SH_pagetitle">Мобильный клиент с возможностью автономной работы</h1>'
    '<p class="V8SH_title">Мобильный клиент с возможностью автономной работы</p>'
    "В данном разделе описывается функции, предназначенные для настройки в мобильном клиенте возможности автономной работы."
    + TAIL
)


class TestHtmlHandlerPlatformMarkup:
    def test_bare_text_after_chapter_is_captured(self):
        page = parse_html_page(FIND_PAGE)
        assert page.get_block_content("syntax") == "Найти(<Значение>, <Колонки>)"

    def test_since_block_does_not_leak_into_syntax(self):
        page = parse_html_page(FIND_PAGE)
        assert page.get_block_content("since") == "Доступен, начиная с версии 8.0."
        assert "Доступен" not in page.get_block_content("syntax")

    def test_owner_and_name_blocks(self):
        page = parse_html_page(FIND_PAGE)
        assert page.get_block_content("owner") == "ТаблицаЗначений (ValueTable)"
        assert page.get_block_content("name") == "Найти (Find)"

    def test_rubrics_become_items(self):
        page = parse_html_page(FIND_PAGE)
        params = page.get_block("parameters")
        assert params is not None
        assert [item.title for item in params.items] == [
            "<Значение> (обязательный)",
            "<Колонки> (необязательный)",
        ]
        assert params.items[0].content == "Тип: Произвольный.\nИскомое значение."
        assert params.items[1].content == (
            "Тип: Строка.\n"
            "Список имен колонок, разделенных запятыми, по которым производится поиск.\n"
            "Если параметр не указан, поиск осуществляется по всей таблице значений.\n"
            "Значение по умолчанию: Пустая строка."
        )

    def test_inline_links_are_joined_without_extra_spaces(self):
        page = parse_html_page(FIND_PAGE)
        rv = page.get_block_content("return_value")
        assert rv.startswith("Тип: СтрокаТаблицыЗначений, Неопределено.\n")

    def test_content_after_hr_is_dropped(self):
        page = parse_html_page(FIND_PAGE)
        assert "Методическая информация" not in " ".join(b.content for b in page.blocks)

    def test_chapter_titles_are_mapped(self):
        page = parse_html_page(FIND_PAGE)
        types = [b.block_type for b in page.blocks]
        for expected in ("syntax", "parameters", "return_value", "description", "availability", "note", "example", "version_info"):
            assert expected in types
        assert "unknown" not in types

    def test_code_sample_keeps_lines_and_indentation(self):
        page = parse_html_page(FIND_PAGE)
        example = page.get_block_content("example")
        assert example == "НайденнаяСтрока = ТаблицаЦен.Найти(ВыбТовар);\n    Предупреждение(1);"

    def test_deprecation_banner_does_not_shadow_description(self):
        page = parse_html_page(DEPRECATED_PROPERTY_PAGE)
        assert page.get_block_content("since") == "Доступен, начиная с версии 8.3.18."
        assert page.get_block_content("deprecated") == (
            "Не рекомендуется использовать, начиная с версии 8.3.18.\n"
            "Рекомендуется использовать:\n"
            "- ДанныеПереходаПоНавигационнойСсылкеЗапуска"
        )
        assert len(page.get_blocks("description")) == 1
        assert page.get_block_content("description").startswith("Тип: ДанныеПереходаПоНавигационнойСсылке, Неопределено.")

    def test_page_without_chapters_is_all_description(self):
        page = parse_html_page(CATALOG_PAGE)
        assert page.get_block_content("owner") == "Мобильный клиент с возможностью автономной работы"
        assert page.get_block_content("description").startswith("В данном разделе описывается функции")
        assert page.get_block("intro") is None

    def test_variant_block_carries_variant_name(self):
        page = parse_html_page(OPEN_FORM_PAGE)
        variants = page.get_blocks("variant")
        assert [v.content for v in variants] == ["По имени", "По форме"]
        assert [b.block_type for b in page.blocks if b.block_type == "syntax"] == ["syntax", "syntax"]

    def test_description_with_br_and_list(self):
        page = parse_html_page(OPEN_FORM_PAGE)
        assert page.get_block_content("description") == (
            "Открывает и возвращает форму.\n"
            "Для следующих форм владелец не учитывается:\n"
            "- ФормаОбъекта,\n"
            "- ФормаЗаписи."
        )

    def test_old_div_markup(self):
        page = parse_html_page(OLD_MARKUP_PAGE)
        assert page.get_block_content("name") == "ПоказатьОповещениеПользователя (ShowUserNotification)"
        assert page.get_block_content("syntax") == "ПоказатьОповещениеПользователя(<Текст>, <ДействиеПриНажатии>)"
        params = page.get_block("parameters")
        assert [item.title for item in params.items] == [
            "<Текст> (необязательный)",
            "<ДействиеПриНажатии> (необязательный)",
        ]
        assert page.get_block_content("description") == "Показывает окно оповещения."
        assert page.get_block_content("availability") == "Тонкий клиент, веб-клиент."

    def test_mixed_escaping_of_variadic_name(self):
        page = parse_html_page(ARRAY_CTOR_PAGE)
        assert page.get_block_content("syntax") == "Новый Массив(<КоличествоЭлементов1>,...,<КоличествоЭлементовN>)"
        params = page.get_block("parameters")
        assert params.items[0].title == "<КоличествоЭлементов1>,...,<КоличествоЭлементовN> (необязательный)"


class TestParseParameters:
    def test_markers_type_and_default(self):
        page = parse_html_page(FIND_PAGE)
        params = parse_parameters(page.get_block("parameters"))
        assert [p.name for p in params] == ["Значение", "Колонки"]
        assert params[0].required is True
        assert params[0].type == "Произвольный"
        assert params[0].description == "Искомое значение."
        assert params[0].default_value is None
        assert params[1].required is False
        assert params[1].type == "Строка"
        assert params[1].default_value == "Пустая строка"
        assert params[1].description == (
            "Список имен колонок, разделенных запятыми, по которым производится поиск.\n"
            "Если параметр не указан, поиск осуществляется по всей таблице значений."
        )

    def test_variadic_parameter_name(self):
        page = parse_html_page(ARRAY_CTOR_PAGE)
        params = parse_parameters(page.get_block("parameters"))
        assert len(params) == 1
        assert params[0].name == "КоличествоЭлементов1,...,КоличествоЭлементовN"
        assert params[0].required is False
        assert params[0].type == "Число"

    def test_double_angle_variadic_name(self):
        block = ParsedBlock(title="Параметры:", block_type="parameters")
        block.items.append(ParsedBlock(title="<<разм0>,...,<размN-1>> (обязательный)", block_type="item", content="Тип: Число."))
        params = parse_parameters(block)
        assert params[0].name == "разм0,...,размN-1"
        assert params[0].required is True

    def test_composite_type_list(self):
        page = parse_html_page(OPEN_FORM_PAGE)
        params = parse_parameters(page.get_blocks("parameters")[1])
        assert params[0].type == "Форма, ФормаКлиентскогоПриложения"
        assert params[0].description == "Форма или форма клиентского приложения."

    def test_marker_missing_gives_unknown_requirement(self):
        block = ParsedBlock(title="Параметры:", block_type="parameters")
        block.items.append(ParsedBlock(title="<Имя>", block_type="item", content="Описание."))
        params = parse_parameters(block)
        assert params[0].required is None
        assert params[0].name == "Имя"
        assert params[0].description == "Описание."

    def test_several_default_values_are_joined(self):
        block = ParsedBlock(title="Параметры:", block_type="parameters")
        block.items.append(
            ParsedBlock(
                title="<Отбор> (необязательный)",
                block_type="item",
                content="Тип: Структура.\nОписание.\nЗначение по умолчанию: пустая структура.\nЗначение по умолчанию: Структура.",
            )
        )
        params = parse_parameters(block)
        assert params[0].default_value == "пустая структура; Структура"
        assert params[0].description == "Описание."

    def test_text_fallback_without_rubrics(self):
        block = ParsedBlock(
            title="Параметры:",
            block_type="parameters",
            content="<Значение> - искомое значение\nТип: Произвольный.\n<Колонки> (необязательный) - имена колонок",
        )
        params = parse_parameters(block)
        assert [(p.name, p.required) for p in params] == [("Значение", None), ("Колонки", False)]
        assert params[0].description == "искомое значение"
        assert params[0].type == "Произвольный"
        assert params[1].description == "имена колонок"

    def test_plain_name_dash_description_fallback(self):
        block = ParsedBlock(title="Параметры:", block_type="parameters", content="Строка - исходная строка\nЧисло - количество")
        params = parse_parameters(block)
        assert [(p.name, p.description) for p in params] == [("Строка", "исходная строка"), ("Число", "количество")]

    def test_empty_block(self):
        assert parse_parameters(None) == []
        assert parse_parameters(ParsedBlock(title="Параметры:", block_type="parameters")) == []


class TestSplitTypePrefix:
    def test_type_and_description(self):
        assert split_type_prefix("Тип: Строка.\nОписание") == ("Строка", "Описание")

    def test_type_list_keeps_inner_dots(self):
        assert split_type_prefix("Тип: СправочникСсылка.<Имя справочника>, Неопределено.\nТекст") == (
            "СправочникСсылка.<Имя справочника>, Неопределено",
            "Текст",
        )

    def test_description_on_the_same_line(self):
        assert split_type_prefix("Тип: Число. Количество строк.") == ("Число", "Количество строк.")

    def test_no_type_line(self):
        assert split_type_prefix("Результат вычисления выражения.") == ("", "Результат вычисления выражения.")

    def test_empty(self):
        assert split_type_prefix("") == ("", "")


class TestParseSignatures:
    def test_single_syntax(self):
        page = parse_html_page(FIND_PAGE)
        sigs = parse_signatures(page, "Найти")
        assert len(sigs) == 1
        assert sigs[0].name == "Найти"
        assert sigs[0].syntax == "Найти(<Значение>, <Колонки>)"
        assert [p.name for p in sigs[0].parameters] == ["Значение", "Колонки"]

    def test_variants(self):
        page = parse_html_page(OPEN_FORM_PAGE)
        sigs = parse_signatures(page, "ОткрытьФорму")
        assert [s.name for s in sigs] == ["По имени", "По форме"]
        assert sigs[0].syntax == "ОткрытьФорму(<ИмяФормы>, <Параметры>)"
        assert sigs[0].description == "Открывает форму по имени."
        assert [p.name for p in sigs[0].parameters] == ["ИмяФормы", "Параметры"]
        assert sigs[1].syntax == "ОткрытьФорму(<Форма>, <Окно>)"
        assert sigs[1].description == ""
        assert [p.name for p in sigs[1].parameters] == ["Форма", "Окно"]

    def test_syntax_without_parameters(self):
        page = parse_html_page(MAP_CTOR_PAGE)
        sigs = parse_signatures(page, "По умолчанию")
        assert len(sigs) == 1
        assert sigs[0].syntax == "Новый Соответствие()"
        assert sigs[0].parameters == []


class TestMethodPageParser:
    def test_find(self):
        info = MethodPageParser().parse(FIND_PAGE)
        assert info.name_ru == "Найти"
        assert info.name_en == "Find"
        assert info.syntax == "Найти(<Значение>, <Колонки>)"
        assert info.description == "Осуществляет поиск значения в указанных колонках таблицы значений."
        assert info.return_value is not None
        assert info.return_value.type == "СтрокаТаблицыЗначений, Неопределено"
        assert info.return_value.description == "Строка, в которой содержится искомое значение."
        assert len(info.signatures) == 1
        params = info.signatures[0].parameters
        assert [(p.name, p.required, p.type) for p in params] == [
            ("Значение", True, "Произвольный"),
            ("Колонки", False, "Строка"),
        ]

    def test_variants_and_return_type_without_description(self):
        info = MethodPageParser().parse(OPEN_FORM_PAGE)
        assert info.name_ru == "ОткрытьФорму"
        assert [s.name for s in info.signatures] == ["По имени", "По форме"]
        assert info.return_value.type == "Форма, ФормаКлиентскогоПриложения"
        assert info.return_value.description == ""

    def test_old_markup(self):
        info = MethodPageParser().parse(OLD_MARKUP_PAGE)
        assert info.name_ru == "ПоказатьОповещениеПользователя"
        assert info.name_en == "ShowUserNotification"
        assert info.description == "Показывает окно оповещения."
        params = info.signatures[0].parameters
        assert [(p.name, p.required, p.type) for p in params] == [
            ("Текст", False, "Строка"),
            ("ДействиеПриНажатии", False, "Строка; ОписаниеОповещения"),
        ]

    def test_free_text_return_value(self):
        html = (
            HEAD
            + '<p class="V8SH_heading">Вычислить (Eval)</p>'
            + chapter("Синтаксис:")
            + "Вычислить(&lt;Выражение&gt;)"
            + chapter("Возвращаемое значение:")
            + "Результат вычисления выражения."
            + TAIL
        )
        info = MethodPageParser().parse(html)
        assert info.return_value.type == ""
        assert info.return_value.description == "Результат вычисления выражения."

    def test_mapping_to_entity(self):
        entity = method_info_to_entity(MethodPageParser().parse(FIND_PAGE))
        assert entity.return_type == "СтрокаТаблицыЗначений, Неопределено"
        assert entity.return_description == "Строка, в которой содержится искомое значение."
        assert entity.signatures[0].syntax == "Найти(<Значение>, <Колонки>)"
        assert entity.signatures[0].parameters[0].required is True
        assert entity.signatures[0].parameters[1].default_value == "Пустая строка"


class TestConstructorPageParser:
    def test_with_parameters(self):
        info = ConstructorPageParser().parse(ARRAY_CTOR_PAGE)
        assert info.name == "По количеству элементов"
        assert info.syntax == "Новый Массив(<КоличествоЭлементов1>,...,<КоличествоЭлементовN>)"
        assert info.description == "Создает массив из указанного количества элементов."
        assert len(info.parameters) == 1
        assert info.parameters[0].name == "КоличествоЭлементов1,...,КоличествоЭлементовN"
        assert info.parameters[0].required is False

    def test_without_parameters(self):
        info = ConstructorPageParser().parse(MAP_CTOR_PAGE)
        assert info.name == "По умолчанию"
        assert info.syntax == "Новый Соответствие()"
        assert info.parameters == []
        assert info.description == "Создает пустое соответствие (без элементов)."


class TestPropertyPageParser:
    def test_type_and_read_only(self):
        info = PropertyPageParser().parse(PROPERTY_PAGE)
        assert info.name_ru == "WebSocketКлиенты"
        assert info.name_en == "WebSocketClients"
        assert info.property_type == "МенеджерWebSocketКлиентов"
        assert info.is_read_only is True
        assert info.description == "Предоставляет доступ к WebSocket-клиентам, описанным в конфигурации."

    def test_read_write_property(self):
        html = PROPERTY_PAGE.replace("Только чтение.", "Чтение и запись.")
        info = PropertyPageParser().parse(html)
        assert info.is_read_only is False


    def test_deprecation_banner_prefixes_description(self):
        info = PropertyPageParser().parse(DEPRECATED_PROPERTY_PAGE)
        assert info.property_type == "ДанныеПереходаПоНавигационнойСсылке, Неопределено"
        assert info.is_read_only is True
        assert info.description == (
            "Не рекомендуется использовать, начиная с версии 8.3.18.\n"
            "Рекомендуется использовать:\n"
            "- ДанныеПереходаПоНавигационнойСсылкеЗапуска\n"
            "Используется для доступа к ссылке, по которой был произведен запуск приложения."
        )


class TestObjectPageParser:
    def test_description_and_toc_naming(self):
        info = ObjectPageParser().parse(TYPE_PAGE)
        # Type pages carry no V8SH_heading: the visitor names them after the TOC
        assert info.name_ru == ""
        assert info.description == "Таблица значений предназначена для хранения значений в табличном виде."
        entity = object_info_to_entity(info)
        assert entity.description == info.description
