"""Alternative context loader from pre-exported JSON files.

Supports loading from JSON exported by platform-context-exporter tool.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)

logger = logging.getLogger(__name__)


class JsonContextLoader:
    """Loads platform context from pre-exported JSON files."""

    def load_methods(self, path: Path) -> list[MethodDefinition]:
        """Load methods from a JSON file."""
        data = self._read_json(path)
        if not isinstance(data, list):
            data = data.get("methods", [])
        return [self._parse_method(m) for m in data]

    def load_properties(self, path: Path) -> list[PropertyDefinition]:
        """Load properties from a JSON file."""
        data = self._read_json(path)
        if not isinstance(data, list):
            data = data.get("properties", [])
        return [self._parse_property(p) for p in data]

    def load_types(self, path: Path) -> list[PlatformTypeDefinition]:
        """Load types from a JSON file."""
        data = self._read_json(path)
        if not isinstance(data, list):
            data = data.get("types", [])
        return [self._parse_type(t) for t in data]

    def load_all(self, directory: Path) -> tuple[
        list[MethodDefinition],
        list[PropertyDefinition],
        list[PlatformTypeDefinition],
    ]:
        """Load all context from a directory with methods.json, properties.json, types.json."""
        methods: list[MethodDefinition] = []
        properties: list[PropertyDefinition] = []
        types: list[PlatformTypeDefinition] = []

        methods_file = directory / "methods.json"
        if methods_file.exists():
            methods = self.load_methods(methods_file)
            logger.info("Loaded %d methods from JSON", len(methods))

        props_file = directory / "properties.json"
        if props_file.exists():
            properties = self.load_properties(props_file)
            logger.info("Loaded %d properties from JSON", len(properties))

        types_file = directory / "types.json"
        if types_file.exists():
            types = self.load_types(types_file)
            logger.info("Loaded %d types from JSON", len(types))

        # Try single combined file
        combined = directory / "context.json"
        if combined.exists() and not (methods or properties or types):
            data = self._read_json(combined)
            methods = [self._parse_method(m) for m in data.get("methods", [])]
            properties = [self._parse_property(p) for p in data.get("properties", [])]
            types = [self._parse_type(t) for t in data.get("types", [])]
            logger.info("Loaded from combined JSON: %d methods, %d properties, %d types",
                        len(methods), len(properties), len(types))

        return methods, properties, types

    @staticmethod
    def _read_json(path: Path) -> dict | list:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _parse_method(self, data: dict) -> MethodDefinition:
        return MethodDefinition(
            name=data.get("name", data.get("name_ru", "")),
            description=data.get("description", ""),
            return_type=data.get("return_type", data.get("returnType", "")),
            signatures=[self._parse_signature(s) for s in data.get("signatures", [])],
        )

    def _parse_property(self, data: dict) -> PropertyDefinition:
        return PropertyDefinition(
            name=data.get("name", data.get("name_ru", "")),
            description=data.get("description", ""),
            property_type=data.get("property_type", data.get("type", "")),
            is_read_only=data.get("is_read_only", data.get("readOnly", False)),
        )

    def _parse_type(self, data: dict) -> PlatformTypeDefinition:
        return PlatformTypeDefinition(
            name=data.get("name", data.get("name_ru", "")),
            description=data.get("description", ""),
            methods=[self._parse_method(m) for m in data.get("methods", [])],
            properties=[self._parse_property(p) for p in data.get("properties", [])],
            constructors=[self._parse_signature(c) for c in data.get("constructors", [])],
        )

    def _parse_signature(self, data: dict) -> Signature:
        return Signature(
            name=data.get("name", ""),
            parameters=[self._parse_parameter(p) for p in data.get("parameters", [])],
            description=data.get("description", ""),
        )

    @staticmethod
    def _parse_parameter(data: dict) -> ParameterDefinition:
        return ParameterDefinition(
            name=data.get("name", ""),
            type=data.get("type", ""),
            description=data.get("description", ""),
            required=data.get("required", False),
            default_value=data.get("default_value", data.get("defaultValue")),
        )
