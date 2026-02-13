"""Shared test fixtures for mcp_bsl_context tests."""

from __future__ import annotations

import pytest

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)


@pytest.fixture
def sample_methods() -> list[MethodDefinition]:
    return [
        MethodDefinition(
            name="НайтиПоСсылке",
            description="Поиск элемента по ссылке",
            return_type="Произвольный",
            signatures=[
                Signature(
                    name="НайтиПоСсылке",
                    parameters=[
                        ParameterDefinition(
                            name="Ссылка",
                            type="СправочникСсылка",
                            description="Ссылка для поиска",
                            required=True,
                        )
                    ],
                    description="",
                )
            ],
        ),
        MethodDefinition(
            name="НайтиПоКоду",
            description="Поиск элемента по коду",
            return_type="Произвольный",
        ),
        MethodDefinition(
            name="НайтиПоНаименованию",
            description="Поиск элемента по наименованию",
            return_type="Произвольный",
        ),
        MethodDefinition(
            name="Сообщить",
            description="Вывод сообщения пользователю",
        ),
        MethodDefinition(
            name="Формат",
            description="Форматирование значения",
        ),
    ]


@pytest.fixture
def sample_properties() -> list[PropertyDefinition]:
    return [
        PropertyDefinition(
            name="ТекущаяДата",
            description="Текущая дата сеанса",
            property_type="Дата",
            is_read_only=True,
        ),
        PropertyDefinition(
            name="ИмяПользователя",
            description="Имя текущего пользователя",
            property_type="Строка",
            is_read_only=True,
        ),
    ]


@pytest.fixture
def sample_types() -> list[PlatformTypeDefinition]:
    return [
        PlatformTypeDefinition(
            name="ТаблицаЗначений",
            description="Таблица значений для хранения данных",
            methods=[
                MethodDefinition(name="Добавить", description="Добавить строку"),
                MethodDefinition(name="Удалить", description="Удалить строку"),
                MethodDefinition(name="Найти", description="Найти значение"),
            ],
            properties=[
                PropertyDefinition(name="Количество", description="Количество строк"),
                PropertyDefinition(name="Колонки", description="Коллекция колонок"),
            ],
            constructors=[
                Signature(name="ТаблицаЗначений", parameters=[], description="Создает пустую таблицу"),
            ],
        ),
        PlatformTypeDefinition(
            name="СправочникОбъект",
            description="Объект справочника",
            methods=[
                MethodDefinition(name="Записать", description="Записать объект"),
            ],
            properties=[
                PropertyDefinition(name="Ссылка", description="Ссылка на объект"),
            ],
        ),
        PlatformTypeDefinition(
            name="Массив",
            description="Массив произвольных значений",
            methods=[
                MethodDefinition(name="Добавить", description="Добавить элемент"),
                MethodDefinition(name="Количество", description="Получить количество"),
            ],
        ),
    ]
