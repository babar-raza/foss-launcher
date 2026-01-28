"""
Evidence Package Creation.

Creates ZIP archives containing all run artifacts with manifest generation
and file hashing.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..io.hashing import sha256_file


@dataclass
class PackageFile:
    """Metadata for a single file in package."""

    relative_path: str
    size_bytes: int
    sha256: str
    modified_at: str  # ISO 8601

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return asdict(self)


@dataclass
class PackageManifest:
    """Manifest of files in evidence package."""

    package_created_at: str  # ISO 8601
    run_id: str
    total_files: int
    total_size_bytes: int
    files: list[PackageFile]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "package_created_at": self.package_created_at,
            "run_id": self.run_id,
            "total_files": self.total_files,
            "total_size_bytes": self.total_size_bytes,
            "files": [f.to_dict() for f in self.files],
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def create_evidence_package(
    run_dir: Path,
    output_path: Path,
    include_patterns: list[str] | None = None,
) -> PackageManifest:
    """
    Create evidence package ZIP with all run artifacts.

    Args:
        run_dir: Path to run directory (e.g., runs/<run_id>)
        output_path: Path to output ZIP file (e.g., runs/<run_id>/evidence.zip)
        include_patterns: List of glob patterns to include (default: all files)

    Returns:
        PackageManifest with metadata for all packaged files
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    # Default patterns: include all artifacts, reports, events, and snapshot
    if include_patterns is None:
        include_patterns = [
            "artifacts/**/*",
            "reports/**/*",
            "events.ndjson",
            "snapshot.json",
            "run_config.yaml",
            "run_config.json",
            "validation_report.json",
        ]

    # Collect all files to package
    files_to_package: list[Path] = []
    for pattern in include_patterns:
        files_to_package.extend(run_dir.glob(pattern))

    # Filter to only actual files (not directories)
    files_to_package = [f for f in files_to_package if f.is_file()]

    # Sort for deterministic ordering
    files_to_package.sort()

    # Create ZIP archive
    package_files: list[PackageFile] = []
    total_size = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_package:
            relative_path = file_path.relative_to(run_dir)
            arcname = str(relative_path).replace("\\", "/")  # Use forward slashes

            # Add to ZIP
            zipf.write(file_path, arcname=arcname)

            # Compute metadata
            size_bytes = file_path.stat().st_size
            sha256_hash = sha256_file(file_path)
            modified_at = datetime.fromtimestamp(
                file_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()

            package_files.append(
                PackageFile(
                    relative_path=arcname,
                    size_bytes=size_bytes,
                    sha256=sha256_hash,
                    modified_at=modified_at,
                )
            )

            total_size += size_bytes

    # Extract run_id from directory name
    run_id = run_dir.name

    # Create manifest
    manifest = PackageManifest(
        package_created_at=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        total_files=len(package_files),
        total_size_bytes=total_size,
        files=package_files,
    )

    return manifest
