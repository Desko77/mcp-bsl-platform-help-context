"""Search query and platform version value objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from .enums import ApiType


@dataclass(frozen=True)
class SearchOptions:
    case_sensitive: bool = False
    exact_match: bool = False


@dataclass(frozen=True)
class SearchQuery:
    query: str
    type: ApiType | None = None
    limit: int = 10
    options: SearchOptions = field(default_factory=SearchOptions)


@dataclass(frozen=True, order=True)
class PlatformVersion:
    """Platform version in 8.XX.XX format. Build number (4th component) is ignored.

    Supports natural ordering via order=True (major, minor, release).
    """

    major: int
    minor: int
    release: int

    _VERSION_RE: ClassVar[re.Pattern[str]] = re.compile(r"(\d+)\.(\d+)\.(\d+)")

    @classmethod
    def parse(cls, version_string: str) -> PlatformVersion | None:
        """Parse from '8.3.25', '8.3.25.1257', or directory name.

        Returns None if the string does not contain a valid 3-component version.
        """
        match = cls._VERSION_RE.search(version_string)
        if match is None:
            return None
        return cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    def distance_to(self, other: PlatformVersion) -> int:
        """Weighted numeric distance for closest-match resolution.

        Major differences weigh 10000x, minor 100x, release 1x.
        """
        return (
            abs(self.major - other.major) * 10000
            + abs(self.minor - other.minor) * 100
            + abs(self.release - other.release)
        )

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.release}"


def find_closest_version(
    target: PlatformVersion,
    available: list[PlatformVersion],
) -> PlatformVersion:
    """Find the version closest to target by weighted distance.

    On tie (equal distance), prefers the higher version (more complete docs).
    Raises ValueError if available list is empty.
    """
    if not available:
        raise ValueError("No versions available for resolution")
    return min(
        available,
        key=lambda v: (target.distance_to(v), -v.major, -v.minor, -v.release),
    )
