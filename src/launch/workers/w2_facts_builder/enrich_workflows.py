"""TC-1043: Workflow enrichment for W2 FactsBuilder.

Enriches minimal workflow structures with metadata, step ordering,
complexity estimation, and snippet tag mapping.

Spec: specs/03_product_facts_and_evidence.md (Workflow enrichment)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def enrich_workflow(
    workflow_tag: str,
    claim_ids: List[str],
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Enrich minimal workflow with metadata and step ordering.

    Args:
        workflow_tag: Workflow identifier tag (e.g., 'installation', 'quickstart')
        claim_ids: List of claim IDs belonging to this workflow
        claims: Full list of claims from evidence map
        snippets: Snippet catalog entries

    Returns:
        Enriched workflow dictionary with metadata, complexity, and ordered steps
    """
    workflow_claims = [c for c in claims if c['claim_id'] in claim_ids]

    complexity = _determine_complexity(workflow_claims)
    estimated_time = _estimate_time(workflow_claims)
    ordered_steps = _order_workflow_steps(workflow_claims, snippets)
    description = _generate_workflow_description(workflow_tag, workflow_claims)

    return {
        "workflow_id": f"wf_{workflow_tag}",
        "workflow_tag": workflow_tag,
        "name": _prettify_workflow_name(workflow_tag),
        "title": _prettify_workflow_name(workflow_tag),
        "description": description,
        "complexity": complexity,
        "estimated_time_minutes": estimated_time,
        "steps": ordered_steps,
        "claim_ids": claim_ids,
        "snippet_tags": _get_snippet_tags(workflow_tag),
    }


def _determine_complexity(claims: List[Dict[str, Any]]) -> str:
    """Determine workflow complexity based on claim count.

    Args:
        claims: List of workflow claims

    Returns:
        Complexity level: 'simple', 'moderate', or 'complex'
    """
    count = len(claims)
    if count <= 2:
        return "simple"
    elif count <= 5:
        return "moderate"
    return "complex"


def _estimate_time(claims: List[Dict[str, Any]]) -> int:
    """Estimate workflow completion time in minutes.

    Args:
        claims: List of workflow claims

    Returns:
        Estimated time in minutes
    """
    text = " ".join(c.get('claim_text', '').lower() for c in claims)
    if 'install' in text or 'setup' in text:
        base = 5
    elif 'configure' in text:
        base = 10
    else:
        base = 15
    return base + max(0, (len(claims) - 1)) * 5


def _order_workflow_steps(
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Order workflow claims into logical steps.

    Phases (in order): install -> setup -> config -> basic -> advanced

    Args:
        claims: List of workflow claims
        snippets: Snippet catalog entries

    Returns:
        Ordered list of step dictionaries
    """
    phases: Dict[str, List[Dict[str, Any]]] = {
        'install': [],
        'setup': [],
        'config': [],
        'basic': [],
        'advanced': [],
    }

    for claim in claims:
        text = claim.get('claim_text', '').lower()
        if any(kw in text for kw in ['install', 'pip']):
            phases['install'].append(claim)
        elif any(kw in text for kw in ['initialize', 'import', 'create']):
            phases['setup'].append(claim)
        elif any(kw in text for kw in ['configure', 'set', 'option']):
            phases['config'].append(claim)
        elif any(kw in text for kw in ['advanced', 'complex', 'custom']):
            phases['advanced'].append(claim)
        else:
            phases['basic'].append(claim)

    ordered = (
        phases['install']
        + phases['setup']
        + phases['config']
        + phases['basic']
        + phases['advanced']
    )

    steps = []
    for i, claim in enumerate(ordered, start=1):
        snippet = _find_matching_snippet(claim, snippets)
        steps.append({
            "step_num": i,
            "step_id": f"step_{i}",
            "name": _extract_step_name(claim.get('claim_text', '')),
            "claim_id": claim['claim_id'],
            "snippet_id": snippet.get('snippet_id') if snippet else None,
        })
    return steps


def _find_matching_snippet(
    claim: Dict[str, Any],
    snippets: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Find a snippet matching a claim by tag overlap.

    Args:
        claim: Claim dictionary
        snippets: List of snippet dictionaries

    Returns:
        Matching snippet or None
    """
    claim_text = claim.get('claim_text', '').lower()
    for s in snippets:
        for tag in s.get('tags', []):
            if tag.lower() in claim_text:
                return s
    return None


def _extract_step_name(claim_text: str) -> str:
    """Extract a short step name from claim text.

    Args:
        claim_text: Full claim text

    Returns:
        Truncated step name (max 60 chars)
    """
    text = claim_text.strip()
    if len(text) > 60:
        text = text[:57] + "..."
    return text


def _prettify_workflow_name(tag: str) -> str:
    """Convert workflow tag to human-readable name.

    Args:
        tag: Workflow tag (e.g., 'installation')

    Returns:
        Title-cased name (e.g., 'Installation')
    """
    return tag.replace('_', ' ').replace('-', ' ').title()


def _generate_workflow_description(
    tag: str,
    claims: List[Dict[str, Any]],
) -> str:
    """Generate a description for a workflow.

    Args:
        tag: Workflow tag
        claims: Workflow claims (unused for now, but available for future enrichment)

    Returns:
        Description string
    """
    templates = {
        'installation': "Install and set up the product for development use",
        'quickstart': "Get started with basic product usage and features",
        'configuration': "Configure product settings and options",
    }
    return templates.get(tag, f"{tag.replace('_', ' ').capitalize()} operations")


def _get_snippet_tags(tag: str) -> List[str]:
    """Get snippet tags associated with a workflow tag.

    Args:
        tag: Workflow tag

    Returns:
        List of snippet tags
    """
    mapping = {
        'installation': ['install'],
        'quickstart': ['quickstart', 'getting-started'],
        'configuration': ['config', 'settings'],
    }
    return mapping.get(tag, [tag])
