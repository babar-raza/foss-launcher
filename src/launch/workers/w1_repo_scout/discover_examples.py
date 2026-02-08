"""W1.4 Example discovery in cloned product repo.

This module implements example discovery per specs/02_repo_ingestion.md and
specs/05_example_curation.md, extended by TC-1023 for configurable scan
directories.

Example discovery algorithm (binding):
1. Scan for standard example directories: examples/, samples/, demo/
2. Merge with extra example_directories from run_config (TC-1023)
3. For each directory that exists in repo_inventory.file_tree, add to example_roots
4. Detect example files (example_*, sample_*, demo_*)
5. Score examples by quality and relevance
6. Extract example metadata (language, complexity)
7. Sort example_roots alphabetically for determinism
8. Record files with unknown language (TC-1023: no skip)
9. Add file_size_bytes to output entries (TC-1023)

Spec references:
- specs/02_repo_ingestion.md:143-156 (Example discovery)
- specs/05_example_curation.md:61-97 (Example discovery order and policy)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/21_worker_contracts.md (Worker interface)

TC-404: W1.4 Discover examples in cloned product repo
TC-1023: Configurable scan directories
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)


# Standard example directory patterns (per specs/02_repo_ingestion.md:146)
STANDARD_EXAMPLE_DIRS = ["examples", "samples", "demo"]

# Example file name patterns
EXAMPLE_FILE_PATTERNS = [
    re.compile(r"^example[_-]", re.IGNORECASE),
    re.compile(r"^sample[_-]", re.IGNORECASE),
    re.compile(r"^demo[_-]", re.IGNORECASE),
    re.compile(r"example\.py$", re.IGNORECASE),
    re.compile(r"sample\.py$", re.IGNORECASE),
    re.compile(r"demo\.py$", re.IGNORECASE),
    re.compile(r"example\.cs$", re.IGNORECASE),
    re.compile(r"sample\.cs$", re.IGNORECASE),
    re.compile(r"demo\.cs$", re.IGNORECASE),
]


def is_example_file(file_path: Path) -> bool:
    """Check if filename matches example file patterns.

    Args:
        file_path: Path to file

    Returns:
        True if file matches example patterns

    Spec reference: specs/05_example_curation.md:61-69
    """
    filename = file_path.name

    for pattern in EXAMPLE_FILE_PATTERNS:
        if pattern.search(filename):
            return True

    return False


def detect_language_from_extension(file_path: Path) -> str:
    """Detect programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language name or "unknown"
    """
    extension_map = {
        ".py": "python",
        ".cs": "csharp",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
    }

    ext = file_path.suffix.lower()
    return extension_map.get(ext, "unknown")


def estimate_complexity(file_path: Path) -> str:
    """Estimate code complexity heuristically.

    Categorizes examples as simple, medium, or complex based on:
    - File size (lines of code)
    - Presence of imports/includes
    - Number of functions/classes

    Args:
        file_path: Path to example file

    Returns:
        Complexity level: "simple" | "medium" | "complex"
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        # Count indicators of complexity
        import_count = sum(1 for line in lines if line.strip().startswith(("import ", "using ", "#include", "require ")))
        function_count = sum(1 for line in lines if re.match(r"^\s*(def|function|func|sub|public|private|protected)\s+", line))
        class_count = sum(1 for line in lines if re.match(r"^\s*(class|interface|struct)\s+", line))

        # Estimate complexity
        if len(non_empty_lines) < 20 and function_count <= 1 and class_count == 0:
            return "simple"
        elif len(non_empty_lines) > 100 or function_count > 5 or class_count > 2:
            return "complex"
        else:
            return "medium"

    except (OSError, UnicodeDecodeError):
        return "unknown"


