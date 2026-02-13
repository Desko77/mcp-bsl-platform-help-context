"""Tests for VersionDiscovery filesystem scanning."""

import pytest

from mcp_bsl_context.domain.value_objects import PlatformVersion
from mcp_bsl_context.infrastructure.storage.version_discovery import (
    VersionDiscovery,
)

HBK_FILENAME = "shcntx_ru.hbk"


@pytest.fixture
def discovery():
    return VersionDiscovery()


class TestMultiVersionDiscovery:
    def test_discovers_version_subdirs(self, tmp_path, discovery):
        for ver in ["8.3.18.1741", "8.3.25.1257"]:
            d = tmp_path / ver
            d.mkdir()
            (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 2
        assert result[0].version == PlatformVersion(8, 3, 18)
        assert result[1].version == PlatformVersion(8, 3, 25)

    def test_skips_non_version_dirs(self, tmp_path, discovery):
        (tmp_path / "common").mkdir()
        d = tmp_path / "8.3.25.1257"
        d.mkdir()
        (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 1
        assert result[0].version == PlatformVersion(8, 3, 25)

    def test_skips_version_dir_without_hbk(self, tmp_path, discovery):
        (tmp_path / "8.3.18.1741").mkdir()  # no HBK inside
        d = tmp_path / "8.3.25.1257"
        d.mkdir()
        (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 1

    def test_finds_hbk_in_bin_subdir(self, tmp_path, discovery):
        d = tmp_path / "8.3.25.1257" / "bin"
        d.mkdir(parents=True)
        (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 1
        assert result[0].hbk_path == d / HBK_FILENAME


class TestNestedArchDiscovery:
    def test_discovers_through_arch_subdir(self, tmp_path, discovery):
        arch = tmp_path / "x86_64"
        d = arch / "8.3.25.1257"
        d.mkdir(parents=True)
        (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 1
        assert result[0].version == PlatformVersion(8, 3, 25)

    def test_discovers_multiple_through_arch(self, tmp_path, discovery):
        arch = tmp_path / "x86_64"
        for ver in ["8.3.18.1741", "8.3.22.2108", "8.3.25.1257"]:
            d = arch / ver
            d.mkdir(parents=True)
            (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 3
        versions = [d.version for d in result]
        assert versions == sorted(versions)


class TestSingleVersionFallback:
    def test_direct_hbk_in_root(self, tmp_path, discovery):
        (tmp_path / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        assert len(result) == 1
        assert result[0].version is None  # can't parse version from tmp dir name
        assert result[0].platform_dir == tmp_path

    def test_version_parsed_from_dir_name(self, tmp_path, discovery):
        ver_dir = tmp_path / "8.3.25.1257"
        ver_dir.mkdir()
        (ver_dir / HBK_FILENAME).write_bytes(b"fake")

        # Pass the version dir directly (user points to specific version)
        result = discovery.discover(ver_dir)
        assert len(result) == 1
        assert result[0].version == PlatformVersion(8, 3, 25)


class TestEdgeCases:
    def test_nonexistent_path(self, discovery):
        from pathlib import Path

        result = discovery.discover(Path("/nonexistent/path/that/does/not/exist"))
        assert result == []

    def test_empty_directory(self, tmp_path, discovery):
        result = discovery.discover(tmp_path)
        assert result == []

    def test_results_sorted_ascending(self, tmp_path, discovery):
        for ver in ["8.3.25.1257", "8.3.18.1741", "8.3.22.2108"]:
            d = tmp_path / ver
            d.mkdir()
            (d / HBK_FILENAME).write_bytes(b"fake")

        result = discovery.discover(tmp_path)
        versions = [d.version for d in result]
        assert versions == sorted(versions)
