"""Tests for HBK binary container reader."""

from __future__ import annotations

import struct

from mcp_bsl_context.infrastructure.hbk.container_reader import HbkContainerReader


def make_block_header(data_size: int, page_size: int, next_page: int) -> bytes:
    """Build a 31-byte block header: \\r\\n{hex8} {hex8} {hex8} \\r\\n."""
    return (
        b"\r\n"
        + f"{data_size:08x}".encode("ascii") + b" "
        + f"{page_size:08x}".encode("ascii") + b" "
        + f"{next_page:08x}".encode("ascii") + b" "
        + b"\r\n"
    )


END_MARKER = 0x7FFFFFFF


class TestParseBlockHeader:
    def test_single_page_header(self):
        header = make_block_header(data_size=100, page_size=256, next_page=END_MARKER)
        data = header + b"\x00" * 256

        ds, ps, np, data_start = HbkContainerReader._parse_block_header(data, 0)

        assert ds == 100
        assert ps == 256
        assert np == END_MARKER
        assert data_start == 31  # 2 + 8+1 + 8+1 + 8+1+2

    def test_multi_page_header(self):
        next_addr = 0x00001000
        header = make_block_header(data_size=500, page_size=128, next_page=next_addr)
        data = header + b"\x00" * 128

        ds, ps, np, data_start = HbkContainerReader._parse_block_header(data, 0)

        assert ds == 500
        assert ps == 128
        assert np == next_addr
        assert data_start == 31

    def test_header_at_offset(self):
        prefix = b"\x00" * 64
        header = make_block_header(data_size=42, page_size=64, next_page=END_MARKER)
        data = prefix + header + b"\x00" * 64

        ds, ps, np, data_start = HbkContainerReader._parse_block_header(data, 64)

        assert ds == 42
        assert ps == 64
        assert np == END_MARKER
        assert data_start == 64 + 31


class TestGetFileBody:
    def test_single_page_body(self):
        payload = b"Hello, World!"
        header = make_block_header(data_size=len(payload), page_size=256, next_page=END_MARKER)
        data = header + payload + b"\x00" * (256 - len(payload))

        reader = HbkContainerReader()
        body = reader._get_file_body(data, 0)

        assert body == payload

    def test_multi_page_chain(self):
        # 3 pages, each holds a chunk of data
        chunk1 = b"AAAA"
        chunk2 = b"BBBB"
        chunk3 = b"CC"
        total_data_size = len(chunk1) + len(chunk2) + len(chunk3)  # 10
        page_size = 4

        # Place pages sequentially; each header is 31 bytes, each page body is page_size
        page_stride = 31 + page_size

        addr_page1 = 0
        addr_page2 = page_stride
        addr_page3 = page_stride * 2

        h1 = make_block_header(data_size=total_data_size, page_size=page_size, next_page=addr_page2)
        h2 = make_block_header(data_size=total_data_size, page_size=page_size, next_page=addr_page3)
        h3 = make_block_header(data_size=total_data_size, page_size=page_size, next_page=END_MARKER)

        data = (
            h1 + chunk1
            + h2 + chunk2
            + h3 + chunk3 + b"\x00" * (page_size - len(chunk3))
        )

        reader = HbkContainerReader()
        body = reader._get_file_body(data, addr_page1)

        assert body == chunk1 + chunk2 + chunk3

    def test_chain_stops_at_end_marker(self):
        chunk1 = b"XXXX"
        chunk2 = b"YY"
        total = len(chunk1) + len(chunk2)
        page_size = 4

        addr_page1 = 0
        addr_page2 = 31 + page_size

        h1 = make_block_header(data_size=total, page_size=page_size, next_page=addr_page2)
        h2 = make_block_header(data_size=total, page_size=page_size, next_page=END_MARKER)

        data = h1 + chunk1 + h2 + chunk2 + b"\x00" * (page_size - len(chunk2))

        reader = HbkContainerReader()
        body = reader._get_file_body(data, addr_page1)

        assert body == chunk1 + chunk2
        assert len(body) == total


class TestGetFilename:
    def _build_header_block(self, name: str) -> bytes:
        """Build a minimal filename header block that _get_filename can parse.

        Layout at header_addr:
          2 bytes skipped
          8-byte ASCII hex payload_size + 1 separator byte
          40 bytes of fixed header
          UTF-16LE name bytes
        """
        name_bytes = name.encode("utf-16-le")
        payload_size = 24 + len(name_bytes)
        block = (
            b"\x00\x00"  # 2 bytes skipped
            + f"{payload_size:08x}".encode("ascii") + b" "  # payload_size (9 bytes)
            + b"\x00" * 40  # fixed header (40 bytes)
            + name_bytes
        )
        return block

    def test_utf16le_filename(self):
        data = self._build_header_block("PackBlock")
        reader = HbkContainerReader()
        name = reader._get_filename(data, 0)
        assert name == "PackBlock"

    def test_empty_filename(self):
        # payload_size = 20 < 24 → name_size <= 0 → empty string
        payload_size = 20
        data = (
            b"\x00\x00"
            + f"{payload_size:08x}".encode("ascii") + b" "
            + b"\x00" * 40
        )
        reader = HbkContainerReader()
        name = reader._get_filename(data, 0)
        assert name == ""

    def test_null_terminated(self):
        raw_name = "Test\x00\x00\x00"
        name_bytes = raw_name.encode("utf-16-le")
        payload_size = 24 + len(name_bytes)
        data = (
            b"\x00\x00"
            + f"{payload_size:08x}".encode("ascii") + b" "
            + b"\x00" * 40
            + name_bytes
        )
        reader = HbkContainerReader()
        name = reader._get_filename(data, 0)
        assert name == "Test"

    def test_cyrillic_filename(self):
        data = self._build_header_block("Файл")
        reader = HbkContainerReader()
        name = reader._get_filename(data, 0)
        assert name == "Файл"