def compute_example_relevance_score(
    file_path: Path,
    repo_dir: Path,
    is_in_example_root: bool,
) -> int:
    """Compute relevance score for example file.

    Scoring rules (per specs/05_example_curation.md):
    - Files in examples/ or samples/ roots: 100
    - Example files in docs/: 80
    - Example files in root: 70
    - Example files in tests/ (test-examples): 50
    - Other example files: 30

    Args:
        file_path: Path to example file
        repo_dir: Repository root directory
        is_in_example_root: Whether file is in a standard example root directory

    Returns:
        Relevance score (0-100)

    Spec reference: specs/05_example_curation.md:61-69
    """
    try:
        relative_path = file_path.relative_to(repo_dir)
    except ValueError:
        return 0

    parts = relative_path.parts

    # Files in standard example roots get highest score
    if is_in_example_root:
        return 100

    # Files in docs/examples or similar
    if len(parts) >= 2 and parts[0] in ("docs", "documentation") and "example" in parts[1].lower():
        return 80

    # Example files in root directory
    if len(parts) == 1:
        return 70

    # Example files in tests/ (treat as test-examples)
    if len(parts) >= 1 and parts[0] in ("tests", "test", "__tests__", "spec"):
        return 50

    # Other example files (nested)
    return 30


def _matches_exclude_pattern(relative_path: str, exclude_patterns: List[str]) -> bool:
    """Check if a path matches any exclude pattern.

    Supports simple glob-like patterns:
    - ``*`` matches any sequence of non-separator characters
    - Patterns are matched against the full relative path

    Args:
        relative_path: Forward-slash-normalized relative path
        exclude_patterns: List of exclude pattern strings

    Returns:
        True if path matches any exclude pattern
    """
    import fnmatch

    for pattern in exclude_patterns:
        if fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def identify_example_roots(
    repo_dir: Path,
    extra_example_dirs: Optional[List[str]] = None,
) -> List[str]:
    """Identify example root directories.

    Per specs/02_repo_ingestion.md:146, MUST scan for standard example
    directories in order: examples/, samples/, demo/

    TC-1023: Also includes extra example directories from run_config.

    Args:
        repo_dir: Repository root directory
        extra_example_dirs: Additional example directories from config (TC-1023)

    Returns:
        Sorted list of example root directories

    Spec reference: specs/02_repo_ingestion.md:145-156
    """
    example_roots = []

    # Scan standard dirs in deterministic order
    for candidate in STANDARD_EXAMPLE_DIRS:
        candidate_path = repo_dir / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            example_roots.append(candidate)

    # TC-1023: Merge extra example directories from config
    if extra_example_dirs:
        for extra_dir in extra_example_dirs:
            # Normalize path separators
            normalized = extra_dir.replace("\\", "/").strip("/")
            if normalized and normalized not in example_roots:
                candidate_path = repo_dir / normalized
                if candidate_path.exists() and candidate_path.is_dir():
                    example_roots.append(normalized)

    # Sort for determinism (per specs/02_repo_ingestion.md:149)
    example_roots.sort()
    return example_roots


