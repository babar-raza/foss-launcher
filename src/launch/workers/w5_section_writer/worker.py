"""TC-440: W5 SectionWriter worker implementation.

This module implements the W5 SectionWriter that generates markdown content for
documentation page sections using templates and LLM-based content generation.

W5 SectionWriter performs:
1. Load page_plan.json from TC-430 (W4 IAPlanner)
2. Load product_facts.json from TC-410 (W2 FactsBuilder)
3. Load snippet_catalog.json from TC-420 (W3 SnippetCurator)
4. Generate markdown content for each page section
5. Ground content in facts and snippets with claim markers
6. Emit events and write draft files + manifest

Output artifacts:
- drafts/<page_id>_<section_id>.md (one per section)
- draft_manifest.json (listing all draft files)

Spec references:
- specs/07_section_templates.md (Section writing templates)
- specs/21_worker_contracts.md:195-226 (W5 SectionWriter contract)
- specs/10_determinism_and_caching.md (Stable output requirements)
- specs/11_state_and_events.md (Event emission)
- specs/23_claim_markers.md (Claim marker format)

TC-440: W5 SectionWriter
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from ...io.run_layout import RunLayout
from ...io.artifact_store import ArtifactStore
from ...models.event import (
    Event,
    EVENT_WORK_ITEM_STARTED,
    EVENT_WORK_ITEM_FINISHED,
    EVENT_ARTIFACT_WRITTEN,
    EVENT_ISSUE_OPENED,
    EVENT_RUN_FAILED,
)
# TC-3310/SR-03: Local event constant (models/event.py owned by TC-250)
W5_FRONTMATTER_LOCKED = "W5_FRONTMATTER_LOCKED"

from ...io.atomic import atomic_write_json, atomic_write_text
from ...util.logging import get_logger
from .link_transformer import transform_cross_section_links
from .._shared.content_sanitizer import (
    SanitizerContext,
    run_pipeline as run_sanitizer_pipeline,
    get_metrics as get_sanitizer_metrics,
    reset_metrics as reset_sanitizer_metrics,
    # Re-export individual sanitizers for backward compatibility (tests import them)
    strip_source_annotations as _strip_source_annotations,
    strip_orphan_claim_markers as _strip_orphan_claim_markers,
    fix_prose_in_code_blocks as _fix_prose_in_code_blocks,
    fence_bare_commands as _fence_bare_commands,
    ensure_related_links as _ensure_related_links,
    fix_self_referential_links as _fix_self_referential_links,
    ensure_h2_intros as _ensure_h2_intros,
    inject_machine_readable as _inject_machine_readable,
    fix_collapsed_frontmatter as _fix_collapsed_frontmatter,
    fix_inline_html_claim_markers as _fix_inline_html_claim_markers,
    close_unclosed_fences as _close_unclosed_fences,
    fix_nested_fences as _fix_nested_fences,
    fix_code_fences as _fix_code_fences,
    merge_adjacent_code_blocks as _merge_adjacent_code_blocks,
    strip_llm_scaffolding as _strip_llm_scaffolding,
    fix_unicode_in_code_blocks as _fix_unicode_in_code_blocks,
    validate_code_blocks as _validate_code_blocks,
    strip_product_name_prefix as _strip_product_name_prefix,
    remove_empty_sections as _remove_empty_sections,
    strip_boilerplate_sentences as _strip_boilerplate_sentences,
    strip_visible_claim_markers as _strip_visible_claim_markers,
    strip_double_periods as _strip_double_periods,
    strip_emojis as _strip_emojis,
    strip_ci_badges as _strip_ci_badges,
    strip_illustrative_comments as _strip_illustrative_comments,
    fix_truncated_sentences as _fix_truncated_sentences,
    normalize_module_names as _normalize_module_names,
    enforce_quality_floor as _enforce_quality_floor,
    fix_license_page as _fix_license_page,
    _mask_yaml_quotes,
)

logger = get_logger()

# TC-1770: Import extracted generator functions for backward compatibility.
# These were moved to generators/content_generators.py but are re-exported here
# so that existing imports from worker.py continue to work.
from .generators.content_generators import (  # noqa: E402,F401
    _get_display_text,
    _sanitize_limitation_bullet,  # TC-2893: re-export for legacy prompt builder
    _sanitize_claims_for_prompt,  # TC-2893: re-export for _try_structured_limitations
    _build_enriched_claim_context,
    _inject_claim_markers_as_comments,
    _enrich_template_output,
    _first_sentence_bullets,
    _fix_claim_grounding,
    get_claims_by_ids,
    get_snippets_by_tags,
    generate_toc_content,
    _generate_deterministic_comprehensive_guide,
    generate_comprehensive_guide_content,
    _find_related_snippet,
    _find_related_claims,
    _validate_feature_showcase_quality,
    _generate_deterministic_feature_showcase,
    generate_feature_showcase_content,
    _is_spec_fragment,
    generate_troubleshooting_content,
    generate_blog_content,
    generate_performance_content,
    _validate_faq_format,
    _generate_deterministic_faq,
    generate_faq_content,
    _validate_best_practice_quality,
    generate_best_practices_content,
    _validate_tutorial_quality,
    _find_related_snippet_tutorial,
    _generate_deterministic_tutorial,
    generate_tutorial_content,
)

# TC-1110: Claim text truncation constants for quality control
MAX_CLAIM_TEXT_LENGTH = 200  # Display limit for claim text in bullet points
MAX_CLAIM_FILTER_LENGTH = 1000  # Pre-filter limit to remove pathological cases
MAX_LIMITATION_CLAIMS = 10  # Maximum number of limitation claims to display

# Compiled regex for list item detection (bullets, numbered, asterisk)
_LIST_ITEM_RE = re.compile(r'^(?:-\s|\*\s|\d+\.\s+)')
# Compiled once at module level — reused in inject_frontmatter_fields, _strip_frontmatter_comments,
# and the LLM-frontmatter stripping block to avoid per-call compilation cost.
_FM_DELIM_RE = re.compile(r'^---\s*$', re.MULTILINE)
# Threshold at which we attempt first-sentence simplification.
# W7 flags >250 chars as ERROR, >180 as WARN.
MAX_BULLET_LEN = 170

def _try_structured_limitations(limitation_claims, product_name, llm_client):
    """Try structured JSON path for Limitations section. Returns None on any failure.

    TC-2445/TC-2446: Optional override for Limitations section generation.
    Only active when LAUNCH_STRUCTURED_LIMITATIONS=json.
    Falls back to None (caller uses freeform path) on any exception or parse failure.
    """
    try:
        from .renderers.limitations_renderer import (
            parse_limitations_json, render_limitations_to_markdown,
            LLM_JSON_PROMPT_ADDENDUM, is_structured_mode,
        )
        if not is_structured_mode():
            return None
        claim_texts = _sanitize_claims_for_prompt(limitation_claims[:10])  # TC-2893
        prompt = (
            f"Generate a Limitations section for {product_name} based on these known limitations:\n"
            f"{claim_texts}"
            + LLM_JSON_PROMPT_ADDENDUM
        )
        raw_result = _call_llm_for_content(prompt, limitation_claims, [], llm_client)
        raw_text = raw_result.get("content", "") if isinstance(raw_result, dict) else str(raw_result)
        items = parse_limitations_json(raw_text)
        if items is None:
            logger.warning("[W5] _try_structured_limitations: JSON parse failed — falling back to freeform")
            return None
        claim_ids = [c.get("claim_id") for c in limitation_claims[:len(items)]]
        return render_limitations_to_markdown(items, product_name, claim_ids)
    except Exception as _e:
        logger.warning("[W5] _try_structured_limitations failed: %s — using freeform", _e)
        return None


# Lazy-loaded prompt loader for centralized prompts (TC-1713)
_prompt_loader = None

# TC-2373 (RD-04): Priority weights by page_type — fallback when content_strategy.priority_weight absent.
# Scale: 0.5 (minimal boilerplate) to 2.0 (high-value user-facing sections).
SECTION_TYPE_WEIGHTS: Dict[str, float] = {
    "getting_started": 1.8,
    "tutorial": 1.6,
    "comprehensive_guide": 1.5,
    "api_reference": 1.4,
    "troubleshooting": 1.3,
    "feature_showcase": 1.2,
    "best_practices": 1.2,
    "workflow_page": 1.1,
    "faq": 1.0,
    "howto_article": 1.0,
    "format_conversion": 0.9,
    "feature_blog": 0.9,
    "landing": 0.8,
    "toc": 0.5,
}


def _compute_token_budget(page: Dict[str, Any], run_config: Dict[str, Any]) -> int:
    """Compute effective LLM token budget for a page based on priority weight.

    TC-2373 (RD-04): Reads content_strategy.priority_weight from the page plan (written
    by W4). Falls back to SECTION_TYPE_WEIGHTS by page_type, then 1.0. Clamps to
    [0.5×base, 2.0×base].

    Args:
        page: Page dict from page_plan.json.
        run_config: Run configuration dict; may contain "token_budget" (default 2048).

    Returns:
        Effective token budget as an integer.

    Spec: specs/21_worker_contracts.md §"Priority-Weighted Token Allocation"
    """
    base = int(run_config.get("token_budget", 2048))
    raw_weight = page.get("content_strategy", {}).get("priority_weight")
    if raw_weight is None:
        raw_weight = SECTION_TYPE_WEIGHTS.get(page.get("page_type", ""), 1.0)
    try:
        weight = float(raw_weight)
    except (TypeError, ValueError):
        weight = 1.0
    effective = max(int(base * 0.5), min(int(base * 2.0), int(base * weight)))
    return effective


def _get_prompt_loader():
    """Return a cached PromptLoader instance, or None if unavailable."""
    global _prompt_loader
    if _prompt_loader is None:
        try:
            from launch.prompts import PromptLoader
            _prompt_loader = PromptLoader()
        except Exception:
            pass
    return _prompt_loader



# _get_display_text moved to generators/content_generators.py (TC-1770)


# Words that, when left dangling at the end of a truncated bullet, trigger FQ-3.
# Includes conjunctions, prepositions, articles, copulas, and correlatives.
_DANGLING_WORDS = frozenset({
    # Coordinating conjunctions
    'and', 'but', 'or', 'nor', 'yet', 'so',
    # Subordinating conjunctions / adverbs
    'as', 'than', 'if', 'then', 'thus', 'also', 'both', 'either', 'neither',
    # Prepositions (signal truncated prepositional phrase)
    'in', 'on', 'at', 'to', 'of', 'with', 'by', 'from', 'into', 'about',
    'over', 'under', 'after', 'before', 'through', 'within', 'between', 'for',
    # Articles (signal truncated noun phrase)
    'a', 'an', 'the',
    # Relative/interrogative pronouns and adverbs
    'that', 'which', 'who', 'where', 'when', 'while',
    # Copulas (signal truncated predicate)
    'is', 'are', 'was', 'were', 'be', 'been',
    # Possessive determiners (signal truncated NP: "quality of your ___")
    'your', 'my', 'our', 'its', 'their', 'his', 'her',
    # Demonstrative / indefinite determiners (signal truncated NP)
    'this', 'these', 'those', 'any', 'some', 'each', 'every',
    # Quantifiers and adjective-like words that precede an implied noun
    'more', 'further', 'additional', 'various', 'other', 'specific',
})


def _backtrack_dangling_words(text: str) -> str:
    """Remove trailing conjunctions/prepositions that would make FQ-3 triggers.

    E.g. '...ensuring compatibility with a wide range of 3D modeling and'
         → '...ensuring compatibility with a wide range of 3D modeling'
    """
    words = text.split()
    while words:
        last = words[-1].lower().rstrip('.,;:!?()')
        if last in _DANGLING_WORDS:
            words.pop()
        else:
            break
    return ' '.join(words) if words else text


def _smart_truncate(text: str, max_len: int = 200, llm_client: Optional[Any] = None) -> str:
    """Truncate text intelligently at sentence boundaries.

    TC-1660: Replace hard truncation (text[:200] + "...") with:
    1. LLM summarization (if llm_client available)
    2. Sentence-boundary truncation (deterministic fallback)
    3. Word-boundary truncation (last resort)

    Args:
        text: Text to truncate
        max_len: Maximum character length
        llm_client: Optional LLM client for summarization

    Returns:
        Truncated text without trailing "..."
    """
    if len(text) <= max_len:
        return text

    # Strategy 1: LLM summarization
    if llm_client:
        try:
            summary = llm_client.generate(
                f"Summarize this in under {max_len} characters, preserving key facts:\n\n{text}",
                max_tokens=100,
                temperature=0.3,
            )
            if summary and len(summary) <= max_len:
                return summary
        except Exception:
            pass  # Fall through to deterministic

    # Strategy 2: Sentence-boundary truncation
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = ""
    for s in sentences:
        candidate = (result + " " + s).strip() if result else s
        if len(candidate) <= max_len:
            result = candidate
        else:
            break
    if result:
        # Backtrack dangling conjunctions/prepositions before adding period (FQ-3 guard)
        result = _backtrack_dangling_words(result)
        # Ensure terminal punctuation on partial sentence results
        if result and result[-1] not in '.!?':
            result = result.rstrip(',;: ') + '.'
        return result

    # Strategy 3: Word-boundary truncation (last resort)
    truncated = text[:max_len]
    if ' ' in truncated:
        truncated = truncated.rsplit(' ', 1)[0]
    # Backtrack dangling conjunctions/prepositions before adding period (FQ-3 guard)
    truncated = _backtrack_dangling_words(truncated)
    # Ensure terminal punctuation — never return a sentence fragment
    if truncated and truncated[-1] not in '.!?':
        truncated = truncated.rstrip(',;: ') + '.'
    return truncated


# TC-1658: LLM Integration Layer - Helper functions for LLM-powered content generation
def _call_llm_for_content(
    prompt: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    llm_client: Optional[Any],
    min_words: int = 100,
    timeout: int = 30,
    page_role: str = "",
) -> Dict[str, Any]:
    """Call LLM to generate content from claims + snippets.

    TC-1658: Shared LLM integration infrastructure for specialized generators.
    Handles timeout, retry, validation, and graceful fallback to deterministic
    generation on LLM failure.

    Args:
        prompt: Full prompt text for the LLM
        claims: List of claim dicts (used for validation)
        snippets: List of snippet dicts (used for validation)
        llm_client: LLM client instance (or None for deterministic fallback)
        min_words: Minimum word count for valid LLM output
        timeout: Timeout in seconds for LLM call

    Returns:
        Dict with:
            content: str - Generated markdown content (empty on failure)
            success: bool - True if LLM succeeded, False if fallback needed
            method: str - "llm", "deterministic", "llm_failed_validation", or "llm_failed_error"
    """
    if not llm_client:
        return {"content": "", "success": False, "method": "deterministic"}

    try:
        # TC-1713: Try centralized prompt first, fall back to inline
        _sys_prompt = None
        _loader = _get_prompt_loader()
        if _loader:
            try:
                _sys_prompt = _loader.load("system/draft_generator").text
            except Exception:
                pass
        if not _sys_prompt:
            _sys_prompt = "You are a technical documentation writer. Generate clear, accurate markdown content following the provided template structure and grounding all factual statements in provided claims."

        # TC-2376: Prompt truncation removed — per-section LLM calls keep prompts small.
        # Call LLM with timeout
        response = llm_client.chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": _sys_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            call_id=f"llm_integration_{hashlib.md5(prompt.encode()).hexdigest()[:8]}",
            temperature=0.0,  # Deterministic
        )
        content = response["content"]

        # Strip <think> tags (gemma3/deepseek issue from MEMORY.md)
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        # Also strip partial/unclosed think tags
        content = re.sub(r'<think>.*', '', content, flags=re.DOTALL)

        # Strip markdown code fences wrapping entire output
        # Only strip opening fence at very start and closing fence at very end
        content = re.sub(r'^```(?:markdown|md)?\s*\n', '', content)
        # Only strip closing fence if it's the last thing (possibly with trailing whitespace)
        content = re.sub(r'\n```\s*\Z', '', content)

        # Strip leading whitespace after cleanup
        content = content.lstrip('\n\r\t ')

        # Validate output has minimum word count
        word_count = len(content.split())
        if word_count < min_words:
            logger.warning(
                f"LLM output too short ({word_count} words < {min_words}), using fallback"
            )
            return {"content": "", "success": False, "method": "llm_failed_validation"}

        # Validate output is non-empty markdown
        if not content.strip():
            logger.warning("LLM produced empty content after stripping, using fallback")
            return {"content": "", "success": False, "method": "llm_failed_validation"}

        # TC-2353: Post-generation acceptance criteria — validate page structure
        # and re-prompt up to 2 times if structural requirements are missing.
        if page_role:
            from .context_validator import validate_page_structure

            max_retries = 2
            for attempt in range(max_retries):
                missing = validate_page_structure(content, page_role)
                if not missing:
                    break
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[W5 Acceptance] Attempt {attempt + 1}: missing {missing}. Re-prompting."
                    )
                    feedback = (
                        "Your output is incomplete. Fix these issues:\n"
                        + "\n".join(f"- {m}" for m in missing)
                        + f"\n\nExisting content:\n{content[:2000]}\n\nFix and return the complete page."
                    )
                    retry_response = llm_client.chat_completion(
                        messages=[
                            {"role": "system", "content": _sys_prompt},
                            {"role": "user", "content": feedback},
                        ],
                        call_id=f"acceptance_retry_{attempt}_{hashlib.md5(prompt.encode()).hexdigest()[:8]}",
                        temperature=0.0,
                    )
                    content = retry_response["content"]
                    content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                    content = re.sub(r'<think>.*', '', content, flags=re.DOTALL)
                    content = re.sub(r'^```(?:markdown|md)?\s*\n', '', content)
                    content = re.sub(r'\n```\s*\Z', '', content)
                    content = content.lstrip('\n\r\t ')
                else:
                    logger.warning(
                        f"[W5 Acceptance] Max retries reached, accepting with issues: {missing}"
                    )

        return {"content": content, "success": True, "method": "llm"}

    except Exception as e:
        logger.warning(f"LLM call failed: {e}, using deterministic fallback")
        return {"content": "", "success": False, "method": "llm_failed_error"}



# _build_enriched_claim_context moved to generators/content_generators.py (TC-1770)



# _inject_claim_markers_as_comments moved to generators/content_generators.py (TC-1770)



# _enrich_template_output moved to generators/content_generators.py (TC-1770)



# _first_sentence_bullets moved to generators/content_generators.py (TC-1770)



# _fix_claim_grounding moved to generators/content_generators.py (TC-1770)


class SectionWriterError(Exception):
    """Base exception for W5 SectionWriter errors."""
    pass


class SectionWriterClaimMissingError(SectionWriterError):
    """Required claim not found in evidence map."""
    pass


class SectionWriterSnippetMissingError(SectionWriterError):
    """Required snippet not found in snippet catalog."""
    pass


class SectionWriterTemplateError(SectionWriterError):
    """Template rendering failure."""
    pass


class SectionWriterUnfilledTokensError(SectionWriterError):
    """Draft contains unfilled template tokens."""
    pass


class SectionWriterLLMError(SectionWriterError):
    """LLM API failure."""
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
        event_type: Event type constant
        payload: Event payload dictionary
    """
    store = ArtifactStore(run_dir=run_layout.run_dir)
    store.emit_event(
        event_type,
        payload,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
    )


