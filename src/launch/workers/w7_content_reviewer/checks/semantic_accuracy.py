"""TC-1405: LLM-based semantic accuracy checks.

Three checks that evaluate content correctness:
1. API hallucination detection: Find fabricated API methods/classes
2. Licensing accuracy: Detect commercial language in FOSS products
3. Content relevance: Identify internal details presented as features

Each check has an offline fallback (regex/heuristic) when llm_client=None.

Per-call timeout is intentionally short (30s) to prevent W7 from stalling when the
remote LLM is slow. If a call times out, the offline fallback result is used instead.
"""
from __future__ import annotations

import hashlib
import json as _json
import logging
import os
import re
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Short timeout for semantic checks — prevents W7 stall when remote LLM hangs.
# The offline heuristic fallback handles the gap.
_SEMANTIC_TIMEOUT_S = 15

# TC-3617: Higher timeout for bundled call (3x content + structured output).
_BUNDLE_TIMEOUT_S = 25

# TC-3617: Cache file name stored in artifacts/.
_CACHE_FILE = "semantic_cache.json"

# TC-3617: Output schema for bundled semantic check.
_BUNDLE_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "api_hallucinations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "line": {"type": "integer"},
                    "reason": {"type": "string"},
                },
                "required": ["name", "line"],
            },
        },
        "licensing_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                    "line": {"type": "integer"},
                    "context": {"type": "string"},
                },
                "required": ["term", "line"],
            },
        },
        "internal_details": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "line": {"type": "integer"},
                    "type": {"type": "string"},
                },
                "required": ["detail", "line"],
            },
        },
    },
    "required": ["api_hallucinations", "licensing_issues", "internal_details"],
}

from ....clients.llm_provider import LLMProviderClient

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


