from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from ..util.errors import ToolchainError
from .yamlio import load_yaml


def toolchain_lock_path(repo_root: Path) -> Path:
    return repo_root / "config" / "toolchain.lock.yaml"


def _iter_values(obj: Any) -> Iterable[Any]:
    """Depth-first traversal over a YAML-loaded structure."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_values(v)
    elif isinstance(obj, list):
        for i in obj:
            yield from _iter_values(i)
    else:
        yield obj


def load_toolchain_lock(repo_root: Path) -> Dict[str, Any]:
    path = toolchain_lock_path(repo_root)
    if not path.exists():
        raise ToolchainError(f"Missing toolchain lock: {path}")

    data = load_yaml(path)
    if not data.get("schema_version"):
        raise ToolchainError(f"toolchain lock missing schema_version: {path}")

    # Fail-fast sentinel check.
    # NOTE: do not scan raw file text because docs/comments may mention PIN_ME.
    for v in _iter_values(data):
        if v == "PIN_ME":
            raise ToolchainError("toolchain.lock.yaml contains PIN_ME sentinel values (must be pinned)")

    return data
