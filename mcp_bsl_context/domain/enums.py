"""API type enumeration."""

from __future__ import annotations

from enum import Enum


class ApiType(Enum):
    METHOD = "method"
    PROPERTY = "property"
    TYPE = "type"
    CONSTRUCTOR = "constructor"

    def get_display_name(self) -> str:
        return _DISPLAY_NAMES[self]

    def get_plural_name(self) -> str:
        return _PLURAL_NAMES[self]

    @classmethod
    def from_string(cls, type_str: str) -> ApiType | None:
        return _STRING_MAPPING.get(type_str.lower())


_DISPLAY_NAMES = {
    ApiType.METHOD: "Метод",
    ApiType.PROPERTY: "Свойство",
    ApiType.TYPE: "Тип",
    ApiType.CONSTRUCTOR: "Конструктор",
}

_PLURAL_NAMES = {
    ApiType.METHOD: "Методы",
    ApiType.PROPERTY: "Свойства",
    ApiType.TYPE: "Типы",
    ApiType.CONSTRUCTOR: "Конструкторы",
}

_STRING_MAPPING: dict[str, ApiType] = {
    "method": ApiType.METHOD,
    "метод": ApiType.METHOD,
    "функция": ApiType.METHOD,
    "property": ApiType.PROPERTY,
    "свойство": ApiType.PROPERTY,
    "type": ApiType.TYPE,
    "тип": ApiType.TYPE,
    "object": ApiType.TYPE,
    "объект": ApiType.TYPE,
    "constructor": ApiType.CONSTRUCTOR,
    "конструктор": ApiType.CONSTRUCTOR,
}
