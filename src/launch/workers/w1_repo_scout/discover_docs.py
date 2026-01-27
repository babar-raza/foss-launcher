"""W1.3 Documentation discovery in cloned product repo.

This module implements documentation discovery per specs/02_repo_ingestion.md.

Documentation discovery algorithm (binding):
1. Find README files (README*, root-level)
2. Scan for standard doc directories (docs/, documentation/, site/)
3. Pattern-based discovery (ARCHITECTURE*, IMPLEMENTATION*, etc.)
4. Content-based discovery (scan first 50 lines for key headings)
5. Score docs by relevance (root README > docs/ > nested)
6. Extract front matter and metadata

Spec references:
- specs/02_repo_ingestion.md:78-142 (Docs discovery)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/21_worker_contracts.md (Worker interface)

TC-403: W1.3 Discover docs in cloned product repo
"""

from __future__ import annotations

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


# Pattern-based detection patterns (per specs/02_repo_ingestion.md:88-93)
PATTERN_BASED_FILENAMES = [
    re.compile(r".*IMPLEMENTATION.*\.md$", re.IGNORECASE),
    re.compile(r".*SUMMARY.*\.md$", re.IGNORECASE),
    re.compile(r"ARCHITECTURE.*\.md$", re.IGNORECASE),
    re.compile(r"DESIGN.*\.md$", re.IGNORECASE),
    re.compile(r"SPEC.*\.md$", re.IGNORECASE),
    re.compile(r"CHANGELOG.*\.md$", re.IGNORECASE),
    re.compile(r"CONTRIBUTING.*\.md$", re.IGNORECASE),
    re.compile(r".*NOTES.*\.md$", re.IGNORECASE),
    re.compile(r".*PLAN.*\.md$", re.IGNORECASE),
    re.compile(r"ROADMAP.*\.md$", re.IGNORECASE),
]

# Content-based detection keywords (per specs/02_repo_ingestion.md:94-97)
CONTENT_KEYWORDS = [
    "Features",
    "Limitations",
    "Implementation",
    "Architecture",
    "Supported",
    "Not supported",
    "TODO",
    "Known Issues",
    "API",
    "Public API",
    "Usage",
    "Quick Start",
]


def is_readme(file_path: Path) -> bool:
    """Check if file is a README file.

    Args:
        file_path: Path to file

    Returns:
        True if file is a README

    Spec reference: specs/02_repo_ingestion.md:50
    """
    filename = file_path.name.upper()
    return filename.startswith("README")