def check_all(
    drafts_dir: Path,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient] = None,
    snippet_catalog: Optional[Dict[str, Any]] = None,
    max_parallel_files: int = 4,
    resolver=None,
    evidence_excerpts: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    run_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Run all semantic accuracy checks.

    TC-2403: Runs 3 LLM-based semantic checks on every draft markdown file in parallel.
    Each file is independent — no result from file N is needed by file M.
    Results sorted by rel_path for determinism.

    TC-3617: When llm_client is present, uses bundled check (1 LLM call per file
    instead of 3).  When run_dir is present, caches results keyed by content hash.

    Args:
        drafts_dir: Path to drafts directory (RUN_DIR/drafts)
        product_facts: Product facts dict from product_facts.json
        llm_client: Optional LLM provider client (None = offline mode)
        snippet_catalog: Optional snippet catalog dict
        max_parallel_files: Max concurrent file checks (default 4, matches max_concurrency)
        resolver: Optional PageResolver for correct slug resolution (TC-3500)
        evidence_excerpts: Optional per-page evidence bundles (TC-3500)
        run_dir: Optional run directory for cache I/O (TC-3617)

    Returns:
        List of issue dicts matching W7 issue format
    """
    if not drafts_dir.exists():
        return []

    draft_files = sorted(drafts_dir.rglob("*.md"))
    _excerpts = evidence_excerpts or {}

    # TC-3617 B2: Load semantic cache (if run_dir provided)
    _cache: Optional[Dict[str, Any]] = None
    if run_dir is not None:
        _cache = _load_cache(run_dir)

    def _check_one_file(draft_file: Path) -> List[Dict[str, Any]]:
        try:
            content = draft_file.read_text(encoding="utf-8", errors="replace")
            rel_path = str(draft_file.relative_to(drafts_dir))
            # TC-3500: Get page-specific evidence excerpts
            page_excerpts = _excerpts.get(rel_path.replace("\\", "/"), [])

            # TC-3617 B2: Check cache before running checks
            cache_k = None
            if _cache is not None:
                cache_k = _cache_key(rel_path, content, page_excerpts)
                cached = _cache.get(cache_k)
                if cached is not None:
                    logger.debug(  # TC-3617 SR-02: cache hit telemetry
                        "Semantic cache hit for %s (1 LLM call saved)", rel_path
                    )
                    return cached

            # TC-3617 B1: Use bundled check when LLM is available
            if llm_client is not None:
                try:
                    file_issues = check_semantic_bundle(
                        content, product_facts, llm_client, rel_path,
                        snippet_catalog=snippet_catalog,
                        evidence_excerpts=page_excerpts,
                    )
                except Exception as _bundle_exc:  # TC-3617 SR-02: log fallback
                    logger.info(
                        "Semantic bundle fallback for %s: %s — using offline heuristics",
                        rel_path, type(_bundle_exc).__name__,
                    )
                    file_issues = _run_offline_checks(
                        content, product_facts, rel_path, snippet_catalog,
                        page_excerpts,
                    )
            else:
                file_issues = _run_offline_checks(
                    content, product_facts, rel_path, snippet_catalog,
                    page_excerpts,
                )

            # TC-3617 B2: Store in cache
            if _cache is not None and cache_k is not None:
                _cache[cache_k] = file_issues

            return file_issues
        except Exception:
            return []

    if max_parallel_files <= 1 or len(draft_files) <= 1:
        # Sequential path (original behavior)
        issues: List[Dict[str, Any]] = []
        for draft_file in draft_files:
            issues.extend(_check_one_file(draft_file))
    else:
        # Parallel path: check all files concurrently
        n_workers = min(len(draft_files), max_parallel_files)
        issues = []
        with ThreadPoolExecutor(max_workers=n_workers, thread_name_prefix="semantic_check") as pool:
            futures = {pool.submit(_check_one_file, df): df for df in draft_files}
            for fut in as_completed(futures):
                issues.extend(fut.result())

    # TC-3617 B2: Write cache after all files processed
    if _cache is not None and run_dir is not None:
        _save_cache(run_dir, _cache)

    return issues


# ---------------------------------------------------------------------------
# TC-3617 B1: Bundled semantic check (3-in-1 LLM call)
# ---------------------------------------------------------------------------


def check_semantic_bundle(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: LLMProviderClient,
    page_slug: str,
    snippet_catalog: Optional[Dict[str, Any]] = None,
    evidence_excerpts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Run all 3 semantic checks in a single LLM call (TC-3617 B1).

    Builds a combined prompt covering API hallucination, licensing accuracy,
    and content relevance.  Uses output_schema for structured JSON response.

    Falls back to offline heuristics on any failure (timeout, parse error).

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: LLM provider client (must not be None)
        page_slug: Relative path for issue location
        snippet_catalog: Optional snippet catalog
        evidence_excerpts: Optional evidence excerpts for grounding (TC-3500)

    Returns:
        List of issue dicts matching W7 issue format
    """
    # Build prompt sections
    api_surface = product_facts.get("api_surface_summary", {})
    api_summary = _format_api_surface(api_surface)
    code_blocks = _extract_code_blocks(content)

    # Format code blocks for prompt
    code_blocks_text = ""
    if code_blocks:
        parts = []
        for blk in code_blocks:
            lang = blk.get("language", "")
            parts.append(f"[Line {blk['line']}]\n```{lang}\n{blk['code'][:500]}\n```")
        code_blocks_text = "\n".join(parts)
    else:
        code_blocks_text = "(no code blocks found)"

    # Licensing: only for FOSS products
    product_name = product_facts.get("product_name", "")
    license_info = product_facts.get("license", "")
    is_foss = "foss" in product_name.lower() or "foss" in str(license_info).lower()

    licensing_text = ""
    if is_foss:
        lic_sections = _extract_sections_by_heading(content, ["licen", "pricing", "plan"])
        if lic_sections:
            licensing_text = "\n---\n".join(s["text"][:1000] for s in lic_sections)[:2000]
        else:
            licensing_text = content[:2000]
    else:
        licensing_text = "NOT APPLICABLE — product is not FOSS. Return empty array."

    # Feature sections for relevance check
    feat_sections = _extract_sections_by_heading(
        content, ["feature", "capabilit", "key feature"],
    )
    features_text = ""
    if feat_sections:
        features_text = "\n---\n".join(s["text"][:1000] for s in feat_sections)[:2000]
    else:
        features_text = "(no feature sections found — return empty array)"

    # Evidence grounding block (TC-3500)
    grounding_section = ""
    if evidence_excerpts:
        grounding_block = _format_evidence_for_prompt(evidence_excerpts)
        if grounding_block:
            grounding_section = (
                "\nGrounding excerpts (verified source evidence):\n"
                f"{grounding_block}\n"
            )

    prompt = (
        "You are a documentation quality reviewer. Analyze the content below "
        "for three types of issues and return structured JSON.\n\n"
        "TASK 1: API HALLUCINATION DETECTION\n"
        f"Known API surface:\n{api_summary}\n\n"
        f"Code blocks:\n{code_blocks_text}\n\n"
        "Identify any API method/class calls in the code blocks that are NOT "
        "in the known API surface. Only flag product API calls (not standard "
        "library). Use the line number from the code block header.\n\n"
        "TASK 2: LICENSING ACCURACY (FOSS)\n"
        f"{licensing_text}\n\n"
        "Identify commercial licensing language inappropriate for FOSS docs "
        "(commercial license, metered license, evaluation limit, paid plan, "
        "trial version, proprietary, enterprise edition, premium feature, "
        "subscription required).\n\n"
        "TASK 3: CONTENT RELEVANCE\n"
        f"{features_text}\n\n"
        "Identify internal implementation details presented as user-facing "
        "features (hex constants, binary format refs, jcid identifiers, "
        "GUIDs, memory layout, wire protocol).\n"
        f"{grounding_section}"
    )

    response = llm_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        call_id=f"semantic_bundle_{page_slug}",
        timeout=_BUNDLE_TIMEOUT_S,
        output_schema=_BUNDLE_OUTPUT_SCHEMA,
    )
    response_text = response.get("content", "")

    # Parse structured JSON response
    data = _json.loads(response_text)

    issues: List[Dict[str, Any]] = []

    # API hallucinations
    for item in data.get("api_hallucinations", []):
        name = item.get("name", "")
        if name:
            issues.append(_make_issue(
                check="semantic_accuracy.api_hallucination",
                severity="error",
                message=f"Possibly hallucinated API: {name}",
                path=page_slug,
                line=item.get("line", 0),
            ))

    # Licensing issues
    for item in data.get("licensing_issues", []):
        term = item.get("term", "")
        if term:
            issues.append(_make_issue(
                check="semantic_accuracy.licensing_accuracy",
                severity="error",
                message=f"Commercial language in FOSS docs: {term}",
                path=page_slug,
                line=item.get("line", 0),
                auto_fixable=True,
            ))

    # Internal details
    for item in data.get("internal_details", []):
        detail = item.get("detail", "")
        if detail:
            issues.append(_make_issue(
                check="semantic_accuracy.content_relevance",
                severity="warn",
                message=f"Internal implementation detail as feature: {detail}",
                path=page_slug,
                line=item.get("line", 0),
            ))

    return issues


