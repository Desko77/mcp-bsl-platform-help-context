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


class MarkdownFormatter:
    """Formats platform context data as Markdown for MCP tool responses."""

    def format_error(self, exception: Exception) -> str:
        return f"**Error:** {exception}\n"

    def format_query(self, query: str) -> str:
        return f"**Search:** `{query}`\n\n"

    def format_search_results(self, results: list[Definition]) -> str:
        if not results:
            return "Nothing found.\n"

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
            parts.append("## Methods\n")
            for m in methods:
                parts.append(f"- **{m.name}**")
                if m.description:
                    short = m.description[:100]
                    if len(m.description) > 100:
                        short += "..."
                    parts.append(f"  {short}")
            parts.append("")

        if properties:
            parts.append("## Properties\n")
            for p in properties:
                ro = " *(read-only)*" if p.is_read_only else ""
                parts.append(f"- **{p.name}**{ro}")
                if p.description:
                    short = p.description[:100]
                    if len(p.description) > 100:
                        short += "..."
                    parts.append(f"  {short}")
            parts.append("")

        if not parts:
            return "No members found.\n"

        return "\n".join(parts)

    def format_constructors(self, constructors: list[Signature], type_name: str) -> str:
        if not constructors:
            return f"Type **{type_name}** has no constructors.\n"

        parts: list[str] = [f"## Constructors for {type_name}\n"]

        for ctor in constructors:
            if ctor.parameters:
                params = ", ".join(p.name for p in ctor.parameters)
                parts.append(f"```\n{ctor.name}({params})\n```\n")
            else:
                parts.append(f"```\n{ctor.name}()\n```\n")

            if ctor.description:
                parts.append(ctor.description)
                parts.append("")

            if ctor.parameters:
                parts.append("**Parameters:**\n")
                for p in ctor.parameters:
                    req = " *(required)*" if p.required else ""
                    parts.append(f"- `{p.name}`{req} — {p.description}")
                parts.append("")

        return "\n".join(parts)

    def _format_type(self, type_def: PlatformTypeDefinition) -> str:
        parts: list[str] = [f"## {type_def.name}\n"]

        if type_def.description:
            parts.append(type_def.description)
            parts.append("")

        if type_def.has_methods():
            parts.append(f"**Methods ({len(type_def.methods)}):**\n")
            for m in type_def.methods[:10]:
                parts.append(f"- `{m.name}`")
            if len(type_def.methods) > 10:
                parts.append(f"- ... and {len(type_def.methods) - 10} more")
            parts.append("")

        if type_def.has_properties():
            parts.append(f"**Properties ({len(type_def.properties)}):**\n")
            for p in type_def.properties[:10]:
                parts.append(f"- `{p.name}`")
            if len(type_def.properties) > 10:
                parts.append(f"- ... and {len(type_def.properties) - 10} more")
            parts.append("")

        if type_def.constructors:
            parts.append(f"**Constructors ({len(type_def.constructors)})**\n")

        return "\n".join(parts)

    def _format_method(self, method: MethodDefinition) -> str:
        parts: list[str] = [f"## {method.name}\n"]

        if method.signatures:
            for sig in method.signatures:
                params = ", ".join(p.name for p in sig.parameters)
                parts.append(f"```\n{method.name}({params})\n```\n")

                if sig.parameters:
                    parts.append("**Parameters:**\n")
                    for p in sig.parameters:
                        req = " *(required)*" if p.required else ""
                        desc = f" — {p.description}" if p.description else ""
                        parts.append(f"- `{p.name}`{req}{desc}")
                    parts.append("")

        if method.description:
            parts.append(method.description)
            parts.append("")

        if method.return_type:
            parts.append(f"**Returns:** `{method.return_type}`\n")

        return "\n".join(parts)

    def _format_property(self, prop: PropertyDefinition) -> str:
        parts: list[str] = [f"## {prop.name}\n"]

        if prop.property_type:
            parts.append(f"**Type:** `{prop.property_type}`\n")

        if prop.is_read_only:
            parts.append("*Read-only*\n")

        if prop.description:
            parts.append(prop.description)
            parts.append("")

        return "\n".join(parts)

    def _format_compact_results(self, results: list[Definition]) -> str:
        parts: list[str] = [f"Found {len(results)} results:\n"]

        for item in results:
            kind = _get_kind_label(item)
            desc = item.description[:80] if item.description else ""
            if len(item.description) > 80:
                desc += "..."
            parts.append(f"- **{item.name}** ({kind}) — {desc}")

        parts.append("")
        # Show details for the first result
        parts.append("---\n")
        parts.append(self.format_member(results[0]))
        return "\n".join(parts)

    def _format_table_results(self, results: list[Definition]) -> str:
        top5 = results[:5]
        parts: list[str] = [
            f"Found {len(results)} results (showing top 5):\n",
            "| # | Name | Type |",
            "|---|------|------|",
        ]

        for i, item in enumerate(top5, 1):
            kind = _get_kind_label(item)
            parts.append(f"| {i} | **{item.name}** | {kind} |")

        parts.append("")
        # Show details for the first result
        parts.append("---\n")
        parts.append(self.format_member(results[0]))
        return "\n".join(parts)


def _get_kind_label(item: Definition) -> str:
    if isinstance(item, MethodDefinition):
        return "Method"
    if isinstance(item, PropertyDefinition):
        return "Property"
    if isinstance(item, PlatformTypeDefinition):
        return "Type"
    return "Unknown"
