"""Markdown formatter for search results and definitions."""

from __future__ import annotations

from mcp_bsl_context.domain.entities import (
    Definition,
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)

SHORT_DESCRIPTION_LIMIT = 100


class MarkdownFormatter:
    """Formats platform context data as Markdown for MCP tool responses."""

    def format_error(self, exception: Exception) -> str:
        return f"**Ошибка:** {exception}\n"

    def format_query(self, query: str) -> str:
        return f"**Поиск:** `{query}`\n\n"

    def format_search_results(self, results: list[Definition]) -> str:
        if not results:
            return "Ничего не найдено.\n"

        if len(results) == 1:
            return self.format_member(results[0])

        if len(results) <= 5:
            return self._format_compact_results(results)

        return self._format_table_results(results)

    def format_member(self, definition: Definition) -> str:
        if isinstance(definition, PlatformTypeDefinition):
            return self._format_type(definition)
        if isinstance(definition, MethodDefinition):
            return self._format_method(definition)
        if isinstance(definition, PropertyDefinition):
            return self._format_property(definition)
        return f"**{definition.name}**\n{definition.description}\n"

    def format_type_members(self, members: list[Definition]) -> str:
        methods = [m for m in members if isinstance(m, MethodDefinition)]
        properties = [p for p in members if isinstance(p, PropertyDefinition)]

        parts: list[str] = []

        if methods:
            parts.append("## Методы\n")
            for m in methods:
                parts.append(f"- **{m.name}**")
                if m.description:
                    parts.append(f"  {_short(m.description)}")
            parts.append("")

        if properties:
            parts.append("## Свойства\n")
            for p in properties:
                ro = " *(только чтение)*" if p.is_read_only else ""
                parts.append(f"- **{p.name}**{ro}")
                if p.description:
                    parts.append(f"  {_short(p.description)}")
            parts.append("")

        if not parts:
            return "Члены типа не найдены.\n"

        return "\n".join(parts)

    def format_constructors(self, constructors: list[Signature], type_name: str) -> str:
        if not constructors:
            return f"У типа **{type_name}** нет конструкторов.\n"

        parts: list[str] = [f"## Конструкторы {type_name}\n"]

        for ctor in constructors:
            if ctor.name:
                parts.append(f"### {ctor.name}\n")
            parts.append(f"```\n{_signature_line(ctor, f'Новый {type_name}')}\n```\n")

            if ctor.description:
                parts.append(ctor.description)
                parts.append("")

            parts.extend(self._format_parameters(ctor.parameters))

        return "\n".join(parts)

    def _format_type(self, type_def: PlatformTypeDefinition) -> str:
        parts: list[str] = [f"## {type_def.name}\n"]

        if type_def.description:
            parts.append(type_def.description)
            parts.append("")

        if type_def.has_methods():
            parts.append(f"**Методы ({len(type_def.methods)}):**\n")
            for m in type_def.methods[:10]:
                parts.append(f"- `{m.name}`")
            if len(type_def.methods) > 10:
                parts.append(f"- ... и еще {len(type_def.methods) - 10}")
            parts.append("")

        if type_def.has_properties():
            parts.append(f"**Свойства ({len(type_def.properties)}):**\n")
            for p in type_def.properties[:10]:
                parts.append(f"- `{p.name}`")
            if len(type_def.properties) > 10:
                parts.append(f"- ... и еще {len(type_def.properties) - 10}")
            parts.append("")

        if type_def.constructors:
            parts.append(f"**Конструкторы ({len(type_def.constructors)}):**\n")
            for ctor in type_def.constructors:
                parts.append(f"- {ctor.name or _signature_line(ctor, f'Новый {type_def.name}')}")
            parts.append("")

        return "\n".join(parts)

    def _format_method(self, method: MethodDefinition) -> str:
        parts: list[str] = [f"## {method.name}\n"]

        several_variants = len(method.signatures) > 1
        for sig in method.signatures:
            if several_variants and sig.name and sig.name != method.name:
                parts.append(f"**Вариант синтаксиса: {sig.name}**\n")
            parts.append(f"```\n{_signature_line(sig, method.name)}\n```\n")
            parts.extend(self._format_parameters(sig.parameters))
            if sig.description:
                parts.append(sig.description)
                parts.append("")

        if not method.signatures:
            parts.append(f"```\n{method.name}()\n```\n")

        if method.description:
            parts.append(method.description)
            parts.append("")

        return_value = _return_value_line(method)
        if return_value:
            parts.append(f"**Возвращаемое значение:** {return_value}\n")

        return "\n".join(parts)

    def _format_property(self, prop: PropertyDefinition) -> str:
        parts: list[str] = [f"## {prop.name}\n"]

        if prop.property_type:
            parts.append(f"**Тип:** {prop.property_type}\n")

        if prop.is_read_only:
            parts.append("*Только чтение*\n")

        if prop.description:
            parts.append(prop.description)
            parts.append("")

        return "\n".join(parts)

    def _format_parameters(self, parameters: list[ParameterDefinition]) -> list[str]:
        if not parameters:
            return []
        parts = ["**Параметры:**\n"]
        for p in parameters:
            parts.append(_format_parameter(p))
        parts.append("")
        return parts

    def _format_compact_results(self, results: list[Definition]) -> str:
        parts: list[str] = [f"Найдено результатов: {len(results)}\n"]

        for item in results:
            kind = _get_kind_label(item)
            desc = _short(item.description, 80) if item.description else ""
            parts.append(f"- **{item.name}** ({kind}) - {desc}")

        parts.append("")
        # Show details for the first result
        parts.append("---\n")
        parts.append(self.format_member(results[0]))
        return "\n".join(parts)

    def _format_table_results(self, results: list[Definition]) -> str:
        top5 = results[:5]
        parts: list[str] = [
            f"Найдено результатов: {len(results)} (показаны первые 5)\n",
            "| # | Имя | Вид |",
            "|---|-----|-----|",
        ]

        for i, item in enumerate(top5, 1):
            kind = _get_kind_label(item)
            parts.append(f"| {i} | **{item.name}** | {kind} |")

        parts.append("")
        # Show details for the first result
        parts.append("---\n")
        parts.append(self.format_member(results[0]))
        return "\n".join(parts)