def _run_offline_checks(
    content: str,
    product_facts: Dict[str, Any],
    rel_path: str,
    snippet_catalog: Optional[Dict[str, Any]],
    page_excerpts: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Run all 3 checks using offline heuristics (no LLM).

    TC-3617: Extracted helper so both check_all and bundle fallback can share.
    """
    file_issues: List[Dict[str, Any]] = []
    file_issues.extend(check_api_hallucination(
        content, product_facts, None, rel_path, snippet_catalog,
        evidence_excerpts=page_excerpts,
    ))
    file_issues.extend(check_licensing_accuracy(
        content, product_facts, None, rel_path,
    ))
    file_issues.extend(check_content_relevance(
        content, product_facts, None, rel_path,
    ))
    return file_issues


# ---------------------------------------------------------------------------
# TC-3617 B2: Semantic result cache helpers
# ---------------------------------------------------------------------------


def _cache_key(
    rel_path: str,
    content: str,
    evidence_excerpts: Optional[List[Dict[str, Any]]],
) -> str:
    """Compute deterministic cache key from file path, content, and evidence."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    evidence_text = _evidence_excerpt_text(evidence_excerpts)
    evidence_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    normalized_path = rel_path.replace("\\", "/")
    combined = f"{normalized_path}:{content_hash}:{evidence_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _evidence_excerpt_text(
    evidence_excerpts: Optional[List[Dict[str, Any]]],
) -> str:
    """Normalize evidence to excerpt text only for cache-key stability."""
    if not evidence_excerpts:
        return ""

    def _sort_key(item: Dict[str, Any]) -> tuple[str, str]:
        claim_id = str(item.get("claim_id", ""))
        excerpt_text = ""
        for key in ("excerpt_text", "excerpt", "text", "content"):
            value = item.get(key)
            if isinstance(value, str) and value:
                excerpt_text = value
                break
        return claim_id, excerpt_text

    parts: List[str] = []
    for item in sorted(evidence_excerpts, key=_sort_key):
        for key in ("excerpt_text", "excerpt", "text", "content"):
            value = item.get(key)
            if isinstance(value, str) and value:
                parts.append(value)
                break
    return "\n".join(parts)