class TestParseFileInfo:
    def _build_container(
        self, file_entries: list[tuple[str, bytes]]
    ) -> bytes:
        """Build a minimal HBK container with given filename->body pairs.

        Container layout:
          16 bytes: main header (4 int32s)
          2 bytes: short
          9 bytes: payload_size (8 hex + separator)
          9 bytes: block_size (8 hex + separator)
          11 bytes: fixed
          N bytes: file info entries (12 bytes each)
          ...then header blocks and body blocks follow

        Each file info entry: (header_addr, body_addr, 0x7FFFFFFF) as 3 int32s.
        """
        entries_data = bytearray()
        extra_blocks = bytearray()
        info_entries_start = 16 + 2 + 9 + 9 + 11
        info_entries_size = len(file_entries) * 12
        block_start = info_entries_start + info_entries_size

        for name, body in file_entries:
            header_addr = block_start + len(extra_blocks)
            # Build name header block
            name_bytes = name.encode("utf-16-le")
            payload_size = 24 + len(name_bytes)
            header_block = (
                b"\x00\x00"
                + f"{payload_size:08x}".encode("ascii") + b" "
                + b"\x00" * 40
                + name_bytes
            )
            extra_blocks.extend(header_block)

            body_addr = block_start + len(extra_blocks)
            # Build body block
            body_block_header = make_block_header(
                data_size=len(body), page_size=max(len(body), 1), next_page=END_MARKER
            )
            extra_blocks.extend(body_block_header)
            extra_blocks.extend(body)

            entry = struct.pack("<iii", header_addr, body_addr, 0x7FFFFFFF)
            entries_data.extend(entry)

        # Main container header
        main_header = b"\x00" * 16  # 4 int32s
        main_header += b"\x00\x00"  # 2 bytes
        main_header += f"{info_entries_size:08x}".encode("ascii") + b" "  # payload_size
        main_header += f"{0:08x}".encode("ascii") + b" "  # block_size (unused)
        main_header += b"\x00" * 11  # 11 bytes fixed

        return bytes(main_header) + bytes(entries_data) + bytes(extra_blocks)

    def test_single_file(self):
        container = self._build_container([("PackBlock", b"data123")])
        reader = HbkContainerReader()
        result = reader.read_from_bytes(container) if hasattr(reader, "read_from_bytes") else None
        # _parse_file_info is called internally; test via _parse_file_info directly
        entities = reader._parse_file_info(container)
        assert "PackBlock" in entities

    def test_two_files(self):
        container = self._build_container([
            ("PackBlock", b"toc-data"),
            ("FileStorage", b"zip-data"),
        ])
        reader = HbkContainerReader()
        entities = reader._parse_file_info(container)
        assert "PackBlock" in entities
        assert "FileStorage" in entities
        assert len(entities) == 2

    def test_skips_non_end_reserved(self):
        """Entries with reserved != 0x7FFFFFFF are skipped."""
        # Build one valid and one invalid entry manually
        info_entries_size = 24  # 2 entries * 12 bytes
        header_data = (
            b"\x00" * 16  # main header
            + b"\x00\x00"  # short
            + f"{info_entries_size:08x}".encode("ascii") + b" "
            + f"{0:08x}".encode("ascii") + b" "
            + b"\x00" * 11
        )
        valid_header_addr = len(header_data) + info_entries_size
        # Valid entry
        entry1 = struct.pack("<iii", valid_header_addr, 0, 0x7FFFFFFF)
        # Invalid entry (reserved != 0x7FFFFFFF)
        entry2 = struct.pack("<iii", 0, 0, 0x00000000)

        name_bytes = "Test".encode("utf-16-le")
        payload_size = 24 + len(name_bytes)
        header_block = (
            b"\x00\x00"
            + f"{payload_size:08x}".encode("ascii") + b" "
            + b"\x00" * 40
            + name_bytes
        )

        container = header_data + entry1 + entry2 + header_block

        reader = HbkContainerReader()
        entities = reader._parse_file_info(container)
        assert len(entities) == 1
        assert "Test" in entities
