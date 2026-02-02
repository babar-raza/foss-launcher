"""Hermetic path validation utilities (Guarantee B).

Validates that all file operations are confined to allowed boundaries
and prevents path escape via .., absolute paths, or symlink traversal.

Binding contract: specs/34_strict_compliance_guarantees.md (Guarantee B)
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

    Examples:
        >>> validate_path_in_boundary("/run/dir/file.txt", "/run/dir")
        Path("/run/dir/file.txt")

        >>> validate_path_in_boundary("/run/dir/../other/file.txt", "/run/dir")
        PathValidationError: Path escapes boundary

        >>> validate_path_in_boundary("/etc/passwd", "/run/dir")
        PathValidationError: Path escapes boundary
    """
    path_obj = Path(path)
    boundary_obj = Path(boundary)

    # Resolve symlinks if requested
    if resolve_symlinks:
        try:
            path_obj = path_obj.resolve()
            boundary_obj = boundary_obj.resolve()
        except (OSError, RuntimeError) as e:
            raise PathValidationError(
                f"Failed to resolve path: {e}",
                error_code="POLICY_PATH_RESOLUTION_FAILED"
            ) from e

    # Check if path is relative to boundary
    try:
        path_obj.relative_to(boundary_obj)
    except ValueError:
        raise PathValidationError(
            f"Path '{path_obj}' escapes boundary '{boundary_obj}'",
            error_code="POLICY_PATH_ESCAPE"
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
        boundary: Optional boundary to enforce (validates both pattern match and boundary)

    Returns:
        Resolved path if valid

    Raises:
        PathValidationError: If path doesn't match any allowed pattern or escapes boundary

    Examples:
        >>> validate_path_in_allowed("src/foo/bar.py", ["src/**"])
        Path("src/foo/bar.py")

        >>> validate_path_in_allowed("tests/test.py", ["src/**"])
        PathValidationError: Path not in allowed paths
    """
    path_obj = Path(path).resolve()

    # First validate boundary if provided
    if boundary:
        path_obj = validate_path_in_boundary(path_obj, boundary)

    # Check if path matches any allowed pattern
    for allowed in allowed_paths:
        allowed_str = str(allowed)

        # Handle /** glob pattern
        if allowed_str.endswith("/**"):
            allowed_prefix = Path(allowed_str[:-3]).resolve()
            try:
                path_obj.relative_to(allowed_prefix)
                return path_obj
            except ValueError:
                continue

        # Handle exact path match
        allowed_path = Path(allowed).resolve()
        if path_obj == allowed_path or path_obj.is_relative_to(allowed_path):
            return path_obj

    raise PathValidationError(
        f"Path '{path_obj}' not in allowed paths: {allowed_paths}",
        error_code="POLICY_PATH_NOT_ALLOWED"
    )


def validate_no_path_traversal(path: Union[str, Path]) -> None:
    """Validate that a path does not contain .. or other traversal patterns.

    This is a lightweight check that can be done before resolution.

    Args:
        path: Path to validate (can be relative or absolute)

    Raises:
        PathValidationError: If path contains .. or other suspicious patterns

    Examples:
        >>> validate_no_path_traversal("src/foo/bar.py")
        None

        >>> validate_no_path_traversal("src/../etc/passwd")
        PathValidationError: Path contains traversal
    """
    path_str = str(path)
    path_parts = Path(path).parts

    # Check for .. in path
    if ".." in path_parts:
        raise PathValidationError(
            f"Path '{path}' contains parent directory traversal (..)",
            error_code="POLICY_PATH_TRAVERSAL"
        )

    # Check for suspicious patterns
    suspicious_patterns = ["~", "%", "$"]
    for pattern in suspicious_patterns:
        if pattern in path_str:
            raise PathValidationError(
                f"Path '{path}' contains suspicious pattern '{pattern}'",
                error_code="POLICY_PATH_SUSPICIOUS"
            )


def is_path_in_boundary(
    path: Union[str, Path],
    boundary: Union[str, Path],
) -> bool:
    """Check if a path is within boundary (non-raising version).

    Args:
        path: Path to check
        boundary: Boundary directory

    Returns:
        True if path is within boundary, False otherwise
    """
    try:
        validate_path_in_boundary(path, boundary)
        return True
    except PathValidationError:
        return False


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
    - Wildcard dir: src/launch/workers/w1_*/** (matches w1_repo_scout, w1_*)
    - Wildcard file: src/**/*.py (matches all .py files under src/)

    Args:
        path: Path to check (absolute or relative)
        patterns: List of glob patterns (relative to repo_root)
        repo_root: Repository root for resolving patterns

    Returns:
        True if path matches any pattern, False otherwise

    Examples:
        >>> validate_path_matches_patterns(
        ...     "src/launch/__init__.py",
        ...     ["src/launch/__init__.py"],
        ...     repo_root=Path(".")
        ... )
        True

        >>> validate_path_matches_patterns(
        ...     "reports/agents/AGENT_B/TC-100/report.md",
        ...     ["reports/**"],
        ...     repo_root=Path(".")
        ... )
        True

        >>> validate_path_matches_patterns(
        ...     "src/launch/workers/w1_repo_scout/worker.py",
        ...     ["src/launch/workers/w1_*/**"],
        ...     repo_root=Path(".")
        ... )
        True
    """
    path_obj = Path(path)
    repo_root_obj = Path(repo_root).resolve()

    # Make path relative to repo_root for matching
    try:
        # Try to make path relative to repo_root
        if path_obj.is_absolute():
            relative_path = path_obj.relative_to(repo_root_obj)
        else:
            # Path is already relative, use as-is
            relative_path = path_obj
    except ValueError:
        # Path is not under repo_root
        return False

    # Check against each pattern
    for pattern in patterns:
        pattern_str = str(pattern).replace("\\", "/")  # Normalize separators
        relative_path_str = str(relative_path).replace("\\", "/")

        # Exact match
        if pattern_str == relative_path_str:
            return True

        # Glob match using pathlib
        # Convert pattern to Path for matching
        pattern_path = Path(pattern_str)

        # Use match() for glob patterns
        if relative_path.match(pattern_str):
            return True

        # Special case: pattern/** should match pattern/anything
        if pattern_str.endswith("/**"):
            prefix = pattern_str[:-3]  # Remove /**
            if relative_path_str.startswith(prefix + "/") or relative_path_str == prefix:
                return True

    return False


def is_source_code_path(path: Union[str, Path], repo_root: Union[str, Path]) -> bool:
    """Check if path is source code requiring taskcard authorization.

    Protected paths that require taskcard:
    - src/launch/** - All source code (all files)
    - specs/** - All specifications (all files)
    - plans/taskcards/** - Taskcard definitions (all files)

    Args:
        path: Path to check
        repo_root: Repository root

    Returns:
        True if path requires taskcard authorization, False otherwise

    Examples:
        >>> is_source_code_path("src/launch/test.py", Path("."))
        True

        >>> is_source_code_path("reports/test.md", Path("."))
        False
    """
    protected_patterns = [
        "src/launch/**",  # Protect entire src/launch directory
        "specs/**",  # Protect entire specs directory
        "plans/taskcards/**",  # Protect entire taskcards directory
    ]

    return validate_path_matches_patterns(path, protected_patterns, repo_root=repo_root)