def matches_pattern_based_detection(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Check if filename matches pattern-based detection rules.

    Args:
        file_path: Path to file

    Returns:
        Tuple of (matches, doc_type)

    Spec reference: specs/02_repo_ingestion.md:88-93
    """
    filename = file_path.name

    for pattern in PATTERN_BASED_FILENAMES:
        if pattern.match(filename):
            # Determine doc_type based on pattern
            filename_upper = filename.upper()

            if "IMPLEMENTATION" in filename_upper or "NOTES" in filename_upper:
                return True, "implementation_notes"
            elif "ARCHITECTURE" in filename_upper or "DESIGN" in filename_upper or "SPEC" in filename_upper:
                return True, "architecture"
            elif "CHANGELOG" in filename_upper:
                return True, "changelog"
            else:
                return True, "other"

    return False, None


def check_content_based_detection(file_path: Path) -> bool:
    """Check if file content matches content-based detection rules.

    Scans first 50 lines for key headings per specs/02_repo_ingestion.md:94-97.

    Args:
        file_path: Path to file

    Returns:
        True if content matches keywords

    Spec reference: specs/02_repo_ingestion.md:94-97
    """
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            # Read first 50 lines
            for _ in range(50):
                line = f.readline()
                if not line:
                    break

                # Check for headings (lines starting with #)
                if line.strip().startswith("#"):
                    heading_text = line.strip().lstrip("#").strip()

                    # Check if heading contains any keywords
                    for keyword in CONTENT_KEYWORDS:
                        if keyword.lower() in heading_text.lower():
                            return True
    except (OSError, UnicodeDecodeError):
        # Cannot read file, skip
        pass

    return False


def extract_front_matter(file_path: Path) -> Optional[Dict[str, Any]]:
    """Extract YAML front matter from markdown file.

    Args:
        file_path: Path to markdown file

    Returns:
        Front matter dictionary or None
    """
    try:
        with file_path.open("r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

            # Check for YAML front matter (--- at start)
            if content.startswith("---\n"):
                # Find closing ---
                end_idx = content.find("\n---\n", 4)
                if end_idx > 0:
                    front_matter_text = content[4:end_idx]

                    # Simple YAML parsing (key: value pairs)
                    # Note: This is a simplified parser. Production code should use PyYAML.
                    front_matter = {}
                    for line in front_matter_text.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            front_matter[key.strip()] = value.strip()

                    return front_matter if front_matter else None
    except (OSError, UnicodeDecodeError):
        pass

    return None


def compute_doc_relevance_score(file_path: Path, repo_dir: Path) -> int:
    """Compute relevance score for documentation file.

    Scoring rules (per specs/02_repo_ingestion.md):
    - Root README: 100
    - Root-level docs: 90
    - docs/ directory: 80
    - Nested docs: 50
    - Other: 30

    Args:
        file_path: Path to documentation file
        repo_dir: Repository root directory

    Returns:
        Relevance score (0-100)

    Spec reference: specs/02_repo_ingestion.md:78-83
    """
    try:
        relative_path = file_path.relative_to(repo_dir)
    except ValueError:
        return 0

    parts = relative_path.parts

    # Root README gets highest score
    if len(parts) == 1 and is_readme(file_path):
        return 100

    # Root-level documentation files
    if len(parts) == 1:
        return 90

    # Files directly in docs/ directory (e.g., docs/intro.md)
    if len(parts) == 2 and parts[0] in ("docs", "documentation", "site"):
        return 80

    # Nested documentation (deeper than docs/ first level, e.g., docs/api/methods.md)
    if len(parts) > 2 and parts[0] in ("docs", "documentation", "site"):
        return 50

    # Other nested files (not in standard doc directories)
    if len(parts) > 2:
        return 50

    # Default (files at second level but not in doc dirs)
    return 30


def discover_documentation_files(repo_dir: Path) -> List[Dict[str, Any]]:
    """Discover documentation files in repository.

    Implements discovery algorithm from specs/02_repo_ingestion.md:78-142.

    Args:
        repo_dir: Repository root directory

    Returns:
        List of discovered documentation files with metadata

    Spec reference: specs/02_repo_ingestion.md:78-142
    """
    discovered_docs = []

    # Scan for markdown and text files
    doc_extensions = {".md", ".rst", ".txt"}

    for file_path in repo_dir.rglob("*"):
        # Skip directories
        if file_path.is_dir():
            continue

        # Skip non-documentation files
        if file_path.suffix.lower() not in doc_extensions:
            continue

        # Skip hidden directories (like .git)
        if any(part.startswith(".") for part in file_path.parts):
            continue

        try:
            relative_path = file_path.relative_to(repo_dir)
        except ValueError:
            continue

        # Determine doc_type
        doc_type = "other"
        evidence_priority = "low"

        # Check if it's a README
        if is_readme(file_path):
            doc_type = "readme"
            evidence_priority = "high"
        else:
            # Check pattern-based detection
            pattern_match, pattern_doc_type = matches_pattern_based_detection(file_path)
            if pattern_match and pattern_doc_type:
                doc_type = pattern_doc_type

                # Implementation notes get high priority
                if doc_type == "implementation_notes":
                    evidence_priority = "high"
                elif doc_type == "architecture":
                    evidence_priority = "medium"
            else:
                # Check content-based detection
                if check_content_based_detection(file_path):
                    # Content matches keywords, likely important doc
                    evidence_priority = "medium"

        # Compute relevance score
        relevance_score = compute_doc_relevance_score(file_path, repo_dir)

        # Extract front matter (if present)
        front_matter = extract_front_matter(file_path)

        doc_entry = {
            "path": str(relative_path).replace("\\", "/"),
            "doc_type": doc_type,
            "evidence_priority": evidence_priority,
            "relevance_score": relevance_score,
        }

        if front_matter:
            doc_entry["front_matter"] = front_matter

        discovered_docs.append(doc_entry)

    # Sort by relevance score (descending), then by path (lexicographic)
    # This ensures deterministic ordering per specs/10_determinism_and_caching.md
    discovered_docs.sort(key=lambda d: (-d["relevance_score"], d["path"]))

    return discovered_docs


def identify_doc_roots(repo_dir: Path) -> List[str]:
    """Identify documentation root directories.

    Per specs/02_repo_ingestion.md:79-83, doc_roots MUST include:
    - docs/ if present
    - documentation/ if present
    - site/ if present

    Args:
        repo_dir: Repository root directory

    Returns:
        Sorted list of doc root directories

    Spec reference: specs/02_repo_ingestion.md:79-83
    """
    doc_root_candidates = ["docs", "documentation", "site"]
    doc_roots = []

    for candidate in doc_root_candidates:
        candidate_path = repo_dir / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            doc_roots.append(candidate)

    # Sort for determinism
    doc_roots.sort()
    return doc_roots


def build_discovered_docs_artifact(
    repo_dir: Path,
    doc_roots: List[str],
    doc_entrypoint_details: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build discovered_docs.json artifact.

    Args:
        repo_dir: Repository root directory
        doc_roots: List of documentation root directories
        doc_entrypoint_details: List of discovered documentation files

    Returns:
        Artifact dictionary
    """
    # Extract doc_entrypoints (simplified list of paths)
    doc_entrypoints = [d["path"] for d in doc_entrypoint_details]

    artifact = {
        "doc_roots": doc_roots,
        "doc_entrypoints": doc_entrypoints,
        "doc_entrypoint_details": doc_entrypoint_details,
        "discovery_summary": {
            "total_docs_found": len(doc_entrypoint_details),
            "readme_count": sum(1 for d in doc_entrypoint_details if d["doc_type"] == "readme"),
            "implementation_notes_count": sum(
                1 for d in doc_entrypoint_details if d["doc_type"] == "implementation_notes"
            ),
            "architecture_count": sum(
                1 for d in doc_entrypoint_details if d["doc_type"] == "architecture"
            ),
        },
    }

    return artifact


def write_discovered_docs_artifact(
    run_layout: RunLayout,
    artifact: Dict[str, Any],
) -> None:
    """Write discovered_docs.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        artifact: Discovered docs artifact dictionary

    Spec reference: specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "discovered_docs.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(artifact, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def update_repo_inventory_with_docs(
    run_layout: RunLayout,
    doc_roots: List[str],
    doc_entrypoints: List[str],
    doc_entrypoint_details: List[Dict[str, Any]],
) -> None:
    """Update repo_inventory.json with documentation discovery results.

    Args:
        run_layout: Run directory layout
        doc_roots: List of documentation root directories
        doc_entrypoints: List of documentation file paths
        doc_entrypoint_details: Detailed documentation metadata

    Spec reference: specs/02_repo_ingestion.md (Repo inventory updates)
    """
    inventory_path = run_layout.artifacts_dir / "repo_inventory.json"

    if not inventory_path.exists():
        raise FileNotFoundError(
            "repo_inventory.json not found. TC-402 must run before TC-403."
        )

    # Load existing inventory
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    # Update with doc discovery results
    inventory["doc_roots"] = doc_roots
    inventory["doc_entrypoints"] = doc_entrypoints
    inventory["doc_entrypoint_details"] = doc_entrypoint_details

    # Update repo_profile.doc_locator
    if doc_roots or doc_entrypoints:
        inventory["repo_profile"]["doc_locator"] = "pattern_and_content_based"
    else:
        inventory["repo_profile"]["doc_locator"] = "none_found"

    # Write updated inventory with atomic write
    content = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    temp_path = inventory_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(inventory_path)


def emit_discover_docs_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    docs_found: int,
) -> None:
    """Emit events for documentation discovery operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        docs_found: Number of documentation files discovered

    Spec reference: specs/21_worker_contracts.md:33-40
    """
    import datetime
    import hashlib
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
        {"worker": "w1_repo_scout", "task": "discover_docs", "step": "TC-403"},
    )

    # Custom event: DOCS_DISCOVERY_COMPLETED
    write_event(
        "DOCS_DISCOVERY_COMPLETED",
        {
            "docs_found": docs_found,
        },
    )

    # ARTIFACT_WRITTEN (for discovered_docs.json)
    artifact_path = run_layout.artifacts_dir / "discovered_docs.json"
    if artifact_path.exists():
        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "discovered_docs.json",
                "path": str(artifact_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": "discovered_docs.schema.json",
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
            "task": "discover_docs",
            "step": "TC-403",
            "status": "success",
        },
    )


def discover_docs(repo_dir: Path, run_dir: Path) -> Dict[str, Any]:
    """Main entry point for TC-403 documentation discovery.

    This function:
    1. Discovers documentation files using pattern and content-based detection
    2. Identifies doc root directories
    3. Scores docs by relevance
    4. Writes discovered_docs.json artifact
    5. Updates repo_inventory.json with doc discovery results
    6. Emits telemetry events

    Args:
        repo_dir: Repository root directory (work/repo/)
        run_dir: Run directory path

    Returns:
        Discovered docs artifact dictionary

    Spec references:
    - specs/02_repo_ingestion.md:78-142 (Doc discovery)
    - specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Discover documentation files
    doc_entrypoint_details = discover_documentation_files(repo_dir)

    # Identify doc root directories
    doc_roots = identify_doc_roots(repo_dir)

    # Build artifact
    artifact = build_discovered_docs_artifact(
        repo_dir=repo_dir,
        doc_roots=doc_roots,
        doc_entrypoint_details=doc_entrypoint_details,
    )

    # Write discovered_docs.json
    write_discovered_docs_artifact(run_layout, artifact)

    # Update repo_inventory.json
    doc_entrypoints = artifact["doc_entrypoints"]
    update_repo_inventory_with_docs(
        run_layout,
        doc_roots,
        doc_entrypoints,
        doc_entrypoint_details,
    )

    # Emit events
    # Note: Using dummy IDs for now. In production, these come from orchestrator.
    emit_discover_docs_events(
        run_layout=run_layout,
        run_id="unknown",
        trace_id="unknown",
        span_id="unknown",
        docs_found=len(doc_entrypoint_details),
    )

    return artifact


def run_discover_docs_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-403 discover_docs worker.

    Entry point for W1.3 discover_docs worker. This can be invoked by:
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
                "TC-401 clone must run before TC-403."
            )

        # Discover docs
        artifact = discover_docs(repo_dir, run_dir)

        # Emit events with proper IDs
        emit_discover_docs_events(
            run_layout,
            run_id,
            trace_id,
            span_id,
            artifact["discovery_summary"]["total_docs_found"],
        )

        return 0

    except FileNotFoundError as e:
        print(f"ERROR: {e}", flush=True)
        return 1

    except Exception as e:
        print(f"ERROR: Unexpected error in discover_docs worker: {e}", flush=True)
        return 5  # Unexpected internal error
