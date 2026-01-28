"""W1.2 Deterministic repo fingerprinting and inventory generation.

This module implements deterministic repository fingerprinting and inventory
generation per specs/02_repo_ingestion.md.

Fingerprinting algorithm (binding):
1. List all non-phantom files (exclude paths in phantom_paths)
2. For each file: Compute SHA-256(file_path + "|" + file_content)
3. Sort file hashes lexicographically (C locale, byte-by-byte)
4. Concatenate sorted hashes (no delimiters)
5. Compute SHA-256(concatenated_hashes) → repo_fingerprint

Spec references:
- specs/02_repo_ingestion.md:158-177 (Fingerprinting algorithm)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/21_worker_contracts.md (Worker interface)

TC-402: W1.2 Deterministic repo fingerprinting and inventory
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import Counter

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)


def compute_file_hash(file_path: Path, relative_path: str) -> str:
    """Compute SHA-256 hash of file path and content.

    Per specs/02_repo_ingestion.md:162, hash format is:
    SHA-256(file_path + "|" + file_content)

    Args:
        file_path: Absolute path to file
        relative_path: Relative path from repo root (for deterministic hash)

    Returns:
        64-character hex hash string

    Spec reference: specs/02_repo_ingestion.md:162
    """
    try:
        content = file_path.read_bytes()
    except (OSError, PermissionError):
        # If file cannot be read, use empty content
        content = b""

    # Hash format: relative_path + "|" + content
    hash_input = relative_path.encode("utf-8") + b"|" + content
    return hashlib.sha256(hash_input).hexdigest()


def detect_primary_language(file_paths: List[str]) -> str:
    """Detect primary programming language from file extensions.

    Args:
        file_paths: List of relative file paths

    Returns:
        Primary language name or "unknown"
    """
    extension_map = {
        ".py": "Python",
        ".cs": "C#",
        ".java": "Java",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C/C++",
        ".hpp": "C++",
        ".md": "Markdown",
        ".json": "JSON",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".xml": "XML",
        ".html": "HTML",
        ".css": "CSS",
        ".sh": "Shell",
        ".bat": "Batch",
    }

    # Count language occurrences
    language_counts = Counter()
    code_file_count = 0

    for path in file_paths:
        ext = Path(path).suffix.lower()
        if ext in extension_map:
            language = extension_map[ext]
            # Weight code files higher than config/docs
            if ext not in [".md", ".json", ".yaml", ".yml", ".xml"]:
                language_counts[language] += 3
                code_file_count += 1
            else:
                language_counts[language] += 1

    if not language_counts:
        return "unknown"

    # If only documentation/config files (no actual code files), return unknown
    if code_file_count == 0:
        return "unknown"

    # Return most common language
    return language_counts.most_common(1)[0][0]


def is_binary_file(file_path: Path) -> bool:
    """Heuristic check if file is binary.

    Args:
        file_path: Path to file

    Returns:
        True if file appears to be binary
    """
    binary_extensions = {
        ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".exe", ".dll", ".so", ".dylib", ".bin", ".dat",
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
        ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv",
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".one", ".onetoc2", ".class", ".jar", ".war",
    }

    if file_path.suffix.lower() in binary_extensions:
        return True

    # Check first 8192 bytes for null bytes
    try:
        with file_path.open("rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                return True
    except (OSError, PermissionError):
        pass

    return False


def walk_repo_files(repo_dir: Path, respect_gitignore: bool = True) -> List[str]:
    """Walk repository and collect all file paths.

    Args:
        repo_dir: Repository root directory
        respect_gitignore: Whether to respect .gitignore patterns

    Returns:
        Sorted list of relative file paths (deterministic)

    Spec reference: specs/10_determinism_and_caching.md:40-46 (Stable ordering)
    """
    file_paths = []
    ignore_dirs = {".git", "__pycache__", "node_modules", ".pytest_cache", ".tox"}

    for file_path in repo_dir.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip ignored directories
        if any(part in ignore_dirs for part in file_path.parts):
            continue

        # Get relative path
        try:
            relative_path = file_path.relative_to(repo_dir)
            file_paths.append(str(relative_path).replace("\\", "/"))
        except ValueError:
            # Path is not relative to repo_dir, skip
            continue

    # Sort for determinism (lexicographic, stable)
    file_paths.sort()
    return file_paths


def compute_repo_fingerprint(repo_dir: Path) -> Dict[str, Any]:
    """Compute deterministic repository fingerprint.

    Implements algorithm from specs/02_repo_ingestion.md:158-177.

    Args:
        repo_dir: Repository root directory

    Returns:
        Dictionary with:
        - repo_fingerprint: 64-char hex SHA-256 hash
        - file_count: Total number of files
        - total_bytes: Total size in bytes

    Spec reference: specs/02_repo_ingestion.md:158-177
    """
    # Step 1: List all files
    file_paths = walk_repo_files(repo_dir)

    if not file_paths:
        # Empty repository - return zero fingerprint
        return {
            "repo_fingerprint": "0" * 64,
            "file_count": 0,
            "total_bytes": 0,
        }

    # Step 2: Compute hash for each file
    file_hashes = []
    total_bytes = 0

    for relative_path in file_paths:
        file_path = repo_dir / relative_path
        if file_path.exists() and file_path.is_file():
            file_hash = compute_file_hash(file_path, relative_path)
            file_hashes.append(file_hash)

            # Track total size
            try:
                total_bytes += file_path.stat().st_size
            except (OSError, PermissionError):
                pass

    # Step 3: Sort hashes lexicographically (already sorted by file_paths sort)
    # file_hashes is already in correct order since we iterate sorted file_paths

    # Step 4: Concatenate sorted hashes
    concatenated = "".join(file_hashes)

    # Step 5: Compute final fingerprint
    repo_fingerprint = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

    return {
        "repo_fingerprint": repo_fingerprint,
        "file_count": len(file_paths),
        "total_bytes": total_bytes,
    }


def build_repo_inventory(
    repo_dir: Path,
    repo_url: str,
    repo_sha: str,
) -> Dict[str, Any]:
    """Build complete repository inventory.

    Generates repo_inventory.json with:
    - Repo fingerprint
    - File tree
    - Language detection
    - File counts and stats

    Args:
        repo_dir: Repository root directory
        repo_url: Repository URL
        repo_sha: Resolved commit SHA

    Returns:
        Dictionary matching repo_inventory.schema.json structure

    Spec references:
    - specs/02_repo_ingestion.md (Repo profiling)
    - specs/schemas/repo_inventory.schema.json (Schema)
    """
    # Compute fingerprint
    fingerprint_data = compute_repo_fingerprint(repo_dir)

    # Walk file tree
    file_paths = walk_repo_files(repo_dir)

    # Detect language
    primary_language = detect_primary_language(file_paths)

    # Identify binary assets
    binary_assets = []
    for relative_path in file_paths:
        file_path = repo_dir / relative_path
        if file_path.exists() and is_binary_file(file_path):
            binary_assets.append(relative_path)

    # Build minimal repo_inventory structure
    # Note: This is a minimal implementation. TC-403, TC-404 will add:
    # - doc_entrypoints discovery
    # - example_paths discovery
    # - repo_profile generation
    # - phantom_paths detection
    inventory = {
        "schema_version": "1.0",
        "repo_url": repo_url,
        "repo_sha": repo_sha,
        "fingerprint": {
            "default_branch": None,  # Will be set by caller
            "latest_release_tag": None,  # Will be set by discovery
            "license_path": None,  # Will be set by discovery
            "primary_languages": [primary_language] if primary_language != "unknown" else [],
        },
        "repo_profile": {
            "platform_family": "unknown",  # Will be set by adapter selection
            "primary_languages": [primary_language] if primary_language != "unknown" else [],
            "build_systems": [],  # Will be set by discovery
            "package_manifests": [],  # Will be set by discovery
            "recommended_test_commands": [],
            "example_locator": "standard_dirs",  # Default strategy
            "doc_locator": "standard_dirs",  # Default strategy
        },
        "paths": file_paths,
        "doc_entrypoints": [],  # Will be populated by TC-403
        "example_paths": [],  # Will be populated by TC-404
        "source_roots": [],  # Will be populated by discovery
        "test_roots": [],  # Will be populated by discovery
        "doc_roots": [],  # Will be populated by discovery
        "example_roots": [],  # Will be populated by discovery
        "binary_assets": binary_assets,
        "phantom_paths": [],  # Will be populated by TC-403
    }

    # Add fingerprint metadata
    inventory["repo_fingerprint"] = fingerprint_data["repo_fingerprint"]
    inventory["file_count"] = fingerprint_data["file_count"]
    inventory["total_bytes"] = fingerprint_data["total_bytes"]

    return inventory


def write_repo_inventory_artifact(
    run_layout: RunLayout,
    inventory: Dict[str, Any],
) -> None:
    """Write repo_inventory.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        inventory: Repository inventory dictionary

    Spec reference:
    - specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "repo_inventory.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(inventory, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def emit_fingerprint_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    fingerprint: str,
    file_count: int,
) -> None:
    """Emit events for fingerprinting operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        fingerprint: Computed repo fingerprint
        file_count: Number of files processed

    Spec reference:
    - specs/11_state_and_events.md (Event emission)
    - specs/21_worker_contracts.md:33-40 (Required events)
    """
    import datetime
    import uuid

    events_file = run_layout.run_dir / "events.ndjson"

    def write_event(event_type: str, payload: Dict[str, Any]) -> None:
        """Helper to write a single event to events.ndjson."""
        event = Event(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            ts=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            type=event_type,
            payload=payload,
            trace_id=trace_id,
            span_id=span_id,
        )

        event_line = json.dumps(event.to_dict()) + "\n"

        # Append to events.ndjson (append-only log)
        with events_file.open("a", encoding="utf-8") as f:
            f.write(event_line)

    # WORK_ITEM_STARTED
    write_event(
        EVENT_WORK_ITEM_STARTED,
        {"worker": "w1_repo_scout", "task": "fingerprint_repo", "step": "TC-402"},
    )

    # Custom event: REPO_FINGERPRINT_COMPUTED
    write_event(
        "REPO_FINGERPRINT_COMPUTED",
        {
            "fingerprint": fingerprint,
            "file_count": file_count,
        },
    )

    # ARTIFACT_WRITTEN (for repo_inventory.json)
    artifact_path = run_layout.artifacts_dir / "repo_inventory.json"
    if artifact_path.exists():
        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "repo_inventory.json",
                "path": str(artifact_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": "repo_inventory.schema.json",
            },
        )

    # WORK_ITEM_FINISHED
    write_event(
        EVENT_WORK_ITEM_FINISHED,
        {
            "worker": "w1_repo_scout",
            "task": "fingerprint_repo",
            "step": "TC-402",
            "status": "success",
        },
    )


