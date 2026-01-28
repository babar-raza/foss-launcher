"""W1.1 Clone inputs and resolve SHAs deterministically.

This module implements deterministic cloning and SHA resolution for:
- Product repository (github_repo_url + github_ref)
- Site repository (site_repo_url + site_ref)
- Workflows repository (workflows_repo_url + workflows_ref)

Resolved SHAs are recorded in artifacts for reproducibility.

Spec references:
- specs/02_repo_ingestion.md (Clone and fingerprint)
- specs/21_worker_contracts.md (W1 binding requirements)
- specs/10_determinism_and_caching.md (Deterministic operations)
- specs/11_state_and_events.md (Event emission)

TC-401: W1.1 Clone inputs and resolve SHAs deterministically
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_INPUTS_CLONED,
    EVENT_ARTIFACT_WRITTEN,
)
from ...models.run_config import RunConfig
from .._git.clone_helpers import clone_and_resolve, GitCloneError, GitResolveError


def clone_inputs(run_layout: RunLayout, run_config: RunConfig) -> Dict[str, Any]:
    """Clone all input repositories and resolve SHAs.

    This function clones:
    1. Product repository → RUN_DIR/work/repo/
    2. Site repository → RUN_DIR/work/site/ (if configured)
    3. Workflows repository → RUN_DIR/work/workflows/ (if configured)

    Each clone operation resolves the requested ref to a full 40-character SHA
    for deterministic reproducibility per specs/10_determinism_and_caching.md.

    Args:
        run_layout: Run directory layout providing paths
        run_config: Run configuration with repository URLs and refs

    Returns:
        Dictionary with resolved metadata:
        {
            "repo": {
                "repo_url": str,
                "requested_ref": str,
                "resolved_sha": str,
                "default_branch": str,
                "clone_path": str
            },
            "site": {...} (if site_repo_url configured),
            "workflows": {...} (if workflows_repo_url configured)
        }

    Raises:
        GitCloneError: If clone operation fails
        GitResolveError: If SHA resolution fails

    Spec references:
    - specs/21_worker_contracts.md:66-72 (W1 binding requirements)
    - specs/02_repo_ingestion.md:36-44 (Clone and fingerprint)
    """
    result = {}

    # Clone product repository (required)
    repo_dir = run_layout.work_dir / "repo"
    repo_resolved = clone_and_resolve(
        repo_url=run_config.github_repo_url,
        ref=run_config.github_ref,
        target_dir=repo_dir,
        shallow=False,  # Full clone for complete history access
    )

    result["repo"] = {
        "repo_url": repo_resolved.repo_url,
        "requested_ref": repo_resolved.requested_ref,
        "resolved_sha": repo_resolved.resolved_sha,
        "default_branch": repo_resolved.default_branch,
        "clone_path": repo_resolved.clone_path,
    }

    # Clone site repository (optional)
    if run_config.site_repo_url and run_config.site_ref:
        site_dir = run_layout.work_dir / "site"
        site_resolved = clone_and_resolve(
            repo_url=run_config.site_repo_url,
            ref=run_config.site_ref,
            target_dir=site_dir,
            shallow=False,
        )

        result["site"] = {
            "repo_url": site_resolved.repo_url,
            "requested_ref": site_resolved.requested_ref,
            "resolved_sha": site_resolved.resolved_sha,
            "default_branch": site_resolved.default_branch,
            "clone_path": site_resolved.clone_path,
        }

    # Clone workflows repository (optional)
    if run_config.workflows_repo_url and run_config.workflows_ref:
        workflows_dir = run_layout.work_dir / "workflows"
        workflows_resolved = clone_and_resolve(
            repo_url=run_config.workflows_repo_url,
            ref=run_config.workflows_ref,
            target_dir=workflows_dir,
            shallow=False,
        )

        result["workflows"] = {
            "repo_url": workflows_resolved.repo_url,
            "requested_ref": workflows_resolved.requested_ref,
            "resolved_sha": workflows_resolved.resolved_sha,
            "default_branch": workflows_resolved.default_branch,
            "clone_path": workflows_resolved.clone_path,
        }

    return result


def write_resolved_refs_artifact(
    run_layout: RunLayout, resolved_metadata: Dict[str, Any]
) -> None:
    """Write resolved refs to artifacts directory.

    This creates a temporary artifact file recording all resolved SHAs.
    The final repo_inventory.json and site_context.json will be created
    by later TC-402, TC-403, TC-404 workers, but this provides early
    provenance recording.

    Args:
        run_layout: Run directory layout
        resolved_metadata: Resolved repository metadata from clone_inputs()

    Spec reference:
    - specs/21_worker_contracts.md:66-72 (W1 binding requirements)
    """
    artifact_path = run_layout.artifacts_dir / "resolved_refs.json"

    # Ensure artifacts directory exists
    run_layout.artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write with stable JSON formatting (deterministic)
    content = json.dumps(resolved_metadata, indent=2, sort_keys=True) + "\n"

    # Atomic write using temp file + rename pattern
    temp_path = artifact_path.with_suffix(".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(artifact_path)


def emit_clone_events(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    resolved_metadata: Dict[str, Any],
) -> None:
    """Emit events for clone operations.

    Per specs/21_worker_contracts.md:33-40, workers MUST emit:
    - WORK_ITEM_STARTED at beginning
    - INPUTS_CLONED after successful clone
    - ARTIFACT_WRITTEN for each artifact created
    - WORK_ITEM_FINISHED at completion

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        resolved_metadata: Resolved repository metadata

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
        {"worker": "w1_repo_scout", "task": "clone_inputs", "step": "TC-401"},
    )

    # INPUTS_CLONED
    write_event(
        EVENT_INPUTS_CLONED,
        {
            "repo_sha": resolved_metadata["repo"]["resolved_sha"],
            "site_sha": resolved_metadata.get("site", {}).get("resolved_sha"),
            "workflows_sha": resolved_metadata.get("workflows", {}).get("resolved_sha"),
        },
    )

    # ARTIFACT_WRITTEN (for resolved_refs.json)
    artifact_path = run_layout.artifacts_dir / "resolved_refs.json"
    if artifact_path.exists():
        import hashlib

        content = artifact_path.read_bytes()
        sha256_hash = hashlib.sha256(content).hexdigest()

        write_event(
            EVENT_ARTIFACT_WRITTEN,
            {
                "name": "resolved_refs.json",
                "path": str(artifact_path.relative_to(run_layout.run_dir)),
                "sha256": sha256_hash,
                "schema_id": None,  # No formal schema for this temporary artifact
            },
        )

    # WORK_ITEM_FINISHED
    write_event(
        EVENT_WORK_ITEM_FINISHED,
        {
            "worker": "w1_repo_scout",
            "task": "clone_inputs",
            "step": "TC-401",
            "status": "success",
        },
    )


