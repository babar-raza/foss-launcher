"""TC-413: Detect contradictions and compute similarity scores.

This module implements contradiction detection between claims per
specs/03_product_facts_and_evidence.md:130-184 and semantic similarity
scoring per specs/03_product_facts_and_evidence.md:157-164.

Contradiction detection algorithm (binding):
1. Load evidence_map.json from TC-412
2. Detect logical contradictions between claims (e.g., "supports X" vs "does not support X")
3. Compute pairwise similarity scores between claims
4. Apply resolution rules based on evidence priority
5. Update evidence_map.json with contradictions array populated

Spec references:
- specs/03_product_facts_and_evidence.md:130-184 (Contradiction resolution)
- specs/04_claims_compiler_truth_lock.md:43-68 (Claims compilation)
- specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
- specs/10_determinism_and_caching.md (Stable ordering)

TC-413: W2.3 Detect contradictions and compute similarity scores
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...io.atomic import atomic_write_json
from ...io.run_layout import RunLayout
from ...util.logging import get_logger

logger = get_logger()


class ContradictionDetectionError(Exception):
    """Raised when contradiction detection fails."""
    pass


def compute_semantic_similarity(claim_a_text: str, claim_b_text: str) -> float:
    """Compute semantic similarity between two claims.

    Per specs/03_product_facts_and_evidence.md:157-164:
    Uses keyword overlap and text similarity as heuristic.
    For production, this would use embedding-based semantic similarity via LLM.

    Args:
        claim_a_text: First claim text
        claim_b_text: Second claim text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Normalize texts
    words_a = set(re.findall(r'\w+', claim_a_text.lower()))
    words_b = set(re.findall(r'\w+', claim_b_text.lower()))

    if not words_a or not words_b:
        return 0.0

    # Compute Jaccard similarity
    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union) if union else 0.0


def extract_claim_core_meaning(claim_text: str) -> Tuple[str, bool, Optional[str]]:
    """Extract core meaning from claim for contradiction detection.

    Returns:
        Tuple of (subject, is_affirmative, format_name)
        - subject: Core subject (e.g., "format", "feature", "api")
        - is_affirmative: True if positive claim, False if negative/limitation
        - format_name: Extracted format name if format claim, else None

    Examples:
        "Supports OBJ format" -> ("format", True, "OBJ")
        "Does not support FBX format" -> ("format", False, "FBX")
        "Can export STL files" -> ("format", True, "STL")
    """
    text_lower = claim_text.lower()

    # Detect negation
    is_affirmative = True
    negation_patterns = [
        'does not support',
        'not supported',
        'cannot',
        'not yet implemented',
        'not implemented',
        'limitation',
        'unsupported',
        'no support for',
    ]
    for pattern in negation_patterns:
        if pattern in text_lower:
            is_affirmative = False
            break

    # Extract format name (common 3D formats)
    format_name = None
    format_patterns = [
        r'\b(obj|fbx|stl|dae|gltf|glb|ply|3ds|off|one|pdf|dwg|dxf)\b',
    ]
    for pattern in format_patterns:
        match = re.search(pattern, text_lower)
        if match:
            format_name = match.group(1).upper()
            break

    # Determine subject
    if 'format' in text_lower or any(marker in text_lower for marker in ['read', 'write', 'import', 'export']):
        subject = 'format'
    elif any(marker in text_lower for marker in ['install', 'setup', 'usage']):
        subject = 'workflow'
    elif any(marker in text_lower for marker in ['class', 'function', 'method', 'api']):
        subject = 'api'
    else:
        subject = 'feature'

    return (subject, is_affirmative, format_name)


