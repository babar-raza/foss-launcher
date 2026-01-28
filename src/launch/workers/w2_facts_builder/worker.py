"""TC-410: W2 FactsBuilder integrator worker.

This module implements the W2 FactsBuilder integrator that orchestrates all
sub-workers (TC-411, TC-412, TC-413) into a single cohesive worker
that the orchestrator can call.

W2 FactsBuilder performs:
1. TC-411: Extract claims from documentation
2. TC-412: Map evidence from claims to docs/examples
3. TC-413: Detect contradictions and resolve conflicts

Output artifacts:
- extracted_claims.json (TC-411)
- evidence_map.json (TC-412, updated by TC-413)
- product_facts.json (final, assembled from all sub-workers)

Spec references:
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/28_coordination_and_handoffs.md (Worker coordination)
- specs/11_state_and_events.md (State transitions and events)
- specs/03_product_facts_and_evidence.md (Facts extraction algorithm)

TC-410: W2 FactsBuilder integrator
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List

from ...io.run_layout import RunLayout
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config
from ...io.atomic import atomic_write_json
from ...clients.llm_provider import LLMProviderClient, LLMError
from ...util.logging import get_logger

# Import sub-worker functions
from .extract_claims import (
    extract_claims,
    ClaimsExtractionError,
    ClaimsValidationError,
)
from .map_evidence import (
    map_evidence,
    EvidenceMappingError,
)
from .detect_contradictions import (
    detect_contradictions,
    ContradictionDetectionError,
)

logger = get_logger()


class FactsBuilderError(Exception):
    """Base exception for W2 FactsBuilder errors."""
    pass


class FactsBuilderClaimsError(FactsBuilderError):
    """Claims extraction failed."""
    pass


class FactsBuilderEvidenceError(FactsBuilderError):
    """Evidence mapping failed."""
    pass


class FactsBuilderContradictionError(FactsBuilderError):
    """Contradiction detection failed."""
    pass


class FactsBuilderAssemblyError(FactsBuilderError):
    """Product facts assembly failed."""
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

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        event_type: Event type string
        payload: Event payload dictionary

    Spec reference: specs/11_state_and_events.md
    """
    events_file = run_layout.run_dir / "events.ndjson"

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

    # Ensure events file exists
    events_file.parent.mkdir(parents=True, exist_ok=True)

    # Append to events.ndjson (append-only log)
    with events_file.open("a", encoding="utf-8") as f:
        f.write(event_line)


def emit_artifact_written_event(
    run_layout: RunLayout,
    run_id: str,
    trace_id: str,
    span_id: str,
    artifact_name: str,
    schema_id: Optional[str] = None,
) -> None:
    """Emit ARTIFACT_WRITTEN event for an artifact.

    Args:
        run_layout: Run directory layout
        run_id: Run identifier
        trace_id: Trace ID for telemetry
        span_id: Span ID for telemetry
        artifact_name: Artifact filename (e.g., "product_facts.json")
        schema_id: Schema identifier (e.g., "product_facts.schema.json")

    Spec reference: specs/21_worker_contracts.md:38-40
    """
    artifact_path = run_layout.artifacts_dir / artifact_name

    if not artifact_path.exists():
        return

    content = artifact_path.read_bytes()
    sha256_hash = hashlib.sha256(content).hexdigest()

    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_ARTIFACT_WRITTEN,
        {
            "name": artifact_name,
            "path": str(artifact_path.relative_to(run_layout.run_dir)),
            "sha256": sha256_hash,
            "schema_id": schema_id,
        },
    )


