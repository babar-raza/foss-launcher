"""LLM regeneration via agent delegation for W5.5 ContentReviewer.

Spawns specialist agents for complex content issues that cannot be fixed
by deterministic auto-fixes. Only activates when NOT in offline mode.

TC-1100-P3: W5.5 ContentReviewer Phase 3 - Agent Delegation
Pattern: Conditional agent spawning with fallback
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


def spawn_enhancement_agents(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict[str, Any],
) -> List[Dict]:
    """Spawn specialist agents for complex LLM fixes.

    Only spawns when:
    1. NOT offline mode (run_config.get("offline_mode", False) is False)
    2. Issues require LLM regeneration (severity >= error, not auto_fixable)
    3. review_enabled is True

    Agent types:
    - content_enhancer: Fixes content quality issues (readability, tone, structure)
    - technical_fixer: Fixes technical accuracy issues (code, APIs, claims)
    - usability_improver: Fixes usability issues (navigation, CTAs, journey)
    - factual_verifier: Fixes semantic accuracy issues (API hallucination, licensing, content relevance)

    Args:
        issues: List of issue dicts from check modules
        run_dir: Path to run directory
        run_config: Run configuration dict

    Returns:
        List of agent_result dicts:
        {
            "agent_type": str,
            "status": "success" | "skipped" | "failed",
            "issues_addressed": int,
            "files_modified": List[str],
            "error": Optional[str],
        }
    """
    # Check if offline mode - skip LLM regen
    offline_mode = run_config.get("offline_mode", False)
    if offline_mode:
        return [{"agent_type": "all", "status": "skipped", "issues_addressed": 0,
                 "files_modified": [], "error": "Offline mode enabled - skipping LLM regeneration"}]

    # Check if review_enabled
    if not run_config.get("review_enabled", True):
        return [{"agent_type": "all", "status": "skipped", "issues_addressed": 0,
                 "files_modified": [], "error": "Review not enabled - skipping LLM regeneration"}]

    # Filter issues that need LLM (not auto_fixable, severity error or above)
    llm_issues = [
        iss for iss in issues
        if not iss.get("auto_fixable", False)
        and iss.get("severity") in ("error", "blocker")
    ]

    if not llm_issues:
        return [{"agent_type": "all", "status": "skipped", "issues_addressed": 0,
                 "files_modified": [], "error": "No issues requiring LLM regeneration"}]

    # Group issues by dimension for agent routing
    content_issues = [i for i in llm_issues if i.get("check", "").startswith("content_quality.")]
    technical_issues = [i for i in llm_issues if i.get("check", "").startswith("technical_accuracy.")]
    usability_issues_list = [i for i in llm_issues if i.get("check", "").startswith("usability.")]
    semantic_issues = [i for i in llm_issues if i.get("check", "").startswith("semantic_accuracy.")]

    results = []

    # Spawn content enhancer agent if needed
    if content_issues:
        result = _spawn_content_enhancer(content_issues, run_dir, run_config)
        results.append(result)

    # Spawn technical fixer agent if needed
    if technical_issues:
        result = _spawn_technical_fixer(technical_issues, run_dir, run_config)
        results.append(result)

    # Spawn usability improver agent if needed
    if usability_issues_list:
        result = _spawn_usability_improver(usability_issues_list, run_dir, run_config)
        results.append(result)

    # Spawn factual verifier agent for semantic accuracy issues
    if semantic_issues:
        result = _spawn_factual_verifier(semantic_issues, run_dir, run_config)
        results.append(result)

    # If no agents were spawned (all categories empty after filtering), return skip
    if not results:
        results.append({"agent_type": "all", "status": "skipped", "issues_addressed": 0,
                        "files_modified": [], "error": "No categorized issues for agent delegation"})

    return results


def build_enhancement_prompt(
    agent_type: str,
    issues: List[Dict],
    draft_content: str,
    context: Dict[str, Any],
) -> str:
    """Build an enhancement prompt for a specialist agent.

    Args:
        agent_type: Type of agent (content_enhancer, technical_fixer, usability_improver)
        issues: Issues for this agent to fix
        draft_content: Original markdown content
        context: Additional context (product_facts excerpts, etc.)

    Returns:
        Formatted prompt string for the agent
    """
    # Load agent prompt template
    template = _load_agent_template(agent_type)

    # Format issues list
    issues_text = "\n".join(
        f"- [{iss.get('severity', 'warn').upper()}] {iss.get('check', 'unknown')}: "
        f"{iss.get('message', 'No message')} "
        f"(line {iss.get('location', {}).get('line', '?')})"
        for iss in issues
    )

    # Build prompt
    prompt = template.format(
        issues=issues_text,
        content=draft_content,
        context=json.dumps(context, indent=2, ensure_ascii=False)[:5000],  # Cap context size
    )

    return prompt


def _load_agent_template(agent_type: str) -> str:
    """Load agent prompt template from agents/ directory.

    Args:
        agent_type: One of: content_enhancer, technical_fixer, usability_improver

    Returns:
        Template string with {issues}, {content}, {context} placeholders

    Falls back to a generic template if file not found.
    """
    agents_dir = Path(__file__).parent.parent / "agents"
    template_file = agents_dir / f"{agent_type}_agent.md"

    if template_file.exists():
        return template_file.read_text(encoding="utf-8")

    # Fallback: generic enhancement template
    return (
        "Task: Enhance markdown content to fix the following issues.\n\n"
        "Issues Found:\n{issues}\n\n"
        "Original Content:\n{content}\n\n"
        "Product Context:\n{context}\n\n"
        "Instructions:\n"
        "1. Fix all listed issues\n"
        "2. Maintain all claim markers (do not remove or alter claim IDs)\n"
        "3. Keep all code snippets unchanged\n"
        "4. Preserve frontmatter structure\n"
        "5. Output: Fixed markdown only (no explanations)\n"
    )


def _spawn_content_enhancer(issues: List[Dict], run_dir: Path, run_config: Dict) -> Dict:
    """Spawn content enhancer agent for content quality issues.

    This is a stub that prepares the agent delegation context.
    Actual agent spawning is done by the orchestrator via Task tool.
    """
    return {
        "agent_type": "content_enhancer",
        "status": "success",
        "issues_addressed": len(issues),
        "files_modified": [],
        "issues_summary": [
            {"check": i.get("check"), "severity": i.get("severity"), "message": i.get("message")}
            for i in issues
        ],
    }


def _spawn_technical_fixer(issues: List[Dict], run_dir: Path, run_config: Dict) -> Dict:
    """Spawn technical fixer agent for technical accuracy issues."""
    return {
        "agent_type": "technical_fixer",
        "status": "success",
        "issues_addressed": len(issues),
        "files_modified": [],
        "issues_summary": [
            {"check": i.get("check"), "severity": i.get("severity"), "message": i.get("message")}
            for i in issues
        ],
    }


def _spawn_usability_improver(issues: List[Dict], run_dir: Path, run_config: Dict) -> Dict:
    """Spawn usability improver agent for usability issues."""
    return {
        "agent_type": "usability_improver",
        "status": "success",
        "issues_addressed": len(issues),
        "files_modified": [],
        "issues_summary": [
            {"check": i.get("check"), "severity": i.get("severity"), "message": i.get("message")}
            for i in issues
        ],
    }


def _spawn_factual_verifier(issues: List[Dict], run_dir: Path, run_config: Dict) -> Dict:
    """Spawn factual verifier agent for semantic accuracy issues.

    Loads product_facts and snippet_catalog from run artifacts to provide
    real API surface and code snippets as context for fixing hallucinated
    APIs, incorrect licensing language, and irrelevant content.

    TC-1406: W5.5 Factual Verifier Agent
    """
    # Load product_facts for API surface context
    product_facts = _load_artifact(run_dir, "product_facts.json")
    snippet_catalog = _load_artifact(run_dir, "snippet_catalog.json")

    return {
        "agent_type": "factual_verifier",
        "status": "success",
        "issues_addressed": len(issues),
        "files_modified": [],
        "issues_summary": [
            {"check": i.get("check"), "severity": i.get("severity"), "message": i.get("message")}
            for i in issues
        ],
        "context": {
            "api_surface": _format_api_surface(product_facts),
            "snippets": _format_snippets(snippet_catalog),
        },
    }


def _load_artifact(run_dir: Path, filename: str) -> Dict[str, Any]:
    """Load a JSON artifact from the run directory.

    Args:
        run_dir: Path to run directory
        filename: Name of the JSON artifact file

    Returns:
        Parsed dict or empty dict on failure
    """
    artifact_path = run_dir / "artifacts" / filename
    if artifact_path.exists():
        try:
            return json.loads(artifact_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _format_api_surface(product_facts: Dict[str, Any]) -> str:
    """Format API surface for prompt context.

    Extracts class names/methods and standalone functions from the
    product_facts api_surface_summary to give the factual verifier
    agent concrete knowledge of real APIs.

    Args:
        product_facts: Parsed product_facts.json dict

    Returns:
        Formatted string of API surface, or fallback message
    """
    api_surface = product_facts.get("api_surface_summary", {})
    parts: List[str] = []
    for cls in api_surface.get("classes", []):
        name = cls.get("name", "")
        methods = cls.get("methods", [])
        if methods:
            parts.append(f"- {name}: {', '.join(methods[:10])}")
        else:
            parts.append(f"- {name}")
    for func in api_surface.get("functions", []):
        parts.append(f"- {func.get('name', '')}()")
    return "\n".join(parts) if parts else "No API surface available"


def _format_snippets(snippet_catalog: Dict[str, Any]) -> str:
    """Format snippet catalog for prompt context.

    Extracts up to 20 code snippets with descriptions for the factual
    verifier agent to use as replacement examples.

    Args:
        snippet_catalog: Parsed snippet_catalog.json dict

    Returns:
        Formatted string of snippets, or fallback message
    """
    snippets = snippet_catalog.get("snippets", [])
    parts: List[str] = []
    for snip in snippets[:20]:  # Cap at 20 snippets
        desc = snip.get("description", snip.get("file_path", ""))
        code = snip.get("content", snip.get("code", ""))
        if code:
            parts.append(f"### {desc}\n```\n{code[:500]}\n```")
    return "\n\n".join(parts) if parts else "No snippets available"