def _load_cache(run_dir: Path) -> Dict[str, Any]:
    """Load semantic cache from artifacts/. Returns {} on missing/corrupt."""
    cache_path = run_dir / "artifacts" / _CACHE_FILE
    if not cache_path.exists():
        return {}
    try:
        return _json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(run_dir: Path, cache: Dict[str, Any]) -> None:
    """Atomic write semantic cache to artifacts/."""
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    cache_path = artifacts_dir / _CACHE_FILE
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(artifacts_dir), suffix=".tmp", prefix="sem_cache_",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                _json.dump(cache, f, sort_keys=True)
            os.replace(tmp_path, str(cache_path))
        except Exception as _write_exc:  # TC-3617 SR-02: warn + clean up on write failure
            logger.warning(
                "Semantic cache write failed for run_dir=%s: %s — cache will not persist",
                run_dir, _write_exc,
            )
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as _save_exc:  # TC-3617 SR-02: warn on mkstemp failure
        logger.warning(
            "Semantic cache write failed for run_dir=%s: %s — cache will not persist",
            run_dir, _save_exc,
        )


# ---------------------------------------------------------------------------
# Check 1: API Hallucination Detection
# ---------------------------------------------------------------------------

def check_api_hallucination(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
    snippet_catalog: Optional[Dict[str, Any]] = None,
    evidence_excerpts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Detect fabricated API methods/classes in code blocks.

    LLM path: sends code block + known API surface to LLM for verification.
    Offline fallback: extracts ClassName.method_name() patterns and cross-
    references against product_facts.api_surface_summary.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location
        snippet_catalog: Optional snippet catalog
        evidence_excerpts: Optional evidence excerpts for grounding (TC-3500)

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    # Extract code blocks (```python ... ``` or ``` ... ```)
    code_blocks = _extract_code_blocks(content)
    if not code_blocks:
        return issues

    # Get known API surface
    api_surface = product_facts.get("api_surface_summary", {})
    # Classes may be strings or dicts with a 'name' key
    raw_classes = api_surface.get("classes", [])
    known_classes = {
        (c if isinstance(c, str) else c.get("name", "")).lower(): (c if isinstance(c, str) else c.get("name", ""))
        for c in raw_classes if (c if isinstance(c, str) else c.get("name", ""))
    }
    known_methods_by_class: Dict[str, set] = {}
    for cls_info in api_surface.get("class_details", []):
        cls_name = cls_info.get("name", "")
        methods = set(m.lower() for m in cls_info.get("methods", []))
        known_methods_by_class[cls_name.lower()] = methods

    # Also build a flat set of all known method names (for classes without details)
    all_known_methods = set()
    for methods in known_methods_by_class.values():
        all_known_methods.update(methods)

    if llm_client is not None:
        issues.extend(_api_hallucination_llm(
            code_blocks, api_surface, llm_client, page_slug, content,
            evidence_excerpts=evidence_excerpts,
        ))
    else:
        issues.extend(_api_hallucination_offline(
            code_blocks, known_classes, known_methods_by_class, page_slug, content,
        ))

    return issues


def _api_hallucination_llm(
    code_blocks: List[Dict[str, Any]],
    api_surface: Dict[str, Any],
    llm_client: LLMProviderClient,
    page_slug: str,
    content: str,
    evidence_excerpts: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """LLM-based API hallucination detection."""
    issues: List[Dict[str, Any]] = []

    api_summary = _format_api_surface(api_surface)
    # TC-3500: Format evidence excerpts for grounding
    grounding_block = _format_evidence_for_prompt(evidence_excerpts) if evidence_excerpts else ""

    for block in code_blocks:
        code = block["code"]
        line = block["line"]

        # Try centralized prompt first, fall back to inline
        _loader = _get_prompt_loader()
        prompt = None
        if _loader:
            try:
                prompt = _loader.load(
                    "review/api_verification",
                    content=code,
                    api_surface=api_summary,
                ).text
            except Exception:
                pass
        if not prompt:
            grounding_section = ""
            if grounding_block:
                grounding_section = (
                    f"\nGrounding excerpts (verified source evidence):\n"
                    f"{grounding_block}\n"
                )
            prompt = (
                "You are an API verification assistant. Given the known API surface "
                "and a code block, identify any method or class names in the code "
                "that are NOT in the known API surface. Only flag names that look "
                "like product API calls (not standard library).\n\n"
                f"Known API surface:\n{api_summary}\n"
                f"{grounding_section}\n"
                f"Code block:\n```\n{code}\n```\n\n"
                "List each hallucinated API name on a separate line prefixed with "
                "'HALLUCINATED:'. If none are hallucinated, respond with 'NONE'."
            )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_api_hallucination_{page_slug}_{line}",
                timeout=_SEMANTIC_TIMEOUT_S,
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("HALLUCINATED:"):
                    api_name = resp_line.split(":", 1)[1].strip()
                    if api_name and api_name.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.api_hallucination",
                            severity="error",
                            message=f"Possibly hallucinated API: {api_name}",
                            path=page_slug,
                            line=line,
                        ))
        except Exception:
            # Fall through to offline if LLM fails for this block
            pass

    return issues