def _return_value_line(method: MethodDefinition) -> str:
    """"Тип: X. Описание" of the return value; either part may be missing."""
    parts: list[str] = []
    if method.return_type:
        parts.append(f"Тип: {method.return_type}.")
    if method.return_description:
        parts.append(method.return_description.replace("\n", " "))
    return " ".join(parts)


def _signature_line(sig: Signature, fallback_name: str) -> str:
    """Syntax line of the help, or one built from parameter names."""
    if sig.syntax:
        return sig.syntax
    params = ", ".join(f"<{p.name}>" for p in sig.parameters)
    return f"{fallback_name}({params})"


def _format_parameter(p: ParameterDefinition) -> str:
    """One list line: name, requirement marker, type, description, default."""
    line = f"- `{p.name}`"
    if p.required is True:
        line += " (обязательный)"
    elif p.required is False:
        line += " (необязательный)"

    details: list[str] = []
    if p.type:
        details.append(f"Тип: {p.type}.")
    if p.description:
        details.append(p.description.replace("\n", " "))
    if p.default_value:
        details.append(f"Значение по умолчанию: {p.default_value}.")

    if details:
        line += " - " + " ".join(details)
    return line


def _short(text: str, limit: int = SHORT_DESCRIPTION_LIMIT) -> str:
    """First line of the text cut to ``limit`` characters."""
    first_line = text.split("\n", 1)[0]
    if len(first_line) > limit:
        return first_line[:limit] + "..."
    return first_line


def _get_kind_label(item: Definition) -> str:
    if isinstance(item, MethodDefinition):
        return "Метод"
    if isinstance(item, PropertyDefinition):
        return "Свойство"
    if isinstance(item, PlatformTypeDefinition):
        return "Тип"
    return "Неизвестно"