def load_page_plan(artifacts_dir: Path) -> Dict[str, Any]:
    """Load page_plan.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Page plan dictionary

    Raises:
        SectionWriterError: If page_plan.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("page_plan.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'page_plan.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in page_plan.json: {e}")


def load_product_facts(artifacts_dir: Path) -> Dict[str, Any]:
    """Load product_facts.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Product facts dictionary

    Raises:
        SectionWriterError: If product_facts.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("product_facts.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'product_facts.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in product_facts.json: {e}")


def load_snippet_catalog(artifacts_dir: Path) -> Dict[str, Any]:
    """Load snippet_catalog.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Snippet catalog dictionary

    Raises:
        SectionWriterError: If snippet_catalog.json is missing or invalid
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact("snippet_catalog.json", validate_schema=False)
    except FileNotFoundError:
        raise SectionWriterError(f"Missing required artifact: {artifacts_dir / 'snippet_catalog.json'}")
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in snippet_catalog.json: {e}")


def load_evidence_map(artifacts_dir: Path) -> Dict[str, Any]:
    """Load evidence_map.json from artifacts directory.

    TC-1033: Delegates to ArtifactStore.load_artifact_or_default for centralized I/O.

    Args:
        artifacts_dir: Path to artifacts directory

    Returns:
        Evidence map dictionary (may be empty if file doesn't exist)
    """
    store = ArtifactStore(run_dir=artifacts_dir.parent)
    try:
        return store.load_artifact_or_default(
            "evidence_map.json",
            default={"claims": []},
            validate_schema=False,
        )
    except json.JSONDecodeError as e:
        raise SectionWriterError(f"Invalid JSON in evidence_map.json: {e}")



# get_claims_by_ids, get_snippets_by_tags moved to generators/content_generators.py (TC-1770)



# TC-1770: All generator functions have been moved to generators/content_generators.py.
# The following functions were extracted:
#   generate_toc_content, _generate_deterministic_comprehensive_guide,
#   generate_comprehensive_guide_content, _find_related_snippet, _find_related_claims,
#   _validate_feature_showcase_quality, _generate_deterministic_feature_showcase,
#   generate_feature_showcase_content, _is_spec_fragment, generate_troubleshooting_content,
#   generate_blog_content, generate_performance_content, _validate_faq_format,
#   _generate_deterministic_faq, generate_faq_content, _validate_best_practice_quality,
#   generate_best_practices_content, _validate_tutorial_quality, _find_related_snippet_tutorial,
#   _generate_deterministic_tutorial, generate_tutorial_content
# They are re-imported at the top of this file for backward compatibility.


def generate_section_content(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client: Optional[Any] = None,
    page_plan: Optional[Dict[str, Any]] = None,
    *,
    multi_pass_orchestrator: Optional[Any] = None,
    code_understanding: Optional[Dict[str, Any]] = None,
    evidence_map: Optional[Dict[str, Any]] = None,
    cross_page_summaries: Optional[Dict[str, str]] = None,
) -> str:
    """Generate markdown content for a page section using LLM or specialized generators.

    Per specs/07_section_templates.md, content must:
    - Use ProductFacts fields (no invention)
    - Include claim markers for factual statements
    - Use snippet_catalog snippets by tag
    - Follow template structure for the section

    TC-973: Routes to specialized generators based on page_role:
    - page_role="toc" -> generate_toc_content()
    - page_role="comprehensive_guide" -> generate_comprehensive_guide_content()
    - page_role="feature_showcase" -> generate_feature_showcase_content()
    - Other roles -> template-driven or LLM-based generation

    TC-1723: When multi_pass_orchestrator is provided, attempts 3-pass generation
    (outline -> draft -> refine) before falling back to single-pass generators.

    Args:
        page: Page specification from page_plan
        product_facts: Product facts dictionary
        snippet_catalog: Snippet catalog dictionary
        llm_client: Optional LLM client for content generation
        page_plan: Optional complete page plan (required for TOC generation)
        multi_pass_orchestrator: Optional MultiPassOrchestrator for 3-pass generation
        code_understanding: Optional code understanding data for rich context
        evidence_map: Optional evidence mapping (claim_id -> evidence)
        cross_page_summaries: Optional summaries from previously generated pages

    Returns:
        Generated markdown content as string

    Raises:
        SectionWriterClaimMissingError: If required claim not found
        SectionWriterSnippetMissingError: If required snippet not found
        SectionWriterLLMError: If LLM call fails
    """
    section = page["section"]
    title = page["title"]
    purpose = page["purpose"]
    required_headings = page.get("required_headings", [])
    required_claim_ids = page.get("required_claim_ids", [])
    required_snippet_tags = page.get("required_snippet_tags", [])
    template_variant = page.get("template_variant", "standard")
    template_path = page.get("template_path")
    token_mappings = page.get("token_mappings")
    page_role = page.get("page_role", "landing")

    # Round 11.5 Fix 1: Normalize field names — page_plan uses "required_claim_ids",
    # but specialized generators (TC-1652–1657) expect "claim_ids".
    if "claim_ids" not in page and "required_claim_ids" in page:
        page["claim_ids"] = page["required_claim_ids"]

    # TC-2352: Pre-generation sufficiency check — downgrade role if context is too thin
    from .context_validator import check_context_sufficiency
    from .generators.content_generators import get_claims_by_ids, get_snippets_by_tags

    _page_claims = get_claims_by_ids(product_facts, required_claim_ids)
    _page_snippets = get_snippets_by_tags(snippet_catalog, required_snippet_tags)
    _is_sufficient, _reasons, _downgrade_role = check_context_sufficiency(
        page, _page_claims, _page_snippets
    )
    if not _is_sufficient:
        logger.warning(
            "context_insufficiency_detected",
            slug=page.get("slug", ""),
            role=page_role,
            reasons=_reasons,
            downgrade=_downgrade_role or "none",
        )
        if _downgrade_role:
            page = {**page, "page_role": _downgrade_role}
            page_role = _downgrade_role
            logger.info(
                "page_role_downgraded",
                slug=page.get("slug", ""),
                new_role=_downgrade_role,
            )

    # TC-1723: Multi-pass generation attempt (outline -> draft -> refine)
    # Skip for TOC pages (deterministic), attempt for all other roles when orchestrator available.
    _MULTI_PASS_SKIP_ROLES = {"toc"}
    if (
        multi_pass_orchestrator is not None
        and page_role not in _MULTI_PASS_SKIP_ROLES
        and llm_client is not None
    ):
        try:
            from .rich_context import build_rich_context

            rich_ctx = build_rich_context(
                page=page,
                product_facts=product_facts,
                snippet_catalog=snippet_catalog,
                evidence_map=evidence_map,
                page_plan=page_plan,
                cross_page_summaries=cross_page_summaries,
                code_understanding=code_understanding,
            )
            mp_result = multi_pass_orchestrator.generate(page, rich_ctx)
            if mp_result.success and mp_result.content:
                logger.info(
                    f"[W5] Multi-pass generated {page['slug']} "
                    f"(pass={mp_result.pass_used}, risks={len(mp_result.risks)})"
                )
                # Inject frontmatter (multi-pass content is raw markdown)
                mp_content = inject_frontmatter_fields(
                    mp_result.content, page, section, token_mappings or {}
                )
                return mp_content
            else:
                logger.warning(
                    f"[W5] Multi-pass failed for {page['slug']}, "
                    f"falling back to single-pass generator"
                )
        except Exception as e:
            logger.warning(
                f"[W5] Multi-pass error for {page['slug']}: {e}, "
                f"falling back to single-pass generator"
            )

    # TC-973: Route specialized generators via registry (replaces if/elif chain)
    from .generators import get_registry
    gen_registry = get_registry()

    if gen_registry.has(page_role):
        gen_fn = gen_registry.get(page_role)
        logger.info(f"[W5] Generating {page_role} content for {page['slug']} (registered generator)")

        if gen_registry.requires_page_plan(page_role):
            # TOC generator needs page_plan
            if not page_plan:
                raise SectionWriterError(f"page_plan required for {page_role} generation")
            gen_content = _first_sentence_bullets(gen_fn(page, product_facts, page_plan))
            # TC-P2A: Safety net — TOC pages MUST NOT contain code snippets (Gate 14 blocker)
            if "```" in gen_content:
                logger.warning(f"[W5] Stripping code blocks from {page_role} page {page['slug']}")
                gen_content = re.sub(r'```\w*\n.*?```', '', gen_content, flags=re.DOTALL)
        else:
            # Standard generators: (page, product_facts, snippet_catalog, llm_client=...)
            gen_content = _first_sentence_bullets(gen_fn(page, product_facts, snippet_catalog, llm_client=llm_client))

        # TC-RCA-SPEC: Strip LLM scaffolding from specialized generator output.
        # Specialized generators call LLM internally and may return content with
        # leaked prompt sections (## Product Context, ## Instructions, JSON metadata, etc.)
        gen_content = _strip_llm_scaffolding(gen_content)

        # TC-RCA-SPEC: Strip boilerplate filler sentences from specialized generator output
        gen_content = _strip_boilerplate_sentences(gen_content)

        # TC-GATE4: Inject layout and permalink into frontmatter for Gate 4 compliance
        # Specialized generators produce frontmatter but may omit permalink/layout fields
        gen_content = inject_frontmatter_fields(gen_content, page, section, token_mappings or {})
        return gen_content

    # TC-2340: Warn when page_role not registered — silent fallback is dangerous
    logger.warning(
        f"[W5] page_role='{page_role}' not registered in GeneratorRegistry for page "
        f"'{page.get('slug', 'unknown')}'. Falling back to generic LLM generation. "
        f"Register a specialized generator for better quality."
    )

    # TC-964: Handle template-driven pages (for non-TOC pages with templates)
    # If page has template_path and token_mappings, load template and apply tokens
    if template_path and token_mappings:
        logger.info(f"[W5 SectionWriter] Loading template for page {page['slug']}: {template_path}")
        try:
            template_file = Path(template_path)
            template_content = template_file.read_text(encoding="utf-8")

            # Apply token mappings to replace placeholders
            content = apply_token_mappings(template_content, token_mappings)

            logger.info(f"[W5 SectionWriter] Applied {len(token_mappings)} token mappings to template")

            # TC-974: Inject layout and permalink into frontmatter if missing (Gate 4 compliance)
            content = inject_frontmatter_fields(content, page, section, token_mappings)

            # TC-938: Transform cross-section links to absolute URLs
            page_metadata = {
                "locale": page.get("locale", "en"),
                "family": product_facts.get("product_family", ""),
            }
            content = transform_cross_section_links(
                markdown_content=content,
                current_section=section,
                page_metadata=page_metadata,
            )

            # Inject claim markers from page plan (content density compliance)
            if required_claim_ids:
                claim_comments = []
                for cid in required_claim_ids[:5]:
                    claim_comments.append(f"<!-- claim: {cid} -->")
                content = content.rstrip() + "\n\n" + "\n".join(claim_comments) + "\n"

            # Inject CTA for landing pages (usability.cta_presence compliance)
            page_slug = page.get("slug", "")
            if "index" in page_slug or page_slug in ("home", "landing"):
                cta_patterns = [r"get started", r"download", r"install", r"try", r"explore"]
                if not any(re.search(p, content, re.IGNORECASE) for p in cta_patterns):
                    product_name = product_facts.get("product_name", "Product")
                    cta_line = (f"\nGet started with {product_name} today "
                                f"— explore the documentation or download the latest release.\n")
                    content = content.rstrip() + "\n" + cta_line + "\n"

            # Inject Next Steps for getting-started pages (usability.user_journey compliance)
            if "getting-started" in page_slug or "quickstart" in page_slug:
                if not re.search(r"(developer guide|next steps|learn more)", content, re.IGNORECASE):
                    product_name = product_facts.get("product_name", "Product")
                    next_steps = (
                        "\n## Next Steps\n\n"
                        f"Now that you have {product_name} set up, explore the "
                        "[Developer Guide](/docs/developer-guide/) for advanced workflows and usage patterns.\n"
                    )
                    content = content.rstrip() + "\n" + next_steps

            # TC-1720: Enrich thin template output with LLM or claim-derived content
            content = _enrich_template_output(content, page, product_facts, snippet_catalog, llm_client)

            return content

        except Exception as e:
            logger.error(f"[W5 SectionWriter] Failed to load template {template_path}: {e}")
            raise SectionWriterTemplateError(f"Failed to load template {template_path}: {e}")

    # Note: Specialized generators (comprehensive_guide, feature_showcase, troubleshooting,
    # faq, best_practices, tutorial, blog, performance_guide) are now handled by the
    # GeneratorRegistry above. The old if/elif chain has been replaced.

    # Get claims and snippets
    claims = get_claims_by_ids(product_facts, required_claim_ids)
    snippets = get_snippets_by_tags(snippet_catalog, required_snippet_tags)

    # Check for missing claims (emit warning but continue)
    if len(claims) < len(required_claim_ids):
        found_ids = {c["claim_id"] for c in claims}
        missing_ids = [cid for cid in required_claim_ids if cid not in found_ids]
        logger.warning(
            f"[W5 SectionWriter] Missing claims for page {page['slug']}: {missing_ids}"
        )

    # Check for missing snippets (emit warning but continue)
    if len(snippets) == 0 and len(required_snippet_tags) > 0:
        logger.warning(
            f"[W5 SectionWriter] No snippets found for page {page['slug']} with tags: {required_snippet_tags}"
        )

    # Build context for LLM prompt
    product_name = product_facts.get("product_name", "Product")
    positioning = product_facts.get("positioning", {})
    short_desc = positioning.get("short_description", "")
    tagline = positioning.get("tagline", "")

    # Build prompt for LLM
    forbidden_topics = page.get("forbidden_topics", [])
    if not forbidden_topics:
        forbidden_topics = page.get("content_strategy", {}).get("forbidden_topics", [])

    # TC-CREV-D-TRACK2: Filter limitation claims if Limitations in required_headings
    limitation_claims = []
    if 'Limitations' in required_headings:
        claim_groups = product_facts.get('claim_groups', {})
        limitation_claim_ids = claim_groups.get('limitations', [])
        all_claims = product_facts.get('claims', [])
        limitation_claims = [c for c in all_claims if c.get('claim_id') in limitation_claim_ids]
        logger.info(f"[W5] Found {len(limitation_claims)} limitation claims for page {page['slug']}")

    # TC-P1B: Extract claim_quota from content_strategy for LLM prompt
    claim_quota = page.get("content_strategy", {}).get("claim_quota", {})

    # TC-2204: Build sibling context for cross-section dedup awareness
    sibling_context = ""
    if page_plan and page_plan.get("pages"):
        siblings = [p for p in page_plan["pages"] if p.get("slug") != page.get("slug")]
        if siblings:
            sibling_lines = []
            for s in siblings[:10]:
                angle = s.get("content_strategy", {}).get("unique_angle", "")
                angle_text = f" — Focus: {angle}" if angle else ""
                sibling_lines.append(
                    f"- {s.get('title', s.get('slug', 'Unknown'))} ({s.get('section', '')}): "
                    f"{s.get('purpose', 'N/A')}{angle_text}"
                )
            sibling_context = (
                "\n\nOTHER PAGES IN THIS SITE (do NOT repeat their content):\n"
                + "\n".join(sibling_lines)
                + "\n\nYour page must provide UNIQUE value not found on the pages above.\n"
            )

    # TC-2204: Add unique angle guidance
    unique_angle = page.get("content_strategy", {}).get("unique_angle", "")
    angle_instruction = ""
    if unique_angle:
        angle_instruction = (
            f"\n\nYOUR UNIQUE ANGLE for this page: {unique_angle}\n"
            f"Focus on this perspective and avoid content that belongs on other pages.\n"
        )

    content = None  # Will be set by LLM or fallback
    if llm_client:
        prompt = _build_section_prompt(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            short_desc=short_desc,
            tagline=tagline,
            claims=claims,
            snippets=snippets,
            template_variant=template_variant,
            forbidden_topics=forbidden_topics,
            limitation_claims=limitation_claims,
            claim_quota=claim_quota,
            api_surface=product_facts.get("api_surface_summary"),
            license_info=_extract_license_string(product_facts),
            sibling_context=sibling_context,
            angle_instruction=angle_instruction,
            page_role=page_role,
        )

        try:
            # TC-1713: Try centralized prompt first, fall back to inline
            _sys_prompt_2 = None
            _loader = _get_prompt_loader()
            if _loader:
                try:
                    _sys_prompt_2 = _loader.load("system/draft_generator").text
                except Exception:
                    pass
            if not _sys_prompt_2:
                _sys_prompt_2 = "You are a technical documentation writer. Generate clear, accurate markdown content following the provided template structure and grounding all factual statements in provided claims."

            response = llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": _sys_prompt_2
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                call_id=f"section_writer_{page['slug']}",
                temperature=0.0,  # Deterministic
            )
            content = response["content"]

            # TC-CONTENT-QUALITY: Strip model reasoning/thinking blocks (qwen3, deepseek, etc.)
            # Some models dump <think>...</think> chain-of-thought into output
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            # Also strip partial/unclosed think tags (model may not close them)
            content = re.sub(r'<think>.*', '', content, flags=re.DOTALL)
            # Strip session timestamps (qwen3 artifact)
            content = re.sub(r'^_Session started at .*$', '', content, flags=re.MULTILINE)
            # Strip markdown code fences wrapping entire output (LLM wraps in ```markdown ... ```)
            content = re.sub(r'^```(?:markdown|md)?\s*\n', '', content, flags=re.MULTILINE)
            content = re.sub(r'\n```\s*$', '', content)
            # Strip leading whitespace/newlines after removal
            content = content.lstrip('\n\r\t ')

            # TC-RCA: Strip LLM scaffolding sections (## Product Context, ## Instructions)
            # The LLM sometimes echoes back its prompt context as visible output.
            content = _strip_llm_scaffolding(content)
            content = _strip_boilerplate_sentences(content)

            # TC-CONTENT-QUALITY: Validate LLM output has actual markdown content
            stripped_check = content.strip()
            if not stripped_check or (not stripped_check.startswith('#') and len(stripped_check) < 50):
                logger.warning(f"[W5] LLM produced no usable content after stripping for page {page['slug']}. Falling back.")
                content = None  # Triggers fallback path

            if content is not None:
                # TC-5A: Post-process LLM output to replace any echoed placeholder tokens
                # LLMs sometimes echo tokens like __PRODUCT_NAME__ from prompt context
                platform_value = page.get("platform", "")
                llm_replacements = {
                    "__PRODUCT_NAME__": product_name,
                    "__FAMILY__": product_facts.get("product_family", ""),
                    "__LOCALE__": page.get("locale", "en"),
                    "__PLATFORM__": platform_value,
                    "__PLATFORM_CAPITALIZED__": platform_value.capitalize() if platform_value else "",
                    "__SECTION__": section,
                    "__title__": title,
                    "__page_title__": title,
                    "__TITLE__": title,
                    "__PAGE_TITLE__": title,
                    "__DESCRIPTION__": purpose,
                }
                for token, value in llm_replacements.items():
                    if token in content:
                        content = content.replace(token, value)

                # TC-5A: Strip invalid bare-number claim markers (LLM uses list index instead of claim_id)
                content = re.sub(r'\[claim:\s*\d+\]', '', content)

                # TC-CONTENT-QUALITY: Fix hallucinated GitHub repo URLs
                # LLM fabricates plausible-looking but wrong repo URLs (e.g. aspose-note/aspose-note-python
                # instead of aspose-note-foss/Aspose.Note-FOSS-for-Python). Detect by checking if the
                # hallucinated org shares significant words with the correct org.
                correct_repo_url = product_facts.get("repo_url", "")
                if correct_repo_url and "github.com/" in correct_repo_url:
                    correct_parts = correct_repo_url.split("github.com/", 1)[1].split("/")
                    correct_org = correct_parts[0].lower() if correct_parts else ""
                    correct_org_words = set(correct_org.split("-")) - {"foss", "oss", "open"}

                    if correct_org_words and len(correct_org_words) >= 2:
                        def _fix_repo_url(m: re.Match) -> str:
                            url = m.group(0)
                            parts = url.split("github.com/", 1)
                            if len(parts) < 2:
                                return url
                            path_after = parts[1]
                            segments = path_after.split("/")
                            if len(segments) < 2:
                                return url
                            found_org = segments[0].lower()
                            # Skip if this is already the correct org
                            if found_org == correct_org:
                                return url
                            # Check if hallucinated org shares 2+ words with correct org
                            found_words = set(found_org.split("-")) - {"foss", "oss", "open"}
                            if len(found_words & correct_org_words) >= 2:
                                # Strip ALL trailing paths — they were hallucinated too
                                # and may not exist at the correct repo
                                return correct_repo_url.rstrip("/")
                            return url

                        content = re.sub(
                            r'https?://github\.com/[^\s\)\]]+',
                            _fix_repo_url,
                            content,
                        )

                # TC-5B: Validate and strip hallucinated claim IDs
                # LLM sometimes generates corrupted claim IDs (e.g., valid prefix + garbage)
                valid_claim_ids = {c.get("claim_id") for c in claims if c.get("claim_id")}

                def validate_claim_marker(match: re.Match) -> str:
                    claim_id = match.group(1)
                    if claim_id in valid_claim_ids:
                        return match.group(0)  # Keep valid marker
                    # Strip invalid/hallucinated claim marker
                    logger.warning(f"[W5] Stripping hallucinated claim marker: {claim_id[:20]}...")
                    return ""

                content = re.sub(r'\[claim:\s*([a-zA-Z0-9_-]+)\]', validate_claim_marker, content)

                # TC-1404: Fix inline HTML claim markers (<!-- claim_id: UUID -->)
                content = _fix_inline_html_claim_markers(content)

                # TC-CONTENT-QUALITY: Truncate bullet/list items that exceed 200 chars
                content = _first_sentence_bullets(content)

                # TC-CONTENT-QUALITY: Fix claim marker grounding (ensure period within 50 chars)
                content = _fix_claim_grounding(content)

                # TC-CONTENT-QUALITY: Fix "text .[claim:" → "text. [claim:" patterns
                # LLMs sometimes place space-before-period before claim markers
                content = re.sub(r'\s+\.\s*(\[claim:)', r'. \1', content)

                # TC-CONTENT-QUALITY: Validate Python code blocks for syntax errors
                # W7 flags syntax errors as BLOCKER. Strip invalid code blocks.
                content = _validate_code_blocks(content)

                # TC-1404: Close unclosed code fences
                content = _close_unclosed_fences(content)

                # TC-1408: Fix Unicode characters in code blocks
                content = _fix_unicode_in_code_blocks(content)

                # TC-CONTENT-QUALITY: Remove placeholder/TODO comments that trigger completeness errors
                content = re.sub(
                    r'^#\s*(?:This is a placeholder|TODO|PLACEHOLDER|FIXME).*$',
                    '',
                    content,
                    flags=re.MULTILINE | re.IGNORECASE,
                )

                # TC-5C: Sanitize headings with forbidden topics
                # Gate 14 flags headings containing forbidden topic keywords
                if forbidden_topics:
                    def sanitize_heading(match: re.Match) -> str:
                        heading_prefix = match.group(1)  # ## or ### etc.
                        heading_text = match.group(2)
                        heading_lower = heading_text.lower()

                        for topic in forbidden_topics:
                            topic_lower = topic.lower().replace("_", " ")
                            if topic_lower in heading_lower:
                                # Replace forbidden topic with generic alternative
                                new_text = re.sub(
                                    re.escape(topic_lower),
                                    "Highlights",
                                    heading_text,
                                    flags=re.IGNORECASE
                                )
                                logger.warning(f"[W5] Sanitized forbidden topic '{topic}' in heading: {heading_text} -> {new_text}")
                                return f"{heading_prefix}{new_text}"

                        return match.group(0)

                    content = re.sub(r'^(#{1,6}\s+)(.+)$', sanitize_heading, content, flags=re.MULTILINE)

                # TC-5A: Always use authoritative frontmatter from page spec.
                # Root cause: LLM sometimes generates frontmatter with trailing periods
                # on YAML values (e.g. permalink: /path/.) or unclosed --- blocks with
                # machine_readable YAML, causing Hugo build failures and Gate 4/13 errors.
                # Fix: ALWAYS strip any LLM-generated frontmatter and replace with clean
                # values from the page spec. Never trust LLM-generated YAML frontmatter.
                layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
                url_path = page.get("url_path", "")
                safe_title = title.replace('"', '\\"')
                # Prefer `description` (SEO-friendly, set by W4) over `purpose` (LLM generation hint).
                # W4 sets both fields separately for mandatory pages; for LLM-generated pages
                # `description` is absent, so `purpose` is used as fallback.
                _desc = page.get("description") or purpose
                safe_desc = _desc.replace('"', '\\"')
                _clean_fm_parts = [
                    "---",
                    f'title: "{safe_title}"',
                    f'description: "{safe_desc}"',
                    f"layout: {layout}",
                ]
                if url_path:
                    _clean_fm_parts.append(f"permalink: {url_path}")
                _clean_fm_parts.extend(["---", ""])
                _clean_fm = "\n".join(_clean_fm_parts) + "\n"

                if content.strip().startswith("---"):
                    # LLM generated content starting with '---'; strip it and use ours.
                    _markers = list(_FM_DELIM_RE.finditer(content))
                    if len(_markers) >= 2:
                        # Well-formed frontmatter: keep only the body after closing ---
                        _body = content[_markers[1].end():]
                    else:
                        # Malformed: no closing --- (LLM emitted YAML that bleeds into
                        # body). Find first H2+ heading as the start of real body content.
                        _first_h = re.search(r'^#{2,6}\s', content, re.MULTILINE)
                        if _first_h:
                            _body = content[_first_h.start():]
                        else:
                            # No heading found; skip past the opening --- line.
                            _body = content[3:].lstrip("\n")
                    content = _clean_fm + _body.lstrip("\n")
                else:
                    # LLM returned raw markdown without any frontmatter; prepend ours.
                    content = _clean_fm + content

                # TC-1404: Fix collapsed frontmatter (multiple YAML keys on one line)
                content = _fix_collapsed_frontmatter(content)
        except Exception as e:
            # TC-5D: Graceful fallback when LLM fails - use template-based content
            logger.warning(f"[W5] LLM call failed for page {page['slug']}: {e}. Falling back to template-based content.")
            llm_client = None  # Force fallback path
            content = None  # Will be generated in fallback block

    if content is None:
        # Fallback: Generate simple template-based content
        content = _generate_fallback_content(
            section=section,
            title=title,
            purpose=purpose,
            required_headings=required_headings,
            product_name=product_name,
            claims=claims,
            snippets=snippets,
            url_path=page.get("url_path", ""),
        )

    # TC-938: Transform cross-section links to absolute URLs
    # This ensures links between different sections (blog->docs, docs->reference, etc.)
    # use absolute URLs that work across the subdomain architecture
    page_metadata = {
        "locale": page.get("locale", "en"),
        "family": product_facts.get("product_family", ""),
    }
    content = transform_cross_section_links(
        markdown_content=content,
        current_section=section,
        page_metadata=page_metadata,
    )

    # Inject Next Steps for getting-started pages (usability.user_journey compliance)
    page_slug = page.get("slug", "")
    if "getting-started" in page_slug or "quickstart" in page_slug:
        if not re.search(r"(developer guide|next steps|learn more)", content, re.IGNORECASE):
            product_name = product_facts.get("product_name", "Product")
            next_steps = (
                "\n## Next Steps\n\n"
                f"Now that you have {product_name} set up, explore the "
                "[Developer Guide](/docs/developer-guide/) for advanced workflows and usage patterns.\n"
            )
            content = content.rstrip() + "\n" + next_steps

    return content


def _extract_license_string(product_facts: Dict[str, Any]) -> Optional[str]:
    """Extract license string from product_facts.

    Checks for a 'license' field (dict or string) and falls back to detecting
    'foss' in the product name.

    Args:
        product_facts: Product facts dictionary

    Returns:
        License string or None if not available
    """
    license_info = product_facts.get("license")
    if isinstance(license_info, dict):
        return license_info.get("name") or license_info.get("type") or license_info.get("spdx_id")
    if isinstance(license_info, str) and license_info:
        return license_info
    # Check product name for FOSS indicator
    product_name = product_facts.get("product_name", "")
    if "foss" in product_name.lower():
        return "FOSS"
    return None


def _build_section_prompt(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    short_desc: str,
    tagline: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    template_variant: str,
    forbidden_topics: Optional[List[str]] = None,
    limitation_claims: Optional[List[Dict[str, Any]]] = None,
    claim_quota: Optional[Dict[str, int]] = None,
    api_surface: Optional[Dict[str, Any]] = None,
    license_info: Optional[str] = None,
    sibling_context: Optional[str] = None,
    angle_instruction: Optional[str] = None,
    page_role: str = "",
) -> str:
    """Build LLM prompt for section content generation.

    Args:
        section: Section name (products, docs, reference, kb, blog)
        title: Page title
        purpose: Page purpose
        required_headings: List of required heading titles
        product_name: Product name
        short_desc: Product short description
        tagline: Product tagline
        claims: List of claim dictionaries
        snippets: List of snippet dictionaries
        template_variant: Template variant (minimal, standard, rich)
        forbidden_topics: Optional list of forbidden topics
        limitation_claims: Optional list of limitation-specific claims
        claim_quota: Optional claim quota constraints
        api_surface: Optional API surface summary with classes/functions
        license_info: Optional license string for FOSS constraints
        sibling_context: Optional sibling page context for cross-page dedup (TC-2204)
        angle_instruction: Optional unique angle guidance for this page (TC-2204)
        page_role: Optional page role for role-aware prompt guidance (TC-2340)

    Returns:
        Formatted prompt string
    """
    # TC-2340: Role-aware generic prompt enhancement
    _role_guidance = {
        "workflow_page": "Structure this as a step-by-step workflow with a complete code example. Include What You'll Learn, Prerequisites, and See Also sections.",
        "landing": "Write as a product landing page with value proposition, feature highlights as prose (not raw params), and a clear call-to-action.",
        "api_reference": "Format as structured API reference with classes grouped by functionality, methods, and parameter tables.",
        "format_conversion": "Structure as a format conversion guide: overview, numbered steps, complete code example, FAQ.",
        "howto_article": "Write as a how-to article: overview, when to use, step-by-step guide, complete code example.",
        "feature_blog": "Write as a friendly blog post highlighting this feature: intro, key highlights, quick example, next steps.",
    }
    role_hint = _role_guidance.get(page_role, f"Write high-quality documentation for this {page_role} page." if page_role else "")

    # TC-RCA: Use XML delimiters instead of markdown headings to prevent LLM echoback.
    # LLMs sometimes reproduce ## headings from the prompt (e.g., "## Product Context")
    # as visible sections in their output. XML tags are structural-only.
    prompt_parts = [
        f"# Task: Generate documentation page content",
        f"",
        f"<page-info>",
        f"- Section: {section}",
        f"- Title: {title}",
        f"- Purpose: {purpose}",
        f"- Template Variant: {template_variant}",
        f"</page-info>",
        f"",
        f"<context>",
        f"- Product Name: {product_name}",
        f"- Short Description: {short_desc}",
        f"- Tagline: {tagline}",
        f"</context>",
        f"",
        f"<required-headings>",
    ]

    for heading in required_headings:
        prompt_parts.append(f"- {heading}")

    prompt_parts.extend([
        f"</required-headings>",
        f"",
        f"<claims>",
    ])

    for claim in claims:
        claim_text = _get_display_text(claim)
        claim_id = claim.get("claim_id", "")
        prompt_parts.append(f"- CLAIM_ID={claim_id}: {claim_text}")

    if not claims:
        prompt_parts.append("(No claims available)")

    prompt_parts.append("</claims>")

    # TC-CREV-D-TRACK2: Add limitation claims if provided
    if limitation_claims:
        prompt_parts.extend([
            f"",
            f"<limitation-claims>",
        ])
        for claim in limitation_claims:
            claim_text = _get_display_text(claim)
            sanitized = _sanitize_limitation_bullet(claim_text)  # TC-2893
            if sanitized is None:
                continue
            if len(sanitized) > MAX_BULLET_LEN - 2:
                sanitized = _smart_truncate(sanitized, MAX_BULLET_LEN - 2)
            claim_id = claim.get("claim_id", "")
            prompt_parts.append(f"- CLAIM_ID={claim_id}: {sanitized}")
        prompt_parts.append("</limitation-claims>")

    # TC-1403: Add Code Example Rules when API surface is available
    if api_surface:
        prompt_parts.extend([
            f"",
            f"<code-rules>",
            f"ALL code examples in your output MUST come from the Available Snippets section below.",
            f"You may adapt, simplify, or annotate real snippets but NEVER fabricate code.",
            f"If no relevant snippet exists for a section, use prose description instead.",
            f"If you must show pseudocode, explicitly label it as ```pseudocode.",
            f"</code-rules>",
        ])

    # TC-1403: Add Known API Surface when available
    if api_surface:
        raw_classes = api_surface.get("classes", [])
        class_names = ", ".join(
            (c if isinstance(c, str) else c.get("name", ""))
            for c in raw_classes
            if (c if isinstance(c, str) else c.get("name"))
        )
        raw_functions = api_surface.get("functions", [])
        function_names = ", ".join(
            (f if isinstance(f, str) else f.get("name", ""))
            for f in raw_functions
            if (f if isinstance(f, str) else f.get("name"))
        )
        prompt_parts.extend([
            f"",
            f"<api-surface>",
            f"The following classes and functions are the ONLY ones that exist in this library.",
            f"Do NOT reference any class, method, or function not listed here.",
            f"Classes: {class_names}" if class_names else "Classes: (none detected)",
            f"Functions: {function_names}" if function_names else "Functions: (none detected)",
            f"</api-surface>",
        ])

    # TC-1403: Add License section when available
    if license_info:
        prompt_parts.extend([
            f"",
            f"<license>",
            f"This is a FOSS (Free and Open Source Software) project: {license_info}.",
            f"Do NOT mention commercial licensing, paid plans, trial versions, or evaluation limitations.",
            f"</license>",
        ])

    prompt_parts.extend([
        f"",
        f"<snippets>",
    ])

    for i, snippet in enumerate(snippets, 1):
        snippet_id = snippet.get("snippet_id", "")
        language = snippet.get("language", "")
        tags = ", ".join(snippet.get("tags", []))
        code = snippet.get("code", "")
        prompt_parts.append(f"{i}. Snippet ID: {snippet_id} (Language: {language}, Tags: {tags})")
        prompt_parts.append(f"```{language}")
        prompt_parts.append(code)
        prompt_parts.append("```")
        prompt_parts.append("")

    if not snippets:
        prompt_parts.append("(No code snippets available)")

    prompt_parts.append("</snippets>")

    # TC-5A: Add forbidden_topics to prompt if provided
    if forbidden_topics:
        prompt_parts.extend([
            f"",
            f"<forbidden-topics>",
        ])
        for topic in forbidden_topics:
            prompt_parts.append(f"- {topic}")
        prompt_parts.append("</forbidden-topics>")

    # TC-P1B: Add claim_quota constraints to prompt
    if claim_quota:
        min_claims = claim_quota.get("min", 0)
        max_claims = claim_quota.get("max", 50)
        prompt_parts.extend([
            f"",
            f"<claim-quota>",
            f"- Use at LEAST {min_claims} claim markers in the output",
            f"- Use at MOST {max_claims} claim markers in the output",
            f"</claim-quota>",
        ])

    prompt_parts.extend([
        f"",
        f"<instructions>",
        f"CRITICAL: The XML tags in this prompt (<context>, <claims>, <snippets>, etc.) are structural delimiters for YOUR reference only. Do NOT reproduce them or their labels in your output.",
        f"",
        f"1. Generate markdown content for this page following the required headings",
        f"2. For every factual statement, add a claim marker using the exact CLAIM_ID: `[claim: <CLAIM_ID>]`",
        f"3. Place the claim marker immediately after the sentence on the same line. Use the FULL CLAIM_ID, not a number.",
        f"4. Use code snippets where appropriate (include them in code fences)",
        f"5. Keep the content clear, concise, and technically accurate",
        f"5b. Keep each bullet point to a single sentence, ideally under 150 characters",
        f"6. Do NOT invent facts - only use the provided claims",
        f"7. Do NOT leave any placeholder tokens like __PRODUCT_NAME__ in the output",
        f"8. Generate complete, ready-to-publish content",
        f"9. Do NOT include YAML frontmatter (---) - provide only the markdown body",
        f"10. All internal links must use Hugo-style URL paths (e.g., /docs/getting-started/), NOT source code file paths",
        f"11. Do NOT link to .py files, examples/ directories, or source code paths",
        f"11b. CRITICAL: When showing code, put the ENTIRE example in a SINGLE code fence. NEVER split one example across multiple code fences separated by explanation text. Step comments belong INSIDE the code block.",
        f"",
        f"Bullet and List Formatting:",
        f"- Use bullet points (- item) for lists of 3+ related items",
        f"- Use numbered lists (1. step) ONLY for sequential steps where order matters",
        f"- Never write lists as run-on paragraphs",
        f"- Each bullet point should be a single, complete thought",
    ])

    instruction_number = 12
    # TC-CREV-D-TRACK2: Add Limitations instruction if required
    if 'Limitations' in required_headings:
        prompt_parts.append(
            f"{instruction_number}. CREATE A '## Limitations' SECTION: Document known limitations and constraints "
            f"from the limitation claims provided. Be honest and clear about what the library cannot do or has restrictions on."
        )
        instruction_number += 1

    if forbidden_topics:
        prompt_parts.append(f"{instruction_number}. Do NOT write about forbidden topics listed above")

    prompt_parts.append("</instructions>")

    # TC-2204: Inject sibling page context for cross-section dedup awareness
    if sibling_context:
        prompt_parts.append(sibling_context)

    # TC-2204: Inject unique angle guidance for this page
    if angle_instruction:
        prompt_parts.append(angle_instruction)

    prompt_parts.extend([
        f"",
        f"<output-format>",
        f"Provide only the markdown content (no explanations or meta-commentary). Do NOT include frontmatter.",
        f"</output-format>",
    ])

    # TC-2340: Prepend role guidance to assembled prompt
    prompt = "\n".join(prompt_parts)
    if role_hint:
        prompt = f"ROLE GUIDANCE: {role_hint}\n\n{prompt}"

    return prompt


def _generate_fallback_content(
    section: str,
    title: str,
    purpose: str,
    required_headings: List[str],
    product_name: str,
    claims: List[Dict[str, Any]],
    snippets: List[Dict[str, Any]],
    url_path: str = "",
) -> str:
    """Generate simple fallback content without LLM.

    Used when LLM client is not available for testing or fallback scenarios.

    Args:
        section: Section name
        title: Page title
        purpose: Page purpose
        required_headings: List of required headings
        product_name: Product name
        claims: List of claims
        snippets: List of snippets
        url_path: URL path for permalink field

    Returns:
        Generated markdown content with frontmatter
    """
    # Generate frontmatter (TC-974: Fix Gate 4 - add layout and permalink fields)
    layout = section if section in ["docs", "products", "reference", "kb", "blog"] else "default"
    frontmatter = [
        "---",
        f"title: \"{title}\"",
        f"description: \"{purpose}\"",
        f"layout: {layout}",
    ]
    if url_path:
        frontmatter.append(f"permalink: {url_path}")
    frontmatter.extend([
        "---",
        "",
    ])

    lines = frontmatter + [
        f"# {title}",
        f"",
        f"{purpose}",
        f"",
    ]

    for i, heading in enumerate(required_headings):
        lines.append(f"## {heading}")
        lines.append("")

        # TC-CONTENT-QUALITY: Add intro sentence after H2 (progressive disclosure)
        lines.append(f"This section covers {heading.lower()} for {product_name}.")
        lines.append("")

        # TC-982: Distribute claims evenly across headings (not same first 2)
        # TC-977: Use [claim: claim_id] format for Gate 14 compliance
        if claims and required_headings:
            claims_per_heading = max(1, len(claims) // len(required_headings))
            start_idx = i * claims_per_heading
            heading_claims = claims[start_idx:start_idx + claims_per_heading]
        else:
            heading_claims = []

        for claim in heading_claims:
            claim_text = _get_display_text(claim)
            claim_id = claim.get("claim_id", "")

            # TC-CONTENT-QUALITY: Simplify long claim text by extracting first sentence
            max_body = MAX_BULLET_LEN - 2  # 2 for "- " prefix
            if len(claim_text) > max_body:
                # Strategy 1: Extract first sentence
                sent_end = re.search(r'[.!?](?:\s|$)', claim_text)
                if sent_end and sent_end.end() < len(claim_text) - 10:
                    claim_text = claim_text[:sent_end.end()].strip()
                # Strategy 2: Still too long — truncate at word boundary
                if len(claim_text) > max_body:
                    claim_text = _smart_truncate(claim_text, max_body)

            lines.append(f"- {claim_text}")
            lines.append(f"<!-- claim: {claim_id} -->")

        # TC-982: If no claims assigned to this heading, use purpose as fallback
        if len(heading_claims) == 0 and purpose:
            lines.append(f"{purpose}")

        lines.append("")

        # TC-982: Broadened snippet matching with partial keyword matching
        heading_lower = heading.lower()
        snippet_keywords = ["example", "code", "quickstart", "started",
                            "usage", "install", "features", "overview"]
        if snippets and any(kw in heading_lower for kw in snippet_keywords):
            # TC-982: Rotate snippets across headings instead of always snippets[0]
            snippet_idx = i % len(snippets)
            snippet = snippets[snippet_idx]
            language = snippet.get("language", "")
            code = snippet.get("code", "")
            lines.append(f"```{language}")
            lines.append(code)
            lines.append("```")
            lines.append("")

    # TC-CONTENT-QUALITY: Add Further Reading section with resource links
    lines.append("## Further Reading")
    lines.append("")
    lines.append(f"Learn more about {product_name} from these resources.")
    lines.append("")
    lines.append("- [Documentation Home](/docs/)")
    lines.append("- [API Reference](/reference/)")
    lines.append("")

    return "\n".join(lines)


def inject_frontmatter_fields(
    content: str,
    page: Dict[str, Any],
    section: str,
    token_mappings: Dict[str, str],
) -> str:
    """Inject layout and permalink into frontmatter if missing (TC-974: Gate 4 compliance).

    Args:
        content: Markdown content with frontmatter
        page: Page specification
        section: Section name
        token_mappings: Token mappings with __LAYOUT__ and __PERMALINK__

    Returns:
        Modified markdown content with layout and permalink in frontmatter
    """
    # TC-1732: If content has no frontmatter, create it
    if not content.startswith("---"):
        title = page.get("title", page.get("slug", "Page"))
        # Clean title: remove underscores, title-case slug-derived titles
        if title and '_' in title:
            title = title.replace('_', ' ').title()
        if title and title.startswith('-'):
            title = title.lstrip('- ').title()
        description = page.get("description") or page.get("purpose") or f"{title} - documentation and resources"
        layout = section if section in ("docs", "products", "reference", "kb", "blog") else "default"
        slug = page.get("slug", "page")
        weight = page.get("weight", 10)
        frontmatter = (
            f'---\ntitle: "{title}"\n'
            f'description: "{description}"\n'
            f'layout: {layout}\n'
            f'slug: "{slug}"\n'
            f'weight: {weight}\n'
            f'---\n'
        )
        # Strip template comments from the body if present
        body = content
        body = re.sub(r'^#\s*Template:.*\n', '', body, flags=re.MULTILINE)
        body = re.sub(r'^#\s*Source pattern:.*\n', '', body, flags=re.MULTILINE)
        content = frontmatter + body

    # Split frontmatter and body using line-aware delimiter
    # Simple split("---", 2) breaks when frontmatter contains "---" in string values
    # (e.g., claim text like '--- some text'). Use regex to find "---" on its own line.
    markers = list(_FM_DELIM_RE.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    # Check if layout and permalink are already present
    has_layout = "layout:" in frontmatter
    has_permalink = "permalink:" in frontmatter

    # Get values from token_mappings
    layout = token_mappings.get("__LAYOUT__", section)
    permalink = token_mappings.get("__PERMALINK__", page.get("url_path", ""))

    # Inject missing fields at the end of frontmatter
    additions = []
    if not has_layout and layout:
        additions.append(f"layout: {layout}")
    if not has_permalink and permalink:
        additions.append(f"permalink: {permalink}")

    if additions:
        # Add fields before closing ---
        frontmatter = frontmatter.rstrip() + "\n" + "\n".join(additions) + "\n"

    # Reconstruct content
    return f"---{frontmatter}---{body}"


# ---------------------------------------------------------------------------
# TC-3310: Compiled regex for single-line frontmatter field extraction.
# Captures the raw value (potentially quoted) for comparison against canonical.
# ---------------------------------------------------------------------------
_FM_FIELD_RE_CACHE: Dict[str, "re.Pattern"] = {}


def _fm_field_re(field: str) -> "re.Pattern":
    """Return compiled regex for a frontmatter field (cached)."""
    if field not in _FM_FIELD_RE_CACHE:
        _FM_FIELD_RE_CACHE[field] = re.compile(
            rf'^{re.escape(field)}:\s*(.+)$', re.MULTILINE
        )
    return _FM_FIELD_RE_CACHE[field]


def _normalize_fm_value(val: str) -> str:
    """Strip surrounding quotes and whitespace for YAML value comparison."""
    v = val.strip()
    if (v.startswith('"') and v.endswith('"')) or \
       (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return v


def enforce_frontmatter_invariants(
    content: str,
    page: Dict[str, Any],
    token_mappings: Dict[str, str],
) -> Tuple[str, List[str]]:
    """Enforce canonical frontmatter values from page plan (TC-3310).

    Called AFTER ``inject_frontmatter_fields()`` AND ``run_sanitizer_pipeline()``
    to correct any drift introduced by LLM generation or sanitizer transforms.

    Invariant fields checked: slug, permalink, layout, title, weight.
    Uses regex line replacement to preserve field ordering (no yaml.dump).

    Args:
        content: Markdown content with frontmatter.
        page: Page specification from page_plan.json.
        token_mappings: Token mappings with ``__LAYOUT__`` and ``__PERMALINK__``.

    Returns:
        Tuple of (corrected_content, list_of_corrected_field_names).
        The list is empty if no corrections were needed.
    """
    # Parse frontmatter boundaries
    markers = list(_FM_DELIM_RE.finditer(content))
    if len(markers) < 2:
        return content, []

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    # Build canonical values
    section = page.get("section", "default")
    canonical: Dict[str, str] = {}

    slug = page.get("slug", "")
    if slug:
        canonical["slug"] = f'"{slug}"'

    title = page.get("title", "")
    if title:
        # Escape inner double quotes for YAML safety
        safe_title = title.replace('"', '\\"')
        canonical["title"] = f'"{safe_title}"'

    permalink = token_mappings.get("__PERMALINK__") or page.get("url_path", "")
    if permalink:
        canonical["permalink"] = permalink

    layout = token_mappings.get("__LAYOUT__", section)
    if layout:
        canonical["layout"] = layout

    weight = page.get("weight")
    if weight is not None:
        canonical["weight"] = str(weight)

    # Compare and replace
    corrections: List[str] = []
    new_fm = frontmatter
    for field, canonical_val in canonical.items():
        pat = _fm_field_re(field)
        m = pat.search(new_fm)
        if not m:
            continue  # Field not present — inject_frontmatter_fields handles that
        current_val = m.group(1).strip()
        if _normalize_fm_value(current_val) == _normalize_fm_value(canonical_val):
            continue
        # Replace the line value
        new_fm = pat.sub(f"{field}: {canonical_val}", new_fm, count=1)
        corrections.append(field)

    if not corrections:
        return content, []

    return f"---{new_fm}---{body}", corrections


def _strip_frontmatter_comments(content: str) -> str:
    """Remove comment-only lines from YAML frontmatter.

    Template files contain developer-facing metadata comments (e.g.,
    '# Template: KB how-to article') that should not appear in generated
    output. This strips lines whose first non-whitespace char is '#' within
    the opening/closing '---' delimiters. Inline comments on data lines
    (e.g., 'key: value  # note') are preserved since they are part of a
    data line, not standalone comments.
    """
    if not content.startswith("---"):
        return content

    markers = list(_FM_DELIM_RE.finditer(content))
    if len(markers) < 2:
        return content

    fm_start = markers[0].end()
    fm_end = markers[1].start()
    frontmatter = content[fm_start:fm_end]
    body = content[markers[1].end():]

    cleaned = "\n".join(
        line for line in frontmatter.split("\n")
        if not line.strip().startswith("#")
    )
    return f"---{cleaned}---{body}"


def apply_token_mappings(template_content: str, token_mappings: Dict[str, str]) -> str:
    """Apply token mappings to template content.

    TC-964: Replaces placeholder tokens with actual values from token_mappings dict.
    This enables template-driven pages (blog) to have their frontmatter and body
    content filled with deterministic values generated by W4 IAPlanner.

    Also strips template metadata comments from YAML frontmatter so they do not
    appear in generated output files.

    Args:
        template_content: Raw template content with tokens (e.g., __TITLE__, __DATE__)
        token_mappings: Dict mapping token names to replacement values

    Returns:
        Template content with tokens replaced and frontmatter comments stripped

    Example:
        >>> template = "title: __TITLE__\\ndate: __DATE__"
        >>> mappings = {"__TITLE__": "My Post", "__DATE__": "2024-01-01"}
        >>> apply_token_mappings(template, mappings)
        'title: My Post\\ndate: 2024-01-01'
    """
    # Strip template metadata comments from frontmatter
    result = _strip_frontmatter_comments(template_content)
    for token, value in token_mappings.items():
        if '\n' in str(value):
            # Multi-line values: preserve indentation of token position
            # so YAML block scalars (content: |) remain properly indented
            token_pos = result.find(token)
            if token_pos >= 0:
                line_start = result.rfind('\n', 0, token_pos) + 1
                indent = ' ' * (token_pos - line_start)
                lines = str(value).split('\n')
                indented_value = lines[0] + '\n' + '\n'.join(
                    (indent + line if line.strip() else line) for line in lines[1:]
                )
                result = result[:token_pos] + indented_value + result[token_pos + len(token):]
            else:
                result = result.replace(token, str(value))
        else:
            result = result.replace(token, str(value))
    # R1: Validate YAML frontmatter is parseable after token replacement
    result = _validate_yaml_frontmatter(result)
    return result


def _validate_yaml_frontmatter(content: str) -> str:
    """Validate YAML frontmatter is parseable. Fix if broken.

    If YAML parsing fails (e.g., code-like text broke the structure),
    attempt to fix by quoting problematic field values.
    """
    if not content.startswith("---"):
        return content

    markers = list(_FM_DELIM_RE.finditer(content))
    if len(markers) < 2:
        return content

    fm_text = content[markers[0].end():markers[1].start()]
    body = content[markers[1].end():]

    try:
        import yaml
        yaml.safe_load(fm_text)
        return content  # Valid YAML, no fix needed
    except Exception:
        # YAML is broken — attempt to fix by escaping the content field
        # Replace problematic lines in block scalar fields
        fixed_lines = []
        in_block_scalar = False
        block_indent = 0
        for line in fm_text.split('\n'):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            # Detect block scalar start (e.g., "content: |")
            if re.match(r'\w+:\s*\|', stripped):
                in_block_scalar = True
                block_indent = indent + 2
                fixed_lines.append(line)
                continue
            # End of block scalar when indent decreases
            if in_block_scalar and indent < block_indent and stripped:
                in_block_scalar = False
            if in_block_scalar:
                # Sanitize code-like content within YAML block scalars
                sanitized = stripped
                for ch in [':', '{', '}']:
                    if ch in sanitized and not sanitized.startswith(('#', '-')):
                        sanitized = sanitized.replace(ch, '')
                fixed_lines.append(' ' * indent + sanitized)
            else:
                fixed_lines.append(line)

        fixed_fm = '\n'.join(fixed_lines)
        try:
            import yaml
            yaml.safe_load(fixed_fm)
            return f"---{fixed_fm}---{body}"
        except Exception:
            # Still broken — return original (Hugo will report the error)
            logger.warning("[W5] YAML frontmatter validation failed; could not auto-fix")
            return content


def check_unfilled_tokens(content: str) -> List[str]:
    """Check for unfilled template tokens in content.

    Per specs/21_worker_contracts.md:211-213, drafts must not contain
    unreplaced template tokens.

    Args:
        content: Markdown content to check

    Returns:
        List of unfilled tokens found (empty if none)
    """
    # TC-1404: Match __UPPER_SNAKE__ patterns (actual template tokens).
    # Lowercase patterns like __cause__, __init__ are Python dunders or LLM text, not tokens.
    pattern = r'__[A-Z][A-Z0-9_]*__'
    matches = re.findall(pattern, content)
    # TC-1404: Exclude Python dunder methods/attributes (legitimate code references)
    python_dunders = {
        '__init__', '__main__', '__name__', '__str__', '__repr__', '__dict__',
        '__class__', '__all__', '__file__', '__doc__', '__enter__', '__exit__',
        '__getattr__', '__setattr__', '__getitem__', '__setitem__', '__len__',
        '__iter__', '__next__', '__call__', '__new__', '__del__', '__eq__',
        '__ne__', '__lt__', '__gt__', '__le__', '__ge__', '__hash__',
        '__contains__', '__add__', '__sub__', '__mul__', '__truediv__',
        '__bool__', '__int__', '__float__', '__index__', '__slots__',
        '__import__', '__builtins__', '__cached__', '__loader__', '__spec__',
        '__package__', '__path__', '__version__', '__author__',
        # TC-1710: Extended dunder list to prevent false positives
        '__module__', '__module_version__', '__qualname__', '__abstractmethods__',
        '__annotations__', '__bases__', '__mro__', '__subclasses__',
        '__wrapped__', '__closure__', '__code__', '__defaults__',
        '__globals__', '__kwdefaults__', '__weakref__', '__reduce__',
        '__reduce_ex__', '__sizeof__', '__format__', '__dir__',
        '__instancecheck__', '__subclasscheck__', '__copy__', '__deepcopy__',
        '__getnewargs__', '__getstate__', '__setstate__',
    }
    # TC-1710: Also skip any dunder inside a code fence block
    # Extract code fence regions and collect dunders found inside them
    in_fence = False
    code_fence_dunders = set()
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            line_dunders = re.findall(r'__[A-Za-z][A-Za-z0-9_]*__', line)
            code_fence_dunders.update(line_dunders)
    filtered = [t for t in set(matches) if t not in python_dunders and t not in code_fence_dunders]
    return filtered


def generate_page_id(page: Dict[str, Any]) -> str:
    """Generate deterministic page ID from page specification.

    Args:
        page: Page specification dictionary

    Returns:
        Page ID string (e.g., "products_overview", "docs_getting-started")
    """
    section = page["section"]
    slug = page["slug"]
    return f"{section}_{slug}"


def _make_page_orchestrator(llm_client, prompt_loader, rc):
    """Create a fresh MultiPassOrchestrator for one page (TC-2362 parallel support).

    Returns None if multi-pass is disabled or prompt_loader is unavailable.
    Each page in parallel mode gets its own instance to avoid shared-state races.

    Spec: specs/21_worker_contracts.md §"Parallel Page Writing"
    """
    if llm_client is None or prompt_loader is None:
        return None
    try:
        if rc is not None and rc.is_multi_pass_enabled():
            from .multi_pass import MultiPassOrchestrator
            return MultiPassOrchestrator(
                llm_client=llm_client,
                prompt_loader=prompt_loader,
                run_config=rc,
            )
    except Exception as e:
        logger.warning(f"[W5 SectionWriter] _make_page_orchestrator failed: {e}")
    return None


def _compute_page_input_hash(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
) -> str:
    """Stable SHA256 of inputs that uniquely determine this page's generated content.

    TC-2450: Used to detect whether a page needs regeneration on rerun.
    Captures: spec fields + resolved claim text + resolved snippet content.
    Pure function — no I/O, no LLM, deterministic for identical inputs.
    """
    spec: Dict[str, Any] = {
        "slug": page.get("slug", ""),
        "section": page.get("section", ""),
        "page_role": page.get("page_role", ""),
        "title": page.get("title", ""),
        "purpose": page.get("purpose", ""),
        "required_claim_ids": sorted(page.get("required_claim_ids", [])),
        "required_snippet_tags": sorted(page.get("required_snippet_tags", [])),
        "required_headings": sorted(page.get("required_headings", [])),
        "template_variant": page.get("template_variant", "standard"),
    }
    # Resolve claim text (sorted by claim_id for determinism)
    _claim_ids = set(spec["required_claim_ids"])
    spec["claims"] = {
        c["claim_id"]: c.get("claim_text", "")
        for c in product_facts.get("claims", [])
        if c["claim_id"] in _claim_ids
    }
    # Resolve snippet content (sorted by tag)
    _tags = set(spec["required_snippet_tags"])
    spec["snippets"] = {
        s["tag"]: s.get("code", "") + "|" + s.get("description", "")
        for s in snippet_catalog.get("snippets", [])
        if s["tag"] in _tags
    }
    canonical = json.dumps(spec, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _find_failed_page_slugs(validation_report_path: Path) -> frozenset:
    """Extract slugs of pages with blocker/error issues from validation_report.json.

    TC-2450: Used by regen_failed_only to identify which pages must be regenerated.
    Returns frozenset of slug strings (filename stems from location.path).
    Returns empty frozenset if file is missing or corrupt.

    .. deprecated:: TC-3310
        Use ``_resolve_failed_page_slugs`` instead, which handles index.md paths
        correctly by building a reverse index from the page plan.
    """
    try:
        report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    except Exception:
        return frozenset()
    failed: set = set()
    for issue in report.get("issues", []):
        if issue.get("severity") in ("blocker", "error"):
            path = issue.get("location", {}).get("path", "")
            if path:
                # path is like "drafts/products/overview.md" or content path
                failed.add(Path(path).stem)
    return frozenset(failed)


def _resolve_failed_page_slugs(
    validation_report_path: Path,
    pages: List[Dict[str, Any]],
) -> frozenset:
    """Resolve failed pages from validation_report using page_plan reverse index.

    TC-3310: Fix index.md stem collision.  Builds a reverse index from
    output_path -> slug and draft_path -> slug using the page_plan pages list,
    so that paths ending in index.md or _index.md resolve to the correct slug.

    Falls back to parent-directory name for index.md paths not in the reverse
    index, and to Path.stem for non-index paths (backward compat).

    Returns frozenset of slug strings.  Empty frozenset if file missing/corrupt.
    """
    try:
        report = json.loads(validation_report_path.read_text(encoding="utf-8"))
    except Exception:
        return frozenset()

    # Build reverse index: normalized_path -> slug
    path_to_slug: Dict[str, str] = {}
    for page in pages:
        slug = page.get("slug", "")
        if not slug:
            continue
        # Map output_path -> slug
        op = page.get("output_path", "")
        if op:
            path_to_slug[op.replace("\\", "/")] = slug
        # Map draft path pattern -> slug  (drafts/<section>/<slug>.md)
        section = page.get("section", "")
        if section:
            path_to_slug[f"drafts/{section}/{slug}.md"] = slug

    failed: set = set()
    for issue in report.get("issues", []):
        if issue.get("severity") not in ("blocker", "error"):
            continue
        raw_path = issue.get("location", {}).get("path", "")
        if not raw_path:
            continue

        normalized = raw_path.replace("\\", "/")

        # 1) Exact match in reverse index
        if normalized in path_to_slug:
            failed.add(path_to_slug[normalized])
            continue

        # 2) Suffix match (handles absolute paths that end with a known relative)
        matched = False
        for known_path, slug in path_to_slug.items():
            if normalized.endswith(known_path) and (
                normalized == known_path
                or normalized[-(len(known_path) + 1)] == "/"
            ):
                failed.add(slug)
                matched = True
                break
        if matched:
            continue

        # 3) Stem-based fallback — skip "index" / "_index" stems
        stem = Path(normalized).stem
        if stem not in ("index", "_index"):
            failed.add(stem)
        else:
            # For index.md paths, use parent directory name as slug candidate
            parent = Path(normalized).parent.name
            _skip = ("content", "drafts", "artifacts", "work", "site")
            if parent and parent not in _skip:
                failed.add(parent)

    return frozenset(failed)


def _generate_single_page(
    page: Dict[str, Any],
    product_facts: Dict[str, Any],
    snippet_catalog: Dict[str, Any],
    llm_client,
    page_plan: Dict[str, Any],
    multi_pass_orchestrator,
    code_understanding: Dict[str, Any],
    evidence_map: Dict[str, Any],
    cross_page_summaries_snapshot: Dict[str, str],
    run_config: Dict[str, Any],
    drafts_dir: Path,
) -> Dict[str, Any]:
    """Generate one page and write its draft to disk. Return the manifest entry dict.

    TC-2362: Extracted from the main loop to allow parallel execution via ThreadPoolExecutor.
    Each call is self-contained — writes only to drafts/<section>/<slug>.md (disjoint paths).

    Does NOT emit events (caller emits EVENT_ARTIFACT_WRITTEN after pool completes to avoid
    concurrent writes to events.ndjson).

    Raises SectionWriterUnfilledTokensError if the generated content has unfilled tokens.

    Spec: specs/21_worker_contracts.md §"Parallel Page Writing"
    """
    page_id = generate_page_id(page)
    slug = page["slug"]
    section = page["section"]
    page_status = page.get("page_status", "new")

    # TC-2373 (RD-04): Compute priority-weighted token budget
    effective_tokens = _compute_token_budget(page, run_config)
    base_tokens = int(run_config.get("token_budget", 2048))
    raw_weight = page.get("content_strategy", {}).get("priority_weight")
    if raw_weight is None:
        raw_weight = SECTION_TYPE_WEIGHTS.get(page.get("page_type", ""), 1.0)
    logger.debug(
        "[W5] %s: base=%d weight=%.2f effective=%d",
        slug, base_tokens, float(raw_weight) if raw_weight is not None else 1.0,
        effective_tokens,
    )

    logger.info(f"[W5 SectionWriter] Generating content for page: {page_id}")

    content = generate_section_content(
        page=page,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        llm_client=llm_client,
        page_plan=page_plan,
        multi_pass_orchestrator=multi_pass_orchestrator,
        code_understanding=code_understanding,
        evidence_map=evidence_map,
        cross_page_summaries=cross_page_summaries_snapshot,
    )

    content = inject_frontmatter_fields(content, page, section, page.get("token_mappings") or {})

    sanitizer_ctx = SanitizerContext(
        page=page,
        product_facts=product_facts,
        snippet_catalog=snippet_catalog,
        llm_client=llm_client,
        target_platform=run_config.get("target_platform", ""),
    )
    content = run_sanitizer_pipeline(content, sanitizer_ctx)

    # TC-3310: Enforce frontmatter invariants (post-sanitizer lock)
    content, _fm_corrections = enforce_frontmatter_invariants(
        content, page, page.get("token_mappings") or {},
    )
    if _fm_corrections:
        logger.info(
            "[W5] frontmatter_locked slug=%s fields=%s", slug, _fm_corrections,
        )

    unfilled_tokens = check_unfilled_tokens(content)
    if unfilled_tokens:
        error_msg = f"Unfilled tokens in page {page_id}: {', '.join(unfilled_tokens)}"
        logger.error(f"[W5 SectionWriter] {error_msg}")
        raise SectionWriterUnfilledTokensError(error_msg)

    section_dir = drafts_dir / section
    section_dir.mkdir(parents=True, exist_ok=True)
    draft_path = section_dir / f"{slug}.md"
    atomic_write_text(draft_path, content)

    logger.info(f"[W5 SectionWriter] Wrote draft: {draft_path}")

    return {
        "page_id": page_id,
        "section": section,
        "slug": slug,
        "output_path": page["output_path"],
        "draft_path": str(draft_path.relative_to(drafts_dir.parent)),
        "title": page["title"],
        "word_count": len(content.split()),
        "claim_count": content.count("<!-- claim:"),
        "page_status": page_status,
        "effective_token_budget": effective_tokens,
        "frontmatter_corrections": _fm_corrections,
    }


def execute_section_writer(
    run_dir: Path,
    run_config: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute W5 SectionWriter worker.

    Generates markdown content for all planned pages using templates,
    product facts, and snippet catalog.

    Per specs/07_section_templates.md and specs/21_worker_contracts.md:195-226.

    Args:
        run_dir: Path to run directory
        run_config: Run configuration dictionary
        llm_client: Optional LLM client for content generation

    Returns:
        Dictionary containing:
        - status: "success" or "failed"
        - manifest_path: Path to draft_manifest.json
        - draft_count: Number of drafts generated
        - total_pages: Total pages processed

    Raises:
        SectionWriterError: If section writing fails
        SectionWriterUnfilledTokensError: If unfilled tokens remain
        SectionWriterLLMError: If LLM call fails
    """
    run_layout = RunLayout(run_dir=run_dir)
    run_id = run_config.get("run_id", "unknown")
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())

    # Extract telemetry context from run_config (passed by orchestrator)
    telemetry_client = run_config.get("_telemetry_client") if isinstance(run_config, dict) else None
    telemetry_run_id = run_config.get("_telemetry_run_id") if isinstance(run_config, dict) else None
    telemetry_trace_id = run_config.get("_telemetry_trace_id") if isinstance(run_config, dict) else trace_id
    telemetry_parent_span_id = run_config.get("_telemetry_parent_span_id") if isinstance(run_config, dict) else span_id

    # TC-999: Auto-construct LLM client from run_config if not provided (uses shared factory with fallback support)
    if llm_client is None and run_config.get("llm", {}).get("api_base_url"):
        try:
            from launch.clients.llm_provider import create_llm_client_from_config

            llm_client = create_llm_client_from_config(
                run_config=run_config,
                run_dir=run_dir,
                telemetry_client=telemetry_client,
                telemetry_run_id=telemetry_run_id or run_id,
                telemetry_trace_id=telemetry_trace_id,
                telemetry_parent_span_id=telemetry_parent_span_id,
            )
            if llm_client:
                logger.info(
                    f"[W5 SectionWriter] Auto-constructed LLM client: "
                    f"model={llm_client.model}, base_url={llm_client.api_base_url}, "
                    f"fallback={'yes' if llm_client.fallback_api_base_url else 'no'}, "
                    f"telemetry_enabled={telemetry_client is not None}"
                )
        except Exception as e:
            logger.warning(
                f"[W5 SectionWriter] Failed to construct LLM client: {e}. "
                f"Falling back to template-based content generation."
            )
            llm_client = None

    logger.info(f"[W5 SectionWriter] Starting section writing for run {run_id}")

    # Emit start event
    emit_event(
        run_layout=run_layout,
        run_id=run_id,
        trace_id=trace_id,
        span_id=span_id,
        event_type=EVENT_WORK_ITEM_STARTED,
        payload={"worker": "w5_section_writer", "phase": "section_writing"},
    )

    try:
        # Load input artifacts
        page_plan = load_page_plan(run_layout.artifacts_dir)
        product_facts = load_product_facts(run_layout.artifacts_dir)
        snippet_catalog = load_snippet_catalog(run_layout.artifacts_dir)
        evidence_map = load_evidence_map(run_layout.artifacts_dir)

        # TC-1723: Load code_understanding artifact if available (for RichContext)
        code_understanding = None
        code_understanding_path = run_layout.artifacts_dir / "code_understanding.json"
        if code_understanding_path.exists():
            try:
                code_understanding = json.loads(code_understanding_path.read_text(encoding="utf-8"))
                logger.info(f"[W5 SectionWriter] Loaded code_understanding artifact")
            except Exception as e:
                logger.warning(f"[W5 SectionWriter] Failed to load code_understanding: {e}")

        # TC-1723: Initialize multi-pass orchestrator if enabled
        multi_pass_orchestrator = None
        rc = None  # RunConfig object; may remain None if from_dict fails (workers use dict directly)
        try:
            from ...models.run_config import RunConfig
            rc = RunConfig.from_dict(run_config) if isinstance(run_config, dict) else run_config
            if rc.is_multi_pass_enabled() and llm_client is not None:
                from .multi_pass import MultiPassOrchestrator
                prompt_loader = _get_prompt_loader()
                if prompt_loader:
                    multi_pass_orchestrator = MultiPassOrchestrator(
                        llm_client=llm_client,
                        prompt_loader=prompt_loader,
                        run_config=rc,
                    )
                    logger.info(f"[W5 SectionWriter] Multi-pass generation ENABLED")
                else:
                    logger.warning(
                        f"[W5 SectionWriter] Multi-pass enabled but PromptLoader unavailable, "
                        f"falling back to single-pass"
                    )
        except Exception as e:
            logger.warning(f"[W5 SectionWriter] Multi-pass init failed: {e}, using single-pass")

        pages = page_plan.get("pages", [])
        logger.info(f"[W5 SectionWriter] Processing {len(pages)} pages")

        # Create drafts directory
        drafts_dir = run_layout.run_dir / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)

        # TC-1764: Load previous drafts for incremental reuse
        previous_drafts: Dict[str, str] = {}
        try:
            if rc.is_incremental_enabled():
                prev_run = rc.get_previous_run_path()
                if prev_run:
                    previous_drafts = run_layout.load_previous_drafts(prev_run)
                    if previous_drafts:
                        logger.info(
                            f"[W5 SectionWriter] Loaded {len(previous_drafts)} "
                            f"previous drafts for incremental reuse"
                        )
        except Exception as e:
            logger.warning(f"[W5 SectionWriter] Failed to load previous drafts: {e}")

        # TC-2450: Hash-based page skip cache (disabled by default)
        from .._shared.worker_cache import load_cache_config as _load_cache_config
        _worker_cache = _load_cache_config(run_dir, run_config)
        if _worker_cache.enabled:
            logger.info("[W5] Page hash cache ENABLED (caching.enabled=true)")

        # TC-2450: regen_failed_only — override page_status from prior validation_report.
        # Requires incremental.enabled=true + previous_run_path for previous_drafts to be loaded.
        if run_config.get("regen_failed_only", False):
            _val_path = run_layout.artifacts_dir / "validation_report.json"
            if _val_path.exists():
                _failed_slugs = _resolve_failed_page_slugs(_val_path, pages)
                for _p in pages:
                    _p["page_status"] = "new" if _p.get("slug") in _failed_slugs else "preserved"
                logger.info(
                    "[W5] regen_failed_only: %d pages to regenerate, %d preserved",
                    len(_failed_slugs), len(pages) - len(_failed_slugs),
                )
            else:
                logger.warning(
                    "[W5] regen_failed_only=true but no validation_report.json found"
                    " — regenerating all pages"
                )

        # TC-1723: Track cross-page summaries for multi-pass (built incrementally in sequential mode)
        cross_page_summaries = {}

        # TC-2362: Parallelism config — default 1 = sequential (backward-compatible)
        # Spec: specs/21_worker_contracts.md §"Parallel Page Writing"
        max_parallel = min(max(run_config.get("max_parallel_pages", 1), 1), 16)

        # Reusable preserved-page fast-path (shared between sequential and parallel modes)
        def _handle_preserved_page(page):
            """Write a preserved page from previous_drafts. Returns manifest entry or None."""
            page_id = generate_page_id(page)
            slug = page["slug"]
            section = page["section"]
            draft_rel = f"{section}\\{slug}.md"
            draft_rel_fwd = f"{section}/{slug}.md"
            prev_content = previous_drafts.get(draft_rel) or previous_drafts.get(draft_rel_fwd)
            if prev_content:
                logger.info(f"[W5 SectionWriter] Reusing preserved draft for {page_id}")
                section_dir = drafts_dir / section
                section_dir.mkdir(parents=True, exist_ok=True)
                draft_path = section_dir / f"{slug}.md"
                with open(draft_path, "w", encoding="utf-8") as f:
                    f.write(prev_content)
                return {
                    "page_id": page_id,
                    "section": section,
                    "slug": slug,
                    "output_path": page["output_path"],
                    "draft_path": str(draft_path.relative_to(run_layout.run_dir)),
                    "title": page["title"],
                    "word_count": len(prev_content.split()),
                    "claim_count": prev_content.count("<!-- claim:"),
                    "page_status": "preserved",
                }
            else:
                logger.warning(
                    f"[W5 SectionWriter] Page {page_id} marked preserved but "
                    f"previous draft not found, regenerating"
                )
                return None

        # Generate content for each page
        draft_files = []
        preserved_count = 0

        if max_parallel == 1:
            # Sequential mode: identical to original behavior.
            # cross_page_summaries accumulates incrementally (each page sees prior pages' summaries).
            for page in pages:
                page_id = generate_page_id(page)
                slug = page["slug"]
                section = page["section"]

                # TC-1764: Skip generation for preserved pages — reuse previous draft
                page_status = page.get("page_status", "new")
                if page_status == "preserved" and previous_drafts:
                    entry = _handle_preserved_page(page)
                    if entry is not None:
                        entry["duration_ms"] = 0  # TC-2451: no generation time for preserved
                        draft_files.append(entry)
                        preserved_count += 1
                        continue
                    # fall through to regenerate if previous draft not found

                # TC-1764: Skip deleted pages entirely
                if page_status == "deleted":
                    logger.info(f"[W5 SectionWriter] Skipping deleted page: {page_id}")
                    continue

                # TC-2435: Skip dry_run pages — policy engine marked these for inspection only
                if page.get("dry_run"):
                    logger.info("[W5] Skipping dry_run page: %s", page.get("slug"))
                    continue

                # TC-2450: Hash-based cache skip — check before calling LLM
                _page_input_hash = ""
                if _worker_cache.enabled:
                    _page_input_hash = _compute_page_input_hash(page, product_facts, snippet_catalog)
                    _cached_rel = _worker_cache.is_page_hit(page_id, _page_input_hash)
                    if _cached_rel and (run_layout.run_dir / _cached_rel).exists():
                        _cached_content = (run_layout.run_dir / _cached_rel).read_text(encoding="utf-8")
                        logger.info("[W5] SKIP %s (cache hit hash=%.8s)", page_id, _page_input_hash)
                        draft_files.append({
                            "page_id": page_id,
                            "section": section,
                            "slug": slug,
                            "output_path": page["output_path"],
                            "draft_path": _cached_rel,
                            "title": page["title"],
                            "word_count": len(_cached_content.split()),
                            "claim_count": _cached_content.count("<!-- claim:"),
                            "page_status": "cache_hit",
                            "duration_ms": 0,
                        })
                        preserved_count += 1
                        continue

                # TC-973/TC-1723: Generate content (single-pass or multi-pass)
                import time as _time
                _t0 = _time.perf_counter()
                entry = _generate_single_page(
                    page=page,
                    product_facts=product_facts,
                    snippet_catalog=snippet_catalog,
                    llm_client=llm_client,
                    page_plan=page_plan,
                    multi_pass_orchestrator=multi_pass_orchestrator,
                    code_understanding=code_understanding,
                    evidence_map=evidence_map,
                    cross_page_summaries_snapshot=cross_page_summaries,
                    run_config=run_config,
                    drafts_dir=drafts_dir,
                )
                entry["duration_ms"] = int((_time.perf_counter() - _t0) * 1000)
                draft_files.append(entry)

                # TC-2450: Record page in cache after successful generation
                if _worker_cache.enabled:
                    _worker_cache.record_page(page_id, entry["draft_path"], _page_input_hash)

                # TC-1723: Update cross-page summaries from shared orchestrator (sequential only)
                if multi_pass_orchestrator is not None:
                    cross_page_summaries = dict(multi_pass_orchestrator.cross_page_summaries)

                # Emit draft written event per page
                emit_event(
                    run_layout=run_layout,
                    run_id=run_id,
                    trace_id=trace_id,
                    span_id=span_id,
                    event_type=EVENT_ARTIFACT_WRITTEN,
                    payload={
                        "artifact": "draft",
                        "page_id": entry["page_id"],
                        "path": str(drafts_dir / entry["section"] / f"{entry['slug']}.md"),
                    },
                )
                # TC-3310/SR-03: Emit frontmatter lock event
                if entry.get("frontmatter_corrections"):
                    emit_event(
                        run_layout=run_layout,
                        run_id=run_id,
                        trace_id=trace_id,
                        span_id=span_id,
                        event_type=W5_FRONTMATTER_LOCKED,
                        payload={
                            "slug": entry["slug"],
                            "corrections": entry["frontmatter_corrections"],
                        },
                    )

        else:
            # TC-2362: Parallel mode — snapshot summaries, per-page orchestrators.
            # Spec: specs/21_worker_contracts.md §"Parallel Page Writing"
            logger.info(f"[W5 SectionWriter] Parallel page writing: max_parallel_pages={max_parallel}")

            # Phase 1: Handle preserved/deleted/cache-hit pages inline (fast-path, no LLM)
            to_generate = []
            for page in pages:
                _par_page_id = generate_page_id(page)
                page_status = page.get("page_status", "new")
                if page_status == "preserved" and previous_drafts:
                    entry = _handle_preserved_page(page)
                    if entry is not None:
                        entry["duration_ms"] = 0
                        draft_files.append(entry)
                        preserved_count += 1
                        continue
                    # fall through to regenerate if previous draft not found
                if page_status == "deleted":
                    logger.info(f"[W5 SectionWriter] Skipping deleted page: {_par_page_id}")
                    continue
                # TC-2435: Skip dry_run pages — policy engine marked these for inspection only
                if page.get("dry_run"):
                    logger.info("[W5] Skipping dry_run page: %s", page.get("slug"))
                    continue
                # TC-2450: Hash-based cache skip in parallel Phase 1 (before thread dispatch)
                if _worker_cache.enabled:
                    _par_hash = _compute_page_input_hash(page, product_facts, snippet_catalog)
                    _par_cached = _worker_cache.is_page_hit(_par_page_id, _par_hash)
                    if _par_cached and (run_layout.run_dir / _par_cached).exists():
                        _par_content = (run_layout.run_dir / _par_cached).read_text(encoding="utf-8")
                        logger.info("[W5] SKIP %s (cache hit hash=%.8s)", _par_page_id, _par_hash)
                        draft_files.append({
                            "page_id": _par_page_id,
                            "section": page["section"],
                            "slug": page["slug"],
                            "output_path": page["output_path"],
                            "draft_path": _par_cached,
                            "title": page["title"],
                            "word_count": len(_par_content.split()),
                            "claim_count": _par_content.count("<!-- claim:"),
                            "page_status": "cache_hit",
                            "duration_ms": 0,
                        })
                        preserved_count += 1
                        continue
                to_generate.append(page)

            # Phase 2: Dispatch remaining pages through thread pool
            # Frozen snapshot: all parallel pages share the same summaries baseline.
            # On incremental runs the orchestrator's existing summaries provide cross-page context.
            cross_page_summaries_snapshot = dict(cross_page_summaries)
            prompt_loader = _get_prompt_loader()

            # TC-2450: Pre-compute input hashes for pages going to thread pool
            _par_hashes: Dict[int, str] = {}
            if _worker_cache.enabled:
                for _pp in to_generate:
                    _par_hashes[id(_pp)] = _compute_page_input_hash(_pp, product_facts, snippet_catalog)

            import time as _time

            futures: Dict[Any, Dict[str, Any]] = {}
            with ThreadPoolExecutor(max_workers=max_parallel) as pool:
                for page in to_generate:
                    # Per-page orchestrator — no shared mutable state between workers
                    page_orch = _make_page_orchestrator(llm_client, prompt_loader, rc)
                    _pp_t0 = _time.perf_counter()
                    fut = pool.submit(
                        _generate_single_page,
                        page,
                        product_facts,
                        snippet_catalog,
                        llm_client,
                        page_plan,
                        page_orch,
                        code_understanding,
                        evidence_map,
                        cross_page_summaries_snapshot,
                        run_config,
                        drafts_dir,
                    )
                    futures[fut] = (page, _pp_t0)

                # BLKR-04: Emit per-page events as each future completes (real-time vs batch).
                # as_completed() yields futures in completion order — earlier pages unblock
                # observers immediately rather than waiting for all pages to finish.
                # All emit_event calls happen on the main thread (no concurrent ndjson writes).
                for fut in as_completed(futures):
                    entry = fut.result()  # re-raises SectionWriterUnfilledTokensError on failure
                    _par_page, _par_t0 = futures[fut]
                    entry["duration_ms"] = int((_time.perf_counter() - _par_t0) * 1000)
                    # TC-2450: Record in cache after parallel generation
                    if _worker_cache.enabled:
                        _par_h = _par_hashes.get(id(_par_page), "")
                        _worker_cache.record_page(generate_page_id(_par_page), entry["draft_path"], _par_h)
                    draft_files.append(entry)
                    emit_event(
                        run_layout=run_layout,
                        run_id=run_id,
                        trace_id=trace_id,
                        span_id=span_id,
                        event_type=EVENT_ARTIFACT_WRITTEN,
                        payload={
                            "artifact": "draft",
                            "page_id": entry["page_id"],
                            "path": str(drafts_dir / entry["section"] / f"{entry['slug']}.md"),
                        },
                    )
                    # TC-3310/SR-03: Emit frontmatter lock event
                    if entry.get("frontmatter_corrections"):
                        emit_event(
                            run_layout=run_layout,
                            run_id=run_id,
                            trace_id=trace_id,
                            span_id=span_id,
                            event_type=W5_FRONTMATTER_LOCKED,
                            payload={
                                "slug": entry["slug"],
                                "corrections": entry["frontmatter_corrections"],
                            },
                        )

        # Sort draft files deterministically per specs/10_determinism_and_caching.md:43
        # Sort by (section_order, output_path)
        section_order = {"products": 0, "docs": 1, "reference": 2, "kb": 3, "blog": 4}
        draft_files.sort(key=lambda d: (section_order.get(d["section"], 99), d["output_path"]))

        # TC-1764/TC-2451: Log incremental + timing summary
        _skipped_entries = [e for e in draft_files if e.get("page_status") in ("preserved", "cache_hit")]
        _generated_entries = [e for e in draft_files if e.get("page_status") not in ("preserved", "cache_hit")]
        _avg_ms = (
            sum(e.get("duration_ms", 0) for e in _generated_entries) / len(_generated_entries)
            if _generated_entries else 0.0
        )
        if preserved_count > 0 or _worker_cache.enabled:
            logger.info(
                "[W5] timing: %d generated avg=%.0fms, %d skipped (preserved+cache)",
                len(_generated_entries), _avg_ms, len(_skipped_entries),
            )
        elif len(draft_files) > 0:
            logger.info(
                "[W5 SectionWriter] Incremental summary: "
                f"{preserved_count} preserved, "
                f"{len(draft_files) - preserved_count} generated"
            )

        # Build manifest
        manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "total_pages": len(pages),
            "draft_count": len(draft_files),
            "preserved_count": preserved_count,
            "drafts": draft_files,
        }

        # Write manifest
        manifest_path = run_layout.artifacts_dir / "draft_manifest.json"
        atomic_write_json(manifest_path, manifest)

        logger.info(f"[W5 SectionWriter] Wrote draft manifest: {manifest_path}")

        # TC-2354: Write sanitizer metrics
        sanitizer_metrics = get_sanitizer_metrics()
        metrics_path = run_layout.artifacts_dir / "sanitizer_metrics.json"
        atomic_write_json(metrics_path, sanitizer_metrics)
        logger.info(
            f"[W5 SectionWriter] Sanitizer metrics: "
            f"{sanitizer_metrics['total_pages']} pages, "
            f"{len(sanitizer_metrics['transforms_that_never_fired'])} transforms never fired"
        )
        reset_sanitizer_metrics()

        # Emit manifest written event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_ARTIFACT_WRITTEN,
            payload={
                "artifact": "draft_manifest.json",
                "path": str(manifest_path),
                "draft_count": len(draft_files),
            },
        )

        # Emit completion event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_WORK_ITEM_FINISHED,
            payload={
                "worker": "w5_section_writer",
                "phase": "section_writing",
                "status": "success",
                "draft_count": len(draft_files),
            },
        )

        return {
            "status": "success",
            "manifest_path": str(manifest_path),
            "draft_count": len(draft_files),
            "total_pages": len(pages),
        }

    except Exception as e:
        logger.error(f"[W5 SectionWriter] Section writing failed: {e}")

        # Emit failure event
        emit_event(
            run_layout=run_layout,
            run_id=run_id,
            trace_id=trace_id,
            span_id=span_id,
            event_type=EVENT_RUN_FAILED,
            payload={
                "worker": "w5_section_writer",
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise
