"""HBK content reader: extracts TOC and HTML pages from the container."""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path
from typing import Callable

from .container_reader import HbkContainerReader
from .toc.toc import Toc

logger = logging.getLogger(__name__)


class HbkContext:
    """Provides access to TOC and HTML pages from an HBK file."""

    def __init__(self, toc: Toc, zip_file: zipfile.ZipFile) -> None:
        self.toc = toc
        self._zip = zip_file
        self._name_set: set[str] | None = None

    def read_page(self, path: str) -> str | None:
        """Read an HTML page by its path from the ZIP archive."""
        if not path:
            return None
        try:
            # Normalize path separators and strip leading slash
            normalized = path.replace("\\", "/").lstrip("/")
            if self._name_set is None:
                self._name_set = set(self._zip.namelist())

            if normalized in self._name_set:
                return self._zip.read(normalized).decode("utf-8", errors="replace")

            # Try case-insensitive match
            lower = normalized.lower()
            for name in self._name_set:
                if name.lower() == lower:
                    return self._zip.read(name).decode("utf-8", errors="replace")
        except (KeyError, zipfile.BadZipFile) as e:
            logger.warning("Failed to read page '%s': %s", path, e)
        return None


class HbkContentReader:
    """Reads and decompresses the HBK container into TOC + ZIP of HTML pages."""

    def __init__(self) -> None:
        self._container_reader = HbkContainerReader()

    def read(self, path: Path, callback: Callable[[HbkContext], None]) -> None:
        """Read HBK file and invoke callback with the context."""
        files = self._container_reader.read(path)

        # Extract and inflate PackBlock (TOC)
        pack_block_data = files.get("PackBlock")
        if pack_block_data is None:
            raise ValueError("PackBlock not found in HBK container")

        toc_data = self._inflate_pack_block(pack_block_data)
        toc = Toc.parse(toc_data)

        # Extract FileStorage (ZIP with HTML pages)
        file_storage_data = files.get("FileStorage")
        if file_storage_data is None:
            raise ValueError("FileStorage not found in HBK container")

        with zipfile.ZipFile(io.BytesIO(file_storage_data)) as zf:
            ctx = HbkContext(toc, zf)
            callback(ctx)

    @staticmethod
    def _inflate_pack_block(data: bytes) -> bytes:
        """Decompress the PackBlock ZIP to get TOC bracket file."""
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names:
                raise ValueError("PackBlock ZIP is empty")
            return zf.read(names[0])
