"""File scanning for secrets with allowlist support.

Binding contract: specs/34_strict_compliance_guarantees.md (security requirements)

Provides:
1. File scanning (text files only, skip binary)
2. Directory scanning with recursive traversal
3. Allowlist support for test fixtures
4. Scan result aggregation
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set

from .secret_detector import SecretMatch, detect_secrets


@dataclass
class ScanResult:
    """Result of scanning a file or directory."""

    file_path: Optional[str]
    secrets_found: List[SecretMatch] = field(default_factory=list)
    scan_timestamp: str = ""
    is_binary: bool = False
    is_allowlisted: bool = False
    error: Optional[str] = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if not self.scan_timestamp:
            self.scan_timestamp = datetime.now(timezone.utc).isoformat()


def is_binary_file(file_path: Path) -> bool:
    """Check if a file is binary by looking for null bytes.

    Args:
        file_path: Path to file

    Returns:
        True if binary, False if text
    """
    try:
        with open(file_path, "rb") as f:
            # Read first 8KB to check for null bytes
            chunk = f.read(8192)
            return b"\x00" in chunk
    except Exception:
        return True  # Assume binary if can't read


def is_allowlisted(file_path: Path, allowlist: Optional[List[str]] = None) -> bool:
    """Check if a file is in the allowlist.

    Allowlist entries can be:
    - Exact file names (e.g., "test_secrets.py")
    - Path patterns (e.g., "tests/fixtures/*")
    - Directory names (e.g., "test_data/")

    Args:
        file_path: Path to check
        allowlist: List of allowlist patterns

    Returns:
        True if allowlisted, False otherwise
    """
    if not allowlist:
        return False

    # Normalize path separators for comparison
    file_str = str(file_path).replace("\\", "/")
    file_name = file_path.name

    for pattern in allowlist:
        # Normalize pattern as well
        pattern = pattern.replace("\\", "/")

        # Exact name match
        if pattern == file_name:
            return True

        # Path contains pattern (for directory names)
        if pattern in file_str:
            return True

        # Glob-style pattern (simple implementation)
        if "*" in pattern:
            pattern_parts = pattern.split("*")
            # Check if all non-empty parts appear in order
            pos = 0
            match = True
            for part in pattern_parts:
                if part:
                    idx = file_str.find(part, pos)
                    if idx == -1:
                        match = False
                        break
                    pos = idx + len(part)
            if match:
                return True

    return False


def scan_file(
    file_path: Path,
    allowlist: Optional[List[str]] = None,
) -> ScanResult:
    """Scan a single file for secrets.

    Args:
        file_path: Path to file to scan
        allowlist: List of allowlist patterns

    Returns:
        ScanResult with findings
    """
    result = ScanResult(file_path=str(file_path))

    # Check if allowlisted
    if is_allowlisted(file_path, allowlist):
        result.is_allowlisted = True
        return result

    # Check if binary
    if is_binary_file(file_path):
        result.is_binary = True
        return result

    # Read and scan file
    try:
        content = file_path.read_text(encoding="utf-8")
        result.secrets_found = detect_secrets(content)
    except UnicodeDecodeError:
        # File claimed to be text but has encoding issues
        result.is_binary = True
    except Exception as e:
        result.error = str(e)

    return result


def scan_directory(
    directory: Path,
    allowlist: Optional[List[str]] = None,
    recursive: bool = True,
    exclude_dirs: Optional[Set[str]] = None,
) -> List[ScanResult]:
    """Scan a directory for secrets.

    Args:
        directory: Directory to scan
        allowlist: List of allowlist patterns
        recursive: Whether to scan subdirectories
        exclude_dirs: Set of directory names to exclude (e.g., {".git", "node_modules"})

    Returns:
        List of ScanResults for all files scanned
    """
    if exclude_dirs is None:
        exclude_dirs = {".git", ".svn", "node_modules", "__pycache__", ".venv", "venv"}

    results: List[ScanResult] = []

    if not directory.exists() or not directory.is_dir():
        return results

    # Get all files
    if recursive:
        # Filter out excluded directories
        for item in directory.rglob("*"):
            if item.is_file():
                # Check if any parent is in exclude_dirs
                if any(part in exclude_dirs for part in item.parts):
                    continue
                results.append(scan_file(item, allowlist))
    else:
        for item in directory.iterdir():
            if item.is_file():
                results.append(scan_file(item, allowlist))

    # Sort by file path for determinism
    results.sort(key=lambda r: r.file_path or "")

    return results


def filter_results_with_secrets(results: List[ScanResult]) -> List[ScanResult]:
    """Filter scan results to only those with secrets found.

    Args:
        results: List of all scan results

    Returns:
        List of results with secrets
    """
    return [r for r in results if r.secrets_found and not r.is_allowlisted]


def count_total_secrets(results: List[ScanResult]) -> int:
    """Count total secrets found across all results.

    Args:
        results: List of scan results

    Returns:
        Total count of secrets
    """
    return sum(len(r.secrets_found) for r in results if not r.is_allowlisted)
