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
TC-1024: .gitignore support + phantom path detection
TC-1025: Fingerprinting improvements (configurable ignore_dirs, file_size_bytes)
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from collections import Counter

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)

logger = logging.getLogger(__name__)

# Default directories to ignore during repo walking
DEFAULT_IGNORE_DIRS: Set[str] = frozenset({
    ".git", "__pycache__", "node_modules", ".pytest_cache", ".tox",
})

# Large file threshold (50 MB) for telemetry warning
LARGE_FILE_THRESHOLD_BYTES = 50 * 1024 * 1024


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


def parse_gitignore(repo_dir: Path) -> List[str]:
    """Parse .gitignore file at repo root and return patterns.

    Reads the .gitignore file (if present) and returns a list of
    non-empty, non-comment patterns. Uses only stdlib (fnmatch).

    Args:
        repo_dir: Repository root directory

    Returns:
        List of gitignore pattern strings (deterministic order)

    TC-1024: .gitignore support
    """
    gitignore_path = repo_dir / ".gitignore"
    if not gitignore_path.exists():
        return []

    patterns: List[str] = []
    try:
        content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            stripped = line.strip()
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
    except OSError:
        pass

    return patterns


def matches_gitignore(relative_path: str, gitignore_patterns: List[str]) -> bool:
    """Check if a relative path matches any .gitignore pattern.

    Supports:
    - Simple glob matching (fnmatch)
    - Directory patterns (trailing /)
    - Patterns matching any path component

    Args:
        relative_path: Forward-slash-separated relative path
        gitignore_patterns: List of gitignore patterns

    Returns:
        True if path matches any gitignore pattern

    TC-1024: .gitignore support
    """
    # Normalize: ensure forward slashes
    normalized = relative_path.replace("\\", "/")
    parts = normalized.split("/")

    for pattern in gitignore_patterns:
        # Negation patterns (!) are not handled for simplicity
        if pattern.startswith("!"):
            continue

        # Strip trailing slash (directory indicator) -- we match files too
        clean_pattern = pattern.rstrip("/")

        # If pattern contains a slash, match against full path
        if "/" in clean_pattern:
            if fnmatch.fnmatch(normalized, clean_pattern):
                return True
            # Also try matching with leading path components
            if fnmatch.fnmatch(normalized, "*/" + clean_pattern):
                return True
        else:
            # Match against any path component or the full filename
            if fnmatch.fnmatch(parts[-1], clean_pattern):
                return True
            # Also try matching the full relative path
            if fnmatch.fnmatch(normalized, clean_pattern):
                return True
            # Match against each directory component
            for part in parts[:-1]:
                if fnmatch.fnmatch(part, clean_pattern):
                    return True

    return False


