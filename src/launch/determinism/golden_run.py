"""Golden run capture and verification.

Provides functionality to:
1. Capture golden runs with deterministic artifact hashes
2. Verify new runs against golden baselines
3. Manage golden run storage and metadata

Spec: specs/10_determinism_and_caching.md (REQ-079)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Determinism guarantee: use fixed hash seed
os.environ.setdefault("PYTHONHASHSEED", "0")


@dataclass
class ArtifactMismatch:
    """Describes a mismatch between golden and actual artifact."""

    artifact_path: str
    expected_hash: str
    actual_hash: str
    size_difference: int  # bytes

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class VerificationResult:
    """Result of golden run verification."""

    run_id: str
    golden_run_id: str
    passed: bool
    mismatches: List[ArtifactMismatch]
    verified_at: str  # ISO 8601

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "golden_run_id": self.golden_run_id,
            "passed": self.passed,
            "mismatches": [m.to_dict() for m in self.mismatches],
            "verified_at": self.verified_at,
        }


@dataclass
class GoldenRunMetadata:
    """Metadata for a golden run."""

    run_id: str
    product_name: str
    git_ref: str
    captured_at: str  # ISO 8601
    git_sha: str
    run_config_hash: str  # SHA256 of run_config.yaml
    artifact_hashes: Dict[str, str]  # artifact_path -> SHA256
    total_artifacts: int

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> GoldenRunMetadata:
        """Create from dictionary."""
        return cls(**data)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of SHA256 hash
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def _compute_config_hash(run_dir: Path) -> str:
    """Compute SHA256 hash of run_config.yaml.

    Args:
        run_dir: Path to run directory

    Returns:
        Hex digest of SHA256 hash

    Raises:
        FileNotFoundError: If run_config.yaml not found
    """
    config_path = run_dir / "run_config.yaml"
    if not config_path.exists():
        # Try JSON variant
        config_path = run_dir / "run_config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"No run_config found in {run_dir}")

    return _compute_file_hash(config_path)


def _normalize_line_endings(content: bytes) -> bytes:
    """Normalize line endings to LF.

    Args:
        content: File content

    Returns:
        Content with normalized line endings
    """
    # Replace CRLF with LF
    return content.replace(b"\r\n", b"\n")


def _strip_trailing_whitespace(content: bytes) -> bytes:
    """Strip trailing whitespace from text files.

    Args:
        content: File content

    Returns:
        Content with trailing whitespace stripped per line
    """
    lines = content.split(b"\n")
    stripped = [line.rstrip() for line in lines]
    return b"\n".join(stripped)


def _compute_normalized_hash(file_path: Path) -> str:
    """Compute normalized hash (line endings + trailing whitespace).

    Args:
        file_path: Path to file

    Returns:
        SHA256 hash of normalized content
    """
    with open(file_path, "rb") as f:
        content = f.read()

    # Normalize line endings
    content = _normalize_line_endings(content)

    # Strip trailing whitespace for text files
    # Skip for binary files (simple heuristic: if null byte present, it's binary)
    if b"\x00" not in content[:8192]:  # Check first 8KB
        content = _strip_trailing_whitespace(content)

    sha256 = hashlib.sha256()
    sha256.update(content)
    return sha256.hexdigest()


def _collect_artifacts(run_dir: Path, exclude_events: bool = True) -> Dict[str, str]:
    """Collect all artifacts and compute their hashes.

    Args:
        run_dir: Path to run directory
        exclude_events: If True, exclude events.ndjson from collection

    Returns:
        Dictionary mapping relative artifact path to SHA256 hash
    """
    artifact_hashes: Dict[str, str] = {}
    artifacts_dir = run_dir / "artifacts"

    if not artifacts_dir.exists():
        return artifact_hashes

    # Collect all files in artifacts directory
    for file_path in sorted(artifacts_dir.rglob("*")):
        if file_path.is_file():
            # Exclude events.ndjson per spec (timestamps/UUIDs vary)
            if exclude_events and file_path.name == "events.ndjson":
                continue

            # Use relative path from run_dir for portability
            rel_path = str(file_path.relative_to(run_dir))
            artifact_hashes[rel_path] = _compute_normalized_hash(file_path)

    # Also collect drafts
    drafts_dir = run_dir / "drafts"
    if drafts_dir.exists():
        for file_path in sorted(drafts_dir.rglob("*.md")):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(run_dir))
                artifact_hashes[rel_path] = _compute_normalized_hash(file_path)

    return artifact_hashes


def _get_golden_runs_dir(product_name: str, git_ref: str) -> Path:
    """Get golden runs directory for product and ref.

    Args:
        product_name: Product name
        git_ref: Git reference

    Returns:
        Path to golden runs directory
    """
    # Use artifacts/golden_runs/<product>/<ref>/
    base_dir = Path("artifacts") / "golden_runs" / product_name / git_ref
    return base_dir


def capture_golden_run(
    run_dir: Path,
    product_name: str,
    git_ref: str,
    git_sha: str,
) -> GoldenRunMetadata:
    """Capture a golden run by hashing all artifacts.

    Args:
        run_dir: Path to completed run directory
        product_name: Product name
        git_ref: Git reference
        git_sha: Git commit SHA

    Returns:
        GoldenRunMetadata with captured information

    Raises:
        FileNotFoundError: If run directory or required files not found
        ValueError: If run_dir does not contain valid run structure
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    # Extract run_id from directory name
    run_id = run_dir.name

    # Compute run_config hash
    run_config_hash = _compute_config_hash(run_dir)

    # Collect and hash all artifacts
    artifact_hashes = _collect_artifacts(run_dir, exclude_events=True)

    if not artifact_hashes:
        raise ValueError(f"No artifacts found in {run_dir}")

    # Create metadata
    metadata = GoldenRunMetadata(
        run_id=run_id,
        product_name=product_name,
        git_ref=git_ref,
        captured_at=datetime.now(timezone.utc).isoformat(),
        git_sha=git_sha,
        run_config_hash=run_config_hash,
        artifact_hashes=artifact_hashes,
        total_artifacts=len(artifact_hashes),
    )

    # Store golden run
    golden_dir = _get_golden_runs_dir(product_name, git_ref)
    golden_run_dir = golden_dir / run_id
    golden_run_dir.mkdir(parents=True, exist_ok=True)

    # Write metadata
    metadata_path = golden_run_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata.to_dict(), f, indent=2, sort_keys=True)

    # Copy artifacts for reference
    artifacts_copy_dir = golden_run_dir / "artifacts"
    artifacts_copy_dir.mkdir(exist_ok=True)

    # Copy all artifacts
    for rel_path in sorted(artifact_hashes.keys()):
        src = run_dir / rel_path
        dst = golden_run_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return metadata


