"""Tests for DocsInfoService."""

import pytest

from mcp_bsl_context.domain.docs_service import (
    DocsInfoService,
    TopicNotFoundException,
)
from mcp_bsl_context.domain.exceptions import InvalidSearchQueryException

SAMPLE_STRICT_TYPES = """\
# Строгая типизация BSL

Вводная часть документа (пропускается при парсинге).

## TOPIC: overview

### Назначение строгой типизации

Строгая типизация позволяет снизить количество ошибок при разработке.

## TOPIC: arrays

### Описание массивов

Массив должен быть типизирован при создании.

```bsl
СписокСсылок = Новый Массив; // Массив из СправочникСсылка.Товары -
СписокСсылок.Добавить(Ссылка);
```

## TOPIC: constructor-functions

### Функции-конструкторы

Для сложных типов используйте функции-конструкторы.

```bsl
Функция НоваяТаблицаТоваров()
    Возврат Новый ТаблицаЗначений;
КонецФункции
```
"""

SAMPLE_GUIDELINE = """\
# Рекомендации по стилю кода BSL

1. Все запросы пишутся в отдельных функциях-конструкторах с описанием типов.
2. Максимум 3-5 параметров у функции.
"""


@pytest.fixture
def service():
    return DocsInfoService(SAMPLE_STRICT_TYPES, SAMPLE_GUIDELINE)


class TestGetGuideline:
    def test_returns_content(self, service):
        result = service.get_guideline()
        assert "Рекомендации по стилю кода BSL" in result
        assert "функциях-конструкторах" in result

    def test_returns_full_content(self, service):
        result = service.get_guideline()
        assert result == SAMPLE_GUIDELINE


class TestGetStrictTypingInfo:
    def test_list_topics(self, service):
        result = service.get_strict_typing_info("topics")
        assert "overview" in result
        assert "arrays" in result
        assert "constructor-functions" in result

    def test_get_specific_topic(self, service):
        result = service.get_strict_typing_info("overview")
        assert "Назначение строгой типизации" in result
        assert "снизить количество ошибок" in result

    def test_get_topic_with_code(self, service):
        result = service.get_strict_typing_info("arrays")
        assert "СписокСсылок" in result
        assert "Новый Массив" in result

    def test_case_insensitive(self, service):
        result = service.get_strict_typing_info("OVERVIEW")
        assert "Назначение строгой типизации" in result

    def test_case_insensitive_mixed(self, service):
        result = service.get_strict_typing_info("Overview")
        assert "Назначение строгой типизации" in result

    def test_topic_with_whitespace(self, service):
        result = service.get_strict_typing_info("  overview  ")
        assert "Назначение строгой типизации" in result

    def test_unknown_topic_raises(self, service):
        with pytest.raises(TopicNotFoundException, match="не найдена"):
            service.get_strict_typing_info("nonexistent")

    def test_unknown_topic_lists_available(self, service):
        with pytest.raises(TopicNotFoundException, match="overview"):
            service.get_strict_typing_info("nonexistent")

    def test_topics_keyword_case_insensitive(self, service):
        result = service.get_strict_typing_info("TOPICS")
        assert "overview" in result

    def test_preamble_not_included_as_topic(self, service):
        result = service.get_strict_typing_info("topics")
        assert "Вводная часть" not in result


class TestSearchStrictTyping:
    def test_found_single(self, service):
        result = service.search_strict_typing("массив")
        assert "arrays" in result
        assert "1 совпадений" in result or "совпадений" in result

    def test_found_multiple(self, service):
        result = service.search_strict_typing("типов")
        # Should match in overview and/or constructor-functions
        assert "совпадений" in result

    def test_found_code_example(self, service):
        result = service.search_strict_typing("СписокСсылок")
        assert "arrays" in result

    def test_not_found(self, service):
        result = service.search_strict_typing("несуществующийтермин12345")
        assert "ничего не найдено" in result

    def test_case_insensitive(self, service):
        result = service.search_strict_typing("МАССИВ")
        assert "arrays" in result

    def test_empty_query_raises(self, service):
        with pytest.raises(InvalidSearchQueryException):
            service.search_strict_typing("")

    def test_whitespace_only_raises(self, service):
        with pytest.raises(InvalidSearchQueryException):
            service.search_strict_typing("   ")

    def test_context_preview(self, service):
        result = service.search_strict_typing("функции-конструкторы")
        assert "constructor-functions" in result
        # Should contain context around the match
        assert "..." in result or "конструктор" in result.lower()


class TestLazyParsing:
    def test_topics_not_parsed_until_access(self):
        svc = DocsInfoService(SAMPLE_STRICT_TYPES, SAMPLE_GUIDELINE)
        assert svc._topics is None

    def test_topics_parsed_on_first_access(self):
        svc = DocsInfoService(SAMPLE_STRICT_TYPES, SAMPLE_GUIDELINE)
        svc.get_strict_typing_info("overview")
        assert svc._topics is not None
        assert "overview" in svc._topics

    def test_guideline_no_topic_parsing(self):
        svc = DocsInfoService(SAMPLE_STRICT_TYPES, SAMPLE_GUIDELINE)
        svc.get_guideline()
        assert svc._topics is None
