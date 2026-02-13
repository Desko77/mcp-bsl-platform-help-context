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
        """Extract file body from a body address, following page chains."""
        data_size, page_size, next_page, page_data_start = self._parse_block_header(data, body_addr)

        # Single-page entry: data fits in one page
        if next_page == 0x7FFFFFFF:
            return data[page_data_start : page_data_start + data_size]

        # Multi-page entry: follow the chain and concatenate
        result = bytearray()
        remaining = data_size
        current_start = page_data_start
        current_page_size = page_size
        current_next = next_page

        while remaining > 0:
            chunk_size = min(current_page_size, remaining)
            result.extend(data[current_start : current_start + chunk_size])
            remaining -= chunk_size

            if remaining <= 0 or current_next == 0x7FFFFFFF:
                break

            _, current_page_size, current_next, current_start = self._parse_block_header(data, current_next)

        return bytes(result)

    @staticmethod
    def _parse_block_header(data: bytes, addr: int) -> tuple[int, int, int, int]:
        """Parse a block header and return (data_size, page_size, next_page, data_start)."""
        pos = addr + 2  # skip CRLF
        data_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9
        page_size = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 9
        next_page = int(data[pos : pos + 8].decode("ascii"), 16)
        pos += 11  # field (8) + space (1) + CRLF (2)
        return data_size, page_size, next_page, pos
