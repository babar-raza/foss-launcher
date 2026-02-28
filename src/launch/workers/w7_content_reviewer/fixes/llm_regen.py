"""LLM regeneration via agent delegation for W7 ContentReviewer.

Spawns specialist agents for complex content issues that cannot be fixed
by deterministic auto-fixes. Only activates when NOT in offline mode.

TC-1100-P3: W7 ContentReviewer Phase 3 - Agent Delegation
TC-1751: Complete LLM Regen Agents (3 specialist agents)
Pattern: Conditional agent spawning with fallback
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Per-call timeout for Phase 4 regen (returns full corrected page, max_tokens=8192).
# Matches the _FORMAT_FIX_TIMEOUT_S pattern from llm_format_fix.py (TC-2406).
_REGEN_TIMEOUT_S: int = 120

# Lazy-loaded prompt loader for centralized prompts
_prompt_loader = None


def _get_prompt_loader():
    global _prompt_loader
    if _prompt_loader is None:
        try:
            from launch.prompts import PromptLoader
            _prompt_loader = PromptLoader()
        except Exception:
            pass
    return _prompt_loader


# Mapping from agent_type to centralized prompt name
_AGENT_PROMPT_MAP = {
    "content_enhancer": "system/content_enhancer",
    "technical_fixer": "system/technical_fixer",
    "usability_improver": "system/usability_improver",
    "factual_verifier": "system/factual_verifier",
}

# Regex for claim markers: [claim: CLAIM_ID] or <!-- claim: CLAIM_ID -->
_CLAIM_MARKER_RE = re.compile(
    r"\[claim:\s*([^\]]+)\]|<!--\s*claim:\s*([^>]+?)-->",
)

# YAML frontmatter regex
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def spawn_enhancement_agents(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict[str, Any],
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> List[Dict]:
    """Spawn specialist agents for complex LLM fixes.

    Only spawns when:
    1. NOT offline mode (run_config.get("offline_mode", False) is False)
    2. Issues require LLM regeneration (severity >= error, not auto_fixable)
    3. review_enabled is True
    4. llm_client is available (otherwise returns metadata-only results)

    Agent types:
    - content_enhancer: Fixes content quality issues (readability, tone, structure)
    - technical_fixer: Fixes technical accuracy issues (code, APIs, claims)
    - usability_improver: Fixes usability issues (navigation, CTAs, journey)
    - factual_verifier: Fixes semantic accuracy issues (API hallucination, licensing)

    Args:
        issues: List of issue dicts from check modules
        run_dir: Path to run directory
        run_config: Run configuration dict
        llm_client: Optional LLM client for actual regeneration
        drafts_dir: Optional path to drafts directory for file modification
        evidence_bundles: Optional per-page evidence excerpts for grounding (SR-02/TC-3500)

    Returns:
        List of agent_result dicts
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

    # Load context artifacts for agents
    product_facts = _load_artifact(run_dir, "product_facts.json")
    snippet_catalog = _load_artifact(run_dir, "snippet_catalog.json")

    results = []

    _ev = evidence_bundles  # short alias for call-site readability

    # Spawn content enhancer agent if needed
    if content_issues:
        result = _spawn_content_enhancer(
            content_issues, run_dir, run_config,
            llm_client=llm_client, drafts_dir=drafts_dir,
            product_facts=product_facts, n_workers=n_workers,
            evidence_bundles=_ev,
        )
        results.append(result)

    # Spawn technical fixer agent if needed
    if technical_issues:
        result = _spawn_technical_fixer(
            technical_issues, run_dir, run_config,
            llm_client=llm_client, drafts_dir=drafts_dir,
            product_facts=product_facts, snippet_catalog=snippet_catalog,
            n_workers=n_workers, evidence_bundles=_ev,
        )
        results.append(result)

    # Spawn usability improver agent if needed
    if usability_issues_list:
        result = _spawn_usability_improver(
            usability_issues_list, run_dir, run_config,
            llm_client=llm_client, drafts_dir=drafts_dir,
            product_facts=product_facts, n_workers=n_workers,
            evidence_bundles=_ev,
        )
        results.append(result)

    # Spawn factual verifier agent for semantic accuracy issues
    if semantic_issues:
        result = _spawn_factual_verifier(
            semantic_issues, run_dir, run_config,
            llm_client=llm_client, drafts_dir=drafts_dir,
            product_facts=product_facts, snippet_catalog=snippet_catalog,
            n_workers=n_workers, evidence_bundles=_ev,
        )
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
    evidence_excerpts: Optional[List[Dict]] = None,
) -> str:
    """Build an enhancement prompt for a specialist agent.

    Args:
        agent_type: Type of agent (content_enhancer, technical_fixer, usability_improver)
        issues: Issues for this agent to fix
        draft_content: Original markdown content
        context: Additional context (product_facts excerpts, etc.)
        evidence_excerpts: Optional per-file evidence excerpts for grounding (SR-02/TC-3500)

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

    # SR-02/TC-3500: Append grounding excerpts when available
    grounding_block = _format_grounding_excerpts(evidence_excerpts)
    if grounding_block:
        prompt += (
            "\n\nGrounding Excerpts (verified source evidence — "
            "do NOT invent facts beyond these):\n"
            + grounding_block
        )

    return prompt


def _format_grounding_excerpts(excerpts: Optional[List[Dict]]) -> str:
    """Format evidence excerpts as a grounding block for LLM prompts.

    SR-02/TC-3500: Produces a compact text block that grounds the LLM agent
    in verified source evidence, reducing hallucinated fixes.

    Args:
        excerpts: List of excerpt dicts with keys: claim_id, source, score, excerpt.

    Returns:
        Formatted multi-line string, or empty string when no excerpts available.
    """
    if not excerpts:
        return ""
    lines: List[str] = []
    for ex in excerpts:
        cid = ex.get("claim_id", "?")
        src = ex.get("source", "unknown")
        score = ex.get("score", 0)
        text = ex.get("excerpt", "").replace("\n", " ").strip()
        if text:
            lines.append(f'[{cid}] (src: {src}, score: {score:.2f}): "{text}"')
    return "\n".join(lines)


def _load_agent_template(agent_type: str) -> str:
    """Load agent prompt template, trying centralized PromptLoader first.

    Attempts to load from the centralized prompt library (system/<agent_type>)
    via PromptLoader. Falls back to local agents/<agent_type>_agent.md file,
    then to a generic template if neither is found.

    Args:
        agent_type: One of: content_enhancer, technical_fixer, usability_improver,
                    factual_verifier

    Returns:
        Template string with {issues}, {content}, {context} placeholders

    Falls back to local file, then generic template if centralized not found.
    """
    # Try centralized PromptLoader first
    _loader = _get_prompt_loader()
    prompt_name = _AGENT_PROMPT_MAP.get(agent_type)
    if _loader and prompt_name:
        try:
            # Load raw template body (without variable substitution)
            # so build_enhancement_prompt() can do its own .format()
            _, body, _ = _loader._load_raw(prompt_name)
            if body:
                return body
        except Exception:
            pass

    # Fallback: load from local agents/ directory
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


# ---------------------------------------------------------------------------
# TC-1751: Full agent implementations
# ---------------------------------------------------------------------------

def _extract_affected_files(issues: List[Dict]) -> List[str]:
    """Extract unique file paths from issue locations.

    Args:
        issues: List of issue dicts with location.path

    Returns:
        Sorted list of unique file paths
    """
    paths = set()
    for iss in issues:
        path = iss.get("location", {}).get("path", "")
        if path:
            paths.add(path)
    return sorted(paths)


def _extract_claim_ids(content: str) -> set:
    """Extract all claim IDs from content (both inline and HTML comment formats).

    Args:
        content: Markdown content string

    Returns:
        Set of claim ID strings
    """
    ids = set()
    for match in _CLAIM_MARKER_RE.finditer(content):
        cid = (match.group(1) or match.group(2) or "").strip()
        if cid:
            ids.add(cid)
    return ids


def _extract_frontmatter(content: str) -> Optional[str]:
    """Extract YAML frontmatter from content.

    Args:
        content: Markdown content string

    Returns:
        Frontmatter string (including ---) or None
    """
    match = _FRONTMATTER_RE.match(content)
    if match:
        return content[:match.end()]
    return None


def _validate_enhanced_content(
    original: str,
    enhanced: str,
    agent_type: str,
) -> List[str]:
    """Validate that enhanced content preserves critical elements.

    TC-1751 validation rules:
    1. All claim markers preserved (no removed claim IDs)
    2. Frontmatter intact (if present in original)
    3. Word count not decreased by more than 20%

    Args:
        original: Original markdown content
        enhanced: Enhanced markdown content
        agent_type: Agent type for logging

    Returns:
        List of validation failure messages (empty = valid)
    """
    failures = []

    # 1. Claim marker preservation
    original_claims = _extract_claim_ids(original)
    enhanced_claims = _extract_claim_ids(enhanced)
    missing_claims = original_claims - enhanced_claims
    if missing_claims:
        failures.append(
            f"{agent_type}: Lost {len(missing_claims)} claim markers: "
            f"{sorted(missing_claims)[:5]}"
        )

    # 2. Frontmatter preservation
    original_fm = _extract_frontmatter(original)
    if original_fm:
        enhanced_fm = _extract_frontmatter(enhanced)
        if not enhanced_fm:
            failures.append(f"{agent_type}: Frontmatter removed entirely")

    # 3. Word count check (allow up to 20% decrease)
    original_words = len(original.split())
    enhanced_words = len(enhanced.split())
    if original_words > 0:
        decrease_pct = (original_words - enhanced_words) / original_words
        if decrease_pct > 0.20:
            failures.append(
                f"{agent_type}: Word count decreased {decrease_pct:.0%} "
                f"({original_words} -> {enhanced_words})"
            )

    return failures


def _process_one_regen_file(
    file_path_str: str,
    agent_type: str,
    issues: List[Dict],
    drafts_dir: Path,
    context: Dict[str, Any],
    llm_client: Any,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Tuple[bool, bool]:
    """Process one file for LLM regen. Thread-safe: reads/writes only its own path.

    TC-2407: Pure helper extracted from _run_agent_on_files() to enable
    parallel execution via ThreadPoolExecutor.

    Returns:
        (was_modified, had_failure) — both False means file was skipped (not found).
    """
    file_path = _resolve_draft_path(drafts_dir, file_path_str)
    if file_path is None or not file_path.exists():
        logger.warning(f"[W7 {agent_type}] Draft file not found: {file_path_str}")
        return False, False

    try:
        original_content = file_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning(f"[W7 {agent_type}] Failed to read {file_path}: {e}")
        return False, True

    # Filter issues for this specific file; fall back to all issues
    file_issues = [i for i in issues if i.get("location", {}).get("path", "") == file_path_str]
    if not file_issues:
        file_issues = issues

    # SR-02/TC-3500: Look up per-file evidence excerpts
    file_excerpts = (evidence_bundles or {}).get(file_path_str, [])

    prompt_text = build_enhancement_prompt(
        agent_type=agent_type,
        issues=file_issues,
        draft_content=original_content,
        context=context,
        evidence_excerpts=file_excerpts or None,
    )

    try:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": f"You are a {agent_type.replace('_', ' ')} specialist. "
                 "Fix the listed issues in the markdown content. "
                 "Output ONLY the fixed markdown. No explanations."},
                {"role": "user", "content": prompt_text},
            ],
            call_id=f"w7_{agent_type}_{file_path.stem}",
            temperature=0.1,
            max_tokens=8192,
            timeout=_REGEN_TIMEOUT_S,
        )
        enhanced_content = response.get("content", "")
    except Exception as e:
        logger.warning(f"[W7 {agent_type}] LLM call failed for {file_path_str}: {e}")
        return False, True

    if not enhanced_content or len(enhanced_content.strip()) < 50:
        logger.warning(f"[W7 {agent_type}] LLM returned empty/short response for {file_path_str}")
        return False, True

    enhanced_content = _strip_markdown_fences(enhanced_content)

    validation_failures = _validate_enhanced_content(original_content, enhanced_content, agent_type)
    if validation_failures:
        for failure in validation_failures:
            logger.warning(f"[W7 {agent_type}] Validation: {failure}")
        return False, True

    try:
        file_path.write_text(enhanced_content, encoding="utf-8")
        logger.info(f"[W7 {agent_type}] Enhanced {file_path_str}")
        return True, False
    except OSError as e:
        logger.warning(f"[W7 {agent_type}] Failed to write {file_path}: {e}")
        return False, True


def _run_agent_on_files(
    agent_type: str,
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict[str, Any],
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    context: Optional[Dict[str, Any]] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """Run a specialist agent on affected draft files.

    TC-1751: Core agent execution logic shared by all agent types.
    TC-2407: n_workers > 1 parallelizes per-file LLM calls via ThreadPoolExecutor.

    For each affected file:
    1. Read current content
    2. Build enhancement prompt with issues + context
    3. Call LLM (with _REGEN_TIMEOUT_S per-call cap)
    4. Validate result (claim markers, frontmatter, word count)
    5. Write back on success

    Args:
        agent_type: Agent type string
        issues: Issues for this agent
        run_dir: Run directory path
        run_config: Run configuration
        llm_client: LLM client (None = metadata-only mode)
        drafts_dir: Path to drafts directory
        context: Additional context for the prompt
        n_workers: Max concurrent files (1=sequential, >1=parallel via ThreadPoolExecutor)

    Returns:
        Agent result dict
    """
    issues_summary = [
        {"check": i.get("check"), "severity": i.get("severity"), "message": i.get("message")}
        for i in issues
    ]

    # If no LLM client or no drafts_dir, return metadata-only result
    if llm_client is None or drafts_dir is None:
        result = {
            "agent_type": agent_type,
            "status": "skipped",
            "issues_addressed": len(issues),
            "files_modified": [],
            "issues_summary": issues_summary,
            "error": "No LLM client available" if llm_client is None else "No drafts directory",
        }
        if context:
            result["context"] = context
        return result

    affected_files = _extract_affected_files(issues)
    if not affected_files:
        return {
            "agent_type": agent_type,
            "status": "skipped",
            "issues_addressed": len(issues),
            "files_modified": [],
            "issues_summary": issues_summary,
            "error": "No affected files identified from issues",
        }

    files_modified: List[str] = []
    files_failed: List[str] = []
    ctx = context or {}

    effective = min(n_workers, len(affected_files)) if n_workers > 1 and affected_files else 1

    _ev = evidence_bundles  # short alias

    if effective <= 1:
        for file_path_str in affected_files:
            modified, failed = _process_one_regen_file(
                file_path_str, agent_type, issues, drafts_dir, ctx, llm_client,
                evidence_bundles=_ev,
            )
            if modified:
                files_modified.append(file_path_str)
            elif failed:
                files_failed.append(file_path_str)
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=effective, thread_name_prefix=f"w7_{agent_type}") as pool:
            futures = {
                pool.submit(
                    _process_one_regen_file, fp, agent_type, issues, drafts_dir, ctx, llm_client,
                    _ev,
                ): fp
                for fp in affected_files
            }
            for fut in as_completed(futures):
                fp = futures[fut]
                try:
                    modified, failed = fut.result()
                    if modified:
                        files_modified.append(fp)
                    elif failed:
                        files_failed.append(fp)
                except Exception as exc:
                    logger.warning("[W7/%s] regen thread failed for %s: %s", agent_type, fp, exc)
                    files_failed.append(fp)

    status = "success" if files_modified else ("failed" if files_failed else "skipped")
    result = {
        "agent_type": agent_type,
        "status": status,
        "issues_addressed": len(issues),
        "files_modified": files_modified,
        "issues_summary": issues_summary,
    }
    if files_failed:
        result["files_failed"] = files_failed
    return result


def _resolve_draft_path(drafts_dir: Path, file_path_str: str) -> Optional[Path]:
    """Resolve a file path from issue location to actual draft file.

    Handles both absolute paths and relative paths (from drafts_dir).

    Args:
        drafts_dir: Base drafts directory
        file_path_str: Path string from issue location

    Returns:
        Resolved Path or None
    """
    # Try as-is first (might be absolute or already correct)
    candidate = Path(file_path_str)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    # Try relative to drafts_dir
    candidate = drafts_dir / file_path_str
    if candidate.exists():
        return candidate

    # Try just the filename in drafts_dir (flat layout)
    candidate = drafts_dir / Path(file_path_str).name
    if candidate.exists():
        return candidate

    # Try searching recursively
    name = Path(file_path_str).name
    matches = list(drafts_dir.rglob(name))
    if len(matches) == 1:
        return matches[0]

    return None


def _strip_markdown_fences(content: str) -> str:
    """Strip wrapping markdown fences if LLM added them.

    Args:
        content: Potentially fence-wrapped content

    Returns:
        Content without outer fences
    """
    stripped = content.strip()
    if stripped.startswith("```markdown"):
        stripped = stripped[len("```markdown"):].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        return stripped
    if stripped.startswith("```md"):
        stripped = stripped[len("```md"):].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
        return stripped
    if stripped.startswith("```") and stripped.endswith("```"):
        # Only strip if the first line is just the fence
        first_line_end = stripped.index("\n") if "\n" in stripped else len(stripped)
        first_line = stripped[:first_line_end].strip()
        if first_line == "```":
            stripped = stripped[first_line_end:].strip()
            if stripped.endswith("```"):
                stripped = stripped[:-3].strip()
            return stripped
    return content


# ---------------------------------------------------------------------------
# Individual agent spawners (TC-1751)
# ---------------------------------------------------------------------------

def _spawn_content_enhancer(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict,
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    product_facts: Optional[Dict] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """Spawn content enhancer agent for content quality issues.

    TC-1751: Loads system/content_enhancer prompt, calls LLM to fix
    content quality issues (readability, tone, structure, density).
    Validates: claim markers preserved, frontmatter intact, word count stable.
    """
    context = {}
    if product_facts:
        positioning = product_facts.get("positioning", {})
        context["product_name"] = product_facts.get("product_name", "")
        context["audience"] = positioning.get("audience", "")
        context["tagline"] = positioning.get("tagline", "")

    return _run_agent_on_files(
        agent_type="content_enhancer",
        issues=issues,
        run_dir=run_dir,
        run_config=run_config,
        llm_client=llm_client,
        drafts_dir=drafts_dir,
        context=context,
        n_workers=n_workers,
        evidence_bundles=evidence_bundles,
    )


def _spawn_technical_fixer(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict,
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    product_facts: Optional[Dict] = None,
    snippet_catalog: Optional[Dict] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """Spawn technical fixer agent for technical accuracy issues.

    TC-1751: Loads system/technical_fixer prompt, calls LLM to fix
    technical accuracy issues (code, APIs, claims, evidence linkage).
    Provides API surface + snippets as context for grounded fixes.
    """
    context = {
        "api_surface": _format_api_surface(product_facts or {}),
        "snippets": _format_snippets(snippet_catalog or {}),
    }

    return _run_agent_on_files(
        agent_type="technical_fixer",
        issues=issues,
        run_dir=run_dir,
        run_config=run_config,
        llm_client=llm_client,
        drafts_dir=drafts_dir,
        context=context,
        n_workers=n_workers,
        evidence_bundles=evidence_bundles,
    )


def _spawn_usability_improver(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict,
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    product_facts: Optional[Dict] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """Spawn usability improver agent for usability issues.

    TC-1751: Loads system/usability_improver prompt, calls LLM to fix
    usability issues (navigation, CTAs, user journey, accessibility).
    """
    context = {}
    if product_facts:
        positioning = product_facts.get("positioning", {})
        context["product_name"] = product_facts.get("product_name", "")
        context["audience"] = positioning.get("audience", "")

    return _run_agent_on_files(
        agent_type="usability_improver",
        issues=issues,
        run_dir=run_dir,
        run_config=run_config,
        llm_client=llm_client,
        drafts_dir=drafts_dir,
        context=context,
        n_workers=n_workers,
        evidence_bundles=evidence_bundles,
    )


def _spawn_factual_verifier(
    issues: List[Dict],
    run_dir: Path,
    run_config: Dict,
    *,
    llm_client: Optional[Any] = None,
    drafts_dir: Optional[Path] = None,
    product_facts: Optional[Dict] = None,
    snippet_catalog: Optional[Dict] = None,
    n_workers: int = 1,
    evidence_bundles: Optional[Dict[str, List[Dict]]] = None,
) -> Dict:
    """Spawn factual verifier agent for semantic accuracy issues.

    TC-1751/TC-1406: Loads system/factual_verifier prompt, calls LLM to fix
    semantic accuracy issues (API hallucination, licensing, content relevance).
    Provides full API surface and code snippets as grounding context.
    """
    context = {
        "api_surface": _format_api_surface(product_facts or {}),
        "snippets": _format_snippets(snippet_catalog or {}),
    }

    return _run_agent_on_files(
        agent_type="factual_verifier",
        issues=issues,
        run_dir=run_dir,
        run_config=run_config,
        llm_client=llm_client,
        drafts_dir=drafts_dir,
        context=context,
        n_workers=n_workers,
        evidence_bundles=evidence_bundles,
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

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
        if isinstance(cls, str):
            parts.append(f"- {cls}")
        elif isinstance(cls, dict):
            name = cls.get("name", "")
            methods = cls.get("methods", [])
            if methods:
                parts.append(f"- {name}: {', '.join(methods[:10])}")
            else:
                parts.append(f"- {name}")
    for func in api_surface.get("functions", []):
        if isinstance(func, str):
            parts.append(f"- {func}()")
        elif isinstance(func, dict):
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
