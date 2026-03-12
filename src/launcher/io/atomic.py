"""Atomic file operations with hermetic path validation.

All write operations validate that paths are within allowed boundaries
to prevent path escape attacks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def _validate_no_path_traversal(path: Path) -> None:
    """Reject paths containing '..' components."""
    resolved = path.resolve()
    if ".." in path.parts:
        raise ValueError(
            f"Path traversal detected: {path} (resolved to {resolved})"
        )


def _validate_path_in_boundary(path: Path, boundary: Path) -> None:
    """Ensure *path* resolves to somewhere inside *boundary*."""
    resolved = path.resolve()
    boundary_resolved = boundary.resolve()
    try:
        resolved.relative_to(boundary_resolved)
    except ValueError:
        raise ValueError(
            f"Path {resolved} is outside boundary {boundary_resolved}"
        )


def atomic_write_text(
    path: Path,
    text: str,
    encoding: str = "utf-8",
    *,
    validate_boundary: Optional[Path] = None,
) -> None:
    """Write text to file atomically with path validation.

    Args:
        path: Destination file path.
        text: Text content to write.
        encoding: Text encoding (default: utf-8).
        validate_boundary: Optional boundary to enforce.
    """
    _validate_no_path_traversal(path)

    if validate_boundary:
        _validate_path_in_boundary(path, validate_boundary)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def atomic_write_json(
    path: Path,
    obj: Any,
    *,
    validate_boundary: Optional[Path] = None,
    schema_path: Optional[str] = None,
) -> None:
    """Write JSON to file atomically with path validation.

    Args:
        path: Destination file path.
        obj: Object to serialize as JSON.
        validate_boundary: Optional boundary to enforce.
        schema_path: Optional path to JSON schema file. When provided,
            data is validated against the schema BEFORE writing.
    """
    if schema_path is not None:
        from .schema_validation import load_schema, validate

        schema = load_schema(Path(schema_path))
        validate(obj, schema, context=str(path.name))

    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    atomic_write_text(
        path,
        text,
        encoding="utf-8",
        validate_boundary=validate_boundary,
    )