def discover_example_files(
    repo_dir: Path,
    example_roots: List[str],
    scan_directories: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    gitignore_mode: str = "respect",
) -> List[Dict[str, Any]]:
    """Discover example files in repository.

    Implements discovery algorithm from specs/02_repo_ingestion.md:143-156
    and specs/05_example_curation.md:61-69.

    TC-1023 extensions:
    - Accept scan_directories and exclude_patterns from run_config
    - Record files with unknown language (no skip)
    - Add file_size_bytes to output entries

    TC-1024 extensions:
    - Accept gitignore_mode and mark gitignored files appropriately
    - DO NOT exclude gitignored files (exhaustive mandate)

    Args:
        repo_dir: Repository root directory
        example_roots: List of identified example root directories
        scan_directories: Directories to scan, default ["."] (TC-1023)
        exclude_patterns: Glob patterns to exclude files (TC-1023)
        gitignore_mode: .gitignore handling mode (TC-1024)

    Returns:
        List of discovered example files with metadata

    Spec references:
    - specs/02_repo_ingestion.md:143-156
    - specs/05_example_curation.md:61-69
    """
    if scan_directories is None:
        scan_directories = ["."]
    if exclude_patterns is None:
        exclude_patterns = []

    # TC-1024: Parse gitignore if applicable
    gitignore_patterns: List[str] = []
    if gitignore_mode != "ignore":
        from .fingerprint import parse_gitignore, matches_gitignore
        gitignore_patterns = parse_gitignore(repo_dir)

    discovered_examples = []

    # First, scan example root directories
    for example_root in example_roots:
        example_root_path = repo_dir / example_root

        for file_path in example_root_path.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip hidden files
            if any(part.startswith(".") for part in file_path.parts):
                continue

            try:
                relative_path = file_path.relative_to(repo_dir)
            except ValueError:
                continue

            # TC-1023: Check exclude patterns
            rel_str = str(relative_path).replace("\\", "/")
            if _matches_exclude_pattern(rel_str, exclude_patterns):
                continue

            # Detect language
            language = detect_language_from_extension(file_path)

            # TC-1023: Do NOT skip unknown language files -- record them
            # (was: if language == "unknown": continue)

            # Estimate complexity
            complexity = estimate_complexity(file_path)

            # Compute relevance score
            relevance_score = compute_example_relevance_score(
                file_path, repo_dir, is_in_example_root=True
            )

            # TC-1023: Add file_size_bytes
            try:
                file_size_bytes = file_path.stat().st_size
            except OSError:
                file_size_bytes = 0

            example_entry = {
                "path": rel_str,
                "language": language,
                "complexity": complexity,
                "relevance_score": relevance_score,
                "source_type": "repo_file",
                "file_size_bytes": file_size_bytes,
            }

            # TC-1024: Mark gitignored files
            if gitignore_patterns and matches_gitignore(rel_str, gitignore_patterns):
                example_entry["gitignored"] = True

            discovered_examples.append(example_entry)

    # Second, scan for example files outside of example roots
    # (per specs/05_example_curation.md:61-69)
    # TC-1023: Use scan_directories instead of hardcoded repo_dir.rglob
    scan_roots = []
    for sd in scan_directories:
        sd_normalized = sd.replace("\\", "/").strip("/")
        if sd_normalized == "." or sd_normalized == "":
            scan_roots.append(repo_dir)
        else:
            candidate = repo_dir / sd_normalized
            if candidate.exists() and candidate.is_dir():
                scan_roots.append(candidate)

    for scan_root in scan_roots:
        for file_path in scan_root.rglob("*"):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip hidden files
            if any(part.startswith(".") for part in file_path.parts):
                continue

            # Skip files in example roots (already processed)
            try:
                relative_path = file_path.relative_to(repo_dir)
            except ValueError:
                continue

            if len(relative_path.parts) > 0 and relative_path.parts[0] in example_roots:
                continue

            # TC-1023: Check exclude patterns
            rel_str = str(relative_path).replace("\\", "/")
            if _matches_exclude_pattern(rel_str, exclude_patterns):
                continue

            # Check if file matches example patterns
            if not is_example_file(file_path):
                continue

            # Detect language
            language = detect_language_from_extension(file_path)

            # TC-1023: Do NOT skip unknown language files -- record them
            # (was: if language == "unknown": continue)

            # Estimate complexity
            complexity = estimate_complexity(file_path)

            # Compute relevance score
            relevance_score = compute_example_relevance_score(
                file_path, repo_dir, is_in_example_root=False
            )

            # Check if this is a test-example
            source_type = "repo_file"
            if len(relative_path.parts) > 0 and relative_path.parts[0] in ("tests", "test", "__tests__", "spec"):
                source_type = "test_example"

            # TC-1023: Add file_size_bytes
            try:
                file_size_bytes = file_path.stat().st_size
            except OSError:
                file_size_bytes = 0

            example_entry = {
                "path": rel_str,
                "language": language,
                "complexity": complexity,
                "relevance_score": relevance_score,
                "source_type": source_type,
                "file_size_bytes": file_size_bytes,
            }

            # TC-1024: Mark gitignored files
            if gitignore_patterns and matches_gitignore(rel_str, gitignore_patterns):
                example_entry["gitignored"] = True

            discovered_examples.append(example_entry)

    # Sort by relevance score (descending), then by path (lexicographic)
    # This ensures deterministic ordering per specs/10_determinism_and_caching.md
    discovered_examples.sort(key=lambda e: (-e["relevance_score"], e["path"]))

    return discovered_examples


