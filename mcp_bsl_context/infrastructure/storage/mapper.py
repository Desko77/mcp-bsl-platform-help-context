"""Mapper: converts HBK models to domain entities."""

from __future__ import annotations

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    ParameterDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
    Signature,
)
from mcp_bsl_context.infrastructure.hbk.models import (
    MethodInfo,
    ObjectInfo,
    ParameterInfo,
    PropertyInfo,
    SignatureInfo,
)


def method_info_to_entity(info: MethodInfo) -> MethodDefinition:
    return MethodDefinition(
        name=info.name_ru or info.name_en,
        description=info.description,
        return_type=info.return_value.type if info.return_value else "",
        signatures=[signature_info_to_entity(s) for s in info.signatures],
    )


def property_info_to_entity(info: PropertyInfo) -> PropertyDefinition:
    return PropertyDefinition(
        name=info.name_ru or info.name_en,
        description=info.description,
        property_type=info.property_type,
        is_read_only=info.is_read_only,
    )


def object_info_to_entity(info: ObjectInfo) -> PlatformTypeDefinition:
    return PlatformTypeDefinition(
        name=info.name_ru or info.name_en,
        description=info.description,
        methods=[method_info_to_entity(m) for m in info.methods],
        properties=[property_info_to_entity(p) for p in info.properties],
        constructors=[signature_info_to_entity(c) for c in info.constructors],
    )


def signature_info_to_entity(info: SignatureInfo) -> Signature:
    return Signature(
        name=info.name,
        parameters=[parameter_info_to_entity(p) for p in info.parameters],
        description=info.description,
    )


def parameter_info_to_entity(info: ParameterInfo) -> ParameterDefinition:
    return ParameterDefinition(
        name=info.name,
        type=info.type,
        description=info.description,
        required=info.required,
        default_value=info.default_value,
    )