def verify_against_golden(
    run_dir: Path,
    golden_run_id: str,
    product_name: Optional[str] = None,
    git_ref: Optional[str] = None,
) -> VerificationResult:
    """Verify a run against a golden baseline.

    Args:
        run_dir: Path to run directory to verify
        golden_run_id: ID of golden run to compare against
        product_name: Optional product name (for locating golden run)
        git_ref: Optional git ref (for locating golden run)

    Returns:
        VerificationResult with comparison details

    Raises:
        FileNotFoundError: If golden run or run directory not found
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    # Extract run_id from directory name
    run_id = run_dir.name

    # Load golden run metadata
    golden_metadata = None
    if product_name and git_ref:
        golden_dir = _get_golden_runs_dir(product_name, git_ref)
        golden_run_dir = golden_dir / golden_run_id
        metadata_path = golden_run_dir / "metadata.json"
    else:
        # Search all golden runs
        golden_runs = list_golden_runs()
        for meta in golden_runs:
            if meta.run_id == golden_run_id:
                golden_metadata = meta
                golden_dir = _get_golden_runs_dir(meta.product_name, meta.git_ref)
                golden_run_dir = golden_dir / golden_run_id
                metadata_path = golden_run_dir / "metadata.json"
                break

        if not golden_metadata:
            raise FileNotFoundError(f"Golden run not found: {golden_run_id}")

    if not metadata_path.exists():
        raise FileNotFoundError(f"Golden run metadata not found: {metadata_path}")

    # Load golden metadata
    with open(metadata_path, encoding="utf-8") as f:
        golden_data = json.load(f)
        golden_metadata = GoldenRunMetadata.from_dict(golden_data)

    # Collect current run artifacts
    current_hashes = _collect_artifacts(run_dir, exclude_events=True)

    # Compare hashes
    mismatches: List[ArtifactMismatch] = []

    # Check all golden artifacts exist in current run
    for artifact_path, expected_hash in sorted(golden_metadata.artifact_hashes.items()):
        actual_hash = current_hashes.get(artifact_path)

        if actual_hash is None:
            # Artifact missing in current run
            mismatches.append(
                ArtifactMismatch(
                    artifact_path=artifact_path,
                    expected_hash=expected_hash,
                    actual_hash="MISSING",
                    size_difference=-1,
                )
            )
        elif actual_hash != expected_hash:
            # Hash mismatch
            golden_file = golden_run_dir / artifact_path
            current_file = run_dir / artifact_path

            golden_size = golden_file.stat().st_size if golden_file.exists() else 0
            current_size = current_file.stat().st_size if current_file.exists() else 0

            mismatches.append(
                ArtifactMismatch(
                    artifact_path=artifact_path,
                    expected_hash=expected_hash,
                    actual_hash=actual_hash,
                    size_difference=current_size - golden_size,
                )
            )

    # Check for unexpected artifacts in current run
    for artifact_path in sorted(current_hashes.keys()):
        if artifact_path not in golden_metadata.artifact_hashes:
            mismatches.append(
                ArtifactMismatch(
                    artifact_path=artifact_path,
                    expected_hash="NOT_IN_GOLDEN",
                    actual_hash=current_hashes[artifact_path],
                    size_difference=0,
                )
            )

    # Create verification result
    result = VerificationResult(
        run_id=run_id,
        golden_run_id=golden_run_id,
        passed=len(mismatches) == 0,
        mismatches=mismatches,
        verified_at=datetime.now(timezone.utc).isoformat(),
    )

    return result


def list_golden_runs(product_name: Optional[str] = None) -> List[GoldenRunMetadata]:
    """List all golden runs, optionally filtered by product.

    Args:
        product_name: Optional product name filter

    Returns:
        List of GoldenRunMetadata, sorted by captured_at descending
    """
    golden_runs: List[GoldenRunMetadata] = []
    base_dir = Path("artifacts") / "golden_runs"

    if not base_dir.exists():
        return golden_runs

    # Scan for metadata files
    if product_name:
        # Filter by product
        product_dir = base_dir / product_name
        if product_dir.exists():
            metadata_files = sorted(product_dir.rglob("metadata.json"))
        else:
            metadata_files = []
    else:
        # All products
        metadata_files = sorted(base_dir.rglob("metadata.json"))

    # Load all metadata
    for metadata_path in metadata_files:
        try:
            with open(metadata_path, encoding="utf-8") as f:
                data = json.load(f)
                metadata = GoldenRunMetadata.from_dict(data)
                golden_runs.append(metadata)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Skip invalid metadata files
            continue

    # Sort by captured_at descending (most recent first)
    golden_runs.sort(key=lambda m: m.captured_at, reverse=True)

    return golden_runs


def delete_golden_run(
    golden_run_id: str,
    product_name: Optional[str] = None,
    git_ref: Optional[str] = None,
) -> bool:
    """Delete a golden run.

    Args:
        golden_run_id: ID of golden run to delete
        product_name: Optional product name (for faster lookup)
        git_ref: Optional git ref (for faster lookup)

    Returns:
        True if deleted successfully, False if not found
    """
    # Find the golden run
    if product_name and git_ref:
        golden_dir = _get_golden_runs_dir(product_name, git_ref)
        golden_run_dir = golden_dir / golden_run_id
    else:
        # Search all golden runs
        golden_runs = list_golden_runs()
        golden_run_dir = None
        for meta in golden_runs:
            if meta.run_id == golden_run_id:
                golden_dir = _get_golden_runs_dir(meta.product_name, meta.git_ref)
                golden_run_dir = golden_dir / golden_run_id
                break

        if not golden_run_dir:
            return False

    if not golden_run_dir.exists():
        return False

    # Delete the directory
    shutil.rmtree(golden_run_dir)
    return True