def build_discovered_examples_artifact(
    repo_dir: Path,
    example_roots: List[str],
    example_file_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build discovered_examples.json artifact.

    Args:
        repo_dir: Repository root directory
        example_roots: List of example root directories
        example_file_details: List of discovered example files

    Returns:
        Artifact dictionary
    """
    # Extract example_paths (simplified list of paths)
    example_paths = [e["path"] for e in example_file_details]

    # Group examples by language for summary
    language_counts = {}
    for example in example_file_details:
        lang = example["language"]
        language_counts[lang] = language_counts.get(lang, 0) + 1

    # Group by complexity
    complexity_counts = {}
    for example in example_file_details:
        comp = example["complexity"]
        complexity_counts[comp] = complexity_counts.get(comp, 0) + 1

    artifact = {
        "example_roots": example_roots,
        "example_paths": example_paths,
        "example_file_details": example_file_details,
        "discovery_summary": {
            "total_examples_found": len(example_file_details),
            "example_roots_count": len(example_roots),
            "languages": language_counts,
            "complexity": complexity_counts,
        },
    }

    return artifact


def write_discovered_examples_artifact(
    run_layout: RunLayout,
    artifact: Dict[str, Any],
) -> None:
    """Write discovered_examples.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        artifact: Discovered examples artifact dictionary

    Spec reference: specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "discovered_examples.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(artifact, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def update_repo_inventory_with_examples(
    run_layout: RunLayout,
    example_roots: List[str],
    example_paths: List[str],
    example_file_details: List[Dict[str, Any]],
) -> None:
    """Update repo_inventory.json with example discovery results.

    Args:
        run_layout: Run directory layout
        example_roots: List of example root directories
        example_paths: List of example file paths
        example_file_details: Detailed example metadata

    Spec reference: specs/02_repo_ingestion.md (Repo inventory updates)
    """
    inventory_path = run_layout.artifacts_dir / "repo_inventory.json"

    if not inventory_path.exists():
        raise FileNotFoundError(
            "repo_inventory.json not found. TC-402 must run before TC-404."
        )

    # Load existing inventory
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    # Update with example discovery results
    inventory["example_roots"] = example_roots
    inventory["example_paths"] = example_paths

    # Add detailed example information (not required by schema but useful)
    if "example_file_details" not in inventory:
        inventory["example_file_details"] = example_file_details

    # Update repo_profile.example_locator
    if example_roots:
        inventory["repo_profile"]["example_locator"] = "standard_dirs"
    elif example_paths:
        inventory["repo_profile"]["example_locator"] = "pattern_based"
    else:
        inventory["repo_profile"]["example_locator"] = "none_found"

    # Write updated inventory with atomic write
    content = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    temp_path = inventory_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(inventory_path)


