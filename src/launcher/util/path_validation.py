"""Hermetic path validation utilities.

Validates that all file operations are confined to allowed boundaries
and prevents path escape via .., absolute paths, or symlink traversal.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union


class PathValidationError(Exception):
    """Raised when path validation fails (policy violation)."""

    def __init__(self, message: str, error_code: str = "POLICY_PATH_ESCAPE"):
        super().__init__(message)
        self.error_code = error_code


def validate_path_in_boundary(
    path: Union[str, Path],
    boundary: Union[str, Path],
    *,
    resolve_symlinks: bool = True,
) -> Path:
    """Validate that a path is within the allowed boundary.

    Args:
        path: Path to validate
        boundary: Allowed boundary directory (e.g., RUN_DIR)
        resolve_symlinks: If True, resolve symlinks before checking

    Returns:
        Resolved path if valid

    Raises:
        PathValidationError: If path escapes boundary
    """
    path_obj = Path(path)
    boundary_obj = Path(boundary)

    if resolve_symlinks:
        try:
            path_obj = path_obj.resolve()
            boundary_obj = boundary_obj.resolve()
        except (OSError, RuntimeError) as e:
            raise PathValidationError(
                f"Failed to resolve path: {e}",
                error_code="POLICY_PATH_RESOLUTION_FAILED",
            ) from e

    try:
        path_obj.relative_to(boundary_obj)
    except ValueError:
        raise PathValidationError(
            f"Path '{path_obj}' escapes boundary '{boundary_obj}'",
            error_code="POLICY_PATH_ESCAPE",
        )

    return path_obj


def validate_path_in_allowed(
    path: Union[str, Path],
    allowed_paths: List[Union[str, Path]],
    *,
    boundary: Union[str, Path, None] = None,
) -> Path:
    """Validate that a path matches at least one allowed path pattern.

    Args:
        path: Path to validate
        allowed_paths: List of allowed path patterns (supports /** glob suffix)
        boundary: Optional boundary to enforce

    Returns:
        Resolved path if valid

    Raises:
        PathValidationError: If path doesn't match any allowed pattern or escapes boundary
    """
    path_obj = Path(path).resolve()

    if boundary:
        path_obj = validate_path_in_boundary(path_obj, boundary)

    for allowed in allowed_paths:
        allowed_str = str(allowed)

        if allowed_str.endswith("/**"):
            allowed_prefix = Path(allowed_str[:-3]).resolve()
            try:
                path_obj.relative_to(allowed_prefix)
                return path_obj
            except ValueError:
                continue

        allowed_path = Path(allowed).resolve()
        if path_obj == allowed_path or path_obj.is_relative_to(allowed_path):
            return path_obj

    raise PathValidationError(
        f"Path '{path_obj}' not in allowed paths: {allowed_paths}",
        error_code="POLICY_PATH_NOT_ALLOWED",
    )


def validate_no_path_traversal(path: Union[str, Path]) -> None:
    """Validate that a path does not contain .. or other traversal patterns.

    Raises:
        PathValidationError: If path contains .. or other suspicious patterns
    """
    path_str = str(path)
    path_parts = Path(path).parts

    if ".." in path_parts:
        raise PathValidationError(
            f"Path '{path}' contains parent directory traversal (..)",
            error_code="POLICY_PATH_TRAVERSAL",
        )

    suspicious_patterns = ["~", "%", "$"]
    for pattern in suspicious_patterns:
        if pattern in path_str:
            raise PathValidationError(
                f"Path '{path}' contains suspicious pattern '{pattern}'",
                error_code="POLICY_PATH_SUSPICIOUS",
            )


def is_path_in_boundary(
    path: Union[str, Path],
    boundary: Union[str, Path],
) -> bool:
    """Check if a path is within boundary (non-raising version)."""
    try:
        validate_path_in_boundary(path, boundary)
        return True
    except PathValidationError:
        return False


def validate_run_dir_under_runs(run_dir: Union[str, Path]) -> Path:
    """Validate RUN_DIR is located under a ``runs/`` directory.

    Returns:
        Resolved RUN_DIR path

    Raises:
        PathValidationError: If path cannot be resolved or is not under runs/
    """
    run_dir_obj = Path(run_dir)

    try:
        run_dir_obj = run_dir_obj.resolve()
    except (OSError, RuntimeError) as e:
        raise PathValidationError(
            f"Failed to resolve RUN_DIR path: {e}",
            error_code="POLICY_RUN_DIR_RESOLUTION_FAILED",
        ) from e

    if run_dir_obj.parent.name.lower() != "runs":
        raise PathValidationError(
            f"RUN_DIR '{run_dir_obj}' is outside the required 'runs/' directory. "
            f"Expected path format: <...>/runs/<run_id>",
            error_code="POLICY_RUN_DIR_OUTSIDE_RUNS",
        )

    return run_dir_obj


def validate_path_matches_patterns(
    path: Union[str, Path],
    patterns: List[str],
    *,
    repo_root: Union[str, Path],
) -> bool:
    """Check if path matches any glob pattern.

    Supports:
    - Exact match: pyproject.toml
    - Recursive glob: reports/** (matches reports/a.txt, reports/sub/b.txt)
    - Wildcard dir: src/launcher/workers/w1_*/**
    - Wildcard file: src/**/*.py
    """
    path_obj = Path(path)
    repo_root_obj = Path(repo_root).resolve()

    try:
        if path_obj.is_absolute():
            relative_path = path_obj.relative_to(repo_root_obj)
        else:
            relative_path = path_obj
    except ValueError:
        return False

    for pattern in patterns:
        pattern_str = str(pattern).replace("\\", "/")
        relative_path_str = str(relative_path).replace("\\", "/")

        if pattern_str == relative_path_str:
            return True

        if relative_path.match(pattern_str):
            return True

        if pattern_str.endswith("/**"):
            prefix = pattern_str[:-3]
            if relative_path_str.startswith(prefix + "/") or relative_path_str == prefix:
                return True

    return False


def is_source_code_path(path: Union[str, Path], repo_root: Union[str, Path]) -> bool:
    """Check if path is source code requiring authorization.

    Protected paths:
    - src/launcher/** - All source code
    - specs/** - All specifications
    """
    protected_patterns = [
        "src/launcher/**",
        "specs/**",
    ]

    return validate_path_matches_patterns(path, protected_patterns, repo_root=repo_root)
