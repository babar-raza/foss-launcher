"""Atomic file operations with hermetic path validation (Guarantee B).

All write operations validate that paths are within allowed boundaries
to prevent path escape attacks.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from ..util.path_validation import validate_no_path_traversal


def atomic_write_text(
    path: Path,
    text: str,
    encoding: str = 'utf-8',
    *,
    validate_boundary: Optional[Path] = None,
) -> None:
    """Write text to file atomically with path validation.

    Args:
        path: Destination file path
        text: Text content to write
        encoding: Text encoding (default: utf-8)
        validate_boundary: Optional boundary to enforce (e.g., RUN_DIR)

    Raises:
        PathValidationError: If path validation fails
    """
    # Basic path traversal check
    validate_no_path_traversal(path)

    # Boundary validation if provided
    if validate_boundary:
        from ..util.path_validation import validate_path_in_boundary
        validate_path_in_boundary(path, validate_boundary)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def atomic_write_json(
    path: Path,
    obj: Any,
    *,
    validate_boundary: Optional[Path] = None,
) -> None:
    """Write JSON to file atomically with path validation.

    Args:
        path: Destination file path
        obj: Object to serialize as JSON
        validate_boundary: Optional boundary to enforce (e.g., RUN_DIR)

    Raises:
        PathValidationError: If path validation fails
    """
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    atomic_write_text(path, text, encoding='utf-8', validate_boundary=validate_boundary)