def assemble_product_facts(
    run_layout: RunLayout,
    evidence_map: Dict[str, Any],
) -> Dict[str, Any]:
    """Assemble final product_facts.json from evidence_map and repo_inventory.

    Per specs/21_worker_contracts.md:98-125, product_facts.json must include:
    - Claims with stable IDs
    - Claim groups (key_features, install_steps, workflows, etc.)
    - Supported formats extracted from format claims
    - API surface summary
    - Example inventory

    Args:
        run_layout: Run directory layout
        evidence_map: Evidence map from TC-412/413

    Returns:
        Product facts dictionary

    Raises:
        FactsBuilderAssemblyError: If assembly fails

    Spec: specs/schemas/product_facts.schema.json
    """
    # Load repo_inventory for metadata
    repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
    if not repo_inventory_path.exists():
        raise FactsBuilderAssemblyError(
            f"repo_inventory.json not found: {repo_inventory_path}"
        )

    with open(repo_inventory_path, 'r', encoding='utf-8') as f:
        repo_inventory = json.load(f)

    # Extract metadata
    product_name = repo_inventory.get('product_name', '')
    repo_url = evidence_map.get('repo_url', '')
    repo_sha = evidence_map.get('repo_sha', '')

    # Generate product_slug from product_name
    product_slug = product_name.lower().replace(' ', '-').replace('_', '-')

    claims = evidence_map.get('claims', [])

    # Build claim groups (group claims by kind)
    key_features = []
    install_steps = []
    quickstart_steps = []
    workflow_claims = []
    limitations = []
    compatibility_notes = []

    for claim in claims:
        claim_id = claim['claim_id']
        claim_kind = claim.get('claim_kind', 'feature')
        claim_text = claim.get('claim_text', '')

        if claim_kind == 'limitation':
            limitations.append(claim_id)
        elif claim_kind == 'workflow':
            # Distinguish install vs quickstart vs general workflow
            if any(marker in claim_text.lower() for marker in ['install', 'setup', 'pip install', 'npm install']):
                install_steps.append(claim_id)
            elif any(marker in claim_text.lower() for marker in ['getting started', 'quickstart', 'first', 'begin']):
                quickstart_steps.append(claim_id)
            else:
                workflow_claims.append(claim_id)
        elif claim_kind == 'feature':
            key_features.append(claim_id)
        elif claim_kind == 'api':
            # API claims go into key_features for now
            key_features.append(claim_id)

    # Extract supported formats from format claims
    supported_formats = []
    for claim in claims:
        if claim.get('claim_kind') == 'format':
            claim_text = claim.get('claim_text', '').lower()

            # Extract format name (simple heuristic)
            import re
            format_match = re.search(r'\b(obj|fbx|stl|dae|gltf|glb|ply|3ds|off|one|pdf|dwg|dxf)\b', claim_text)
            if format_match:
                format_name = format_match.group(1).upper()

                # Determine status and direction
                is_negative = any(neg in claim_text for neg in ['does not', 'cannot', 'not supported', 'unsupported'])
                status = 'unknown' if is_negative else 'implemented'

                # Determine direction
                if 'import' in claim_text or 'read' in claim_text:
                    direction = 'import'
                elif 'export' in claim_text or 'write' in claim_text:
                    direction = 'export'
                elif 'both' in claim_text:
                    direction = 'both'
                else:
                    direction = 'unknown'

                supported_formats.append({
                    'format': format_name,
                    'status': status,
                    'claim_id': claim['claim_id'],
                    'direction': direction,
                })

    # Build workflows (group workflow claims)
    workflows = []
    if install_steps:
        workflows.append({
            'workflow_tag': 'installation',
            'title': 'Installation',
            'claim_ids': install_steps,
            'snippet_tags': ['install'],
        })
    if quickstart_steps:
        workflows.append({
            'workflow_tag': 'quickstart',
            'title': 'Quickstart',
            'claim_ids': quickstart_steps,
            'snippet_tags': ['quickstart', 'getting-started'],
        })

    # Build API surface summary (placeholder - would need deeper analysis)
    api_surface_summary = {}
    api_claims = [c for c in claims if c.get('claim_kind') == 'api']
    if api_claims:
        api_surface_summary['classes'] = [c['claim_id'] for c in api_claims if 'class' in c.get('claim_text', '').lower()]
        api_surface_summary['functions'] = [c['claim_id'] for c in api_claims if 'function' in c.get('claim_text', '').lower()]

    # Build example inventory (from discovered_examples if available)
    example_inventory = []
    discovered_examples_path = run_layout.artifacts_dir / "discovered_examples.json"
    if discovered_examples_path.exists():
        with open(discovered_examples_path, 'r', encoding='utf-8') as f:
            discovered_examples = json.load(f)
            example_files = discovered_examples.get('example_file_details', [])
            for i, example_file in enumerate(example_files[:10]):  # Limit to 10 examples
                example_inventory.append({
                    'example_id': f"example_{i+1}",
                    'title': example_file.get('path', '').split('/')[-1],
                    'tags': example_file.get('tags', []),
                    'primary_snippet_id': f"snippet_{i+1}",
                })

    # Assemble product_facts
    product_facts = {
        'schema_version': '1.0.0',
        'product_name': product_name,
        'product_slug': product_slug,
        'repo_url': repo_url,
        'repo_sha': repo_sha,
        'positioning': {
            'tagline': f"{product_name} - Product tagline",  # Placeholder
            'short_description': f"A product for working with {product_name}",  # Placeholder
        },
        'supported_platforms': repo_inventory.get('supported_platforms', []),
        'claims': claims,
        'claim_groups': {
            'key_features': key_features,
            'install_steps': install_steps,
            'quickstart_steps': quickstart_steps,
            'workflow_claims': workflow_claims,
            'limitations': limitations,
            'compatibility_notes': compatibility_notes,
        },
        'supported_formats': supported_formats,
        'workflows': workflows,
        'api_surface_summary': api_surface_summary,
        'example_inventory': example_inventory,
    }

    return product_facts