def run_clone_worker(
    run_dir: Path,
    run_id: str,
    trace_id: str,
    span_id: str,
) -> int:
    """Run TC-401 clone worker.

    Entry point for W1.1 clone worker. This can be invoked by:
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

        # Load run_config.yaml
        from ...io.run_config import load_and_validate_run_config
        from ...models.run_config import RunConfig

        # Determine repo root (go up from src/launch to repo root)
        repo_root = Path(__file__).parent.parent.parent.parent.parent
        run_config_path = run_dir / "run_config.yaml"
        config_data = load_and_validate_run_config(repo_root, run_config_path)
        run_config = RunConfig.from_dict(config_data)

        # Clone all inputs
        resolved_metadata = clone_inputs(run_layout, run_config)

        # Write artifact
        write_resolved_refs_artifact(run_layout, resolved_metadata)

        # Emit events
        emit_clone_events(run_layout, run_id, trace_id, span_id, resolved_metadata)

        return 0

    except GitCloneError as e:
        # Log error and return failure
        error_msg = str(e)
        print(f"ERROR: Clone failed: {error_msg}", flush=True)

        # Determine if retryable
        is_retryable = "RETRYABLE" in error_msg

        # TODO: Open BLOCKER issue via issue.schema.json
        # For now, just fail with appropriate exit code
        return 3 if is_retryable else 1

    except GitResolveError as e:
        error_msg = str(e)
        print(f"ERROR: SHA resolution failed: {error_msg}", flush=True)

        is_retryable = "RETRYABLE" in error_msg
        return 3 if is_retryable else 1

    except Exception as e:
        print(f"ERROR: Unexpected error in clone worker: {e}", flush=True)
        return 5  # Unexpected internal error
