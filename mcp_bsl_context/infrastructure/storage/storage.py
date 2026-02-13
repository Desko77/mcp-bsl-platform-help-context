"""Platform context storage with lazy initialization."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from mcp_bsl_context.domain.entities import (
    MethodDefinition,
    PlatformTypeDefinition,
    PropertyDefinition,
)

from .loader import PlatformContextLoader
from .mapper import method_info_to_entity, object_info_to_entity, property_info_to_entity

logger = logging.getLogger(__name__)


class PlatformContextStorage:
    """Thread-safe lazy-loading storage for platform context data."""

    def __init__(self, loader: PlatformContextLoader, platform_path: Path) -> None:
        self._loader = loader
        self._platform_path = platform_path
        self.methods: list[MethodDefinition] = []
        self.properties: list[PropertyDefinition] = []
        self.types: list[PlatformTypeDefinition] = []
        self._loaded = False
        self._lock = threading.RLock()

    def ensure_loaded(self) -> None:
        """Ensure context is loaded (double-checked locking)."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._do_load()
            self._loaded = True

    def _do_load(self) -> None:
        """Load platform context from HBK file."""
        logger.info("Loading platform context from: %s", self._platform_path)
        context = self._loader.load(self._platform_path)

        self.methods = [method_info_to_entity(m) for m in context.global_methods]
        self.properties = [property_info_to_entity(p) for p in context.global_properties]
        self.types = [object_info_to_entity(t) for t in context.types]

        # Add methods from types to global methods list for search
        for type_def in self.types:
            # Types themselves are searchable, their members are accessed via type

            pass

        logger.info(
            "Platform context loaded: %d methods, %d properties, %d types",
            len(self.methods),
            len(self.properties),
            len(self.types),
        )

    @property
    def is_loaded(self) -> bool:
        return self._loaded
