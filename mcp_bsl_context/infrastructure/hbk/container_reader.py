"""Binary container reader for 1C HBK files.

The HBK file format is a proprietary 1C binary container with:
- A header with file info entries (12 bytes each)
- File names stored as UTF-16LE strings
- File bodies stored as raw bytes (typically ZIP-compressed)
"""

from __future__ import annotations

import logging
import struct
from pathlib import Path

logger = logging.getLogger(__name__)


class HbkContainerReader:
    """Reads the binary container structure of an HBK file."""

    def read(self, path: Path) -> dict[str, bytes]:
        """Read an HBK file and return a dict of filename -> body bytes."""
        data = path.read_bytes()
        entities = self._parse_file_info(data)
        result: dict[str, bytes] = {}
        for name, body_addr in entities.items():
            result[name] = self._get_file_body(data, body_addr)
        logger.debug("HBK container: found %d files: %s", len(result), list(result.keys()))
        return result

    def _parse_file_info(self, data: bytes) -> dict[str, int]:
        """Parse the file info table from the container header."""
        pos = 0

        # Skip 16-byte header (4 int32s)
        pos += 16

        # Skip 2 bytes (short)
        pos += 2

        # Read payload_size: 8-byte ASCII hex + 1 separator byte
        payload_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9

        # Read block_size: 8-byte ASCII hex + 1 separator byte
        block_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9

        # Skip 11 bytes (long + byte + short equivalent)
        pos += 11

        file_info_start = pos
        file_info_data = data[pos : pos + payload_size]

        # Parse file info entries (12 bytes each: header_addr, body_addr, reserved)
        entities: dict[str, int] = {}
        entry_count = len(file_info_data) // 12

        for i in range(entry_count):
            offset = i * 12
            header_addr, body_addr, reserved = struct.unpack_from(
                "<iii", file_info_data, offset
            )
            if reserved != 0x7FFFFFFF:
                continue

            name = self._get_filename(data, header_addr)
            entities[name] = body_addr

        return entities

    def _get_filename(self, data: bytes, header_addr: int) -> str:
        """Extract filename from a header address."""
        pos = header_addr

        # Skip 2 bytes
        pos += 2

        # Read payload_size: 8-byte ASCII hex + 1 separator byte
        payload_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9

        # Skip 40 bytes of fixed header fields
        pos += 40

        # Read filename as UTF-16LE
        name_size = payload_size - 24
        if name_size <= 0:
            return ""
        name_bytes = data[pos : pos + name_size]
        return name_bytes.decode("utf-16-le").rstrip("\x00")

    def _get_file_body(self, data: bytes, body_addr: int) -> bytes:
        """Extract file body from a body address."""
        pos = body_addr

        # Skip 2 bytes
        pos += 2

        # Read payload_size: 8-byte ASCII hex + 1 separator byte
        payload_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9

        # Skip 20 bytes of header fields
        pos += 20

        return data[pos : pos + payload_size]
