"""Tests for PlatformVersion value object and find_closest_version."""

import pytest

from mcp_bsl_context.domain.value_objects import PlatformVersion, find_closest_version


class TestPlatformVersionParse:
    def test_three_components(self):
        v = PlatformVersion.parse("8.3.25")
        assert v == PlatformVersion(8, 3, 25)

    def test_four_components_ignores_build(self):
        v = PlatformVersion.parse("8.3.25.1257")
        assert v == PlatformVersion(8, 3, 25)

    def test_from_directory_name(self):
        v = PlatformVersion.parse("8.3.18.1741")
        assert v == PlatformVersion(8, 3, 18)

    def test_invalid_string_returns_none(self):
        assert PlatformVersion.parse("invalid") is None

    def test_two_components_returns_none(self):
        assert PlatformVersion.parse("8.3") is None

    def test_empty_string_returns_none(self):
        assert PlatformVersion.parse("") is None

    def test_embedded_in_path(self):
        v = PlatformVersion.parse("platform-8.3.25-release")
        assert v == PlatformVersion(8, 3, 25)


class TestPlatformVersionOrdering:
    def test_less_than(self):
        assert PlatformVersion(8, 3, 18) < PlatformVersion(8, 3, 25)

    def test_equal(self):
        assert PlatformVersion(8, 3, 25) == PlatformVersion(8, 3, 25)

    def test_minor_version_ordering(self):
        assert PlatformVersion(8, 3, 25) < PlatformVersion(8, 4, 1)

    def test_major_version_ordering(self):
        assert PlatformVersion(8, 3, 99) < PlatformVersion(9, 0, 0)

    def test_max_of_list(self):
        versions = [
            PlatformVersion(8, 3, 18),
            PlatformVersion(8, 3, 25),
            PlatformVersion(8, 3, 22),
        ]
        assert max(versions) == PlatformVersion(8, 3, 25)


class TestPlatformVersionStr:
    def test_str_representation(self):
        assert str(PlatformVersion(8, 3, 25)) == "8.3.25"


class TestPlatformVersionDistance:
    def test_zero_distance_same_version(self):
        v = PlatformVersion(8, 3, 25)
        assert v.distance_to(v) == 0

    def test_symmetric_distance(self):
        a = PlatformVersion(8, 3, 18)
        b = PlatformVersion(8, 3, 25)
        assert a.distance_to(b) == b.distance_to(a)

    def test_release_difference(self):
        a = PlatformVersion(8, 3, 20)
        b = PlatformVersion(8, 3, 25)
        assert a.distance_to(b) == 5

    def test_minor_weighs_more(self):
        a = PlatformVersion(8, 3, 20)
        b = PlatformVersion(8, 4, 20)
        assert a.distance_to(b) == 100

    def test_major_weighs_most(self):
        a = PlatformVersion(8, 3, 20)
        b = PlatformVersion(9, 3, 20)
        assert a.distance_to(b) == 10000


class TestFindClosestVersion:
    def test_exact_match(self):
        target = PlatformVersion(8, 3, 22)
        available = [
            PlatformVersion(8, 3, 18),
            PlatformVersion(8, 3, 22),
            PlatformVersion(8, 3, 25),
        ]
        assert find_closest_version(target, available) == PlatformVersion(8, 3, 22)

    def test_closest_higher_on_tie(self):
        target = PlatformVersion(8, 3, 20)
        available = [PlatformVersion(8, 3, 18), PlatformVersion(8, 3, 22)]
        # distance to 18 = 2, distance to 22 = 2, tie → prefer higher
        assert find_closest_version(target, available) == PlatformVersion(8, 3, 22)

    def test_closest_by_distance(self):
        target = PlatformVersion(8, 3, 20)
        available = [PlatformVersion(8, 3, 10), PlatformVersion(8, 3, 25)]
        # distance to 10 = 10, distance to 25 = 5 → pick 25
        assert find_closest_version(target, available) == PlatformVersion(8, 3, 25)

    def test_single_available(self):
        target = PlatformVersion(8, 3, 20)
        available = [PlatformVersion(8, 3, 25)]
        assert find_closest_version(target, available) == PlatformVersion(8, 3, 25)

    def test_empty_raises_value_error(self):
        target = PlatformVersion(8, 3, 20)
        with pytest.raises(ValueError):
            find_closest_version(target, [])

    def test_prefer_closer_lower(self):
        target = PlatformVersion(8, 3, 23)
        available = [PlatformVersion(8, 3, 18), PlatformVersion(8, 3, 25)]
        # distance to 18 = 5, distance to 25 = 2 → pick 25
        assert find_closest_version(target, available) == PlatformVersion(8, 3, 25)
