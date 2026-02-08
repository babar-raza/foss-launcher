"""TC-400: W1 RepoScout integrator worker.

This module implements the W1 RepoScout integrator that orchestrates all
sub-workers (TC-401, TC-402, TC-403, TC-404) into a single cohesive worker
that the orchestrator can call.

W1 RepoScout performs:
1. TC-401: Clone inputs and resolve SHAs deterministically
2. TC-402: Deterministic repo fingerprinting and inventory
3. TC-403: Discover documentation files
4. TC-404: Discover example files

Output artifacts:
- resolved_refs.json (temporary, TC-401)
- repo_inventory.json (final, updated by all sub-workers)
- discovered_docs.json (TC-403)
- discovered_examples.json (TC-404)

Spec references:
- specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (State transitions and events)

TC-400: W1 RepoScout integrator
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

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
from .clone import clone_inputs, write_resolved_refs_artifact
from .fingerprint import build_repo_inventory, write_repo_inventory_artifact
from .discover_docs import (
    discover_documentation_files,
    identify_doc_roots,
    build_discovered_docs_artifact,
    write_discovered_docs_artifact,
    update_repo_inventory_with_docs,
)
from .discover_examples import (
    identify_example_roots,
    discover_example_files,
    build_discovered_examples_artifact,
    write_discovered_examples_artifact,
    update_repo_inventory_with_examples,
)
from .._git.clone_helpers import GitCloneError, GitResolveError
from .frontmatter_discovery import build_frontmatter_contract
from .site_context_builder import build_site_context
from .hugo_facts_builder import build_hugo_facts


class RepoScoutError(Exception):
    """Base exception for W1 RepoScout errors."""
    pass


class RepoScoutCloneError(RepoScoutError):
    """Clone operation failed."""
    pass


class RepoScoutFingerprintError(RepoScoutError):
    """Fingerprinting operation failed."""
    pass


class RepoScoutDiscoveryError(RepoScoutError):
    """Discovery operation failed."""
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
        artifact_name: Artifact filename (e.g., "repo_inventory.json")
        schema_id: Schema identifier (e.g., "repo_inventory.schema.json")

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


def execute_repo_scout(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute W1 RepoScout worker (TC-400 integrator).

    This is the main entry point for W1 RepoScout. It orchestrates all
    sub-workers in sequence:
    1. TC-401: Clone and resolve SHAs
    2. TC-402: Fingerprint repo
    3. TC-403: Discover docs
    4. TC-404: Discover examples

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
                "resolved_refs": str,
                "repo_inventory": str,
                "discovered_docs": str,
                "discovered_examples": str
            },
            "metadata": {
                "repo_sha": str,
                "file_count": int,
                "docs_found": int,
                "examples_found": int
            },
            "error": Optional[str]
        }

    Raises:
        RepoScoutCloneError: If clone operation fails
        RepoScoutFingerprintError: If fingerprinting fails
        RepoScoutDiscoveryError: If discovery fails

    Spec references:
    - specs/21_worker_contracts.md:54-95 (W1 RepoScout contract)
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
            "worker": "W1_RepoScout",
            "task": "execute_repo_scout",
            "taskcard": "TC-400",
            "sub_workers": ["TC-401", "TC-402", "TC-403", "TC-404"],
        },
    )

    result = {
        "status": "success",
        "artifacts": {},
        "metadata": {},
        "error": None,
    }

    try:
        # Step 1: TC-401 - Clone inputs and resolve SHAs
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_STARTED",
            {"step": "TC-401", "description": "Clone inputs and resolve SHAs"},
        )

        resolved_metadata = clone_inputs(run_layout, run_config_obj)
        write_resolved_refs_artifact(run_layout, resolved_metadata)

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "resolved_refs.json", schema_id=None
        )

        result["artifacts"]["resolved_refs"] = str(
            run_layout.artifacts_dir / "resolved_refs.json"
        )
        result["metadata"]["repo_sha"] = resolved_metadata["repo"]["resolved_sha"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_COMPLETED",
            {"step": "TC-401", "status": "success"},
        )

        # Step 2: TC-402 - Fingerprint repo
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_STARTED",
            {"step": "TC-402", "description": "Fingerprint repository"},
        )

        repo_dir = run_layout.work_dir / "repo"
        if not repo_dir.exists():
            raise RepoScoutFingerprintError(
                f"Repository directory not found: {repo_dir}"
            )

        # TC-1024/TC-1025: Pass ingestion config to build_repo_inventory
        inventory = build_repo_inventory(
            repo_dir=repo_dir,
            repo_url=resolved_metadata["repo"]["repo_url"],
            repo_sha=resolved_metadata["repo"]["resolved_sha"],
            gitignore_mode=run_config_obj.get_gitignore_mode(),
            exclude_patterns=run_config_obj.get_exclude_patterns(),
            detect_phantoms=run_config_obj.get_detect_phantom_paths(),
        )

        # Update with default_branch from resolved metadata
        inventory["fingerprint"]["default_branch"] = resolved_metadata["repo"].get(
            "default_branch", "unknown"
        )

        write_repo_inventory_artifact(run_layout, inventory)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "repo_inventory.json",
            schema_id="repo_inventory.schema.json",
        )

        result["artifacts"]["repo_inventory"] = str(
            run_layout.artifacts_dir / "repo_inventory.json"
        )
        result["metadata"]["file_count"] = inventory["file_count"]
        result["metadata"]["repo_fingerprint"] = inventory["repo_fingerprint"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_COMPLETED",
            {"step": "TC-402", "status": "success"},
        )

        # Step 3: TC-403 - Discover docs
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_STARTED",
            {"step": "TC-403", "description": "Discover documentation"},
        )

        # TC-1024: Pass gitignore_mode to discover_documentation_files
        doc_entrypoint_details = discover_documentation_files(
            repo_dir,
            gitignore_mode=run_config_obj.get_gitignore_mode(),
        )
        doc_roots = identify_doc_roots(repo_dir)

        docs_artifact = build_discovered_docs_artifact(
            repo_dir=repo_dir,
            doc_roots=doc_roots,
            doc_entrypoint_details=doc_entrypoint_details,
        )

        write_discovered_docs_artifact(run_layout, docs_artifact)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "discovered_docs.json",
            schema_id="discovered_docs.schema.json",
        )

        # Update repo_inventory with doc discovery results
        doc_entrypoints = docs_artifact["doc_entrypoints"]
        update_repo_inventory_with_docs(
            run_layout,
            doc_roots,
            doc_entrypoints,
            doc_entrypoint_details,
        )

        # Re-emit repo_inventory artifact written event (it was updated)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "repo_inventory.json",
            schema_id="repo_inventory.schema.json",
        )

        result["artifacts"]["discovered_docs"] = str(
            run_layout.artifacts_dir / "discovered_docs.json"
        )
        result["metadata"]["docs_found"] = len(doc_entrypoint_details)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_COMPLETED",
            {"step": "TC-403", "status": "success"},
        )

        # Step 4: TC-404 - Discover examples
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_STARTED",
            {"step": "TC-404", "description": "Discover examples"},
        )

        # TC-1023: Pass configurable directories from run_config
        example_roots = identify_example_roots(
            repo_dir,
            extra_example_dirs=run_config_obj.get_example_directories(),
        )
        example_file_details = discover_example_files(
            repo_dir,
            example_roots,
            scan_directories=run_config_obj.get_scan_directories(),
            exclude_patterns=run_config_obj.get_exclude_patterns(),
            gitignore_mode=run_config_obj.get_gitignore_mode(),
        )

        examples_artifact = build_discovered_examples_artifact(
            repo_dir=repo_dir,
            example_roots=example_roots,
            example_file_details=example_file_details,
        )

        write_discovered_examples_artifact(run_layout, examples_artifact)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "discovered_examples.json",
            schema_id="discovered_examples.schema.json",
        )

        # Update repo_inventory with example discovery results
        example_paths = examples_artifact["example_paths"]
        update_repo_inventory_with_examples(
            run_layout,
            example_roots,
            example_paths,
            example_file_details,
        )

        # Re-emit repo_inventory artifact written event (it was updated again)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "repo_inventory.json",
            schema_id="repo_inventory.schema.json",
        )

        result["artifacts"]["discovered_examples"] = str(
            run_layout.artifacts_dir / "discovered_examples.json"
        )
        result["metadata"]["examples_found"] = len(example_file_details)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "REPO_SCOUT_STEP_COMPLETED",
            {"step": "TC-404", "status": "success"},
        )

        # TC-1034: Build enriched artifacts using real builders
        # (replaces minimal TC-300 stubs)

        # Load discovered_docs artifact for frontmatter scanning
        discovered_docs_path = run_layout.artifacts_dir / "discovered_docs.json"
        discovered_docs_data = {}
        if discovered_docs_path.exists():
            discovered_docs_data = json.loads(
                discovered_docs_path.read_text(encoding="utf-8")
            )

        run_config_dict = run_config_obj.to_dict()

        # Write frontmatter_contract.json (TC-1034: real builder)
        frontmatter_contract = build_frontmatter_contract(
            repo_dir=repo_dir,
            discovered_docs=discovered_docs_data,
            run_config_dict=run_config_dict,
            resolved_metadata=resolved_metadata,
        )
        frontmatter_contract_path = run_layout.artifacts_dir / "frontmatter_contract.json"
        frontmatter_contract_path.write_text(
            json.dumps(frontmatter_contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8"
        )
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "frontmatter_contract.json",
            schema_id="frontmatter_contract.schema.json"
        )
        result["artifacts"]["frontmatter_contract"] = str(frontmatter_contract_path)

        # Write site_context.json (TC-1034: real builder)
        site_dir = run_layout.work_dir / "site"
        site_context = build_site_context(
            run_config_dict=run_config_dict,
            resolved_metadata=resolved_metadata,
            site_dir=site_dir if site_dir.exists() else None,
        )
        site_context_path = run_layout.artifacts_dir / "site_context.json"
        site_context_path.write_text(
            json.dumps(site_context, indent=2, sort_keys=True) + "\n",
            encoding="utf-8"
        )
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "site_context.json",
            schema_id="site_context.schema.json"
        )
        result["artifacts"]["site_context"] = str(site_context_path)

        # Write hugo_facts.json (TC-1034: real builder)
        hugo_facts = build_hugo_facts(
            site_dir=site_dir if site_dir.exists() else None,
            run_config_dict=run_config_dict,
        )
        hugo_facts_path = run_layout.artifacts_dir / "hugo_facts.json"
        hugo_facts_path.write_text(
            json.dumps(hugo_facts, indent=2, sort_keys=True) + "\n",
            encoding="utf-8"
        )
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "hugo_facts.json",
            schema_id="hugo_facts.schema.json"
        )
        result["artifacts"]["hugo_facts"] = str(hugo_facts_path)

        # Emit WORK_ITEM_FINISHED
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_WORK_ITEM_FINISHED,
            {
                "worker": "W1_RepoScout",
                "task": "execute_repo_scout",
                "taskcard": "TC-400",
                "status": "success",
                "artifacts_produced": list(result["artifacts"].keys()),
            },
        )

        return result

    except (GitCloneError, GitResolveError) as e:
        # Clone errors (TC-401)
        error_msg = f"Clone failed: {e}"
        result["status"] = "failed"
        result["error"] = error_msg

        # Emit failure event (using custom event type since WORK_ITEM_FAILED doesn't exist)
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "WORK_ITEM_FAILED",
            {
                "worker": "W1_RepoScout",
                "task": "execute_repo_scout",
                "taskcard": "TC-400",
                "error": error_msg,
                "error_type": "clone_error",
                "retryable": "RETRYABLE" in str(e),
            },
        )

        raise RepoScoutCloneError(error_msg) from e

    except RepoScoutFingerprintError:
        # Re-raise our own exceptions as-is
        raise

    except RepoScoutDiscoveryError:
        # Re-raise our own exceptions as-is
        raise

    except FileNotFoundError as e:
        # Missing dependencies (likely TC-402/403/404)
        error_msg = f"Missing required artifact or directory: {e}"
        result["status"] = "failed"
        result["error"] = error_msg

        # Emit failure event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "WORK_ITEM_FAILED",
            {
                "worker": "W1_RepoScout",
                "task": "execute_repo_scout",
                "taskcard": "TC-400",
                "error": error_msg,
                "error_type": "missing_artifact",
                "retryable": False,
            },
        )

        raise RepoScoutFingerprintError(error_msg) from e

    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error: {e}"
        result["status"] = "failed"
        result["error"] = error_msg

        # Emit failure event
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "WORK_ITEM_FAILED",
            {
                "worker": "W1_RepoScout",
                "task": "execute_repo_scout",
                "taskcard": "TC-400",
                "error": error_msg,
                "error_type": "unexpected",
                "retryable": False,
            },
        )

        raise RepoScoutError(error_msg) from e
