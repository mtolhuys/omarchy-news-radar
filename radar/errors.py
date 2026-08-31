"""Typed public-safe failures."""

from __future__ import annotations


class RadarError(Exception):
    """Base class for expected Radar failures."""


class ValidationError(RadarError):
    """Untrusted input failed a documented contract."""


class StorageError(RadarError):
    """A local file could not be accessed safely."""


class FetchError(RadarError):
    """A bounded network fetch failed."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


class ShortcutError(RadarError):
    """Shortcut inspection or mutation failed closed."""
