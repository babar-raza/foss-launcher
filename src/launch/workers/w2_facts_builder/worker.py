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
from ...io.artifact_store import ArtifactStore
from ...io.hashing import sha256_bytes
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
)
from ...models.run_config import RunConfig
from ...io.run_config import load_and_validate_run_config
from ...io.atomic import atomic_write_json
from ...clients.llm_provider import LLMProviderClient, LLMError, create_llm_client_from_config
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
from .enrich_claims import enrich_claims_batch

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
        artifact_name: Artifact filename (e.g., "product_facts.json")
        schema_id: Schema identifier (e.g., "product_facts.schema.json")

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


def _infer_audience(claims: List[Dict], product_family: str, product_name: str) -> str:
    """Infer target audience from claims and metadata.

    TC-1612: Populate positioning.audience from claims analysis.

    Args:
        claims: List of claim dicts
        product_family: Product family name
        product_name: Product name

    Returns:
        Inferred audience string
    """
    # Check for enterprise/production mentions
    claim_texts = ' '.join(c.get('claim_text', '') for c in claims[:50]).lower()

    if 'enterprise' in claim_texts or 'production' in claim_texts or 'scalable' in claim_texts:
        return "Enterprise developers and software architects"

    # Check manifest compatibility claims for platform
    for c in claims:
        if c.get('claim_kind') == 'compatibility' and 'python' in c.get('claim_text', '').lower():
            return "Python developers"
        if c.get('source_type') == 'manifest' and 'node' in c.get('claim_text', '').lower():
            return "Node.js developers"

    # Fallback based on product family
    if product_family:
        return f"Software developers working with {product_family}"

    return "Software developers and AI agents"


def _infer_who_it_is_for(claims: List[Dict], product_name: str, supported_formats: List[Dict]) -> str:
    """Infer who_it_is_for from product capabilities.

    TC-1612: Populate positioning.who_it_is_for from product facts.
    USER REQUIREMENT: Must mention "both humans and AI agents".

    Args:
        claims: List of claim dicts
        product_name: Product name
        supported_formats: List of format dicts

    Returns:
        Who_it_is_for string including "both humans and AI agents"
    """
    # Extract format names
    formats = [f.get('format', '') for f in supported_formats[:5]]
    format_str = ', '.join(formats) if formats else "various file formats"

    # Get platform from claims
    platform = "Python"  # default
    for c in claims:
        if 'javascript' in c.get('claim_text', '').lower():
            platform = "JavaScript"
            break
        if 'java' in c.get('claim_text', '').lower() and 'javascript' not in c.get('claim_text', '').lower():
            platform = "Java"
            break

    # USER REQUIREMENT: Must mention "both humans and AI agents"
    return f"Both humans and AI agents who need to work with {format_str} in {platform}"


def _synthesize_manifest_claims(
    manifest_data: Dict[str, Any],
    product_name: str,
) -> List[Dict[str, Any]]:
    """Synthesize claims from parsed setup.py manifest data.

    Generates structured claims for install command, Python version requirement,
    dependency information, and version from manifest fields.

    Args:
        manifest_data: Parsed manifest dict (from parse_setup_py)
        product_name: Product name for claim text

    Returns:
        List of claim dicts with claim_id, claim_text, claim_kind, etc.
    """
    from .extract_claims import compute_claim_id

    claims: List[Dict[str, Any]] = []
    manifest_citation = [{
        "path": "setup.py",
        "start_line": 1,
        "end_line": 1,
        "source_type": "manifest",
    }]

    pkg_name = manifest_data.get("name", "")

    # 1. Install claim
    if pkg_name:
        claim_text = f"Install {product_name} with pip: pip install {pkg_name}"
        claim_kind = "workflow"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    # 2. Python version requirement
    python_requires = manifest_data.get("python_requires", "")
    if python_requires:
        claim_text = f"{product_name} requires Python {python_requires}"
        claim_kind = "compatibility"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    # 3. Dependency information
    install_requires = manifest_data.get("install_requires", [])
    if not install_requires:
        claim_text = (
            f"{product_name} has zero runtime dependencies, "
            "making it lightweight and easy to install"
        )
        claim_kind = "feature"
    else:
        deps = ", ".join(sorted(install_requires))
        claim_text = f"{product_name} depends on {deps}"
        claim_kind = "feature"

    claims.append({
        "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
        "claim_text": claim_text,
        "claim_kind": claim_kind,
        "truth_status": "fact",
        "confidence": "high",
        "source_type": "manifest",
        "source_priority": 1,
        "source_relevance": 100,
        "citations": [dict(c) for c in manifest_citation],
    })

    # 4. Version claim
    version = manifest_data.get("version", "")
    if version:
        claim_text = f"{product_name} version {version} is the current release"
        claim_kind = "feature"
        claims.append({
            "claim_id": compute_claim_id(claim_text, claim_kind, product_name),
            "claim_text": claim_text,
            "claim_kind": claim_kind,
            "truth_status": "fact",
            "confidence": "high",
            "source_type": "manifest",
            "source_priority": 1,
            "source_relevance": 100,
            "citations": [dict(c) for c in manifest_citation],
        })

    return claims