def fingerprint_repo(repo_dir: Path, run_dir: Path) -> Dict[str, Any]:
    """Main entry point for TC-402 repo fingerprinting.

    This function:
    1. Computes deterministic repo fingerprint
    2. Builds repo inventory with file tree and metadata
    3. Writes repo_inventory.json artifact
    4. Emits telemetry events

    Args:
        repo_dir: Repository root directory (work/repo/)
        run_dir: Run directory path

    Returns:
        Repository inventory dictionary

    Spec references:
    - specs/02_repo_ingestion.md:158-177 (Fingerprinting)
    - specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load resolved_refs.json to get repo metadata
    resolved_refs_path = run_layout.artifacts_dir / "resolved_refs.json"
    if not resolved_refs_path.exists():
        raise FileNotFoundError(
            f"Missing resolved_refs.json. TC-401 must run before TC-402."
        )

    resolved_refs = json.loads(resolved_refs_path.read_text())
    repo_metadata = resolved_refs.get("repo", {})
    repo_url = repo_metadata.get("repo_url", "unknown")
    repo_sha = repo_metadata.get("resolved_sha", "unknown")

    # Build inventory
    inventory = build_repo_inventory(repo_dir, repo_url, repo_sha)

    # Write artifact
    write_repo_inventory_artifact(run_layout, inventory)

    # Emit events
    # Note: Using dummy IDs for now. In production, these come from orchestrator.
    emit_fingerprint_events(
        run_layout=run_layout,
        run_id="unknown",
        trace_id="unknown",
        span_id="unknown",
        fingerprint=inventory["repo_fingerprint"],
        file_count=inventory["file_count"],
    )

    return inventory


def run_fingerprint_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-402 fingerprint worker.

    Entry point for W1.2 fingerprint worker. This can be invoked by:
    - Orchestrator (TC-300) as part of W1 RepoScout
    - Standalone for testing/debugging

    Args:
        run_dir: Run directory path
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry

    Returns:
        Exit code (0 = success, non-zero = failure)

    Spec reference:
    - specs/21_worker_contracts.md (Worker contract)
    """
    try:
        run_layout = RunLayout(run_dir=run_dir)
        repo_dir = run_layout.work_dir / "repo"

        if not repo_dir.exists():
            raise FileNotFoundError(
                f"Repository directory not found: {repo_dir}. "
                "TC-401 clone must run before TC-402."
            )

        # Build inventory
        from ...models.run_config import RunConfig
        from ...io.run_config import load_and_validate_run_config

        # Load repo metadata from resolved_refs.json
        resolved_refs_path = run_layout.artifacts_dir / "resolved_refs.json"
        resolved_refs = json.loads(resolved_refs_path.read_text())
        repo_metadata = resolved_refs.get("repo", {})

        inventory = build_repo_inventory(
            repo_dir=repo_dir,
            repo_url=repo_metadata.get("repo_url", "unknown"),
            repo_sha=repo_metadata.get("resolved_sha", "unknown"),
        )

        # Write artifact
        write_repo_inventory_artifact(run_layout, inventory)

        # Emit events
        emit_fingerprint_events(
            run_layout,
            run_id,
            trace_id,
            span_id,
            inventory["repo_fingerprint"],
            inventory["file_count"],
        )

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", flush=True)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error in fingerprint worker: {e}", flush=True)
        return 5  # Unexpected internal error
