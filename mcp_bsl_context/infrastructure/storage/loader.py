"""Platform context loader — finds and reads HBK files."""

from __future__ import annotations

import logging
from pathlib import Path

from mcp_bsl_context.domain.exceptions import PlatformContextLoadException
from mcp_bsl_context.infrastructure.hbk.context_reader import PlatformContext, PlatformContextReader

logger = logging.getLogger(__name__)

HBK_FILENAME = "shcntx_ru.hbk"


class PlatformContextLoader:
    """Locates and loads platform context from the 1C installation directory."""

    def __init__(self) -> None:
        self._reader = PlatformContextReader()

    def load(self, platform_path: Path) -> PlatformContext:
        """Load platform context from the given platform directory."""
        hbk_path = self._find_hbk_file(platform_path)
        if hbk_path is None:
            raise PlatformContextLoadException(
                f"Help file '{HBK_FILENAME}' not found in '{platform_path}'"
            )

        logger.info("Found HBK file: %s", hbk_path)
        return self._reader.read(hbk_path)

    @staticmethod
    def _find_hbk_file(platform_path: Path) -> Path | None:
        """Recursively search for the HBK file in the platform directory."""
        if not platform_path.exists():
            logger.error("Platform path does not exist: %s", platform_path)
            return None

        # Direct check
        direct = platform_path / HBK_FILENAME
        if direct.is_file():
            return direct

        # Recursive search
        for path in platform_path.rglob(HBK_FILENAME):
            if path.is_file():
                return path

        return None