def emit_discover_examples_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    examples_found: int,
    example_roots_count: int,
) -> None:
    """Emit events for example discovery operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        examples_found: Number of example files discovered
        example_roots_count: Number of example root directories found

    Spec reference:
    - specs/02_repo_ingestion.md:154 (EXAMPLE_DISCOVERY_COMPLETED event)
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
        {"worker": "w1_repo_scout", "task": "discover_examples", "step": "TC-404"},
    )

    # Custom event: EXAMPLE_DISCOVERY_COMPLETED (per specs/02_repo_ingestion.md:154)
    write_event(
        "EXAMPLE_DISCOVERY_COMPLETED",
        {
            "examples_found": examples_found,
            "example_roots_count": example_roots_count,
        },
    )

    # ARTIFACT_WRITTEN (for discovered_examples.json)
    artifact_path = run_layout.artifacts_dir / "discovered_examples.json"
    if artifact_path.exists():
        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "discovered_examples.json",
                "path": str(artifact_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": "discovered_examples.schema.json",
            },
        )

    # ARTIFACT_WRITTEN (for updated repo_inventory.json)
    inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
    if inventory_path.exists():
        content = inventory_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "repo_inventory.json",
                "path": str(inventory_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": "repo_inventory.schema.json",
            },
        )

    # WORK_ITEM_FINISHED
    write_event(
        EVENT_WORK_ITEM_FINISHED,
        {
            "worker": "w1_repo_scout",
            "task": "discover_examples",
            "step": "TC-404",
            "status": "success",
        },
    )


def discover_examples(repo_dir: Path, run_dir: Path) -> Dict[str, Any]:
    """Main entry point for TC-404 example discovery.

    This function:
    1. Identifies example root directories (examples/, samples/, demo/)
    2. Discovers example files using pattern and location-based detection
    3. Scores examples by relevance and quality
    4. Extracts example metadata (language, complexity)
    5. Writes discovered_examples.json artifact
    6. Updates repo_inventory.json with example discovery results
    7. Emits telemetry events

    Args:
        repo_dir: Repository root directory (work/repo/)
        run_dir: Run directory path

    Returns:
        Discovered examples artifact dictionary

    Spec references:
    - specs/02_repo_ingestion.md:143-156 (Example discovery)
    - specs/05_example_curation.md:61-97 (Example curation)
    - specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Identify example root directories
    example_roots = identify_example_roots(repo_dir)

    # Discover example files
    example_file_details = discover_example_files(repo_dir, example_roots)

    # Build artifact
    artifact = build_discovered_examples_artifact(
        repo_dir=repo_dir,
        example_roots=example_roots,
        example_file_details=example_file_details,
    )

    # Write discovered_examples.json
    write_discovered_examples_artifact(run_layout, artifact)

    # Update repo_inventory.json
    example_paths = artifact["example_paths"]
    update_repo_inventory_with_examples(
        run_layout,
        example_roots,
        example_paths,
        example_file_details,
    )

    # Emit events
    # Note: Using dummy IDs for now. In production, these come from orchestrator.
    emit_discover_examples_events(
        run_layout=run_layout,
        run_id="unknown",
        trace_id="unknown",
        span_id="unknown",
        examples_found=len(example_file_details),
        example_roots_count=len(example_roots),
    )

    return artifact


def run_discover_examples_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-404 discover_examples worker.

    Entry point for W1.4 discover_examples worker. This can be invoked by:
    - Orchestrator (TC-300) as part of W1 RepoScout
    - Standalone for testing/debugging

    Args:
        run_dir: Run directory path
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry

    Returns:
        Exit code (0 = success, non-zero = failure)

    Spec reference: specs/21_worker_contracts.md (Worker contract)
    """
    try:
        run_layout = RunLayout(run_dir=run_dir)
        repo_dir = run_layout.work_dir / "repo"

        if not repo_dir.exists():
            raise FileNotFoundError(
                f"Repository directory not found: {repo_dir}. "
                "TC-401 clone must run before TC-404."
            )

        # Discover examples
        artifact = discover_examples(repo_dir, run_dir)

        # Emit events with proper IDs
        emit_discover_examples_events(
            run_layout,
            run_id,
            trace_id,
            span_id,
            artifact["discovery_summary"]["total_examples_found"],
            artifact["discovery_summary"]["example_roots_count"],
        )

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", flush=True)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error in discover_examples worker: {e}", flush=True)
        return 5  # Unexpected internal error