def detect_claim_contradiction(
    claim_a: Dict[str, Any],
    claim_b: Dict[str, Any],
    similarity_threshold: float = 0.3,
) -> Optional[Dict[str, Any]]:
    """Detect if two claims contradict each other.

    Per specs/03_product_facts_and_evidence.md:130-184:
    Contradictions occur when claims:
    1. Have high semantic similarity (share subject/format)
    2. Have opposite affirmations (one positive, one negative)
    3. Have different source priorities

    Args:
        claim_a: First claim
        claim_b: Second claim
        similarity_threshold: Minimum similarity to consider for contradiction

    Returns:
        Contradiction dictionary if detected, else None
        {
            "claim_a_id": str,
            "claim_b_id": str,
            "resolution": str,
            "winning_claim_id": str,
            "reasoning": str
        }
    """
    # Skip if same claim
    if claim_a['claim_id'] == claim_b['claim_id']:
        return None

    # Compute semantic similarity
    similarity = compute_semantic_similarity(
        claim_a['claim_text'],
        claim_b['claim_text']
    )

    # Only check for contradictions if claims are semantically related
    if similarity < similarity_threshold:
        return None

    # Extract core meanings
    subject_a, affirmative_a, format_a = extract_claim_core_meaning(claim_a['claim_text'])
    subject_b, affirmative_b, format_b = extract_claim_core_meaning(claim_b['claim_text'])

    # Check for contradiction:
    # 1. Same subject OR same format name
    # 2. Opposite affirmations
    is_same_subject = subject_a == subject_b
    is_same_format = format_a is not None and format_a == format_b
    is_opposite_affirmation = affirmative_a != affirmative_b

    if (is_same_subject or is_same_format) and is_opposite_affirmation:
        # Contradiction detected! Apply resolution rules
        return resolve_contradiction(claim_a, claim_b, format_a or subject_a)

    return None


def resolve_contradiction(
    claim_a: Dict[str, Any],
    claim_b: Dict[str, Any],
    subject: str,
) -> Dict[str, Any]:
    """Resolve contradiction between two claims using priority rules.

    Per specs/03_product_facts_and_evidence.md:153-184:
    Resolution algorithm:
    - priority_diff >= 2: Automatic resolution (prefer higher priority)
    - priority_diff == 1: Manual review required
    - priority_diff == 0: Unresolvable conflict (halt run)

    Args:
        claim_a: First claim
        claim_b: Second claim
        subject: Subject of contradiction (format name or subject type)

    Returns:
        Contradiction entry dictionary
    """
    priority_a = claim_a.get('source_priority', 7)
    priority_b = claim_b.get('source_priority', 7)

    priority_diff = abs(priority_a - priority_b)

    # Determine higher priority claim
    if priority_a < priority_b:
        higher_claim = claim_a
        lower_claim = claim_b
    else:
        higher_claim = claim_b
        lower_claim = claim_a

    # Apply resolution rules
    if priority_diff >= 2:
        # Automatic resolution: prefer higher priority
        resolution = "prefer_higher_priority"
        winning_claim_id = higher_claim['claim_id']
        reasoning = (
            f"Contradiction resolved automatically: {subject} claim from "
            f"priority {higher_claim['source_priority']} source "
            f"({higher_claim['citations'][0].get('source_type', 'unknown')}) "
            f"preferred over priority {lower_claim['source_priority']} source "
            f"({lower_claim['citations'][0].get('source_type', 'unknown')})"
        )

        logger.info(
            "contradiction_auto_resolved",
            claim_a_id=claim_a['claim_id'],
            claim_b_id=claim_b['claim_id'],
            winning_claim_id=winning_claim_id,
            priority_diff=priority_diff,
        )

    elif priority_diff == 1:
        # Manual review required
        resolution = "manual_review_required"
        winning_claim_id = higher_claim['claim_id']  # Tentatively prefer higher priority
        reasoning = (
            f"Contradiction requires manual review: {subject} claims from "
            f"similar priority sources (priority {priority_a} vs {priority_b}). "
            f"Tentatively using priority {higher_claim['source_priority']} claim."
        )

        logger.warning(
            "contradiction_manual_review_required",
            claim_a_id=claim_a['claim_id'],
            claim_b_id=claim_b['claim_id'],
            priority_diff=priority_diff,
        )

    else:  # priority_diff == 0
        # Unresolvable conflict (same priority)
        resolution = "unresolved"
        winning_claim_id = claim_a['claim_id']  # Arbitrary (both same priority)
        reasoning = (
            f"Contradiction cannot be resolved automatically: {subject} claims "
            f"from same priority source (priority {priority_a}). "
            f"Requires human intervention or repo_hints override."
        )

        logger.error(
            "contradiction_unresolved",
            claim_a_id=claim_a['claim_id'],
            claim_b_id=claim_b['claim_id'],
            priority_diff=priority_diff,
        )

    return {
        'claim_a_id': claim_a['claim_id'],
        'claim_b_id': claim_b['claim_id'],
        'resolution': resolution,
        'winning_claim_id': winning_claim_id,
        'reasoning': reasoning,
    }


