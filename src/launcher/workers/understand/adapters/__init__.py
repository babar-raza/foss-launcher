"""Platform adapter registry and dispatch."""
from __future__ import annotations

from launcher.workers.understand.adapters._base import PlatformExtractor
from launcher.workers.understand.adapters._generic import GenericExtractor
from launcher.workers.understand.adapters._python import PythonExtractor
from launcher.workers.understand.adapters._typescript import TypeScriptExtractor

_REGISTRY: dict[str, type[PlatformExtractor]] = {
    "python": PythonExtractor,
    "typescript": TypeScriptExtractor,
    "javascript": TypeScriptExtractor,  # JS uses same extraction path
    "node": TypeScriptExtractor,        # "node" platform alias
}


def get_extractor(platform: str) -> PlatformExtractor:
    """Resolve a platform extractor by platform identifier.

    Falls back to GenericExtractor for unregistered platforms.
    """
    cls = _REGISTRY.get(platform, GenericExtractor)
    return cls()


__all__ = [
    "PlatformExtractor",
    "PythonExtractor",
    "TypeScriptExtractor",
    "GenericExtractor",
    "get_extractor",
]
