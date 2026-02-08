"""TC-420: W3 SnippetCurator integrator worker.

This module implements the W3 SnippetCurator integrator that orchestrates all
sub-workers (TC-421, TC-422) into a single cohesive worker that the orchestrator
can call.

W3 SnippetCurator performs:
1. TC-421: Extract snippets from documentation files
2. TC-422: Extract snippets from code/example files
3. Merge doc_snippets.json and code_snippets.json into snippet_catalog.json
4. Deduplicate snippets across sources

Output artifacts:
- doc_snippets.json (intermediate, TC-421)
- code_snippets.json (intermediate, TC-422)
- snippet_catalog.json (final, merged and deduplicated)

Spec references:
- specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (State transitions and events)

TC-420: W3 SnippetCurator integrator
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...io.run_layout import RunLayout
from ...io.artifact_store import ArtifactStore
from ...io.hashing import sha256_bytes
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_RUN_FAILED,
)
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config

# Import sub-worker functions
from .extract_doc_snippets import extract_doc_snippets
from .extract_code_snippets import extract_code_snippets


class SnippetCuratorError(Exception):
    """Base exception for W3 SnippetCurator errors."""
    pass


class SnippetCuratorExtractionError(SnippetCuratorError):
    """Snippet extraction operation failed."""
    pass


class SnippetCuratorMergeError(SnippetCuratorError):
    """Snippet merge operation failed."""
    pass


def emit_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    event_type: str,
    payload: Dict[str, Any],
) -> None:
    """Emit a single event to events.ndjson.

    TC-1033: Delegates to ArtifactStore.emit_event for centralized event emission.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type string
        payload: Event payload dictionary

    Spec reference: specs/11_state_and_events.md
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def emit_artifact_written_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    artifact_name: str,
    schema_id: Optional[str] = None,
) -> None:
    """Emit ARTIFACT_WRITTEN event for an artifact.

    TC-1033: Uses ArtifactStore for sha256 computation via centralized hashing.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        artifact_name: Artifact filename (e.g., "snippet_catalog.json")
        schema_id: Schema identifier (e.g., "snippet_catalog.schema.json")

    Spec reference: specs/21_worker_contracts.md:38-40
    """
    artifact_path = run_layout.artifacts_dir / artifact_name

    if not artifact_path.exists():
        return

    content = artifact_path.read_bytes()
    sha256_hash = sha256_bytes(content)

    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        EVENT_ARTIFACT_WRITTEN,
        {
            "name": artifact_name,
            "path": str(artifact_path.relative_to(run_layout.run_dir)),
            "sha256": sha256_hash,
            "schema_id": schema_id,
        },
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def deduplicate_snippets(snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate snippets by snippet_id, keeping the first occurrence.

    Per specs/21_worker_contracts.md:142, snippet_id is stable and derived from
    {path, line_range, sha256(content)}, so duplicate snippet_ids indicate
    identical snippets from different extraction passes.

    Args:
        snippets: List of snippet dictionaries (possibly with duplicates)

    Returns:
        Deduplicated list of snippets (first occurrence wins)

    Spec reference: specs/21_worker_contracts.md:142
    """
    seen_ids = set()
    unique_snippets = []

    for snippet in snippets:
        snippet_id = snippet.get("snippet_id")

        if not snippet_id:
            # Skip snippets without ID (should not happen)
            continue

        if snippet_id not in seen_ids:
            seen_ids.add(snippet_id)
            unique_snippets.append(snippet)

    return unique_snippets


def merge_snippet_artifacts(
    doc_snippets: Dict[str, Any],
    code_snippets: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge doc_snippets.json and code_snippets.json into unified catalog.

    Merging strategy:
    1. Combine snippets from both sources
    2. Deduplicate by snippet_id (first occurrence wins)
    3. Sort deterministically (per specs/10_determinism_and_caching.md)
    4. Preserve schema_version from source artifacts

    Args:
        doc_snippets: doc_snippets.json artifact
        code_snippets: code_snippets.json artifact

    Returns:
        Merged snippet_catalog.json artifact

    Spec references:
    - specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
    - specs/10_determinism_and_caching.md:46 (Stable ordering)
    """
    # Combine snippets from both sources
    all_snippets = []

    # Add doc snippets first (they have priority for deduplication)
    all_snippets.extend(doc_snippets.get("snippets", []))

    # Add code snippets
    all_snippets.extend(code_snippets.get("snippets", []))

    # Deduplicate by snippet_id
    unique_snippets = deduplicate_snippets(all_snippets)

    # Sort deterministically per specs/10_determinism_and_caching.md:46
    # Sort by: language ASC, tags[0] ASC, snippet_id ASC
    unique_snippets.sort(
        key=lambda s: (
            s.get("language", ""),
            s.get("tags", [""])[0] if s.get("tags") else "",
            s.get("snippet_id", ""),
        )
    )

    # Build merged artifact
    merged_artifact = {
        "schema_version": doc_snippets.get("schema_version", "1.0"),
        "snippets": unique_snippets,
    }

    return merged_artifact


def write_snippet_catalog_artifact(
    run_layout: RunLayout,
    artifact: Dict[str, Any],
) -> None:
    """Write snippet_catalog.json to artifacts directory.

    Args:
        run_layout: Run directory layout
        artifact: Snippet catalog artifact dictionary

    Spec reference: specs/21_worker_contracts.md:47 (Atomic writes)
    """
    artifact_path = run_layout.artifacts_dir / "snippet_catalog.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(artifact, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def execute_snippet_curator(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute W3 SnippetCurator worker (TC-420 integrator).

    This is the main entry point for W3 SnippetCurator. It orchestrates all
    sub-workers in sequence:
    1. TC-421: Extract doc snippets
    2. TC-422: Extract code snippets
    3. Merge and deduplicate snippets
    4. Write snippet_catalog.json

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary (optional, will load from disk if None)
        run_id: Run identifier (optional, generated if None)
        trace_id: Trace ID for telemetry (optional, generated if None)
        span_id: Span ID for telemetry (optional, generated if None)

    Returns:
        Dictionary with completion status and artifact paths:
        {
            "status": "success" | "failed",
            "artifacts": {
                "doc_snippets": str,
                "code_snippets": str,
                "snippet_catalog": str
            },
            "metadata": {
                "doc_snippets_count": int,
                "code_snippets_count": int,
                "total_snippets_count": int,
                "unique_snippets_count": int,
                "duplicates_removed": int
            },
            "error": Optional[str]
        }

    Raises:
        SnippetCuratorExtractionError: If extraction operation fails
        SnippetCuratorMergeError: If merge operation fails

    Spec references:
    - specs/21_worker_contracts.md:127-145 (W3 SnippetCurator contract)
    - specs/28_coordination_and_handoffs.md (Worker coordination)
    """
    # Generate default IDs if not provided
    run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
    trace_id = trace_id or str(uuid.uuid4())
    span_id = span_id or str(uuid.uuid4())

    run_layout = RunLayout(run_dir=run_dir)

    # Ensure run directory exists
    run_dir.mkdir(parents=True, exist_ok=True)

    # Load run_config if not provided
    if run_config is None:
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        run_config_path = run_dir / "run_config.yaml"
        config_data = load_and_validate_run_config(repo_root, run_config_path)
        run_config_obj = RunConfig.from_dict(config_data)
    else:
        run_config_obj = RunConfig.from_dict(run_config)

    # Emit WORK_ITEM_STARTED
    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_WORK_ITEM_STARTED,
        {
            "worker": "w3_snippet_curator",
            "task": "snippet_curation",
            "step": "TC-420",
        },
    )

    try:
        repo_dir = run_layout.work_dir / "repo"

        # Validate inputs exist
        if not repo_dir.exists():
            error_msg = (
                f"Repository directory not found: {repo_dir}. "
                "W1 RepoScout must run before W3 SnippetCurator."
            )
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_RUN_FAILED,
                {
                    "worker": "w3_snippet_curator",
                    "error": error_msg,
                    "error_code": "W3_MISSING_INPUT",
                },
            )
            raise SnippetCuratorExtractionError(error_msg)

        # Step 1: Extract doc snippets (TC-421)
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "SNIPPET_EXTRACTION_STARTED",
            {"source": "documentation", "step": "TC-421"},
        )

        try:
            doc_snippets_artifact = extract_doc_snippets(repo_dir, run_dir)
            doc_snippets_count = len(doc_snippets_artifact.get("snippets", []))

            emit_artifact_written_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "doc_snippets.json",
                "snippet_catalog.schema.json",
            )

            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "SNIPPET_EXTRACTION_COMPLETED",
                {
                    "source": "documentation",
                    "step": "TC-421",
                    "snippets_extracted": doc_snippets_count,
                },
            )

        except Exception as e:
            error_msg = f"Doc snippet extraction failed (TC-421): {e}"
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_RUN_FAILED,
                {
                    "worker": "w3_snippet_curator",
                    "step": "TC-421",
                    "error": error_msg,
                    "error_code": "W3_DOC_EXTRACTION_FAILED",
                },
            )
            raise SnippetCuratorExtractionError(error_msg) from e

        # Step 2: Extract code snippets (TC-422)
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "SNIPPET_EXTRACTION_STARTED",
            {"source": "code", "step": "TC-422"},
        )

        try:
            code_snippets_artifact = extract_code_snippets(repo_dir, run_dir)
            code_snippets_count = len(code_snippets_artifact.get("snippets", []))

            emit_artifact_written_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "code_snippets.json",
                "snippet_catalog.schema.json",
            )

            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "SNIPPET_EXTRACTION_COMPLETED",
                {
                    "source": "code",
                    "step": "TC-422",
                    "snippets_extracted": code_snippets_count,
                },
            )

        except Exception as e:
            error_msg = f"Code snippet extraction failed (TC-422): {e}"
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_RUN_FAILED,
                {
                    "worker": "w3_snippet_curator",
                    "step": "TC-422",
                    "error": error_msg,
                    "error_code": "W3_CODE_EXTRACTION_FAILED",
                },
            )
            raise SnippetCuratorExtractionError(error_msg) from e

        # Step 3: Merge and deduplicate snippets
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "SNIPPET_MERGE_STARTED",
            {
                "doc_snippets_count": doc_snippets_count,
                "code_snippets_count": code_snippets_count,
            },
        )

        try:
            merged_catalog = merge_snippet_artifacts(
                doc_snippets_artifact,
                code_snippets_artifact,
            )

            unique_snippets_count = len(merged_catalog.get("snippets", []))
            total_before_dedup = doc_snippets_count + code_snippets_count
            duplicates_removed = total_before_dedup - unique_snippets_count

            # Write snippet_catalog.json
            write_snippet_catalog_artifact(run_layout, merged_catalog)

            emit_artifact_written_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "snippet_catalog.json",
                "snippet_catalog.schema.json",
            )

            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "SNIPPET_MERGE_COMPLETED",
                {
                    "total_snippets_before": total_before_dedup,
                    "unique_snippets_after": unique_snippets_count,
                    "duplicates_removed": duplicates_removed,
                },
            )

        except Exception as e:
            error_msg = f"Snippet merge failed: {e}"
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                EVENT_RUN_FAILED,
                {
                    "worker": "w3_snippet_curator",
                    "step": "merge",
                    "error": error_msg,
                    "error_code": "W3_MERGE_FAILED",
                },
            )
            raise SnippetCuratorMergeError(error_msg) from e

        # Emit WORK_ITEM_FINISHED
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_WORK_ITEM_FINISHED,
            {
                "worker": "w3_snippet_curator",
                "task": "snippet_curation",
                "step": "TC-420",
                "status": "success",
            },
        )

        # Return success result
        return {
            "status": "success",
            "artifacts": {
                "doc_snippets": str(run_layout.artifacts_dir / "doc_snippets.json"),
                "code_snippets": str(run_layout.artifacts_dir / "code_snippets.json"),
                "snippet_catalog": str(run_layout.artifacts_dir / "snippet_catalog.json"),
            },
            "metadata": {
                "doc_snippets_count": doc_snippets_count,
                "code_snippets_count": code_snippets_count,
                "total_snippets_count": total_before_dedup,
                "unique_snippets_count": unique_snippets_count,
                "duplicates_removed": duplicates_removed,
            },
            "error": None,
        }

    except (SnippetCuratorExtractionError, SnippetCuratorMergeError) as e:
        # Return failure result
        return {
            "status": "failed",
            "artifacts": {},
            "metadata": {},
            "error": str(e),
        }

    except Exception as e:
        # Unexpected error
        error_msg = f"Unexpected error in W3 SnippetCurator: {e}"
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_RUN_FAILED,
            {
                "worker": "w3_snippet_curator",
                "error": error_msg,
                "error_code": "W3_UNEXPECTED_ERROR",
            },
        )

        return {
            "status": "failed",
            "artifacts": {},
            "metadata": {},
            "error": error_msg,
        }