def assemble_product_facts(
    run_layout: RunLayout,
    evidence_map: Dict[str, Any],
    run_config: Optional[Dict[str, Any]] = None,
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
        run_config: Run configuration dict (optional, for product_name/family)

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

    # Load code analysis from artifact (TC-1042, generated in execute_facts_builder())
    code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
    code_analysis = {}
    if code_analysis_path.exists():
        with open(code_analysis_path, 'r', encoding='utf-8') as f:
            code_analysis = json.load(f)

    # Extract metadata — prefer run_config over repo_inventory for product_name
    product_name = ''
    if run_config:
        product_name = run_config.get('product_name', '')
    if not product_name:
        product_name = repo_inventory.get('product_name', '')
    if not product_name:
        # Fallback: derive from repo URL
        repo_url_fallback = evidence_map.get('repo_url', '')
        if repo_url_fallback:
            product_name = repo_url_fallback.split('/')[-1].replace('.git', '').replace('-', ' ').title()

    # Extract product_family from run_config
    product_family = ''
    if run_config:
        product_family = run_config.get('family', '')
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

    # Normalize claim_kind variants from different extraction paths
    kind_map = {'key_feature': 'feature', 'api_reference': 'api'}

    # TC-1604: Helper to infer source quality from claim or its citations
    _META_CITATION_MARKERS = ('agents.md', '.claude/', 'claude.md', 'contributing.md')
    _IMPL_CITATION_MARKERS = ('implementation', '_implementation', 'architecture', 'design')

    def _is_low_quality_source(claim):
        """Check if claim comes from meta/implementation docs or low-quality code sources.

        TC-1616: source_code is low quality for key_features/features (marketing content),
        but OK for api_reference (technical reference documentation).
        """
        st = claim.get('source_type', '')
        claim_kind = claim.get('claim_kind', '')

        # TC-1616: Source code is low quality for key_features, OK for api_reference
        if st == 'source_code':
            if claim_kind in ('key_feature', 'feature'):
                return True  # Deprioritize for marketing content
            # Allow for api_reference (intentional - technical docs should reference code)

        # Existing meta/implementation doc checks
        if st in ('implementation_doc', 'meta'):
            return True

        # Fallback: check citation paths when source_type is missing
        if not st:
            for cit in claim.get('citations', []):
                path = cit.get('path', '').lower().replace('\\', '/')
                if any(m in path for m in _META_CITATION_MARKERS):
                    return True
                if any(m in path for m in _IMPL_CITATION_MARKERS):
                    return True

        return False

    for claim in claims:
        claim_id = claim['claim_id']
        raw_kind = claim.get('claim_kind', 'feature')
        claim_kind = kind_map.get(raw_kind, raw_kind)
        claim_text = claim.get('claim_text', '')

        if claim_kind == 'limitation':
            limitations.append(claim_id)
        elif claim_kind == 'compatibility':
            compatibility_notes.append(claim_id)
        elif claim_kind == 'workflow':
            # Distinguish install vs quickstart vs general workflow
            if any(marker in claim_text.lower() for marker in ['install', 'setup', 'pip install', 'npm install']):
                install_steps.append(claim_id)
            elif any(marker in claim_text.lower() for marker in ['getting started', 'quickstart', 'quick start', 'first', 'begin']):
                quickstart_steps.append(claim_id)
            else:
                workflow_claims.append(claim_id)
        elif claim_kind in ('feature', 'api'):
            # TC-1604: Gate key_features by source quality
            if _is_low_quality_source(claim):
                pass  # Don't route to key_features — still in claims[]
            else:
                key_features.append(claim_id)
        elif claim_kind == 'format':
            pass  # Format claims go to supported_formats list, not claim groups
        else:
            # TC-1604: Also gate catch-all by source quality
            if not _is_low_quality_source(claim):
                key_features.append(claim_id)

    # Cap limitations to avoid over-representation (most useful 15)
    if len(limitations) > 15:
        # Prefer fact over inference, then by claim text length (more informative)
        def _limitation_quality(cid):
            c = claim_lookup_all.get(cid, {})
            is_fact = 1 if c.get('truth_status') == 'fact' else 0
            return (-is_fact, -len(c.get('claim_text', '')))
        claim_lookup_all = {c['claim_id']: c for c in claims}
        limitations.sort(key=_limitation_quality)
        limitations = limitations[:15]

    # TC-1604: Quality-rank key_features (README > manifest > others; longer > shorter)
    claim_lookup = {c['claim_id']: c for c in claims}

    def _claim_quality(cid):
        c = claim_lookup.get(cid, {})
        source_type = c.get('source_type', '')
        # Fallback: infer source type from citation paths
        if not source_type:
            for cit in c.get('citations', []):
                path = cit.get('path', '').lower()
                if 'readme' in path:
                    source_type = 'readme_technical'
                    break
                elif 'setup.py' in path or 'pyproject' in path:
                    source_type = 'manifest'
                    break
        relevance = c.get('source_relevance', 50)
        length_score = min(len(c.get('claim_text', '')), 200)
        type_bonus = 100 if source_type.startswith('readme') else (
            80 if source_type == 'manifest' else 0
        )
        return -(type_bonus + relevance + length_score)  # negative for ascending sort

    key_features.sort(key=_claim_quality)

    # Extract supported formats from format claims (TC-1515: deduplicated)
    import re

    def _merge_directions(existing: str, new: str) -> str:
        if existing == new:
            return existing
        if existing == 'unknown':
            return new
        if new == 'unknown':
            return existing
        if {existing, new} == {'import', 'export'}:
            return 'both'
        return 'both' if 'both' in (existing, new) else existing

    format_data: dict = {}  # format_name → {format, status, direction, claim_ids}
    for claim in claims:
        if claim.get('claim_kind') == 'format':
            claim_text = claim.get('claim_text', '').lower()

            format_match = re.search(
                r'\b(obj|fbx|stl|dae|gltf|glb|ply|3ds|3mf|amf|u3d|rvm|off|one|pdf|dwg|dxf)\b',
                claim_text,
            )
            if format_match:
                format_name = format_match.group(1).upper()

                is_negative = any(neg in claim_text for neg in ['does not', 'cannot', 'not supported', 'unsupported'])
                status = 'unknown' if is_negative else 'implemented'

                import_kws = ('import', 'read', 'load', 'parse', 'open', 'reads', 'loads', 'parses')
                export_kws = ('export', 'write', 'save', 'generate', 'writes', 'saves', 'generates')
                has_import = any(w in claim_text for w in import_kws)
                has_export = any(w in claim_text for w in export_kws)

                if has_import and has_export:
                    direction = 'both'
                elif 'both' in claim_text:
                    direction = 'both'
                elif has_import:
                    direction = 'import'
                elif has_export:
                    direction = 'export'
                else:
                    direction = 'unknown'

                if format_name not in format_data:
                    format_data[format_name] = {
                        'format': format_name,
                        'status': status,
                        'direction': direction,
                        'claim_ids': [claim['claim_id']],
                    }
                else:
                    existing = format_data[format_name]
                    existing['claim_ids'].append(claim['claim_id'])
                    existing['direction'] = _merge_directions(existing['direction'], direction)
                    if status == 'implemented':
                        existing['status'] = 'implemented'

    supported_formats = list(format_data.values())
    # Backward compat: keep claim_id pointing to first claim
    for entry in supported_formats:
        entry['claim_id'] = entry['claim_ids'][0]

    # TC-1516: Load code_understanding early — needed for workflows + feature_profiles + examples
    code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
    code_understanding = None
    if code_understanding_path.exists():
        try:
            with open(code_understanding_path, 'r', encoding='utf-8') as f:
                code_understanding = json.load(f)
        except Exception:
            pass

    # Build enriched workflows (TC-1043)
    from .enrich_workflows import enrich_workflow

    snippet_catalog_path = run_layout.artifacts_dir / "snippet_catalog.json"
    snippet_catalog = {'snippets': []}
    if snippet_catalog_path.exists():
        with open(snippet_catalog_path, 'r', encoding='utf-8') as f:
            snippet_catalog = json.load(f)

    # Build step-aware workflows from decomposed claims (TC-1611)
    claim_lookup = {c['claim_id']: c for c in claims}

    def _build_workflow_from_step_claims(tag, title, claim_ids):
        """Build workflow with steps from claims that have step_order.

        TC-1611: Synthesize workflow objects from decomposed README claims.
        Each claim with step_order becomes a workflow step.

        Args:
            tag: Workflow tag (e.g., 'installation', 'quickstart')
            title: Human-readable workflow title
            claim_ids: List of claim IDs belonging to this workflow

        Returns:
            Workflow dictionary with ordered steps
        """
        step_claims = []
        for cid in claim_ids:
            c = claim_lookup.get(cid, {})
            step_claims.append((c.get('step_order', 999), c))
        step_claims.sort(key=lambda x: x[0])

        steps = []
        for i, (_, c) in enumerate(step_claims, 1):
            steps.append({
                'step_num': i,
                'step_id': f"step_{i}",
                'name': c.get('claim_text', f'Step {i}'),
                'claim_id': c.get('claim_id'),
                'snippet_id': None,
            })

        return {
            'workflow_id': f"wf_{tag}",
            'workflow_tag': tag,
            'title': title,
            'name': title,
            'description': f'{title} workflow for {product_name}',
            'complexity': 'simple' if len(steps) <= 3 else 'moderate',
            'estimated_time_minutes': 5 + (len(steps) - 1) * 2,
            'steps': steps,
            'claim_ids': claim_ids,
            'snippet_tags': [tag],
        }

    workflows = []
    # Build installation workflow from decomposed claims
    if install_steps:
        workflows.append(_build_workflow_from_step_claims(
            'installation',
            'Installation',
            install_steps
        ))

    # Build quickstart workflow from decomposed claims
    if quickstart_steps:
        workflows.append(_build_workflow_from_step_claims(
            'quickstart',
            'Quick Start',
            quickstart_steps
        ))

    # TC-1617: Merge and enrich workflows
    def _merge_workflows(claim_workflows, cu_workflows):
        """Merge code_understanding workflows with claim-based workflows.

        TC-1617: Strategy - prefer README workflows (higher quality), add
        code_understanding workflows only for NEW workflow types.

        Args:
            claim_workflows: Workflows from README claims
            cu_workflows: Workflows from code_understanding

        Returns:
            Merged workflow list with deduplication
        """
        merged = []
        seen_tags = set()

        # Add README workflows first (higher priority)
        for wf in claim_workflows:
            tag = wf.get('workflow_tag', '')
            merged.append(wf)
            seen_tags.add(tag)

        # Add code_understanding workflows for NEW types only
        for wf in cu_workflows:
            tag = wf.get('workflow_tag', '')
            if tag not in seen_tags:
                # Expand step descriptions with "how to" context
                for step in wf.get('steps', []):
                    if 'name' in step:
                        name = step['name']
                        # Add "How to" prefix if not already present
                        if not name.lower().startswith('how to'):
                            step['name'] = f"How to {name.lower()}"
                merged.append(wf)
                seen_tags.add(tag)

        return merged

    def _synthesize_common_task_workflows(product_facts_partial, claims_list):
        """Synthesize workflows for common tasks inferred from product capabilities.

        TC-1617: Creates format conversion and batch processing workflows based
        on product features.

        Args:
            product_facts_partial: Partial product facts (with supported_formats)
            claims_list: All claims for inference

        Returns:
            List of synthesized workflow dicts
        """
        synthesized = []
        pname = product_facts_partial.get('product_name', 'Product')

        # Synthesize format conversion workflow if 2+ formats
        formats = product_facts_partial.get('supported_formats', [])
        if len(formats) >= 2:
            source_fmt = formats[0]
            target_fmt = formats[1]
            synthesized.append({
                'workflow_id': f"wf_format_conversion",
                'workflow_tag': 'format_conversion',
                'title': f"Convert between {source_fmt} and {target_fmt} formats",
                'name': 'Format Conversion',
                'description': f'Convert files from {source_fmt} to {target_fmt} using {pname}',
                'complexity': 'simple',
                'estimated_time_minutes': 5,
                'steps': [
                    {'step_num': 1, 'step_id': 'step_1', 'name': f'Load {source_fmt} file', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 2, 'step_id': 'step_2', 'name': 'Process content', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 3, 'step_id': 'step_3', 'name': f'Save as {target_fmt} format', 'claim_id': None, 'snippet_id': None},
                ],
                'claim_ids': [],
                'source': 'synthesized',
            })

        # Synthesize batch processing workflow if batch indicators present
        batch_indicators = ['batch', 'multiple', 'list', 'collection']
        api_claims = [c for c in claims_list if c.get('claim_kind') == 'api_reference']
        has_batch = any(
            ind in c.get('claim_text', '').lower()
            for c in api_claims
            for ind in batch_indicators
        )

        if has_batch:
            synthesized.append({
                'workflow_id': f"wf_batch_processing",
                'workflow_tag': 'batch_processing',
                'title': 'Process multiple files in batch',
                'name': 'Batch Processing',
                'description': f'Process multiple files efficiently using {pname}',
                'complexity': 'moderate',
                'estimated_time_minutes': 10,
                'steps': [
                    {'step_num': 1, 'step_id': 'step_1', 'name': 'Prepare list of input files', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 2, 'step_id': 'step_2', 'name': 'Iterate over files', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 3, 'step_id': 'step_3', 'name': 'Process each file', 'claim_id': None, 'snippet_id': None},
                    {'step_num': 4, 'step_id': 'step_4', 'name': 'Save results', 'claim_id': None, 'snippet_id': None},
                ],
                'claim_ids': [],
                'source': 'synthesized',
            })

        return synthesized

    # TC-1516/TC-1617: Bridge code_understanding usage_workflows into product_facts
    cu_workflows = []
    if code_understanding:
        for cu_wf in code_understanding.get('usage_workflows', []):
            wf_name = cu_wf.get('name', '')
            wf_tag = wf_name.lower().replace(' ', '_')[:30]

            cu_steps = cu_wf.get('steps', [])
            if len(cu_steps) < 2:
                continue  # Skip trivial 1-step workflows

            steps = []
            for i, step in enumerate(cu_steps, start=1):
                steps.append({
                    'step_num': i,
                    'step_id': f"step_{i}",
                    'name': step.get('description', f'Step {i}'),
                    'claim_id': None,
                    'snippet_id': None,
                    'code': step.get('code', ''),
                })

            n = len(steps)
            cu_workflows.append({
                'workflow_id': f"wf_cu_{wf_tag}",
                'workflow_tag': wf_tag,
                'name': wf_name,
                'title': wf_name,
                'description': cu_wf.get('description', ''),
                'complexity': 'simple' if n <= 2 else ('moderate' if n <= 5 else 'complex'),
                'estimated_time_minutes': 5 + (n - 1) * 3,
                'steps': steps,
                'claim_ids': [],
                'source': 'code_understanding',
            })

    # TC-1617: Merge README workflows with code_understanding workflows
    workflows = _merge_workflows(workflows, cu_workflows)

    # TC-1617: Synthesize common task workflows
    # Note: Need partial product_facts for formats, so build minimal dict
    partial_facts = {
        'product_name': product_name,
        'supported_formats': supported_formats,
    }
    synthesized = _synthesize_common_task_workflows(partial_facts, claims)
    workflows.extend(synthesized)

    # Build API surface summary from code analysis (TC-1042)
    api_surface_summary = code_analysis.get("api_surface", {})
    if not api_surface_summary.get("classes") and not api_surface_summary.get("functions"):
        # Fallback: extract from claim text if code analysis found nothing
        api_claims = [c for c in claims if c.get('claim_kind') == 'api']
        if api_claims:
            api_surface_summary['classes'] = [c['claim_id'] for c in api_claims if 'class' in c.get('claim_text', '').lower()]
            api_surface_summary['functions'] = [c['claim_id'] for c in api_claims if 'function' in c.get('claim_text', '').lower()]

    # Build enriched example inventory (TC-1044)
    from .enrich_examples import enrich_example

    example_inventory = []
    discovered_examples_path = run_layout.artifacts_dir / "discovered_examples.json"
    if discovered_examples_path.exists():
        with open(discovered_examples_path, 'r', encoding='utf-8') as f:
            discovered_examples = json.load(f)
            example_files = discovered_examples.get('example_file_details', [])
            example_repo_dir = run_layout.work_dir / "repo"
            if not example_repo_dir.exists():
                example_repo_dir = run_layout.work_dir
            for i, example_file in enumerate(example_files):
                example_file['example_id'] = f"example_{i+1}"
                example_file['primary_snippet_id'] = f"snippet_{i+1}"
                try:
                    enriched = enrich_example(example_file, example_repo_dir, claims)
                    example_inventory.append(enriched)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"Failed to enrich example: {e}")
                    example_inventory.append({
                        'example_id': f"example_{i+1}",
                        'title': example_file.get('path', '').split('/')[-1],
                        'tags': example_file.get('tags', []),
                        'primary_snippet_id': f"snippet_{i+1}",
                    })

    # Extract supported_platforms from compatibility claims (TC-1509)
    supported_platforms = repo_inventory.get('supported_platforms', [])
    if not supported_platforms:
        import re as _re
        for claim in claims:
            raw_kind = claim.get('claim_kind', 'feature')
            ck = kind_map.get(raw_kind, raw_kind)
            if ck == 'compatibility':
                ctext = claim.get('claim_text', '').lower()
                for m in _re.finditer(r'python\s*(\d+\.\d+)\+?', ctext):
                    plat = f"Python {m.group(1)}+"
                    if plat not in supported_platforms:
                        supported_platforms.append(plat)
                for os_name in ['windows', 'linux', 'macos']:
                    if os_name in ctext:
                        pretty = os_name.title()
                        if pretty not in supported_platforms:
                            supported_platforms.append(pretty)

    # Assemble product_facts
    product_facts = {
        'schema_version': '1.0.0',
        'product_name': product_name,
        'product_family': product_family,
        'product_slug': product_slug,
        'repo_url': repo_url,
        'repo_sha': repo_sha,
        # Positioning from code analysis (TC-1042)
        'positioning': {
            'tagline': code_analysis.get("positioning", {}).get("tagline") or f"{product_name} - Product tagline",
            'short_description': code_analysis.get("positioning", {}).get("short_description") or f"A product for working with {product_name}",
            # TC-1612: Pass through audience and who_it_is_for from code_analysis if present
            **({k: v for k, v in code_analysis.get("positioning", {}).items() if k in ['audience', 'who_it_is_for'] and v})
        },
        'supported_platforms': supported_platforms,
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

    # TC-1612: Enrich positioning with audience and who_it_is_for
    if not product_facts['positioning'].get('audience'):
        product_facts['positioning']['audience'] = _infer_audience(
            claims, product_family, product_name
        )
    if not product_facts['positioning'].get('who_it_is_for'):
        product_facts['positioning']['who_it_is_for'] = _infer_who_it_is_for(
            claims, product_name, supported_formats
        )

    # Code structure from code analysis (TC-1042)
    code_structure = code_analysis.get("code_structure")
    if code_structure:
        product_facts["code_structure"] = code_structure

    # Version from code analysis (TC-1042)
    version = code_analysis.get("constants", {}).get("version")
    if version:
        product_facts["version"] = version

    # TC-1601: Populate distribution and version from manifest claims
    manifest_claims_list = [c for c in claims if c.get('source_type') == 'manifest']
    for mc in manifest_claims_list:
        claim_text = mc.get('claim_text', '')
        # Extract pip install command → distribution field
        # TC-1607: Use schema-compliant array format (product_facts.schema.json lines 345-389)
        if 'pip install' in claim_text.lower():
            pip_match = re.search(r'pip install (\S+)', claim_text)
            if pip_match:
                pip_pkg = pip_match.group(1)
                product_facts["distribution"] = [{
                    "method": "pip",
                    "identifier": pip_pkg,
                    "install_commands": [f"pip install {pip_pkg}"],
                }]
        # Extract version from "version X is the current release"
        if 'version' in claim_text.lower() and 'current release' in claim_text.lower():
            ver_match = re.search(r'version (\S+)', claim_text)
            if ver_match and "version" not in product_facts:
                product_facts["version"] = ver_match.group(1)

    # TC-1607: Populate runtime_requirements from manifest claims
    runtime_reqs = {}
    for mc in manifest_claims_list:
        ct = mc.get('claim_text', '')
        if 'requires Python' in ct or 'requires python' in ct.lower():
            import re as _rt_re
            ver_match = _rt_re.search(r'Python\s+([\d.><=!~]+)', ct)
            if ver_match:
                runtime_reqs.setdefault('language_versions', []).append(
                    f"Python {ver_match.group(1)}"
                )
    # Extract OS from compatibility claims
    for cc in claims:
        if cc.get('claim_kind') == 'compatibility':
            ctext = cc.get('claim_text', '').lower()
            for os_name in ['windows', 'linux', 'macos']:
                if os_name in ctext:
                    runtime_reqs.setdefault('os', [])
                    pretty = os_name.title()
                    if pretty not in runtime_reqs['os']:
                        runtime_reqs['os'].append(pretty)
    if runtime_reqs:
        product_facts["runtime_requirements"] = runtime_reqs

    # TC-1607: Populate dependencies from manifest claims
    deps_runtime = []
    for mc in manifest_claims_list:
        ct = mc.get('claim_text', '')
        if 'depends on' in ct.lower():
            # Extract dependency names after "depends on"
            dep_match = re.search(r'depends on (.+)', ct, re.IGNORECASE)
            if dep_match:
                deps_runtime = [d.strip() for d in dep_match.group(1).split(',')]
        elif 'zero runtime dependencies' in ct.lower() or 'zero dependencies' in ct.lower():
            deps_runtime = []  # Explicitly empty
    if deps_runtime or any(
        'zero' in mc.get('claim_text', '').lower() and 'dependenc' in mc.get('claim_text', '').lower()
        for mc in manifest_claims_list
    ):
        product_facts["dependencies"] = {"runtime": deps_runtime}

    # TC-1609: Populate license from repo inventory
    license_info = repo_inventory.get('license', {})
    if not license_info:
        # Fallback: scan repo_inventory files for LICENSE patterns
        for item in repo_inventory.get('files', []):
            path = item.get('path', '') if isinstance(item, dict) else str(item)
            if any(name in path.upper() for name in ['LICENSE', 'LICENCE', 'COPYING']):
                license_info = {'file_path': path}
                break
    if license_info:
        product_facts["license"] = {
            "spdx_id": license_info.get("spdx_id", ""),
            "name": license_info.get("name", license_info.get("type", "")),
            "file_path": license_info.get("file_path", license_info.get("path", "")),
        }
        if license_info.get("url"):
            product_facts["license"]["url"] = license_info["url"]

    # Feature profiles (TC-1411): structured feature groupings from claims
    try:
        from .feature_profiles import build_feature_profiles, synthesize_use_cases_from_profiles
        feature_profiles = build_feature_profiles(
            claims=claims,
            product_name=product_name,
            code_understanding=code_understanding,
        )
        product_facts["feature_profiles"] = feature_profiles

        # TC-1618: Synthesize use cases from feature profiles for marketing content
        if feature_profiles:
            from .extract_claims import compute_claim_id, classify_claim_kind
            synthesized_use_cases = synthesize_use_cases_from_profiles(
                feature_profiles, product_name
            )
            if synthesized_use_cases:
                # Generate claim_id for each synthesized use case
                for uc in synthesized_use_cases:
                    # Classify and assign claim_kind (should already be 'use_case')
                    claim_kind = classify_claim_kind(uc.get("claim_text", ""))
                    uc["claim_kind"] = "use_case"  # Override with explicit type
                    # Generate stable claim_id
                    uc["claim_id"] = compute_claim_id(
                        uc["claim_text"], uc["claim_kind"], product_name
                    )
                    # Add default truth_status
                    uc.setdefault("truth_status", "verified")
                    uc.setdefault("citations", [])

                # Add synthesized use cases to claims list
                claims.extend(synthesized_use_cases)
                logger.info(
                    "synthesized_use_cases_from_profiles",
                    product_name=product_name,
                    count=len(synthesized_use_cases),
                )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Feature profiles failed: {e}")
        product_facts["feature_profiles"] = []

    # TC-1512: Populate example_inventory from code_understanding when W1 found
    # no examples/ directory.  This harvests typical_usage from class profiles
    # and code from usage_workflows so downstream workers have code examples.
    if not example_inventory and code_understanding:
        for cls_profile in code_understanding.get('class_profiles', []):
            usage = cls_profile.get('typical_usage', '')
            if usage and len(usage) > 20 and not usage.startswith("# See source"):
                example_inventory.append({
                    'example_id': f"cu_{cls_profile['name'].lower()}",
                    'title': f"{cls_profile['name']} Usage",
                    'tags': ['api', cls_profile.get('module', '')],
                    'primary_snippet_id': '',
                    'description': cls_profile.get('purpose', ''),
                    'code': usage,
                })
        for workflow in code_understanding.get('usage_workflows', []):
            steps_code = '\n'.join(
                s.get('code', '') for s in workflow.get('steps', []) if s.get('code')
            )
            if steps_code:
                wf_name = workflow.get('name', 'workflow')
                example_inventory.append({
                    'example_id': f"wf_{wf_name.lower().replace(' ', '_')[:30]}",
                    'title': wf_name,
                    'tags': ['workflow'],
                    'primary_snippet_id': '',
                    'description': workflow.get('description', ''),
                    'code': steps_code,
                })
        # Update the product_facts since example_inventory was mutated
        product_facts['example_inventory'] = example_inventory

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
        run_config_dict = config_data
    else:
        run_config_obj = RunConfig.from_dict(run_config)
        run_config_dict = run_config

    # Extract telemetry context from run_config (passed by orchestrator)
    telemetry_client = run_config_dict.get("_telemetry_client") if isinstance(run_config_dict, dict) else None
    telemetry_run_id = run_config_dict.get("_telemetry_run_id") if isinstance(run_config_dict, dict) else None
    telemetry_trace_id = run_config_dict.get("_telemetry_trace_id") if isinstance(run_config_dict, dict) else trace_id
    telemetry_parent_span_id = run_config_dict.get("_telemetry_parent_span_id") if isinstance(run_config_dict, dict) else span_id

    # Initialize LLM client if not provided (uses shared factory with fallback support)
    if llm_client is None and hasattr(run_config_obj, 'llm') and run_config_obj.llm:
        try:
            llm_client = create_llm_client_from_config(
                run_config=run_config_dict,
                run_dir=run_dir,
                telemetry_client=telemetry_client,
                telemetry_run_id=telemetry_run_id or run_id,
                telemetry_trace_id=telemetry_trace_id,
                telemetry_parent_span_id=telemetry_parent_span_id,
            )
            if llm_client:
                logger.info(
                    "w2_llm_client_initialized",
                    model=llm_client.model,
                    api_base_url=llm_client.api_base_url,
                    api_key_present=llm_client.api_key is not None,
                    fallback_configured=llm_client.fallback_api_base_url is not None,
                    telemetry_enabled=telemetry_client is not None,
                )
        except Exception as e:
            logger.warning("w2_llm_client_init_failed", error=str(e))
            # Continue without LLM client (will use heuristic extraction)
            llm_client = None

    if llm_client is None:
        logger.warning(
            "w2_using_offline_path",
            message="No LLM client available. Code understanding and claim enrichment will use offline heuristics. "
                    "Documentation quality will be limited. Configure llm section in run_config to enable LLM.",
            llm_config_present=hasattr(run_config_obj, 'llm') and bool(run_config_obj.llm),
        )

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

        # Step 0.5: TC-1042 - Run code analysis (required for TC-1401)
        # Must run BEFORE extract_claims() so code_analysis.json exists for code-grounded claims
        from .code_analyzer import analyze_repository_code

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-1042", "description": "Analyze repository code (TC-1401 prerequisite)"},
        )

        repo_inventory_path = run_layout.artifacts_dir / "repo_inventory.json"
        if repo_inventory_path.exists():
            with open(repo_inventory_path, 'r', encoding='utf-8') as f:
                repo_inventory = json.load(f)
            product_name_for_analysis = repo_inventory.get('product_name', '') or (run_config or {}).get('product_name', '')
            code_analysis = analyze_repository_code(repo_dir, repo_inventory, product_name_for_analysis)

            # Write code_analysis.json artifact (TC-1042, required for TC-1401)
            code_analysis_path = run_layout.artifacts_dir / "code_analysis.json"
            atomic_write_json(code_analysis_path, code_analysis)

            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id, "code_analysis.json", schema_id=None
            )

        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_COMPLETED",
            {"step": "TC-1042", "status": "success"},
        )

        # Step 0.75: TC-1410 - Build LLM-powered code understanding
        emit_event(
            run_layout,
            run_id,
            trace_id,
            span_id,
            "FACTS_BUILDER_STEP_STARTED",
            {"step": "TC-1410", "description": "Build code understanding"},
        )

        try:
            from .code_understanding import build_code_understanding

            code_understanding = build_code_understanding(
                code_analysis=code_analysis,
                repo_dir=repo_dir,
                product_name=product_name_for_analysis,
                llm_client=llm_client,
            )

            # Write code_understanding.json artifact
            code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
            atomic_write_json(code_understanding_path, code_understanding)

            emit_artifact_written_event(
                run_layout, run_id, trace_id, span_id,
                "code_understanding.json", schema_id=None,
            )

            result["artifacts"]["code_understanding"] = str(code_understanding_path)

            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_COMPLETED",
                {
                    "step": "TC-1410",
                    "status": "success",
                    "source": code_understanding.get("metadata", {}).get("source", "unknown"),
                    "classes_profiled": len(code_understanding.get("class_profiles", [])),
                },
            )
        except Exception as e:
            # Code understanding failure MUST NOT crash W2
            error_type = type(e).__name__
            error_str = str(e)
            is_auth_error = "401" in error_str or "403" in error_str or "auth" in error_str.lower()
            logger.warning(
                "code_understanding_failed",
                error=error_str,
                error_type=error_type,
                is_auth_error=is_auth_error,
                llm_model=llm_client.model if llm_client else "none",
                api_key_present=llm_client.api_key is not None if llm_client else False,
                suggestion="Check API key configuration" if is_auth_error else "Check LLM endpoint availability",
            )
            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_COMPLETED",
                {"step": "TC-1410", "status": "skipped", "reason": error_str},
            )

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

        # Step 1.25: TC-1402 - Classify claims to filter non-user-facing content
        # Per Content Quality Hardening Plan: filter internal_detail + developer_instruction
        classify_enabled = True
        if isinstance(run_config, dict):
            classify_enabled = run_config.get("classify_claims", True)
        elif hasattr(run_config_obj, "classify_claims"):
            classify_enabled = getattr(run_config_obj, "classify_claims", True)

        if classify_enabled and len(extracted_claims.get("claims", [])) > 0:
            emit_event(
                run_layout, run_id, trace_id, span_id,
                "FACTS_BUILDER_STEP_STARTED",
                {"step": "TC-1402", "description": "Classify claims"},
            )

            try:
                from .classify_claims import classify_claims_batch

                n_claims = len(extracted_claims["claims"])
                classify_offline = llm_client is None or n_claims > 500

                classify_cache_dir = run_layout.run_dir / "cache" / "classified_claims"

                pre_count = len(extracted_claims["claims"])
                classified_claims = classify_claims_batch(
                    claims=extracted_claims["claims"],
                    product_name=extracted_claims.get("product_name", ""),
                    llm_client=llm_client if not classify_offline else None,
                    cache_dir=classify_cache_dir,
                    offline_mode=classify_offline,
                    repo_url=extracted_claims.get("repo_url", ""),
                    repo_sha=extracted_claims.get("repo_sha", ""),
                )

                post_count = len(classified_claims)
                extracted_claims["claims"] = classified_claims

                # Re-write extracted_claims.json with filtered claims
                extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
                atomic_write_json(extracted_claims_path, extracted_claims)

                result["metadata"]["claims_classified"] = pre_count
                result["metadata"]["claims_after_classification"] = post_count
                result["metadata"]["claims_filtered"] = pre_count - post_count

                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {
                        "step": "TC-1402",
                        "status": "success",
                        "claims_before": pre_count,
                        "claims_after": post_count,
                        "claims_filtered": pre_count - post_count,
                    },
                )
            except Exception as e:
                logger.warning("classify_claims_failed", error=str(e))
                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {"step": "TC-1402", "status": "skipped", "reason": str(e)},
                )

        # Step 1.5: TC-1045 - Enrich claims via LLM (between TC-411 and TC-412)
        # Per spec 08 section 9.1: enrichment runs AFTER extraction, BEFORE evidence mapping
        enrich_enabled = True
        if isinstance(run_config, dict):
            enrich_enabled = run_config.get("enrich_claims", True)
        elif hasattr(run_config_obj, "enrich_claims"):
            enrich_enabled = getattr(run_config_obj, "enrich_claims", True)

        if enrich_enabled and len(extracted_claims.get("claims", [])) > 0:
            emit_event(
                run_layout,
                run_id,
                trace_id,
                span_id,
                "FACTS_BUILDER_STEP_STARTED",
                {"step": "TC-1045", "description": "Enrich claims via LLM"},
            )

            try:
                # Determine offline mode: force offline for large claim sets
                # to avoid impractical LLM batch times (6000+ claims × 22s/batch)
                n_claims = len(extracted_claims.get("claims", []))
                offline_mode = llm_client is None or n_claims > 500
                if n_claims > 500 and llm_client is not None:
                    logger.info(
                        "enrichment_auto_offline",
                        reason=f"{n_claims} claims exceeds LLM batch threshold (500)",
                    )

                # Set up cache directory per spec 08 section 5.2
                enrichment_cache_dir = run_layout.run_dir / "cache" / "enriched_claims"

                enriched_claims = enrich_claims_batch(
                    claims=extracted_claims["claims"],
                    product_name=extracted_claims.get("product_name", ""),
                    llm_client=llm_client,
                    cache_dir=enrichment_cache_dir,
                    offline_mode=offline_mode,
                    repo_url=extracted_claims.get("repo_url", ""),
                    repo_sha=extracted_claims.get("repo_sha", ""),
                )

                # Update extracted_claims in-memory
                extracted_claims["claims"] = enriched_claims

                # Re-write extracted_claims.json with enrichment fields
                extracted_claims_path = run_layout.artifacts_dir / "extracted_claims.json"
                atomic_write_json(extracted_claims_path, extracted_claims)

                # Re-emit artifact written event for updated file
                emit_artifact_written_event(
                    run_layout, run_id, trace_id, span_id,
                    "extracted_claims.json", schema_id=None,
                )

                result["metadata"]["claims_enriched"] = len(enriched_claims)

                emit_event(
                    run_layout,
                    run_id,
                    trace_id,
                    span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {
                        "step": "TC-1045",
                        "status": "success",
                        "claims_enriched": len(enriched_claims),
                    },
                )

            except Exception as enrichment_error:
                # Per spec 08 section 9.4: enrichment failure MUST NOT crash W2
                logger.error(
                    "claim_enrichment_integration_failed",
                    error=str(enrichment_error),
                    message="Claim enrichment failed; continuing with unenriched claims",
                )
                emit_event(
                    run_layout,
                    run_id,
                    trace_id,
                    span_id,
                    "CLAIM_ENRICHMENT_FAILED",
                    {
                        "error_type": type(enrichment_error).__name__,
                        "error_message": str(enrichment_error),
                    },
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
                run_id=run_id,
                trace_id=trace_id,
                span_id=span_id,
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

        # Step 3.5: TC-1601 - Synthesize manifest claims from setup.py
        setup_py_path = repo_dir / "setup.py"
        if setup_py_path.exists():
            try:
                from .code_analyzer import parse_setup_py

                manifest_data = parse_setup_py(setup_py_path)
                if manifest_data:
                    product_name_for_manifest = (
                        manifest_data.get("name", "")
                        or (run_config_dict or {}).get("product_name", "")
                    )
                    manifest_claims = _synthesize_manifest_claims(
                        manifest_data, product_name_for_manifest
                    )
                    # Merge into evidence_map claims (avoid duplicates)
                    existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                    added = 0
                    for mc in manifest_claims:
                        if mc["claim_id"] not in existing_ids:
                            evidence_map["claims"].append(mc)
                            existing_ids.add(mc["claim_id"])
                            added += 1

                    if added > 0:
                        # Re-write evidence_map with new claims
                        evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                        atomic_write_json(evidence_map_path, evidence_map)

                        logger.info(
                            "manifest_claims_synthesized",
                            source="setup.py",
                            claims_added=added,
                            product_name=product_name_for_manifest,
                        )

                    emit_event(
                        run_layout, run_id, trace_id, span_id,
                        "FACTS_BUILDER_STEP_COMPLETED",
                        {
                            "step": "TC-1601",
                            "status": "success",
                            "manifest_source": "setup.py",
                            "claims_added": added,
                        },
                    )
            except Exception as e:
                logger.warning("manifest_claims_synthesis_failed", error=str(e))
                emit_event(
                    run_layout, run_id, trace_id, span_id,
                    "FACTS_BUILDER_STEP_COMPLETED",
                    {"step": "TC-1601", "status": "skipped", "reason": str(e)},
                )

        # Step 3.75: TC-1605 - Extract limitations from source code
        try:
            from .code_analyzer import extract_code_limitations
            code_limitations = extract_code_limitations(repo_dir, product_name_for_analysis)
            if code_limitations:
                existing_ids = {c["claim_id"] for c in evidence_map.get("claims", [])}
                new_count = 0
                for lc in code_limitations:
                    if lc["claim_id"] not in existing_ids:
                        evidence_map["claims"].append(lc)
                        new_count += 1
                if new_count > 0:
                    # Re-write evidence_map with new limitation claims
                    evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
                    atomic_write_json(evidence_map_path, evidence_map)
                logger.info(
                    "code_limitation_claims_extracted",
                    total=len(code_limitations),
                    new=new_count,
                    deduplicated=len(code_limitations) - new_count,
                )
        except Exception as e:
            logger.warning("code_limitation_extraction_failed", error=str(e))

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
            product_facts = assemble_product_facts(run_layout, evidence_map, run_config=run_config_dict)
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
            examples_processed_count=len(product_facts.get("example_inventory", [])),
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