def _api_hallucination_offline(
    code_blocks: List[Dict[str, Any]],
    known_classes: Dict[str, str],
    known_methods_by_class: Dict[str, set],
    page_slug: str,
    content: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic API hallucination detection.

    Extracts ClassName.method_name() patterns from code blocks and flags
    any method call where the class exists in the API surface but the
    method does NOT.

    Also resolves variable-to-class mappings (e.g., ``scene = Scene()``
    maps variable ``scene`` to class ``Scene``) so that
    ``scene.nonexistent()`` is correctly flagged.
    """
    issues: List[Dict[str, Any]] = []

    # Pattern: identifier.method_name(
    call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
    # Pattern: variable = ClassName(...)
    assignment_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([A-Z][a-zA-Z0-9_]*)\s*\(')

    for block in code_blocks:
        code = block["code"]
        line = block["line"]

        # Build variable -> class name mapping from assignments
        var_to_class: Dict[str, str] = {}
        for var_name, cls_name in assignment_pattern.findall(code):
            var_to_class[var_name.lower()] = cls_name

        matches = call_pattern.findall(code)
        seen = set()
        for obj_name, method_name in matches:
            # Resolve variable to class if possible
            resolved_class = obj_name
            if obj_name.lower() in var_to_class:
                resolved_class = var_to_class[obj_name.lower()]

            pair = (resolved_class.lower(), method_name.lower())
            if pair in seen:
                continue
            seen.add(pair)

            # Only flag if the class IS known but the method is NOT
            # Offline heuristic: lower confidence → warn (not error)
            if resolved_class.lower() in known_classes:
                class_methods = known_methods_by_class.get(resolved_class.lower(), set())
                if class_methods and method_name.lower() not in class_methods:
                    display_class = known_classes.get(resolved_class.lower(), resolved_class)
                    issues.append(_make_issue(
                        check="semantic_accuracy.api_hallucination",
                        severity="warn",
                        message=(
                            f"Possibly hallucinated API: {display_class}.{method_name}() "
                            f"- class '{display_class}' exists but method '{method_name}' "
                            f"not found in API surface"
                        ),
                        path=page_slug,
                        line=line,
                    ))

    return issues


# ---------------------------------------------------------------------------
# Check 2: Licensing Accuracy
# ---------------------------------------------------------------------------

def check_licensing_accuracy(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Detect commercial language in FOSS product documentation.

    Only active when 'foss' appears in product_name (case-insensitive)
    or in product_facts.license.

    LLM path: sends licensing-related sections to LLM for evaluation.
    Offline fallback: regex for commercial terms in licensing sections.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    # Guard: only active for FOSS products
    product_name = product_facts.get("product_name", "")
    license_info = product_facts.get("license", "")
    if "foss" not in product_name.lower() and "foss" not in str(license_info).lower():
        return issues

    if llm_client is not None:
        issues.extend(_licensing_llm(content, llm_client, page_slug))
    else:
        issues.extend(_licensing_offline(content, page_slug))

    return issues


def _licensing_llm(
    content: str,
    llm_client: LLMProviderClient,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """LLM-based licensing accuracy check."""
    issues: List[Dict[str, Any]] = []

    # Extract licensing-related sections
    sections = _extract_sections_by_heading(content, ["licen", "pricing", "plan"])
    if not sections:
        # If no specific licensing sections, check full content
        sections = [{"text": content, "line": 1}]

    for section in sections:
        # Try centralized prompt first, fall back to inline
        _loader = _get_prompt_loader()
        prompt = None
        if _loader:
            try:
                prompt = _loader.load(
                    "review/licensing_review",
                    content=section['text'][:2000],
                ).text
            except Exception:
                pass
        if not prompt:
            prompt = (
                "You are a licensing compliance reviewer for open-source (FOSS) "
                "documentation. Identify any commercial licensing language in the "
                "following text that would be inappropriate for FOSS documentation.\n\n"
                "Look for: commercial license, metered license, evaluation limit, "
                "paid plan, trial version, proprietary, enterprise edition, "
                "premium feature, subscription required.\n\n"
                f"Text:\n{section['text'][:2000]}\n\n"
                "List each commercial term found on a separate line prefixed with "
                "'COMMERCIAL:'. If none found, respond with 'NONE'."
            )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_licensing_{page_slug}_{section['line']}",
                timeout=_SEMANTIC_TIMEOUT_S,
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("COMMERCIAL:"):
                    term = resp_line.split(":", 1)[1].strip()
                    if term and term.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.licensing_accuracy",
                            severity="error",
                            message=f"Commercial language in FOSS docs: {term}",
                            path=page_slug,
                            line=section["line"],
                            auto_fixable=True,
                        ))
        except Exception:
            pass

    return issues


def _licensing_offline(
    content: str,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic licensing accuracy check.

    Searches for commercial terms in licensing-related sections.
    """
    issues: List[Dict[str, Any]] = []

    commercial_terms = [
        r"commercial\s+licen[sc]",
        r"metered\s+licen[sc]",
        r"evaluation\s+limit",
        r"paid\s+plan",
        r"trial\s+version",
        r"\bproprietary\b",
        r"enterprise\s+edition",
        r"premium\s+feature",
        r"subscription\s+required",
    ]

    # Only check licensing-related sections
    sections = _extract_sections_by_heading(content, ["licen", "pricing", "plan"])
    if not sections:
        # If no licensing sections, skip (no false positives on non-licensing content)
        return issues

    for section in sections:
        text = section["text"]
        base_line = section["line"]
        lines = text.split("\n")

        for idx, line_text in enumerate(lines):
            for pattern in commercial_terms:
                if re.search(pattern, line_text, re.IGNORECASE):
                    # Offline heuristic: lower confidence → warn (not error)
                    issues.append(_make_issue(
                        check="semantic_accuracy.licensing_accuracy",
                        severity="warn",
                        message=(
                            f"Commercial language in FOSS docs: "
                            f"{line_text.strip()[:80]}"
                        ),
                        path=page_slug,
                        line=base_line + idx,
                        auto_fixable=True,
                    ))
                    break  # One issue per line

    return issues


# ---------------------------------------------------------------------------
# Check 3: Content Relevance
# ---------------------------------------------------------------------------

def check_content_relevance(
    content: str,
    product_facts: Dict[str, Any],
    llm_client: Optional[LLMProviderClient],
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Identify internal implementation details presented as features.

    LLM path: asks LLM to identify internal details in feature sections.
    Offline fallback: looks for hex constants, jcid-prefixed identifiers,
    binary format references in feature/capability sections.

    Args:
        content: Markdown content of a draft file
        product_facts: Product facts dict
        llm_client: Optional LLM client (None = offline)
        page_slug: Relative path for issue location

    Returns:
        List of issue dicts
    """
    issues: List[Dict[str, Any]] = []

    if llm_client is not None:
        issues.extend(_content_relevance_llm(content, llm_client, page_slug))
    else:
        issues.extend(_content_relevance_offline(content, page_slug))

    return issues


def _content_relevance_llm(
    content: str,
    llm_client: LLMProviderClient,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """LLM-based content relevance check."""
    issues: List[Dict[str, Any]] = []

    # Extract feature/capability sections
    sections = _extract_sections_by_heading(
        content, ["feature", "capabilit", "key feature"],
    )
    if not sections:
        return issues

    for section in sections:
        # Try centralized prompt first, fall back to inline
        _loader = _get_prompt_loader()
        prompt = None
        if _loader:
            try:
                prompt = _loader.load(
                    "review/internal_detail_review",
                    content=section['text'][:2000],
                ).text
            except Exception:
                pass
        if not prompt:
            prompt = (
                "You are a documentation reviewer. Identify any internal "
                "implementation details that are presented as user-facing features "
                "in the following text. Internal details include: hex constants, "
                "binary format references (GUID, CompactID, FileNode), internal "
                "identifiers (jcid-prefixed), memory layout details, wire protocol "
                "specifics.\n\n"
                f"Text:\n{section['text'][:2000]}\n\n"
                "List each internal detail on a separate line prefixed with "
                "'INTERNAL:'. If none found, respond with 'NONE'."
            )

        try:
            response = llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                call_id=f"semantic_relevance_{page_slug}_{section['line']}",
                timeout=_SEMANTIC_TIMEOUT_S,
            )
            response_text = response.get("content", "")

            for resp_line in response_text.strip().split("\n"):
                resp_line = resp_line.strip()
                if resp_line.upper().startswith("INTERNAL:"):
                    detail = resp_line.split(":", 1)[1].strip()
                    if detail and detail.upper() != "NONE":
                        issues.append(_make_issue(
                            check="semantic_accuracy.content_relevance",
                            severity="warn",
                            message=f"Internal implementation detail as feature: {detail}",
                            path=page_slug,
                            line=section["line"],
                        ))
        except Exception:
            pass

    return issues


def _content_relevance_offline(
    content: str,
    page_slug: str,
) -> List[Dict[str, Any]]:
    """Offline heuristic content relevance check.

    Looks for hex constants, jcid-prefixed identifiers, and binary format
    references in feature/capability sections.
    """
    issues: List[Dict[str, Any]] = []

    # Only check in feature/capability sections
    sections = _extract_sections_by_heading(
        content, ["feature", "capabilit", "key feature"],
    )
    if not sections:
        return issues

    internal_patterns = [
        (re.compile(r'\b0x[0-9a-fA-F]{4,}\b'), "Hex constant"),
        (re.compile(r'\bjcid[A-Za-z0-9_]+\b'), "jcid-prefixed identifier"),
        (re.compile(r'\bCompactID\b'), "Binary format reference (CompactID)"),
        (re.compile(r'\bFileNode\b'), "Binary format reference (FileNode)"),
        (re.compile(r'\b[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}\b'),
         "Raw GUID in feature section"),
    ]

    for section in sections:
        text = section["text"]
        base_line = section["line"]
        lines = text.split("\n")

        for idx, line_text in enumerate(lines):
            for pattern, description in internal_patterns:
                if pattern.search(line_text):
                    issues.append(_make_issue(
                        check="semantic_accuracy.content_relevance",
                        severity="warn",
                        message=(
                            f"{description} in feature section: "
                            f"{line_text.strip()[:80]}"
                        ),
                        path=page_slug,
                        line=base_line + idx,
                    ))
                    break  # One issue per line

    return issues


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_issue(
    check: str,
    severity: str,
    message: str,
    path: str,
    line: int,
    auto_fixable: bool = False,
) -> Dict[str, Any]:
    """Create a W7-compatible issue dict.

    Args:
        check: Check identifier (e.g. "semantic_accuracy.api_hallucination")
        severity: Issue severity ("error", "warn", "info")
        message: Human-readable description
        path: Relative file path
        line: Line number (0 if not determinable)
        auto_fixable: Whether the issue can be automatically fixed (default False)

    Returns:
        Issue dict matching W7 schema
    """
    return {
        "issue_id": str(uuid.uuid4()),
        "check": check,
        "severity": severity,
        "auto_fixable": auto_fixable,
        "message": message,
        "location": {
            "path": path,
            "line": line,
        },
    }


def _extract_code_blocks(content: str) -> List[Dict[str, Any]]:
    """Extract code blocks from markdown content.

    Args:
        content: Markdown content

    Returns:
        List of dicts with 'code', 'language', and 'line' keys
    """
    blocks: List[Dict[str, Any]] = []
    pattern = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)

    for match in pattern.finditer(content):
        language = match.group(1).lower() or "unknown"
        code = match.group(2)
        line = content[:match.start()].count("\n") + 1
        blocks.append({
            "code": code,
            "language": language,
            "line": line,
        })

    return blocks


def _extract_sections_by_heading(
    content: str,
    heading_keywords: List[str],
) -> List[Dict[str, Any]]:
    """Extract sections whose headings contain any of the given keywords.

    Each section spans from its heading to the next heading of equal or
    higher level (or end of file).

    Args:
        content: Markdown content
        heading_keywords: List of keywords to match in heading text (case-insensitive)

    Returns:
        List of dicts with 'text' and 'line' keys
    """
    sections: List[Dict[str, Any]] = []
    lines = content.split("\n")
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$')

    i = 0
    while i < len(lines):
        match = heading_pattern.match(lines[i])
        if match:
            heading_level = len(match.group(1))
            heading_text = match.group(2).lower()

            if any(kw in heading_text for kw in heading_keywords):
                # Collect section text until next heading of equal or higher level
                section_start = i
                section_lines = [lines[i]]
                j = i + 1
                while j < len(lines):
                    next_match = heading_pattern.match(lines[j])
                    if next_match and len(next_match.group(1)) <= heading_level:
                        break
                    section_lines.append(lines[j])
                    j += 1

                sections.append({
                    "text": "\n".join(section_lines),
                    "line": section_start + 1,  # 1-indexed
                })
                i = j
                continue
        i += 1

    return sections


def _format_evidence_for_prompt(
    excerpts: List[Dict[str, Any]],
    max_total: int = 9,
) -> str:
    """Format evidence excerpts for inclusion in LLM prompts (TC-3500).

    Args:
        excerpts: List of excerpt dicts with claim_id, excerpt, source, score.
        max_total: Maximum number of excerpts to include.

    Returns:
        Formatted string block for prompt injection.
    """
    if not excerpts:
        return ""
    lines: List[str] = []
    for ex in excerpts[:max_total]:
        cid = ex.get("claim_id", "?")
        src = ex.get("source", "?")
        score = ex.get("score", 0)
        text = ex.get("excerpt", "")[:300]
        lines.append(f'[{cid}] (src: {src}, score: {score:.2f}): "{text}"')
    return "\n".join(lines)


def _format_api_surface(api_surface: Dict[str, Any]) -> str:
    """Format API surface summary for LLM prompt.

    Args:
        api_surface: API surface summary dict

    Returns:
        Human-readable API surface summary
    """
    parts: List[str] = []

    classes = api_surface.get("classes", [])
    if classes:
        class_names = [c if isinstance(c, str) else c.get("name", "") for c in classes]
        parts.append(f"Known classes: {', '.join(n for n in class_names if n)}")

    functions = api_surface.get("functions", [])
    if functions:
        func_names = [f if isinstance(f, str) else f.get("name", "") for f in functions]
        parts.append(f"Known functions: {', '.join(n for n in func_names if n)}")

    for cls_info in api_surface.get("class_details", []):
        cls_name = cls_info.get("name", "")
        methods = cls_info.get("methods", [])
        if methods:
            parts.append(f"{cls_name} methods: {', '.join(methods)}")

    return "\n".join(parts) if parts else "No API surface information available."