def execute_facts_builder(
    run_dir: Path,
    run_config: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    llm_client: Optional[LLMProviderClient] = None,
) -> Dict[str, Any]:
    """Execute W2 FactsBuilder worker (TC-410 integrator).

    This is the main entry point for W2 FactsBuilder. It orchestrates all
    sub-workers in sequence:
    1. TC-411: Extract claims from documentation
    2. TC-412: Map evidence to claims
    3. TC-413: Detect and resolve contradictions
    4. Assemble final product_facts.json

    Args:
        run_dir: Run directory path
        run_config: Run configuration dictionary (optional, will load from disk if None)
        run_id: Run identifier (optional, generated if None)
        trace_id: Trace ID for telemetry (optional, generated if None)
        span_id: Span ID for telemetry (optional, generated if None)
        llm_client: Optional LLM client for claims extraction and evidence mapping

    Returns:
        Dictionary with completion status and artifact paths:
        {
            "status": "success" | "failed",
            "artifacts": {
                "extracted_claims": str,
                "evidence_map": str,
                "product_facts": str
            },
            "metadata": {
                "total_claims": int,
                "fact_claims": int,
                "inference_claims": int,
                "contradictions_detected": int,
                "auto_resolved": int
            },
            "error": Optional[str]
        }

    Raises:
        FactsBuilderClaimsError: If claims extraction fails
        FactsBuilderEvidenceError: If evidence mapping fails
        FactsBuilderContradictionError: If contradiction detection fails
        FactsBuilderAssemblyError: If product facts assembly fails

    Spec references:
    - specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
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

    # Initialize LLM client if not provided
    if llm_client is None and hasattr(run_config_obj, 'llm_config'):
        # LLM client initialization would go here
        # For now, pass None (will use heuristic extraction)
        pass

    # Emit WORK_ITEM_STARTED
    emit_event(
        run_layout,
        run_id,
        trace_id,
        span_id,
        EVENT_WORK_ITEM_STARTED,
        {
            "worker": "W2_FactsBuilder",
            "task": "execute_facts_builder",
            "taskcard": "TC-410",
            "sub_workers": ["TC-411", "TC-412", "TC-413"],
        },
    )

    result = {
        "status": "success",
        "artifacts": {},
        "metadata": {},
        "error": None,
    }

    try:
        # Get repo_dir from run_layout
        repo_dir = run_layout.work_dir / "repo"
        if not repo_dir.exists():
            raise FactsBuilderError(f"Repository directory not found: {repo_dir}")

        # Step 1: TC-411 - Extract claims
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-411", "description": "Extract claims from documentation"},
        )

        try:
            extracted_claims = extract_claims(
                repo_dir=repo_dir,
                run_dir=run_dir,
                llm_client=llm_client,
            )
        except (ClaimsExtractionError, ClaimsValidationError) as e:
            raise FactsBuilderClaimsError(f"Claims extraction failed: {e}") from e

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout, run_id, trace_id, span_id, "extracted_claims.json", schema_id=None
        )

        result["artifacts"]["extracted_claims"] = str(
            run_layout.artifacts_dir / "extracted_claims.json"
        )
        result["metadata"]["total_claims"] = extracted_claims["metadata"]["total_claims"]
        result["metadata"]["fact_claims"] = extracted_claims["metadata"]["fact_claims"]
        result["metadata"]["inference_claims"] = extracted_claims["metadata"]["inference_claims"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "TC-411", "status": "success", "claims_extracted": len(extracted_claims["claims"])},
        )

        # Handle edge case: zero claims extracted
        if len(extracted_claims["claims"]) == 0:
            logger.warning(
                "facts_builder_zero_claims",
                repo_url=extracted_claims.get("repo_url"),
                message="No claims extracted. Proceeding with empty ProductFacts.",
            )
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_ZERO_CLAIMS",
                {"repo_url": extracted_claims.get("repo_url")},
            )

        # Handle edge case: sparse claims (< 5)
        if len(extracted_claims["claims"]) < 5 and len(extracted_claims["claims"]) > 0:
            logger.warning(
                "facts_builder_sparse_claims",
                total_claims=len(extracted_claims["claims"]),
                message="Fewer than 5 claims extracted. Launch tier forced to minimal.",
            )
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_SPARSE_CLAIMS",
                {"total_claims": len(extracted_claims["claims"])},
            )

        # Step 2: TC-412 - Map evidence
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-412", "description": "Map evidence to claims"},
        )

        try:
            evidence_map = map_evidence(
                repo_dir=repo_dir,
                run_dir=run_dir,
                llm_client=llm_client,
            )
        except EvidenceMappingError as e:
            raise FactsBuilderEvidenceError(f"Evidence mapping failed: {e}") from e

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "evidence_map.json",
            schema_id="evidence_map.schema.json",
        )

        result["artifacts"]["evidence_map"] = str(
            run_layout.artifacts_dir / "evidence_map.json"
        )
        result["metadata"]["claims_with_evidence"] = evidence_map["metadata"]["claims_with_evidence"]

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {
                "step": "TC-412",
                "status": "success",
                "claims_with_evidence": evidence_map["metadata"]["claims_with_evidence"],
            },
        )

        # Step 3: TC-413 - Detect contradictions
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-413", "description": "Detect and resolve contradictions"},
        )

        try:
            evidence_map = detect_contradictions(
                run_dir=run_dir,
                llm_client=llm_client,
            )
        except ContradictionDetectionError as e:
            raise FactsBuilderContradictionError(f"Contradiction detection failed: {e}") from e

        # Re-emit evidence_map artifact written event (it was updated)
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "evidence_map.json",
            schema_id="evidence_map.schema.json",
        )

        contradictions = evidence_map.get("contradictions", [])
        result["metadata"]["contradictions_detected"] = len(contradictions)
        result["metadata"]["auto_resolved"] = evidence_map["metadata"].get("auto_resolved_contradictions", 0)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {
                "step": "TC-413",
                "status": "success",
                "contradictions_detected": len(contradictions),
                "auto_resolved": result["metadata"]["auto_resolved"],
            },
        )

        # Handle edge case: contradictory evidence detected
        if len(contradictions) > 0:
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_CONTRADICTION_DETECTED",
                {
                    "total_contradictions": len(contradictions),
                    "auto_resolved": result["metadata"]["auto_resolved"],
                },
            )

        # Step 4: Assemble product_facts.json
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "assemble", "description": "Assemble product_facts.json"},
        )

        try:
            product_facts = assemble_product_facts(run_layout, evidence_map)
        except FactsBuilderAssemblyError as e:
            raise FactsBuilderAssemblyError(f"Product facts assembly failed: {e}") from e

        # Write product_facts.json
        output_path = run_layout.artifacts_dir / "product_facts.json"
        atomic_write_json(output_path, product_facts)

        # Emit artifact written event
        emit_artifact_written_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "product_facts.json",
            schema_id="product_facts.schema.json",
        )

        result["artifacts"]["product_facts"] = str(output_path)

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "assemble", "status": "success"},
        )

        # Emit WORK_ITEM_FINISHED
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            EVENT_WORK_ITEM_FINISHED,
            {
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "status": "success",
                "artifacts_produced": list(result["artifacts"].keys()),
            },
        )

        # Emit telemetry events (per spec requirement)
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STARTED",
            {"repo_url": evidence_map.get("repo_url")},
        )

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_COMPLETED",
            {
                "total_claims": result["metadata"]["total_claims"],
                "fact_claims": result["metadata"]["fact_claims"],
                "inference_claims": result["metadata"]["inference_claims"],
            },
        )

        logger.info(
            "facts_builder_completed",
            total_claims=result["metadata"]["total_claims"],
            contradictions_detected=result["metadata"]["contradictions_detected"],
            artifacts_produced=list(result["artifacts"].keys()),
        )

        return result

    except FactsBuilderClaimsError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderEvidenceError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderContradictionError:
        # Re-raise our own exceptions as-is
        raise

    except FactsBuilderAssemblyError:
        # Re-raise our own exceptions as-is
        raise

    except FileNotFoundError as e:
        # Missing dependencies
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
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "error": error_msg,
                "error_type": "missing_artifact",
                "retryable": False,
            },
        )

        raise FactsBuilderError(error_msg) from e

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
                "worker": "W2_FactsBuilder",
                "task": "execute_facts_builder",
                "taskcard": "TC-410",
                "error": error_msg,
                "error_type": "unexpected",
                "retryable": False,
            },
        )

        raise FactsBuilderError(error_msg) from e
