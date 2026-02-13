"""DocumentBuilder — converts domain entities to embeddable text + metadata."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from mcp_bsl_context.domain.entities import (
    Definition,
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)

if TYPE_CHECKING:
    from mcp_bsl_context.infrastructure.storage.storage import PlatformContextStorage

# Fixed namespace for deterministic UUID5 generation.
# Same entity always gets the same point ID across restarts.
_NAMESPACE = uuid.UUID("7f3e8a2b-1c4d-5e6f-9a0b-2d3c4e5f6a7b")


@dataclass(frozen=True)
class EmbeddingDocument:
    """A document prepared for embedding and storage in the vector DB.

    Attributes:
        id: Deterministic UUID (stable across restarts for the same entity).
        text: Text to embed (concatenation of name, description, etc.).
        metadata: Stored in Qdrant payload for retrieval and filtering.
    """

    id: str
    text: str
    metadata: dict[str, Any]


class DocumentBuilder:
    """Converts domain entities to embeddable documents.

    Text format for each entity type:
      Method:   "TypeName.MethodName\\nDescription\\nВозвращает: ReturnType\\nПараметры: p1, p2"
      Property: "TypeName.PropertyName\\nDescription\\nТип: PropertyType\\nТолько чтение"
      Type:     "TypeName\\nDescription\\nМетоды: m1, m2, ...\\nСвойства: p1, p2, ..."
    """

    def build_all(self, storage: PlatformContextStorage) -> list[EmbeddingDocument]:
        """Build embedding documents from all entities in storage.

        Produces documents for:
        - Global methods
        - Global properties
        - Platform types (with method/property list summary)
        - Type members (methods and properties with type context)
        """
        docs: list[EmbeddingDocument] = []

        for method in storage.methods:
            docs.append(self.build_from_method(method))

        for prop in storage.properties:
            docs.append(self.build_from_property(prop))

        for type_def in storage.types:
            docs.append(self.build_from_type(type_def))
            for method in type_def.methods:
                docs.append(self.build_from_method(method, type_name=type_def.name))
            for prop in type_def.properties:
                docs.append(self.build_from_property(prop, type_name=type_def.name))

        return docs

    def build_from_method(
        self, method: MethodDefinition, type_name: str | None = None
    ) -> EmbeddingDocument:
        """Build a document from a method definition."""
        parts: list[str] = []

        if type_name:
            parts.append(f"{type_name}.{method.name}")
        else:
            parts.append(method.name)

        if method.description:
            parts.append(method.description)

        if method.return_type:
            parts.append(f"Возвращает: {method.return_type}")

        if method.signatures:
            for sig in method.signatures:
                param_names = [p.name for p in sig.parameters]
                if param_names:
                    parts.append(f"Параметры: {', '.join(param_names)}")
                    break  # one signature is enough for embedding context

        text = "\n".join(parts)
        doc_id = _make_id("method", method.name, type_name)
        metadata = {
            "name": method.name,
            "api_type": "method",
            "type_name": type_name or "",
            "text": text,
        }
        return EmbeddingDocument(id=doc_id, text=text, metadata=metadata)

    def build_from_property(
        self, prop: PropertyDefinition, type_name: str | None = None
    ) -> EmbeddingDocument:
        """Build a document from a property definition."""
        parts: list[str] = []

        if type_name:
            parts.append(f"{type_name}.{prop.name}")
        else:
            parts.append(prop.name)

        if prop.description:
            parts.append(prop.description)

        if prop.property_type:
            parts.append(f"Тип: {prop.property_type}")

        if prop.is_read_only:
            parts.append("Только чтение")

        text = "\n".join(parts)
        doc_id = _make_id("property", prop.name, type_name)
        metadata = {
            "name": prop.name,
            "api_type": "property",
            "type_name": type_name or "",
            "text": text,
        }
        return EmbeddingDocument(id=doc_id, text=text, metadata=metadata)

    def build_from_type(
        self, type_def: PlatformTypeDefinition
    ) -> EmbeddingDocument:
        """Build a document from a type definition."""
        parts: list[str] = [type_def.name]

        if type_def.description:
            parts.append(type_def.description)

        if type_def.methods:
            method_names = [m.name for m in type_def.methods[:20]]
            summary = f"Методы: {', '.join(method_names)}"
            if len(type_def.methods) > 20:
                summary += f" ...и ещё {len(type_def.methods) - 20}"
            parts.append(summary)

        if type_def.properties:
            prop_names = [p.name for p in type_def.properties[:20]]
            summary = f"Свойства: {', '.join(prop_names)}"
            if len(type_def.properties) > 20:
                summary += f" ...и ещё {len(type_def.properties) - 20}"
            parts.append(summary)

        text = "\n".join(parts)
        doc_id = _make_id("type", type_def.name, None)
        metadata = {
            "name": type_def.name,
            "api_type": "type",
            "type_name": "",
            "text": text,
        }
        return EmbeddingDocument(id=doc_id, text=text, metadata=metadata)

    def build_text(self, definition: Definition) -> str:
        """Build embeddable text from a Definition (useful for reranking).

        Does not need type context — produces text with the element name only.
        """
        if isinstance(definition, MethodDefinition):
            return self.build_from_method(definition).text
        if isinstance(definition, PropertyDefinition):
            return self.build_from_property(definition).text
        if isinstance(definition, PlatformTypeDefinition):
            return self.build_from_type(definition).text
        return str(definition)


def _make_id(api_type: str, name: str, type_name: str | None) -> str:
    """Create a deterministic UUID5 for a Qdrant point.

    Same inputs always produce the same ID, ensuring stability
    across server restarts (Qdrant can reuse persisted data).
    """
    key = f"{api_type}:{type_name or ''}:{name}"
    return str(uuid.uuid5(_NAMESPACE, key))
