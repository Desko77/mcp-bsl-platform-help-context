"""Tests for HTML page block extraction."""

from __future__ import annotations

import pytest

from mcp_bsl_context.infrastructure.hbk.parsers.html_handler import (
    parse_html_page,
    ParsedPage,
)


def make_html(body_content: str) -> str:
    """Wrap body content in a minimal HTML document."""
    return f"<html><head><title>Test</title></head><body>{body_content}</body></html>"


class TestV8SHHeading:
    def test_heading_creates_name_block(self):
        html = make_html('<p class="V8SH_heading">МоёИмя</p>')
        page = parse_html_page(html)

        name_block = page.get_block("name")
        assert name_block is not None
        assert name_block.content == "МоёИмя"

    def test_heading_resets_current_block(self):
        html = make_html(
            '<h2>Описание</h2>'
            '<p>Текст описания</p>'
            '<p class="V8SH_heading">НовоеИмя</p>'
            '<p>Ещё текст</p>'
        )
        page = parse_html_page(html)

        types = [b.block_type for b in page.blocks]
        assert "description" in types
        assert "name" in types


class TestV8SHChapter:
    def test_chapter_detects_syntax(self):
        html = make_html('<p class="V8SH_chapter">Синтаксис</p><p>Code()</p>')
        page = parse_html_page(html)

        syntax_block = page.get_block("syntax")
        assert syntax_block is not None
        assert syntax_block.content == "Code()"

    def test_chapter_detects_parameters(self):
        html = make_html(
            '<p class="V8SH_chapter">Параметры</p>'
            '<p>Param1 - описание</p>'
        )
        page = parse_html_page(html)

        params_block = page.get_block("parameters")
        assert params_block is not None

    def test_chapter_unknown_title(self):
        html = make_html('<p class="V8SH_chapter">НеизвестныйРаздел</p>')
        page = parse_html_page(html)

        block = page.blocks[0]
        assert block.block_type == "unknown"


class TestColonNormalization:
    def test_title_with_colon(self):
        html = make_html('<p class="V8SH_chapter">Синтаксис:</p><p>X()</p>')
        page = parse_html_page(html)

        assert page.get_block("syntax") is not None

    def test_title_without_colon(self):
        html = make_html('<p class="V8SH_chapter">Синтаксис</p><p>X()</p>')
        page = parse_html_page(html)

        assert page.get_block("syntax") is not None


class TestStandardBlockDetection:
    def test_h2_block_title(self):
        html = make_html('<h2>Описание</h2><p>Текст</p>')
        page = parse_html_page(html)

        desc = page.get_block("description")
        assert desc is not None
        assert desc.content == "Текст"

    def test_bold_paragraph(self):
        html = make_html('<p><b>Пример</b></p><p>код</p>')
        page = parse_html_page(html)

        example = page.get_block("example")
        assert example is not None
        assert example.content == "код"

    def test_css_class_head(self):
        html = make_html('<p class="head">Описание</p><p>body</p>')
        page = parse_html_page(html)

        desc = page.get_block("description")
        assert desc is not None
        assert desc.content == "body"

    def test_unrecognized_paragraph(self):
        html = make_html('<p>Обычный текст</p>')
        page = parse_html_page(html)

        # No heading detected — goes into description block
        desc = page.get_block("description")
        assert desc is not None
        assert "Обычный текст" in desc.content

    def test_pre_content_preserved(self):
        html = make_html(
            '<h2>Пример</h2>'
            '<pre>  строка 1\n  строка 2</pre>'
        )
        page = parse_html_page(html)

        example = page.get_block("example")
        assert example is not None
        # .strip() removes leading whitespace on first line, but inner lines keep theirs
        assert "строка 1" in example.content
        assert "  строка 2" in example.content

    def test_table_parsed(self):
        html = make_html(
            '<h2>Описание</h2>'
            '<table><tr><th>Кол1</th><th>Кол2</th></tr>'
            '<tr><td>a</td><td>b</td></tr></table>'
        )
        page = parse_html_page(html)

        desc = page.get_block("description")
        assert desc is not None
        assert "Кол1 | Кол2" in desc.content
        assert "a | b" in desc.content


class TestParseFullPage:
    def test_page_with_multiple_blocks(self):
        html = make_html(
            '<p class="V8SH_heading">Метод</p>'
            '<p class="V8SH_chapter">Синтаксис</p>'
            '<p>Метод(Парам)</p>'
            '<p class="V8SH_chapter">Описание</p>'
            '<p>Описание метода</p>'
        )
        page = parse_html_page(html)

        assert page.get_block("name") is not None
        assert page.get_block("name").content == "Метод"
        assert page.get_block("syntax") is not None
        assert page.get_block("syntax").content == "Метод(Парам)"
        assert page.get_block("description") is not None

    def test_page_no_blocks(self):
        html = make_html('<p>Просто текст без заголовков</p>')
        page = parse_html_page(html)

        # Everything goes into a description block
        assert len(page.blocks) == 1
        assert page.blocks[0].block_type == "description"

    def test_empty_body(self):
        html = "<html><body></body></html>"
        page = parse_html_page(html)

        assert page.blocks == []

    def test_title_extraction(self):
        html = '<html><head><title>Мой заголовок</title></head><body><p>x</p></body></html>'
        page = parse_html_page(html)

        assert page.title == "Мой заголовок"

    def test_h3_heading(self):
        html = make_html('<h3>Возвращаемое значение</h3><p>Число</p>')
        page = parse_html_page(html)

        rv = page.get_block("return_value")
        assert rv is not None
        assert rv.content == "Число"

    def test_list_content(self):
        html = make_html(
            '<h2>Описание</h2>'
            '<ul><li>Пункт 1</li><li>Пункт 2</li></ul>'
        )
        page = parse_html_page(html)

        desc = page.get_block("description")
        assert "- Пункт 1" in desc.content
        assert "- Пункт 2" in desc.content