def detect_all_contradictions(
    claims: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect all contradictions between claims (pairwise).

    Per specs/03_product_facts_and_evidence.md:130-184:
    Performs pairwise contradiction detection with stable ordering.

    Args:
        claims: List of claims from evidence_map

    Returns:
        List of contradiction entries (sorted deterministically)
    """
    contradictions = []

    # Pairwise comparison (stable ordering by claim_id)
    for i, claim_a in enumerate(claims):
        for claim_b in claims[i + 1:]:
            contradiction = detect_claim_contradiction(claim_a, claim_b)
            if contradiction:
                # Normalize so claim_a_id < claim_b_id (lexicographic ordering)
                if contradiction['claim_a_id'] > contradiction['claim_b_id']:
                    contradiction = {
                        'claim_a_id': contradiction['claim_b_id'],
                        'claim_b_id': contradiction['claim_a_id'],
                        'resolution': contradiction['resolution'],
                        'winning_claim_id': contradiction['winning_claim_id'],
                        'reasoning': contradiction['reasoning'],
                    }
                contradictions.append(contradiction)

    # Sort deterministically by claim_a_id, then claim_b_id
    contradictions.sort(key=lambda c: (c['claim_a_id'], c['claim_b_id']))

    return contradictions


def update_claims_with_contradiction_resolution(
    claims: List[Dict[str, Any]],
    contradictions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Update claims based on contradiction resolution.

    Per specs/03_product_facts_and_evidence.md:162-164:
    - Mark lower-priority claims as inference with low confidence
    - Keep higher-priority claims unchanged

    Args:
        claims: List of claims
        contradictions: List of contradiction entries

    Returns:
        Updated claims list
    """
    # Build map of losing claims
    losing_claims = {}
    for contradiction in contradictions:
        winning_id = contradiction['winning_claim_id']
        claim_a_id = contradiction['claim_a_id']
        claim_b_id = contradiction['claim_b_id']

        # Determine loser
        losing_id = claim_b_id if winning_id == claim_a_id else claim_a_id
        losing_claims[losing_id] = contradiction

    # Update claims
    updated_claims = []
    for claim in claims:
        if claim['claim_id'] in losing_claims:
            contradiction = losing_claims[claim['claim_id']]

            # Only downgrade if resolution is automatic
            if contradiction['resolution'] == 'prefer_higher_priority':
                # Downgrade to inference with low confidence
                claim = claim.copy()
                claim['truth_status'] = 'inference'
                claim['confidence'] = 'low'

                logger.info(
                    "claim_downgraded_due_to_contradiction",
                    claim_id=claim['claim_id'],
                    resolution=contradiction['resolution'],
                )

        updated_claims.append(claim)

    return updated_claims


def validate_evidence_map_with_contradictions(evidence_map: Dict[str, Any]) -> None:
    """Validate evidence map structure with contradictions array.

    Args:
        evidence_map: Evidence map dictionary

    Raises:
        ContradictionDetectionError: If structure is invalid
    """
    required_fields = ['schema_version', 'repo_url', 'repo_sha', 'claims', 'contradictions']

    for field in required_fields:
        if field not in evidence_map:
            raise ContradictionDetectionError(f"Missing required field: {field}")

    # Validate contradictions array
    if not isinstance(evidence_map['contradictions'], list):
        raise ContradictionDetectionError("contradictions must be a list")

    # Validate each contradiction
    for contradiction in evidence_map['contradictions']:
        required_contradiction_fields = ['claim_a_id', 'claim_b_id', 'resolution', 'winning_claim_id']
        for field in required_contradiction_fields:
            if field not in contradiction:
                raise ContradictionDetectionError(
                    f"Contradiction missing required field: {field}"
                )


def detect_contradictions(
    run_dir: Path,
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Detect contradictions and compute similarity scores between claims.

    This is the main entry point for TC-413 contradiction detection.

    Per specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract):
    - Reads evidence_map.json from TC-412
    - Detects logical contradictions between claims
    - Computes pairwise similarity scores
    - Applies resolution rules based on evidence priority
    - Updates evidence_map.json with contradictions array

    Args:
        run_dir: Run directory path
        llm_client: Optional LLM client (for semantic similarity)

    Returns:
        Updated evidence map with contradictions:
        {
            "schema_version": "1.0.0",
            "repo_url": str,
            "repo_sha": str,
            "claims": List[Dict] (possibly updated with downgraded truth_status),
            "contradictions": List[Dict] (newly detected),
            "metadata": {
                "total_contradictions": int,
                "auto_resolved": int,
                "manual_review_required": int,
                "unresolved": int
            }
        }

    Raises:
        ContradictionDetectionError: If contradiction detection fails
        FileNotFoundError: If evidence_map.json is missing

    Spec references:
    - specs/03_product_facts_and_evidence.md:130-184 (Contradiction resolution)
    - specs/21_worker_contracts.md:98-125 (W2 FactsBuilder contract)
    """
    run_layout = RunLayout(run_dir=run_dir)

    # Load evidence_map.json from TC-412
    evidence_map_path = run_layout.artifacts_dir / "evidence_map.json"
    if not evidence_map_path.exists():
        raise FileNotFoundError(
            f"evidence_map.json not found: {evidence_map_path}"
        )

    with open(evidence_map_path, 'r', encoding='utf-8') as f:
        evidence_map = json.load(f)

    # Extract claims
    claims = evidence_map.get('claims', [])

    logger.info(
        "contradiction_detection_started",
        total_claims=len(claims),
    )

    # Detect all contradictions
    contradictions = detect_all_contradictions(claims)

    # Update claims based on contradiction resolution
    if contradictions:
        claims = update_claims_with_contradiction_resolution(claims, contradictions)

    # Compute metadata
    auto_resolved = sum(1 for c in contradictions if c['resolution'] == 'prefer_higher_priority')
    manual_review = sum(1 for c in contradictions if c['resolution'] == 'manual_review_required')
    unresolved = sum(1 for c in contradictions if c['resolution'] == 'unresolved')

    # Update evidence map
    evidence_map['claims'] = claims
    evidence_map['contradictions'] = contradictions

    # Update metadata
    if 'metadata' not in evidence_map:
        evidence_map['metadata'] = {}

    evidence_map['metadata'].update({
        'total_contradictions': len(contradictions),
        'auto_resolved_contradictions': auto_resolved,
        'manual_review_required': manual_review,
        'unresolved_contradictions': unresolved,
    })

    # Validate structure
    try:
        validate_evidence_map_with_contradictions(evidence_map)
    except ContradictionDetectionError as e:
        logger.error("evidence_map_validation_failed", error=str(e))
        raise

    # Write updated artifact
    atomic_write_json(evidence_map_path, evidence_map)

    logger.info(
        "contradiction_detection_completed",
        total_contradictions=len(contradictions),
        auto_resolved=auto_resolved,
        manual_review=manual_review,
        unresolved=unresolved,
        output_path=str(evidence_map_path),
    )

    return evidence_map
