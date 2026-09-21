"""Domain entities for 1C platform context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass(frozen=True)
class ParameterDefinition:
    name: str
    type: str
    description: str
    required: bool | None = None
    default_value: str | None = None


@dataclass(frozen=True)
class Signature:
    name: str
    parameters: list[ParameterDefinition]
    description: str
    syntax: str = ""


@dataclass(frozen=True)
class MethodDefinition:
    name: str
    description: str
    return_type: str = ""
    signatures: list[Signature] = field(default_factory=list)
    return_description: str = ""


@dataclass(frozen=True)
class PropertyDefinition:
    name: str
    description: str
    property_type: str = ""
    is_read_only: bool = False


@dataclass(frozen=True)
class PlatformTypeDefinition:
    name: str
    description: str
    methods: list[MethodDefinition] = field(default_factory=list)
    properties: list[PropertyDefinition] = field(default_factory=list)
    constructors: list[Signature] = field(default_factory=list)

    def has_methods(self) -> bool:
        return len(self.methods) > 0

    def has_properties(self) -> bool:
        return len(self.properties) > 0


Definition = Union[MethodDefinition, PropertyDefinition, PlatformTypeDefinition]