def walk_repo_files(
    repo_dir: Path,
    respect_gitignore: bool = True,
    extra_ignore_dirs: Optional[Set[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> List[str]:
    """Walk repository and collect all file paths.

    TC-1024: Implements respect_gitignore parameter using fnmatch.
    TC-1025: Accepts extra_ignore_dirs merged with DEFAULT_IGNORE_DIRS.

    Args:
        repo_dir: Repository root directory
        respect_gitignore: Whether to respect .gitignore patterns (TC-1024)
        extra_ignore_dirs: Additional directory names to ignore (TC-1025)
        exclude_patterns: Glob patterns from run_config to exclude (TC-1025)

    Returns:
        Sorted list of relative file paths (deterministic)

    Spec reference: specs/10_determinism_and_caching.md:40-46 (Stable ordering)
    """
    file_paths = []

    # TC-1025: Merge hardcoded ignore_dirs with configurable extras
    ignore_dirs = set(DEFAULT_IGNORE_DIRS)
    if extra_ignore_dirs:
        ignore_dirs.update(extra_ignore_dirs)

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
            rel_str = str(relative_path).replace("\\", "/")
        except ValueError:
            # Path is not relative to repo_dir, skip
            continue

        # TC-1025: Check exclude_patterns from run_config
        if exclude_patterns:
            matched = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(rel_str, pattern):
                    matched = True
                    break
            if matched:
                continue

        file_paths.append(rel_str)

    # Sort for determinism (lexicographic, stable)
    file_paths.sort()
    return file_paths


def walk_repo_files_with_gitignore(
    repo_dir: Path,
    gitignore_mode: str = "respect",
    extra_ignore_dirs: Optional[Set[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """Walk repo and classify files as gitignored or not.

    Per TC-1024 exhaustive mandate: gitignored files are RECORDED but marked
    separately. They are NOT excluded from the inventory.

    Args:
        repo_dir: Repository root directory
        gitignore_mode: "respect" | "ignore" | "strict" (TC-1024)
        extra_ignore_dirs: Additional directory names to ignore (TC-1025)
        exclude_patterns: Glob patterns from run_config to exclude (TC-1025)

    Returns:
        Dictionary with:
        - "all_files": sorted list of ALL relative file paths
        - "gitignored_files": sorted list of paths matching .gitignore

    TC-1024: .gitignore support + exhaustive mandate
    """
    # Get all files first (no gitignore filtering)
    all_files = walk_repo_files(
        repo_dir,
        respect_gitignore=False,
        extra_ignore_dirs=extra_ignore_dirs,
        exclude_patterns=exclude_patterns,
    )

    gitignored_files: List[str] = []

    if gitignore_mode != "ignore":
        gitignore_patterns = parse_gitignore(repo_dir)
        if gitignore_patterns:
            for rel_path in all_files:
                if matches_gitignore(rel_path, gitignore_patterns):
                    gitignored_files.append(rel_path)
            gitignored_files.sort()

    return {
        "all_files": all_files,
        "gitignored_files": gitignored_files,
    }


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


def detect_phantom_paths(
    repo_dir: Path,
    file_paths: List[str],
) -> List[Dict[str, Any]]:
    """Detect phantom path references in markdown and text documents.

    Scans all markdown/text files for file references (markdown links,
    image refs) and cross-references them against actual files in the repo.
    Unmatched paths are recorded as phantom paths.

    Args:
        repo_dir: Repository root directory
        file_paths: List of relative file paths known to exist in the repo

    Returns:
        Sorted list of phantom path entries, each with:
        - referenced_path: The path referenced in the document
        - referencing_file: The file containing the reference
        - reference_line: Line number of the reference
        - reference_type: Type of reference (link, image, etc.)

    TC-1024: Phantom path detection
    """
    # Build a set of known paths for fast lookup
    known_paths = set(file_paths)

    # Also build a set of known directories
    known_dirs: Set[str] = set()
    for fp in file_paths:
        parts = fp.split("/")
        for i in range(1, len(parts)):
            known_dirs.add("/".join(parts[:i]))

    # Regex patterns for detecting file references in markdown
    # Matches: [text](path) and ![alt](path)
    md_link_pattern = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
    # Matches: [text]: path (reference-style links)
    md_ref_pattern = re.compile(r"^\[([^\]]+)\]:\s+(.+)$")

    phantom_paths: List[Dict[str, Any]] = []
    scannable_extensions = {".md", ".rst", ".txt"}

    for rel_path in file_paths:
        # Only scan text-based document files
        ext = Path(rel_path).suffix.lower()
        if ext not in scannable_extensions:
            continue

        file_path = repo_dir / rel_path
        if not file_path.exists():
            continue

        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, start=1):
                    # Check markdown links: [text](path) and ![alt](path)
                    for match in md_link_pattern.finditer(line):
                        ref_path = match.group(2).strip()
                        ref_type = "image" if match.group(0).startswith("!") else "link"
                        _check_phantom_ref(
                            ref_path, rel_path, line_num, ref_type,
                            known_paths, known_dirs, phantom_paths,
                        )

                    # Check reference-style links: [id]: path
                    ref_match = md_ref_pattern.match(line.strip())
                    if ref_match:
                        ref_path = ref_match.group(2).strip()
                        _check_phantom_ref(
                            ref_path, rel_path, line_num, "ref_link",
                            known_paths, known_dirs, phantom_paths,
                        )
        except OSError:
            continue

    # Sort for determinism: by referenced_path, then referencing_file, then line
    phantom_paths.sort(
        key=lambda p: (p["referenced_path"], p["referencing_file"], p["reference_line"])
    )
    return phantom_paths


def _check_phantom_ref(
    ref_path: str,
    referencing_file: str,
    line_num: int,
    ref_type: str,
    known_paths: Set[str],
    known_dirs: Set[str],
    phantom_paths: List[Dict[str, Any]],
) -> None:
    """Check if a reference path is a phantom (does not exist in repo).

    Helper for detect_phantom_paths. Filters out URLs, anchors, and
    known paths.

    Args:
        ref_path: The referenced path string
        referencing_file: The file containing the reference
        line_num: Line number
        ref_type: Type of reference
        known_paths: Set of known file paths
        known_dirs: Set of known directory paths
        phantom_paths: List to append phantom entries to (mutated)

    TC-1024: Phantom path detection
    """
    # Skip URLs (http://, https://, ftp://, mailto:, etc.)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref_path):
        return

    # Skip pure anchors (#section-name)
    if ref_path.startswith("#"):
        return

    # Skip empty references
    if not ref_path:
        return

    # Strip anchor from path (path#anchor -> path)
    clean_path = ref_path.split("#")[0].strip()
    if not clean_path:
        return

    # Strip query string (path?query -> path)
    clean_path = clean_path.split("?")[0].strip()
    if not clean_path:
        return

    # Normalize to forward slashes
    clean_path = clean_path.replace("\\", "/")

    # Resolve relative paths against the referencing file's directory
    if not clean_path.startswith("/"):
        ref_dir = "/".join(referencing_file.split("/")[:-1])
        if ref_dir:
            resolved = ref_dir + "/" + clean_path
        else:
            resolved = clean_path
    else:
        # Absolute path from repo root (strip leading /)
        resolved = clean_path.lstrip("/")

    # Normalize .. and . components
    parts = resolved.split("/")
    normalized_parts: List[str] = []
    for part in parts:
        if part == "..":
            if normalized_parts:
                normalized_parts.pop()
        elif part != "." and part != "":
            normalized_parts.append(part)
    resolved = "/".join(normalized_parts)

    if not resolved:
        return

    # Check if the resolved path exists in known files or directories
    if resolved in known_paths or resolved in known_dirs:
        return

    phantom_paths.append({
        "referenced_path": resolved,
        "referencing_file": referencing_file,
        "reference_line": line_num,
        "reference_type": ref_type,
    })


def build_repo_inventory(
    repo_dir: Path,
    repo_url: str,
    repo_sha: str,
    gitignore_mode: str = "respect",
    extra_ignore_dirs: Optional[Set[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    detect_phantoms: bool = True,
) -> Dict[str, Any]:
    """Build complete repository inventory.

    Generates repo_inventory.json with:
    - Repo fingerprint
    - File tree with file_size_bytes per path (TC-1025)
    - Language detection
    - File counts and stats
    - Gitignore classification (TC-1024)
    - Phantom path detection (TC-1024)

    Args:
        repo_dir: Repository root directory
        repo_url: Repository URL
        repo_sha: Resolved commit SHA
        gitignore_mode: .gitignore handling mode (TC-1024)
        extra_ignore_dirs: Additional directory names to ignore (TC-1025)
        exclude_patterns: Glob patterns from run_config (TC-1025)
        detect_phantoms: Whether to detect phantom paths (TC-1024)

    Returns:
        Dictionary matching repo_inventory.schema.json structure

    Spec references:
    - specs/02_repo_ingestion.md (Repo profiling)
    - specs/schemas/repo_inventory.schema.json (Schema)
    """
    # Compute fingerprint
    fingerprint_data = compute_repo_fingerprint(repo_dir)

    # TC-1024: Walk file tree with gitignore classification
    walk_result = walk_repo_files_with_gitignore(
        repo_dir,
        gitignore_mode=gitignore_mode,
        extra_ignore_dirs=extra_ignore_dirs,
        exclude_patterns=exclude_patterns,
    )
    file_paths = walk_result["all_files"]
    gitignored_files = walk_result["gitignored_files"]

    # Detect language
    primary_language = detect_primary_language(file_paths)

    # TC-1025: Build paths with file_size_bytes and check for large files
    paths_with_size: List[Dict[str, Any]] = []
    large_files: List[str] = []
    binary_assets = []

    for relative_path in file_paths:
        file_path = repo_dir / relative_path
        file_size = 0

        if file_path.exists():
            try:
                file_size = file_path.stat().st_size
            except (OSError, PermissionError):
                pass

            # TC-1025: Track large files for telemetry
            if file_size > LARGE_FILE_THRESHOLD_BYTES:
                large_files.append(relative_path)

            # Binary detection
            if is_binary_file(file_path):
                binary_assets.append(relative_path)

        # TC-1024: Mark gitignored files
        is_gitignored = relative_path in set(gitignored_files)

        path_entry: Dict[str, Any] = {
            "path": relative_path,
            "file_size_bytes": file_size,
        }
        if is_gitignored:
            path_entry["gitignored"] = True

        paths_with_size.append(path_entry)

    # TC-1025: Log large file warnings
    for lf in large_files:
        logger.warning(
            "REPO_SCOUT_LARGE_FILE: %s exceeds %d bytes threshold",
            lf, LARGE_FILE_THRESHOLD_BYTES,
        )

    # TC-1024: Detect phantom paths
    phantom_paths: List[Dict[str, Any]] = []
    if detect_phantoms:
        phantom_paths = detect_phantom_paths(repo_dir, file_paths)

    # Build minimal repo_inventory structure
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
        # Backward-compatible flat list of relative paths
        "paths": [p["path"] for p in paths_with_size],
        # TC-1025: Detailed paths with file_size_bytes
        "paths_detailed": paths_with_size,
        "doc_entrypoints": [],  # Will be populated by TC-403
        "example_paths": [],  # Will be populated by TC-404
        "source_roots": [],  # Will be populated by discovery
        "test_roots": [],  # Will be populated by discovery
        "doc_roots": [],  # Will be populated by discovery
        "example_roots": [],  # Will be populated by discovery
        "binary_assets": binary_assets,
        "phantom_paths": phantom_paths,  # TC-1024: Populated by phantom detection
        "gitignored_files": gitignored_files,  # TC-1024: Files matching .gitignore
        "large_files": large_files,  # TC-1025: Files exceeding threshold
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
    large_files: Optional[List[str]] = None,
) -> None:
    """Emit events for fingerprinting operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion
    - REPO_SCOUT_LARGE_FILE for files exceeding threshold (TC-1025)

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        fingerprint: Computed repo fingerprint
        file_count: Number of files processed
        large_files: List of file paths exceeding size threshold (TC-1025)

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

    # TC-1025: Emit REPO_SCOUT_LARGE_FILE for files exceeding threshold
    if large_files:
        for large_file_path in sorted(large_files):
            write_event(
                "REPO_SCOUT_LARGE_FILE",
                {
                    "file_path": large_file_path,
                    "threshold_bytes": LARGE_FILE_THRESHOLD_BYTES,
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
