"""
Multi-pass content generation orchestrator for W5 SectionWriter.

Spec reference: specs/21_worker_contracts.md 'W5 Multi-Pass Generation Contract'

The MultiPassOrchestrator implements a 3-pass generation strategy:
1. OUTLINE: Generate content structure with claim mapping
2. DRAFT: Generate full content from outline
3. REFINE: Polish draft with cross-page awareness

Each pass includes validation and fallback to deterministic generation.
Hallucination detection runs after draft generation.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

try:
    import yaml as yaml_mod
except ImportError:  # pragma: no cover
    yaml_mod = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .rich_context import RichContext

from launch.workers.w5_section_writer.code_generator import (
    CodeBlock,
    generate_code_block,
    normalize_assembled_content,
)
from launch.workers.w5_section_writer.renderer import json_to_markdown, parse_json_draft

# TC-2519/2520/2521: LLM contract hardening
from launch.workers._shared.llm_contract import (
    FailureClassifier,
    OutputSchemaValidator,
    RetryStrategy,
    RuleChecklist,
)

logger = logging.getLogger(__name__)

_SECTION_DRAFT_TIMEOUT_S: int = 90  # Per-section draft cap (TC-2401 addendum); max_tokens ~1500–2048

_SECTION_TEMPLATES_PATH = Path(__file__).parent / "section_templates.yaml"

# TC-2524: Maximum section output length (characters). Safety net to prevent
# runaway LLM output from consuming excessive storage or downstream processing.
_MAX_SECTION_LENGTH: int = 15_000

# TC-2520: JSON Schemas for micro-task output contracts.
# Draft output must have a "content" key; metadata is optional.
_DRAFT_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["heading", "body"],
    "properties": {
        "heading": {"type": "string"},
        "level": {"type": "integer"},
        "body": {"type": "string"},
        "claim_ids_used": {"type": "array", "items": {"type": "string"}},
        "code_blocks": {"type": "array"},
    },
}

_REFINE_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["content"],
    "properties": {
        "content": {"type": "string"},
        "metadata": {"type": "object"},
    },
}

_section_draft_validator = OutputSchemaValidator(_DRAFT_OUTPUT_SCHEMA)
_failure_classifier = FailureClassifier()
_retry_strategy = RetryStrategy(max_retries=2)

# TC-2521: Per-section-type rule checklists.
# Keys match page_role values from section_templates.yaml.
_SECTION_RULE_CHECKLISTS: Dict[str, List[str]] = {
    "getting_started": [
        "Include import statements at the top of every code example.",
        "Every code example must be runnable as-is (no pseudo-code).",
        "Use pip install commands in the prerequisites section.",
        "Keep prose concise -- prefer code over explanation.",
        "End with a clear next-steps section linking to deeper docs.",
    ],
    "tutorial": [
        "Structure content as numbered steps.",
        "Each step must include a code example.",
        "Include prerequisite checks before the first step.",
        "Use inline comments in code blocks to explain key lines.",
        "Avoid marketing language -- be technical and precise.",
        "End with a working, complete code example.",
    ],
    "howto_article": [
        "State the goal clearly in the first sentence.",
        "Include a 'When to Use' section before the steps.",
        "Each step must have a code snippet and explanation.",
        "Use concrete values in examples, not placeholders.",
        "Include error handling in code examples.",
        "Link to the API reference for methods used.",
    ],
    "api_reference": [
        "List all parameters with types and descriptions.",
        "Include a return-type annotation for every method.",
        "Provide at least one code example per class.",
        "Document exceptions that can be raised.",
        "Use docstring-style formatting for parameter tables.",
    ],
    "blog": [
        "Open with a compelling technical problem statement.",
        "Include at least one complete code example.",
        "Keep paragraphs to 3-4 sentences maximum.",
        "End with a clear call-to-action or summary.",
        "Use sub-headings every 200-300 words.",
    ],
    "feature_showcase": [
        "Lead with the user benefit, not the API name.",
        "Include before/after code comparisons where relevant.",
        "Keep code examples focused on one feature per block.",
        "Mention supported formats explicitly when applicable.",
        "Link to the getting-started guide for setup instructions.",
    ],
    "format_conversion": [
        "List all supported source and target formats.",
        "Include a code example for the most common conversion.",
        "Mention any format-specific limitations.",
        "Show how to handle conversion errors.",
        "Include file I/O examples (open, save, close).",
    ],
    "default": [
        "Write in clear, technical prose.",
        "Include code examples where relevant.",
        "Use claim markers (<!-- claim: id -->) for every factual statement.",
        "Keep headings descriptive and concise.",
        "Avoid marketing or promotional language.",
    ],
}


# C2: Truncated sentence detection regex
_SENTENCE_TERMINAL_RE = re.compile(r'[.!?:]\s*$|```\s*$|-->\s*$')


def _trim_truncated_ending(body: str) -> str:
    """Trim a truncated ending from LLM output (max_tokens cutoff mid-sentence).

    If the body doesn't end with sentence-terminal punctuation (. ! ? : ``` -->),
    trim to the last complete sentence. Preserves at least 50% of the content.
    """
    body = body.rstrip()
    if not body:
        return body
    if _SENTENCE_TERMINAL_RE.search(body):
        return body
    # Find last complete sentence boundary
    min_keep = len(body) // 2
    # Try ". " or ".\n" first (prose sentence end)
    for sep in (". ", ".\n", "! ", "!\n", "? ", "?\n"):
        pos = body.rfind(sep, min_keep)
        if pos > 0:
            return body[: pos + 1]
    # Try just "." at end of a word
    pos = body.rfind(".", min_keep)
    if pos > 0:
        return body[: pos + 1]
    # No good boundary found — return as-is rather than destroying content
    return body


def _truncate_to_length(content: str, max_length: int = _MAX_SECTION_LENGTH) -> str:
    """Truncate *content* at the last paragraph boundary before *max_length*.

    TC-2524: Safety net for runaway LLM output. Truncates at the last blank
    line (paragraph boundary) before the limit. If no blank line is found,
    truncates at the last sentence boundary instead.

    Args:
        content:    The content string to truncate.
        max_length: Maximum allowed character length.

    Returns:
        The (possibly truncated) content string.
    """
    if len(content) <= max_length:
        return content

    logger.warning(
        "W5_OUTPUT_TRUNCATED: content length %d exceeds max %d -- truncating",
        len(content), max_length,
    )
    # Find last paragraph boundary (blank line) before limit
    search_region = content[:max_length]
    last_blank = search_region.rfind("\n\n")
    if last_blank > max_length // 2:
        return content[:last_blank].rstrip()

    # Fallback: last sentence boundary
    for sep in (". ", ".\n", "! ", "!\n", "? ", "?\n"):
        pos = search_region.rfind(sep)
        if pos > max_length // 2:
            return content[: pos + 1]

    # Hard cut at limit (should be rare)
    return content[:max_length]


def _get_rule_checklist(page_role: str) -> str:
    """Return the formatted rule checklist for a page role (TC-2521).

    Args:
        page_role: The page role key (e.g. ``"getting_started"``).

    Returns:
        Formatted rules string for prompt injection, or empty string.
    """
    rules = _SECTION_RULE_CHECKLISTS.get(
        page_role,
        _SECTION_RULE_CHECKLISTS.get("default", []),
    )
    if not rules:
        return ""
    checklist = RuleChecklist(rules=rules)
    return checklist.format_for_prompt()


def _validate_section_output(
    raw: str,
    heading: str,
    slug: str,
    section_idx: int,
) -> Optional[Dict[str, Any]]:
    """Validate and parse a section draft against the output schema (TC-2520).

    Returns the parsed dict on success, or ``None`` if validation failed.
    Logs validation results at debug level.
    """
    ok, parsed, err = _section_draft_validator.validate(raw)
    if ok and parsed is not None:
        logger.debug(
            "W5_SCHEMA_OK section=%s slug=%s idx=%d",
            heading, slug, section_idx,
        )
        return parsed
    logger.debug(
        "W5_SCHEMA_FAIL section=%s slug=%s idx=%d error=%s",
        heading, slug, section_idx, err,
    )
    return None


# ---------------------------------------------------------------------------
# TC-2376: Per-section draft helpers (module-level, not class methods)
# ---------------------------------------------------------------------------

def _get_section_claims(
    section_claim_ids: List[str],
    all_page_claims: List[Dict[str, Any]],
    max_claims: int = 5,
    page_index: int = 0,
) -> List[Dict[str, Any]]:
    """Return up to max_claims claim dicts matching the given section claim IDs.

    Falls back to page claims with a page_index-based offset for diversity,
    so different pages get different claims when no section IDs are provided.
    """
    if not section_claim_ids:
        offset = page_index * max_claims
        pool = all_page_claims[offset:offset + max_claims]
        return pool if pool else all_page_claims[:max_claims]
    id_set = set(section_claim_ids)
    matched = [c for c in all_page_claims if c.get("claim_id") in id_set]
    return matched[:max_claims] if matched else all_page_claims[:max_claims]


def _get_section_snippets(
    section_claims: List[Dict[str, Any]],
    all_snippets: List[Dict[str, Any]],
    max_snippets: int = 2,
) -> List[Dict[str, Any]]:
    """Return up to max_snippets snippet dicts linked to the given claims.

    Uses demo_snippet_ids on each claim. Falls back to the first max_snippets
    snippets from all_snippets when no linked snippets exist.
    """
    seen: set = set()
    snippet_ids: List[str] = []
    for c in section_claims:
        for sid in c.get("demo_snippet_ids", []):
            if sid not in seen:
                snippet_ids.append(sid)
                seen.add(sid)
    if not snippet_ids:
        return all_snippets[:max_snippets]
    smap = {s.get("snippet_id", ""): s for s in all_snippets}
    result = [smap[sid] for sid in snippet_ids if sid in smap]
    return result[:max_snippets] if result else all_snippets[:max_snippets]


def _load_section_template(page_role: str) -> dict:
    """Load required/optional sections for a page role from section_templates.yaml.

    Args:
        page_role: The page role key (e.g. 'tutorial', 'api_reference').

    Returns:
        Dict with 'required_sections' and 'optional_sections' lists,
        or empty dict if the YAML cannot be loaded.
    """
    if yaml_mod is None:
        return {}
    try:
        with open(_SECTION_TEMPLATES_PATH, "r", encoding="utf-8") as f:
            templates = yaml_mod.safe_load(f)
        return templates.get(page_role, templates.get("default", {}))
    except Exception:
        return {}


@dataclass
class MultiPassResult:
    """Result of multi-pass content generation."""

    content: str
    outline: Optional[Dict] = None
    risks: List[Dict] = field(default_factory=list)
    success: bool = True
    pass_used: int = 0  # Which pass produced the final content (1=outline only, 2=draft, 3=refined)


class MultiPassOrchestrator:
    """
    3-pass content generation orchestrator.

    Passes:
    1. OUTLINE: Structure with claim mapping
    2. DRAFT: Full content generation
    3. REFINE: Polish with cross-page awareness

    Includes validation, fallback, and hallucination detection.
    """

    def __init__(self, llm_client, prompt_loader, run_config=None):
        """
        Initialize orchestrator.

        Args:
            llm_client: LLM client for generation.
            prompt_loader: Prompt loader for system/page prompts.
            run_config: Optional run configuration.
        """
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.run_config = run_config
        self.cross_page_summaries: Dict[str, str] = {}
        # TC-2376: Structured output envelope feature flags.
        # run_config may be a plain dict, a RunConfig dataclass (no .get()),
        # or a MockRunConfig object — only extract flags from dict-like objects.
        if isinstance(run_config, dict):
            self._use_json_draft: bool = run_config.get("use_json_draft", True)
            self._per_section_draft: bool = run_config.get("per_section_draft", True)
            # TC-2401: Within-page section parallelization.
            # When > 1, sections within a page are drafted concurrently.
            # Default 1 = sequential (backwards compatible).
            self._section_parallelism: int = max(1, int(run_config.get("max_parallel_sections", 1)))
        else:
            self._use_json_draft = True
            self._per_section_draft = True
            self._section_parallelism = 1
        # TC-2383: Source chunks for grounding (lazy-loaded from W2 artifact)
        self._source_chunks: list = []
        # TC-2479: Shared facts for canonical version/format references
        self._shared_facts: Dict[str, Any] = {}
        # TC-2812: API inventory for evidence-gated code generation
        self._api_inventory: Dict[str, Any] = {}

    def generate(self, page: Dict, rich_ctx: "RichContext") -> MultiPassResult:
        """
        3-pass generation: outline -> draft -> refine.

        Args:
            page: Page specification.
            rich_ctx: Rich context for generation.

        Returns:
            MultiPassResult with final content and metadata.
        """
        # Get config — run_config may be a RunConfig object (has .get_multi_pass_config()),
        # a plain dict (feature flags only, no multi-pass config), or None.
        if self.run_config is None:
            mp_config: Dict[str, Any] = {}
        elif isinstance(self.run_config, dict):
            mp_config = self.run_config
        else:
            mp_config = self.run_config.get_multi_pass_config()

        # C1: Zero-claim guard — pages with no claims use deterministic fallback
        all_page_claims = rich_ctx.page_claims if hasattr(rich_ctx, "page_claims") else []
        _nav_roles = {"toc", "landing", "index"}
        page_role = page.get("page_role", "")
        slug = page.get("slug", "unknown")
        if not all_page_claims and page_role not in _nav_roles and slug not in ("_index", "index"):
            logger.warning("W5_ZERO_CLAIM_PAGE slug=%s role=%s", slug, page_role)
            return MultiPassResult(
                content=self._deterministic_fallback(page, rich_ctx),
                pass_used=0,
                success=False,
            )

        # TC-2479: Lazy-load shared_facts for canonical version/format references
        if not self._shared_facts:
            try:
                _run_dir = (
                    self.run_config.get("run_dir")
                    if isinstance(self.run_config, dict)
                    else getattr(self.run_config, "run_dir", None)
                )
                if _run_dir:
                    sf_path = Path(_run_dir) / "artifacts" / "shared_facts.json"
                    if sf_path.exists():
                        self._shared_facts = json.loads(sf_path.read_text(encoding="utf-8"))
                        logger.info("loaded_shared_facts keys=%s", list(self._shared_facts.keys()))
            except Exception as e:
                logger.warning("shared_facts_load_failed: %s", e)

        # TC-2812: Lazy-load api_inventory for evidence-gated code generation
        if not self._api_inventory:
            try:
                _run_dir_inv = (
                    self.run_config.get("run_dir")
                    if isinstance(self.run_config, dict)
                    else getattr(self.run_config, "run_dir", None)
                )
                if _run_dir_inv:
                    inv_path = Path(_run_dir_inv) / "artifacts" / "api_inventory.json"
                    if inv_path.exists():
                        self._api_inventory = json.loads(inv_path.read_text(encoding="utf-8"))
                        logger.info(
                            "loaded_api_inventory classes=%d",
                            len(self._api_inventory.get("classes", [])),
                        )
            except Exception as e:
                logger.warning("api_inventory_load_failed: %s", e)

        # Pass 1: OUTLINE
        logger.info(f"Pass 1: Generating outline for {page.get('slug', 'unknown')}")
        outline = self._generate_outline(rich_ctx, page)
        if not self._validate_outline(outline, page):
            logger.warning(f"Outline validation failed, using deterministic outline")
            outline = self._deterministic_outline(page, rich_ctx)

        # Pass 2: DRAFT
        logger.info(f"Pass 2: Generating draft for {page.get('slug', 'unknown')}")
        draft = self._generate_draft(rich_ctx, outline, page)
        if not self._validate_draft(draft, page):
            logger.error(f"Draft validation failed, using deterministic fallback")
            return MultiPassResult(
                content=self._deterministic_fallback(page, rich_ctx),
                pass_used=0,
                success=False
            )

        # Check hallucination risk
        logger.info(f"Detecting hallucination risks in draft")
        risks = detect_hallucination_risk(draft, rich_ctx)
        if any(r.get("level") == "HIGH" for r in risks):
            logger.error(f"High hallucination risk detected, using deterministic fallback")
            return MultiPassResult(
                content=self._deterministic_fallback(page, rich_ctx),
                risks=risks,
                pass_used=0,
                success=False
            )

        # TC-2482/2483: Evidence pack consistency check (between draft and refine)
        try:
            evidence_packs = self._build_evidence_packs(outline, rich_ctx, page)
            consistency_violations = self._check_draft_consistency(draft, evidence_packs, page)
            if consistency_violations:
                logger.warning(
                    "W5_DRAFT_CONSISTENCY slug=%s violations=%d: %s",
                    slug, len(consistency_violations),
                    "; ".join(consistency_violations[:3]),
                )
                # Pass violations to refine stage as correction instructions
                self._pending_corrections = consistency_violations
        except Exception as _e:
            logger.debug("evidence_pack_check_skipped: %s", _e)

        # Pass 3: REFINE (always run for thin pages — forcing refinement to expand content)
        word_count = len(draft.split())
        if word_count < 250:
            logger.info(f"thin_page_force_refine words={word_count} — running refinement pass")

        logger.info(f"Pass 3: Refining draft for {page.get('slug', 'unknown')}")
        refined = self._refine_draft(rich_ctx, outline, draft, page)
        if not self._validate_refinement(draft, refined):
            logger.warning(f"Refinement validation failed, keeping draft")
            refined = draft  # Keep draft if refinement failed

        # TC-2393: Normalize assembled content (dedup headings, infer fence languages)
        refined = normalize_assembled_content(refined)

        # TC-2812: Post-generation code fence validation against api_inventory
        if self._api_inventory and self._api_inventory.get("classes"):
            refined = _sanitize_invalid_code_fences(refined, self._api_inventory)

        self._update_cross_page_summaries(refined, page)
        return MultiPassResult(content=refined, outline=outline, risks=risks, pass_used=3)

    def _load_source_chunks(self, run_dir) -> None:
        """Load source_chunks.json from artifacts if available (lazy load).

        TC-2383: Source chunks are produced by W2 chunk_sources and used to
        ground W5 section generation, reducing hallucination.
        """
        if run_dir is None or self._source_chunks:
            return
        try:
            source_chunks_path = Path(run_dir) / "artifacts" / "source_chunks.json"
            if source_chunks_path.exists():
                import json as _json
                data = _json.loads(source_chunks_path.read_text(encoding="utf-8"))
                self._source_chunks = data.get("chunks", [])
                logger.info("loaded_source_chunks count=%d", len(self._source_chunks))
        except Exception as e:
            logger.warning("source_chunks_load_failed error=%s", e)

    def _build_evidence_packs(
        self,
        outline: Dict,
        rich_ctx: "RichContext",
        page: Dict,
    ) -> List[Dict[str, Any]]:
        """Build per-section evidence packs from outline and context (TC-2482).

        Each evidence pack contains ONLY the facts needed for one section.
        Built ONCE deterministically before any LLM calls. This prevents
        cross-section fact leakage and enables post-draft consistency checking.

        Returns:
            List of evidence pack dicts, one per section in outline order.
        """
        all_claims = rich_ctx.page_claims if hasattr(rich_ctx, "page_claims") else []
        all_snippets = rich_ctx.relevant_snippets if hasattr(rich_ctx, "relevant_snippets") else []
        sections = (outline or {}).get("sections", [])
        slug = page.get("slug", "unknown")
        page_idx = abs(hash(slug)) % max(len(all_claims) if all_claims else 1, 1)

        packs: List[Dict[str, Any]] = []
        for i, section_spec in enumerate(sections):
            heading = section_spec.get("heading", f"Section {i + 1}")
            claim_ids = section_spec.get("claim_ids", [])

            section_claims = _get_section_claims(
                claim_ids, all_claims or [], max_claims=5, page_index=page_idx + i
            )
            section_snippets = _get_section_snippets(
                section_claims, all_snippets or [], max_snippets=2
            )

            pack: Dict[str, Any] = {
                "heading": heading,
                "level": section_spec.get("level", 2),
                "claim_ids": [c.get("claim_id", "") for c in section_claims],
                "claim_texts": [c.get("claim_text", "") for c in section_claims],
                "snippet_ids": [s.get("snippet_id", "") for s in section_snippets],
                "canonical_facts": {
                    k: v for k, v in self._shared_facts.items()
                    if k in ("runtime_versions", "package_name", "installation_method", "supported_formats")
                } if self._shared_facts else {},
                "forbidden_topics": page.get("content_strategy", {}).get("forbidden_topics", []),
            }
            packs.append(pack)

        return packs

    def _check_draft_consistency(
        self,
        draft: str,
        evidence_packs: List[Dict[str, Any]],
        page: Dict,
    ) -> List[str]:
        """Check draft against evidence packs for consistency violations (TC-2483/2527).

        Runs AFTER draft generation, BEFORE refine pass.
        All checks are deterministic (no LLM).

        Checks:
        1. Claim coverage (>50% missing = violation)
        2. Fact leakage (claim IDs not in evidence packs)
        3. Version mismatch against canonical min_python_version
        4. Package name mismatch against canonical product_name (TC-2527)

        Returns:
            List of violation strings with CORRECTION prefixes for the refine
            pass. Empty list means the draft is consistent.
        """
        violations: List[str] = []

        # 1. Check all evidence pack claim_ids appear as markers in draft
        all_pack_claim_ids: set = set()
        for pack in evidence_packs:
            all_pack_claim_ids.update(cid for cid in pack.get("claim_ids", []) if cid)

        marker_re = re.compile(r"<!--\s*claim:\s*([a-zA-Z0-9_-]+)\s*-->")
        found_markers = set(marker_re.findall(draft))

        if all_pack_claim_ids:
            missing_claims = all_pack_claim_ids - found_markers
            # Only flag if >50% of claims are missing (LLM may paraphrase some)
            if missing_claims and len(missing_claims) > len(all_pack_claim_ids) * 0.5:
                violations.append(
                    f"MISSING_CLAIMS: {len(missing_claims)}/{len(all_pack_claim_ids)} "
                    f"claim markers not in draft: {sorted(missing_claims)[:5]}"
                )

        # 2. Check for claim IDs NOT in any evidence pack (fact leakage)
        if found_markers and all_pack_claim_ids:
            leaked_claims = found_markers - all_pack_claim_ids
            if leaked_claims:
                violations.append(
                    f"LEAKED_CLAIMS: {len(leaked_claims)} claim IDs in draft "
                    f"not in evidence packs: {sorted(leaked_claims)[:5]}"
                )

        # 3. Check version strings against canonical facts
        if self._shared_facts:
            canonical_min = (
                self._shared_facts.get("runtime_versions", {})
                .get("python", {}).get("minimum", "")
            )
            if canonical_min and "." in canonical_min:
                try:
                    canonical_parts = tuple(int(x) for x in canonical_min.split("."))
                    version_re = re.compile(r"[Pp]ython\s*(?:>=?\s*)?(\d+)\.(\d+)")
                    for m in version_re.finditer(draft):
                        page_ver = (int(m.group(1)), int(m.group(2)))
                        if page_ver[0] != canonical_parts[0] or abs(page_ver[1] - canonical_parts[1]) > 1:
                            violations.append(
                                f"CORRECTION: The draft incorrectly states Python "
                                f"{m.group(1)}.{m.group(2)}, the canonical minimum "
                                f"version is Python {canonical_min}"
                            )
                except (ValueError, IndexError):
                    pass

        # 4. TC-2527: Check package name against canonical product_name
        if self._shared_facts:
            canonical_pkg = self._shared_facts.get("package_name", "")
            if canonical_pkg:
                pip_re = re.compile(r"pip\s+install\s+([a-zA-Z0-9._-]+)")
                for m in pip_re.finditer(draft):
                    found_pkg = re.split(r"[>=<!\[]", m.group(1))[0]
                    if found_pkg and found_pkg != canonical_pkg:
                        violations.append(
                            f"CORRECTION: The draft uses package name "
                            f"{found_pkg!r} but the canonical package name "
                            f"is {canonical_pkg!r}"
                        )

        return violations

    def _generate_outline(self, rich_ctx: "RichContext", page: Dict) -> Optional[Dict]:
        """
        Generate content outline with claim mapping.

        Args:
            rich_ctx: Rich context for generation.
            page: Page specification.

        Returns:
            Outline dict or None if generation failed.
        """
        try:
            # Load system prompt
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")

            system_prompt = self.prompt_loader.load("system/content_architect", **prompt_vars)

            # Generate outline via chat_completion
            # I-4: Include claim_text in outline request so draft pass has concrete material
            outline_user_message = (
                "Generate the content outline as JSON. "
                "Each section must include 'claim_ids' (list of IDs) AND "
                "'claim_texts' (list of corresponding claim text strings) "
                "so the draft writer has concrete material to expand — "
                "do not include IDs without their text."
            )

            # TC-2382: Inject role-specific required/optional section constraints
            page_role = page.get("page_role", "default")
            _tmpl = _load_section_template(page_role)
            _required = _tmpl.get("required_sections", [])
            _optional = _tmpl.get("optional_sections", [])
            if _required:
                _tmpl_instruction = (
                    "\n\nREQUIRED sections (must ALL appear in the outline, in any order):\n"
                    + "\n".join(f"- {s.replace('_', ' ').title()}" for s in _required)
                )
                if _optional:
                    _tmpl_instruction += (
                        "\n\nOPTIONAL sections (include if relevant to the content):\n"
                        + "\n".join(f"- {s.replace('_', ' ').title()}" for s in _optional)
                    )
                outline_user_message += _tmpl_instruction

            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt.text},
                    {
                        "role": "user",
                        "content": outline_user_message,
                    },
                ],
                call_id=f"mp_outline_{page.get('slug', 'unknown')}",
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            # Parse JSON from response
            # Try to extract JSON from markdown code blocks if present
            content = response_data["content"].strip()
            if "```json" in content:
                json_match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)
            elif "```" in content:
                json_match = re.search(r"```\s*\n(.*?)\n```", content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            outline = json.loads(content)
            return outline

        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return None

    def _generate_draft(self, rich_ctx: "RichContext", outline: Dict, page: Dict) -> str:
        """Generate content section by section (TC-2376 D-1 JSON + D-2 per-section).

        When ``self._per_section_draft`` is True (default), makes one LLM call per
        section requesting JSON output. Assembles sections into markdown via
        ``json_to_markdown()``. Falls back to ``_generate_draft_legacy()`` when the
        flag is False or when ``outline`` has no sections.

        Args:
            rich_ctx: Rich context for generation.
            outline: Content outline (must have a 'sections' list).
            page: Page specification.

        Returns:
            Draft content string.
        """
        if not self._per_section_draft:
            return self._generate_draft_legacy(rich_ctx, outline, page)

        # TC-2383: Lazy-load source chunks for grounding (uses run_dir from run_config if available)
        if not self._source_chunks:
            try:
                _run_dir = (
                    self.run_config.get("run_dir")
                    if isinstance(self.run_config, dict)
                    else getattr(self.run_config, "run_dir", None)
                )
                self._load_source_chunks(_run_dir)
            except Exception:
                pass

        sections = (outline or {}).get("sections", [])
        if not sections:
            return self._generate_draft_legacy(rich_ctx, outline, page)

        all_page_claims: List[Dict[str, Any]] = rich_ctx.page_claims or []
        all_snippets: List[Dict[str, Any]] = rich_ctx.relevant_snippets or []

        # Build a system prompt once for all section calls
        try:
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")
            prompt_vars["outline"] = json.dumps(outline, indent=2)
            prompt_vars["pre_generated_code_blocks"] = ""
            system_prompt = self.prompt_loader.load_with_fragments(
                "system/technical_writer",
                ["fragments/anti_hallucination"],
                **prompt_vars,
            )
            combined_system = system_prompt.text

            # A+.4: Inject cross-page dedup context to reduce gate_20 warnings
            cross_page_ctx = self._format_cross_page_summaries(self.cross_page_summaries)
            if cross_page_ctx and cross_page_ctx != "None" and cross_page_ctx.strip():
                combined_system += (
                    "\n\nPREVIOUSLY GENERATED PAGES:\n" + cross_page_ctx +
                    "\nIMPORTANT: Do NOT repeat paragraphs verbatim from these pages. "
                    "Use different phrasing and examples when covering similar topics."
                )

            # TC-2479: Inject canonical facts block for version/format consistency
            if self._shared_facts:
                py_ver = self._shared_facts.get("runtime_versions", {}).get("python", {})
                min_ver = py_ver.get("minimum", "")
                pkg = self._shared_facts.get("package_name", "")
                install = self._shared_facts.get("installation_method", "")
                formats = ", ".join(self._shared_facts.get("supported_formats", [])[:15])

                canonical_block = (
                    "\n\nCANONICAL FACTS (use these exact values "
                    "-- never invent versions or names):\n"
                )
                if min_ver:
                    canonical_block += f"- Python requirement: Python {min_ver}+\n"
                if pkg:
                    canonical_block += (
                        f"- Package name: {pkg} "
                        f"(ALWAYS use EXACTLY `{pkg}` in every pip install command — "
                        f"NEVER use a different package name or spelling)\n"
                    )
                if install:
                    canonical_block += f"- Installation: {install}\n"
                if formats:
                    canonical_block += f"- Supported formats: {formats}\n"
                combined_system += canonical_block

            # TC-2812: Inject ALLOWED API SYMBOLS block for evidence-gated code gen
            if self._api_inventory and self._api_inventory.get("classes"):
                api_block = _format_api_symbols_block(self._api_inventory)
                if api_block:
                    combined_system += api_block

            # TC-2521: Inject per-section-type rule checklist into system prompt
            _page_role = page.get("page_role", "default")
            _rules_text = _get_rule_checklist(_page_role)
            if _rules_text:
                combined_system += "\n\n" + _rules_text
        except Exception as _e:
            logger.warning("TC-2376: could not build system prompt for per-section draft: %s", _e)
            combined_system = (
                "You are a technical documentation writer. "
                "Generate clear, accurate markdown for the given section as JSON."
            )

        assembled_sections: List[Dict[str, Any]] = []
        prev_section_summary = ""
        slug = page.get("slug", "unknown")
        # Derive a page-level offset for claim diversity across pages
        _page_idx = abs(hash(slug)) % max(len(all_page_claims), 1)

        # TC-2401: Parallel section drafting.
        # When max_parallel_sections > 1, draft all sections concurrently using
        # ThreadPoolExecutor. Results are assembled in original index order.
        # Trade-off: no prev_section_summary chaining in parallel mode (minor quality
        # impact; the outline in combined_system provides full structural context).
        if self._section_parallelism > 1 and len(sections) > 1:
            _llm = self.llm_client
            _src_chunks = self._source_chunks

            def _draft_section_parallel(i_spec: tuple) -> tuple:
                """Draft one section concurrently. Returns (index, section_dict)."""
                _i, _spec = i_spec
                _heading = _spec.get("heading", f"Section {_i + 1}")
                _claim_ids = _spec.get("claim_ids", [])
                _sec_claims = _get_section_claims(
                    _claim_ids, all_page_claims, page_index=_page_idx + _i,
                )
                _sec_snippets = _get_section_snippets(_sec_claims, all_snippets)
                _claim_lines = "\n".join(
                    f"- [{c.get('claim_id', '')}] {c.get('claim_text', '')}"
                    for c in _sec_claims
                )
                _snippet_text = ""
                if _sec_snippets:
                    _snippet_text = "\n\nCode snippets:\n" + "\n".join(
                        f"```{s.get('language', 'python')}\n{s.get('code', '')[:200]}\n```"
                        for s in _sec_snippets
                    )
                _level = _spec.get("level", 2)
                _user_msg = (
                    f'Write the "{_heading}" section as JSON with this exact structure:\n'
                    f'{{"heading": "{_heading}", "level": {_level}, '
                    f'"body": "prose with <!-- claim: id --> markers", '
                    f'"claim_ids_used": ["claim-id"], '
                    f'"code_blocks": [{{"language": "python", "code": "...", "caption": "..."}}]}}\n\n'
                    f"Claims to cover:\n{_claim_lines}"
                    + _snippet_text
                )
                if _src_chunks:
                    try:
                        from launch.workers.w2_facts_builder.chunk_sources import retrieve_relevant_chunks
                        _query = _heading + " " + " ".join(
                            c.get("claim_text", "") for c in _sec_claims[:3]
                        )
                        _chunks = retrieve_relevant_chunks(_query, _src_chunks, top_k=3)
                        if _chunks:
                            _user_msg += "\n\nSource material for grounding:\n" + "\n\n---\n".join(
                                c["text"][:300] for c in _chunks
                            )
                    except Exception:
                        pass
                # TC-2520: Schema-validated draft with retry (parallel path)
                _max_tokens = max(
                    1500,
                    page.get("effective_token_budget", 2048) // max(1, len(sections)),
                )
                _last_raw = ""
                for _attempt in range(_retry_strategy.max_retries + 1):
                    try:
                        _resp = _llm.chat_completion(
                            messages=[
                                {"role": "system", "content": combined_system},
                                {"role": "user", "content": _user_msg},
                            ],
                            call_id=f"mp_section_{slug}_{_i}_a{_attempt}",
                            temperature=0.1,
                            max_tokens=_max_tokens,
                            response_format={"type": "json_object"},
                        )
                        _last_raw = _resp.get("content", "")

                        # TC-2520: Validate against schema first
                        _validated = _validate_section_output(
                            _last_raw, _heading, slug, _i,
                        )
                        if _validated is not None:
                            _validated.setdefault("heading", _heading)
                            _validated.setdefault("level", _level)
                            _body = _validated.get("body", "")
                            if _body:
                                _validated["body"] = _truncate_to_length(
                                    _trim_truncated_ending(_body),
                                )
                            return _i, _validated

                        # Schema validation failed -- try parse_json_draft fallback
                        _sec_json = parse_json_draft(_last_raw)
                        if _sec_json and isinstance(_sec_json, dict):
                            _sec_json.setdefault("heading", _heading)
                            _sec_json.setdefault("level", _level)
                            _body = _sec_json.get("body", "")
                            if _body:
                                _sec_json["body"] = _truncate_to_length(
                                    _trim_truncated_ending(_body),
                                )
                            return _i, _sec_json

                        # Classify and decide retry
                        _fc = _failure_classifier.classify("schema_error", _last_raw)
                        if not _retry_strategy.should_retry(_fc, _attempt):
                            break
                        logger.debug(
                            "W5_SCHEMA_RETRY section=%s attempt=%d class=%s",
                            _heading, _attempt, _fc,
                        )
                    except Exception as _e:
                        _fc = _failure_classifier.classify(str(_e), "")
                        if not _retry_strategy.should_retry(_fc, _attempt):
                            logger.error("Section parallel draft failed for '%s': %s", _heading, _e)
                            break
                        logger.debug(
                            "W5_CALL_RETRY section=%s attempt=%d class=%s",
                            _heading, _attempt, _fc,
                        )

                # All retries exhausted -- fall back to raw output or deterministic
                if _last_raw:
                    logger.warning(
                        "W5_ENVELOPE_PARSE_FAILURE: section '%s' returned non-JSON (parallel)",
                        _heading,
                    )
                    return _i, {
                        "heading": _heading, "level": _level,
                        "body": _truncate_to_length(
                            _last_raw[:500] if _last_raw else f"Content for {_heading}.",
                        ),
                        "code_blocks": [],
                    }
                return _i, {
                    "heading": _heading, "level": _level,
                    "body": "\n".join(
                        f"<!-- claim: {c.get('claim_id', '')} --> {c.get('claim_text', '')}"
                        for c in _sec_claims
                    ),
                    "code_blocks": [],
                }

            _n_workers = min(len(sections), self._section_parallelism)
            _par_results: Dict[int, Dict[str, Any]] = {}
            with ThreadPoolExecutor(max_workers=_n_workers, thread_name_prefix="sec_draft") as _pool:
                _futures = {
                    _pool.submit(_draft_section_parallel, (i, spec)): i
                    for i, spec in enumerate(sections)
                }
                for _fut in as_completed(_futures):
                    _idx, _sec = _fut.result()
                    _par_results[_idx] = _sec
            assembled_sections = [_par_results[i] for i in range(len(sections))]

        else:
            # Sequential path (original behavior): draft one section at a time,
            # passing prev_section_summary for continuity context.
            for i, section_spec in enumerate(sections):
                heading = section_spec.get("heading", f"Section {i + 1}")
                section_claim_ids = section_spec.get("claim_ids", [])
                section_claims = _get_section_claims(
                    section_claim_ids, all_page_claims, page_index=_page_idx + i,
                )
                section_snippets = _get_section_snippets(section_claims, all_snippets)

                claim_lines = "\n".join(
                    f"- [{c.get('claim_id', '')}] {c.get('claim_text', '')}"
                    for c in section_claims
                )
                snippet_text = ""
                if section_snippets:
                    snippet_text = "\n\nCode snippets:\n" + "\n".join(
                        f"```{s.get('language', 'python')}\n{s.get('code', '')[:200]}\n```"
                        for s in section_snippets
                    )

                level = section_spec.get("level", 2)
                user_message = (
                    f'Write the "{heading}" section as JSON with this exact structure:\n'
                    f'{{"heading": "{heading}", "level": {level}, '
                    f'"body": "prose with <!-- claim: id --> markers", '
                    f'"claim_ids_used": ["claim-id"], '
                    f'"code_blocks": [{{"language": "python", "code": "...", "caption": "..."}}]}}\n\n'
                    f"Claims to cover:\n{claim_lines}"
                    + (f"\n\nPrevious section summary: {prev_section_summary}" if prev_section_summary else "")
                    + snippet_text
                )

                # TC-2383: Source chunk retrieval for grounding
                if self._source_chunks:
                    try:
                        from launch.workers.w2_facts_builder.chunk_sources import retrieve_relevant_chunks
                        query = heading + " " + " ".join(c.get("claim_text", "") for c in section_claims[:3])
                        relevant_chunks = retrieve_relevant_chunks(query, self._source_chunks, top_k=3)
                        if relevant_chunks:
                            chunk_context = "\n\n---\n".join(c["text"][:300] for c in relevant_chunks)
                            user_message += f"\n\nSource material for grounding:\n{chunk_context}"
                    except Exception:
                        pass  # Never block generation

                # TC-2520: Schema-validated draft with retry (sequential path)
                _max_tok = max(1500, page.get("effective_token_budget", 2048) // max(1, len(sections)))
                _last_raw = ""
                _section_done = False
                for _attempt in range(_retry_strategy.max_retries + 1):
                    try:
                        response_data = self.llm_client.chat_completion(
                            messages=[
                                {"role": "system", "content": combined_system},
                                {"role": "user", "content": user_message},
                            ],
                            call_id=f"mp_section_{slug}_{i}_a{_attempt}",
                            temperature=0.1,
                            max_tokens=_max_tok,
                            response_format={"type": "json_object"},
                            timeout=_SECTION_DRAFT_TIMEOUT_S,
                        )
                        _last_raw = response_data.get("content", "")

                        # TC-2520: Validate against schema first
                        _validated = _validate_section_output(
                            _last_raw, heading, slug, i,
                        )
                        if _validated is not None:
                            _validated.setdefault("heading", heading)
                            _validated.setdefault("level", level)
                            body = _validated.get("body", "")
                            if body:
                                _validated["body"] = _truncate_to_length(
                                    _trim_truncated_ending(body),
                                )
                            assembled_sections.append(_validated)
                            body = _validated.get("body", "")
                            prev_section_summary = body[:100].strip() if body else heading
                            _section_done = True
                            break

                        # Schema validation failed -- try parse_json_draft fallback
                        section_json = parse_json_draft(_last_raw)
                        if section_json and isinstance(section_json, dict):
                            section_json.setdefault("heading", heading)
                            section_json.setdefault("level", level)
                            body = section_json.get("body", "")
                            if body:
                                section_json["body"] = _truncate_to_length(
                                    _trim_truncated_ending(body),
                                )
                            assembled_sections.append(section_json)
                            body = section_json.get("body", "")
                            prev_section_summary = body[:100].strip() if body else heading
                            _section_done = True
                            break

                        # Classify and decide retry
                        _fc = _failure_classifier.classify("schema_error", _last_raw)
                        if not _retry_strategy.should_retry(_fc, _attempt):
                            break
                        logger.debug(
                            "W5_SCHEMA_RETRY section=%s attempt=%d class=%s",
                            heading, _attempt, _fc,
                        )
                    except Exception as e:
                        _fc = _failure_classifier.classify(str(e), "")
                        if not _retry_strategy.should_retry(_fc, _attempt):
                            logger.error("Section draft failed for '%s': %s", heading, e)
                            break
                        logger.debug(
                            "W5_CALL_RETRY section=%s attempt=%d class=%s",
                            heading, _attempt, _fc,
                        )

                if not _section_done:
                    # All retries exhausted -- fall back
                    if _last_raw:
                        logger.warning(
                            "W5_ENVELOPE_PARSE_FAILURE: section '%s' returned non-JSON; using raw text",
                            heading,
                        )
                        assembled_sections.append(
                            {
                                "heading": heading,
                                "level": level,
                                "body": _truncate_to_length(
                                    _last_raw[:500] if _last_raw else f"Content for {heading}.",
                                ),
                                "code_blocks": [],
                            }
                        )
                    else:
                        assembled_sections.append(
                            {
                                "heading": heading,
                                "level": level,
                                "body": "\n".join(
                                    f"<!-- claim: {c.get('claim_id', '')} --> {c.get('claim_text', '')}"
                                    for c in section_claims
                                ),
                                "code_blocks": [],
                            }
                        )
                    prev_section_summary = heading

        if not assembled_sections:
            return self._deterministic_fallback(page, rich_ctx)

        return json_to_markdown({"sections": assembled_sections}, page)

    def _generate_draft_legacy(self, rich_ctx: "RichContext", outline: Dict, page: Dict) -> str:
        """Legacy single-shot full-page draft (pre TC-2376 path).

        Called when ``per_section_draft`` is False, or as a fallback when
        the outline has no sections.

        TC-2393: Code-first pass — before prose generation, identify code-heavy sections
        (install, example, usage, start, basic, code) and generate their code blocks with
        API-only context at low temperature. Pre-generated code blocks are injected into
        the prompt so the prose writer places code FIRST in each section.

        Args:
            rich_ctx: Rich context for generation.
            outline: Content outline.
            page: Page specification.

        Returns:
            Draft content string.
        """
        # TC-2393: Code-first pass — generate code blocks before prose
        _CODE_KEYWORDS = {"install", "example", "usage", "start", "basic", "code"}
        code_sections: Dict[str, Any] = {}
        try:
            page_claims = rich_ctx.page_claims or []
            for section in (outline or {}).get("sections", []):
                heading = section.get("heading", "")
                if not any(kw in heading.lower() for kw in _CODE_KEYWORDS):
                    continue
                # Gather API signatures from claims assigned to this section
                section_claim_ids = set(section.get("claim_ids", []))
                section_claims = [
                    c for c in page_claims
                    if c.get("claim_id", "") in section_claim_ids
                ] or page_claims  # Fall back to all page claims if none matched
                api_sigs = [
                    c.get("claim_text", "")
                    for c in section_claims
                    if "(" in c.get("claim_text", "")
                ]
                if not api_sigs:
                    continue
                cb = generate_code_block(heading, api_sigs, self.llm_client)
                code_sections[heading] = cb
                logger.info(
                    "TC-2393 code_first: generated code block for section=%s valid=%s",
                    heading,
                    cb.is_valid,
                )
        except Exception as _code_err:
            logger.warning("TC-2393 code_first pass failed (non-fatal): %s", _code_err)

        try:
            # Load system prompt with anti-hallucination fragment
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")
            prompt_vars["outline"] = json.dumps(outline, indent=2)

            # TC-2393: Inject pre-generated code blocks into the prompt context so the
            # prose writer knows to place them FIRST (before explanation paragraphs).
            if code_sections:
                code_hint_lines = [
                    "Pre-generated code blocks (place FIRST in each section, before prose):"
                ]
                for heading, cb in code_sections.items():
                    fence = f"```{cb.language}\n{cb.code}\n```"
                    code_hint_lines.append(f"\n### {heading}\n{fence}")
                prompt_vars["pre_generated_code_blocks"] = "\n".join(code_hint_lines)
            else:
                prompt_vars["pre_generated_code_blocks"] = ""

            system_prompt = self.prompt_loader.load_with_fragments(
                "system/technical_writer",
                ["fragments/anti_hallucination"],
                **prompt_vars
            )

            # Load page-role specific prompt
            page_role = rich_ctx.page_role or "default"
            try:
                page_prompt = self.prompt_loader.load(f"pages/{page_role}", **prompt_vars)
            except Exception as e:
                logger.warning(f"Failed to load page prompt for {page_role}, using default: {e}")
                page_prompt = self.prompt_loader.load("pages/default", **prompt_vars)

            # Combine system + page prompts
            combined_prompt = f"{system_prompt.text}\n\n{page_prompt.text}"

            # Generate draft via chat_completion
            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": combined_prompt},
                    {"role": "user", "content": f"Write the full page for: {page.get('title', '')}"},
                ],
                call_id=f"mp_draft_{page.get('slug', 'unknown')}",
                temperature=0.1,
                max_tokens=4000,
            )

            # TC-2524: Bounded output length enforcement
            return _truncate_to_length(response_data["content"].strip())

        except Exception as e:
            logger.error(f"Draft generation failed: {e}")
            return ""

    def _refine_draft(self, rich_ctx: "RichContext", outline: Dict, draft: str, page: Dict) -> str:
        """
        Refine draft with cross-page awareness.

        Args:
            rich_ctx: Rich context for generation.
            outline: Content outline.
            draft: Draft content.
            page: Page specification.

        Returns:
            Refined content string.
        """
        try:
            # Load system prompt
            prompt_vars = rich_ctx.to_prompt_vars()
            prompt_vars["slug"] = page.get("slug", "")
            prompt_vars["title"] = page.get("title", "")
            prompt_vars["outline"] = json.dumps(outline, indent=2)
            prompt_vars["draft"] = draft
            prompt_vars["cross_page_summaries"] = self._format_cross_page_summaries(
                self.cross_page_summaries
            )

            system_prompt = self.prompt_loader.load("system/content_editor", **prompt_vars)

            # TC-2483: Inject consistency corrections into refine prompt
            refine_user_msg = "Refine the draft for clarity, flow, and cross-page consistency."
            corrections = getattr(self, '_pending_corrections', [])
            if corrections:
                refine_user_msg += (
                    "\n\nCORRECTIONS NEEDED (fix these in the refined version):\n"
                    + "\n".join(f"- {v}" for v in corrections[:5])
                )
                self._pending_corrections = []

            # Generate refinement via chat_completion
            response_data = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt.text},
                    {"role": "user", "content": refine_user_msg},
                ],
                call_id=f"mp_refine_{page.get('slug', 'unknown')}",
                temperature=0.3,
                max_tokens=4000,
            )

            # TC-2524: Bounded output length enforcement
            return _truncate_to_length(response_data["content"].strip())

        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return draft

    def _validate_outline(self, outline: Optional[Dict], page: Dict) -> bool:
        """
        Validate outline structure.

        Args:
            outline: Outline dict to validate.
            page: Page specification.

        Returns:
            True if outline is valid.
        """
        if not outline:
            return False

        if not isinstance(outline, dict):
            logger.warning(f"Outline is not a dict: {type(outline)}")
            return False

        if "sections" not in outline:
            logger.warning(f"Outline missing 'sections' key")
            return False

        sections = outline["sections"]
        if not isinstance(sections, list):
            logger.warning(f"Outline 'sections' is not a list: {type(sections)}")
            return False

        for i, section in enumerate(sections):
            if not isinstance(section, dict):
                logger.warning(f"Section {i} is not a dict: {type(section)}")
                return False

            if "heading" not in section:
                logger.warning(f"Section {i} missing 'heading' key")
                return False

            if "claim_ids" not in section:
                logger.warning(f"Section {i} missing 'claim_ids' key")
                return False

        return True

    def _validate_draft(self, draft: str, page: Dict) -> bool:
        """
        Validate draft content.

        Args:
            draft: Draft content string.
            page: Page specification.

        Returns:
            True if draft is valid.
        """
        if not draft:
            logger.warning(f"Draft is empty")
            return False

        # Check minimum word count (configurable)
        min_words = 50  # Could be made configurable
        word_count = len(draft.split())
        if word_count < min_words:
            logger.warning(f"Draft too short: {word_count} words (minimum {min_words})")
            return False

        # Check for at least 1 claim marker (HTML comment or bracket format)
        claim_markers = re.findall(
            r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
            draft,
        )
        if not claim_markers:
            logger.warning(f"Draft contains no claim markers")
            return False

        return True

    def _validate_refinement(self, draft: str, refined: str) -> bool:
        """
        Validate that refinement preserved key elements.

        Args:
            draft: Original draft content.
            refined: Refined content.

        Returns:
            True if refinement is valid.
        """
        if not refined:
            logger.warning(f"Refined content is empty")
            return False

        # Check claim markers preserved (count in refined >= count in draft * 0.9)
        _marker_re = r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]"
        draft_markers = re.findall(_marker_re, draft)
        refined_markers = re.findall(_marker_re, refined)

        min_markers = int(len(draft_markers) * 0.9)
        if len(refined_markers) < min_markers:
            logger.warning(
                f"Refinement lost too many claim markers: "
                f"{len(refined_markers)} < {min_markers} (90% of {len(draft_markers)})"
            )
            return False

        # Check word count not decreased >10%
        draft_words = len(draft.split())
        refined_words = len(refined.split())

        min_words = int(draft_words * 0.9)
        if refined_words < min_words:
            logger.warning(
                f"Refinement reduced word count too much: "
                f"{refined_words} < {min_words} (90% of {draft_words})"
            )
            return False

        return True

    def _deterministic_outline(self, page: Dict, rich_ctx: "RichContext") -> Dict:
        """
        Create basic outline from required_headings and page_claims.

        Args:
            page: Page specification.
            rich_ctx: Rich context.

        Returns:
            Deterministic outline dict.
        """
        sections = []

        # Use required headings if available
        required_headings = rich_ctx.required_headings
        if required_headings:
            for heading in required_headings:
                sections.append({"heading": heading, "claim_ids": []})
        else:
            # Default sections based on page role
            page_role = rich_ctx.page_role
            if page_role == "tutorial":
                sections = [
                    {"heading": "Introduction", "claim_ids": []},
                    {"heading": "Prerequisites", "claim_ids": []},
                    {"heading": "Step-by-Step Guide", "claim_ids": []},
                    {"heading": "Conclusion", "claim_ids": []},
                ]
            elif page_role == "faq":
                sections = [
                    {"heading": "Frequently Asked Questions", "claim_ids": []},
                ]
            else:
                sections = [
                    {"heading": "Overview", "claim_ids": []},
                    {"heading": "Details", "claim_ids": []},
                ]

        # Distribute claims across sections
        # I-4: Include claim_text alongside claim_id so draft LLM has concrete material
        page_claims = rich_ctx.page_claims
        if page_claims and sections:
            claims_per_section = len(page_claims) // len(sections)
            remainder = len(page_claims) % len(sections)

            claim_idx = 0
            for i, section in enumerate(sections):
                num_claims = claims_per_section + (1 if i < remainder else 0)
                slice_claims = [
                    page_claims[claim_idx + j]
                    for j in range(num_claims)
                    if claim_idx + j < len(page_claims)
                ]
                section["claim_ids"] = [c.get("claim_id", "") for c in slice_claims]
                section["claim_texts"] = [c.get("claim_text", "") for c in slice_claims]
                claim_idx += num_claims

        return {"sections": sections}

    def _deterministic_fallback(self, page: Dict, rich_ctx: "RichContext") -> str:
        """
        Generate minimal content with headings and claim markers only (no LLM).

        Args:
            page: Page specification.
            rich_ctx: Rich context.

        Returns:
            Minimal content string.
        """
        lines = []

        # Title
        title = page.get("title", "")
        if title:
            lines.append(f"# {title}")
            lines.append("")

        # Introduction
        lines.append("## Introduction")
        lines.append("")
        short_description = rich_ctx.short_description
        if short_description:
            lines.append(short_description)
            lines.append("")

        # Required headings with claim markers
        required_headings = rich_ctx.required_headings
        page_claims = rich_ctx.page_claims

        if required_headings:
            claims_per_section = len(page_claims) // len(required_headings) if page_claims else 0

            for i, heading in enumerate(required_headings):
                lines.append(f"## {heading}")
                lines.append("")

                # Add claim markers for this section
                start_idx = i * claims_per_section
                end_idx = start_idx + claims_per_section
                for claim in page_claims[start_idx:end_idx]:
                    claim_id = claim.get("claim_id", "")
                    claim_text = claim.get("claim_text", "")
                    lines.append(f"<!-- claim: {claim_id} --> {claim_text}")
                    lines.append("")

        else:
            # Just list all claims
            lines.append("## Details")
            lines.append("")
            for claim in page_claims:
                claim_id = claim.get("claim_id", "")
                claim_text = claim.get("claim_text", "")
                lines.append(f"<!-- claim: {claim_id} --> {claim_text}")
                lines.append("")

        return "\n".join(lines)

    def _update_cross_page_summaries(self, content: str, page: Dict) -> None:
        """
        Extract summary from content and store in cross_page_summaries.

        Args:
            content: Generated content.
            page: Page specification.
        """
        slug = page.get("slug", "")
        if not slug:
            return

        # Extract first 200 characters as summary
        # Strip markdown headings and claim markers for cleaner summary
        clean_content = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
        clean_content = re.sub(
            r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
            "",
            clean_content,
        )
        clean_content = clean_content.strip()

        summary = clean_content[:200]
        if len(clean_content) > 200:
            summary += "..."

        self.cross_page_summaries[slug] = summary

    def _format_cross_page_summaries(self, summaries: Dict[str, str]) -> str:
        """
        Format cross-page summaries for prompt.

        Args:
            summaries: Dict mapping slug to summary.

        Returns:
            Formatted string.
        """
        if not summaries:
            return "None"

        lines = []
        for slug, summary in summaries.items():
            lines.append(f"[{slug}] {summary}")

        return "\n".join(lines)


def detect_hallucination_risk(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """
    8-layer hallucination detection.

    Layers:
    2. API names not in whitelist
    3. Code blocks not matching any snippet (basic Jaccard)
    4. Claim marker density check (< 1 per 150 words)
    7. Performance claims without claim markers

    Args:
        content: Generated content to check.
        rich_ctx: Rich context with reference data.

    Returns:
        List of risk dicts with layer, level, message, location.
    """
    risks = []

    # Layer 2: API names not in whitelist
    risks.extend(_check_api_names(content, rich_ctx))

    # Layer 3: Code blocks not matching any snippet
    risks.extend(_check_code_blocks(content, rich_ctx))

    # Layer 4: Claim marker density
    risks.extend(_check_claim_density(content))

    # Layer 7: Performance claims without claim markers
    risks.extend(_check_performance_claims(content))

    return risks


def _check_api_names(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """Check for API names not in whitelist."""
    risks = []

    # Extract API-like names from content (CamelCase, snake_case with parens)
    api_pattern = r"\b([A-Z][a-zA-Z0-9_]*(?:\.[A-Z][a-zA-Z0-9_]*)*)\s*\("
    found_apis = set(re.findall(api_pattern, content))

    # Build whitelist from code understanding and snippets
    whitelist = set()

    # Add classes and functions from code understanding
    code_understanding = rich_ctx.code_understanding
    for cls in code_understanding.get("classes", []):
        whitelist.add(cls.get("name", ""))
    for func in code_understanding.get("functions", []):
        whitelist.add(func.get("name", ""))

    # Add APIs from snippets
    for snippet in rich_ctx.relevant_snippets:
        snippet_code = snippet.get("code", "")
        snippet_apis = re.findall(api_pattern, snippet_code)
        whitelist.update(snippet_apis)

    # Check for unknown APIs
    unknown_apis = found_apis - whitelist
    if unknown_apis:
        risks.append({
            "layer": 2,
            "level": "MEDIUM",
            "message": f"API names not in whitelist: {', '.join(sorted(unknown_apis)[:5])}",
            "location": "content"
        })

    return risks


def _check_code_blocks(content: str, rich_ctx: "RichContext") -> List[Dict]:
    """Check for code blocks not matching any snippet (basic Jaccard)."""
    risks = []

    # Extract code blocks
    code_blocks = re.findall(r"```(?:\w+)?\s*\n(.*?)\n```", content, re.DOTALL)
    if not code_blocks:
        return risks

    # Build snippet word sets
    snippet_word_sets = []
    for snippet in rich_ctx.relevant_snippets:
        snippet_code = snippet.get("code", "")
        words = set(re.findall(r"\w+", snippet_code.lower()))
        snippet_word_sets.append(words)

    # Check each code block
    for i, code_block in enumerate(code_blocks):
        code_words = set(re.findall(r"\w+", code_block.lower()))
        if not code_words:
            continue

        # Calculate max Jaccard similarity with any snippet
        max_similarity = 0.0
        for snippet_words in snippet_word_sets:
            intersection = len(code_words & snippet_words)
            union = len(code_words | snippet_words)
            similarity = intersection / union if union > 0 else 0.0
            max_similarity = max(max_similarity, similarity)

        # Flag if similarity too low
        if max_similarity < 0.3:
            risks.append({
                "layer": 3,
                "level": "HIGH",
                "message": f"Code block {i+1} has low similarity to snippets ({max_similarity:.2f})",
                "location": f"code_block_{i+1}"
            })

    return risks


def _check_claim_density(content: str) -> List[Dict]:
    """Check claim marker density (< 1 per 150 words)."""
    risks = []

    word_count = len(content.split())
    claim_markers = re.findall(
        r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
        content,
    )

    if word_count == 0:
        return risks

    density = len(claim_markers) / (word_count / 150)

    if density < 1.0:
        risks.append({
            "layer": 4,
            "level": "MEDIUM",
            "message": f"Low claim marker density: {density:.2f} per 150 words (expected >= 1.0)",
            "location": "content"
        })

    return risks


def _check_performance_claims(content: str) -> List[Dict]:
    """Check for performance claims without claim markers."""
    risks = []

    # Performance keywords
    perf_keywords = [
        r"\bfast(?:er)?\b",
        r"\bslow(?:er)?\b",
        r"\bperformance\b",
        r"\boptimiz(?:e|ed|ation)\b",
        r"\befficient(?:cy)?\b",
        r"\bhigh(?:-|\s)?throughput\b",
        r"\blow(?:-|\s)?latency\b",
        r"\bscalable?\b",
        r"\bspeed(?:up)?\b",
    ]

    # Find sentences with performance claims
    sentences = re.split(r"[.!?]\s+", content)
    for i, sentence in enumerate(sentences):
        # Check if sentence contains performance keyword
        has_perf_keyword = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in perf_keywords)

        if has_perf_keyword:
            # Check if sentence has claim marker
            has_claim_marker = re.search(
                r"<!--\s*claim:\s*[a-zA-Z0-9_\-]+\s*-->|\[claim:\s*[a-zA-Z0-9_\-]+\]",
                sentence,
            )

            if not has_claim_marker:
                risks.append({
                    "layer": 7,
                    "level": "MEDIUM",
                    "message": f"Performance claim without marker in sentence {i+1}",
                    "location": f"sentence_{i+1}"
                })

    return risks


# ---------------------------------------------------------------------------
# TC-2812/TC-2870: Evidence-gated code generation helpers
# ---------------------------------------------------------------------------

from launch.workers._shared.code_fence_validator import (
    validate_code_fence as _validate_fence_core,
    PYTHON_FENCE_RE as _PYTHON_FENCE_RE_W5,
)


def _format_api_symbols_block(inventory: Dict[str, Any]) -> str:
    """Format api_inventory as an ALLOWED API SYMBOLS block for prompt injection.

    TC-2812: Constrains LLM code generation to verified symbols only.
    Keeps block concise (top 20 classes max) to avoid context overflow.

    Phase 1: Prefers public_surface subset when confidence is not "unknown".
    """
    all_classes = inventory.get("classes", [])
    if not all_classes:
        return ""

    # Phase 1: Prefer public_surface when available and confident.
    # public_surface.classes may contain import paths (e.g. "aspose.threed.Scene")
    # or short names (backward compat). Build both sets for matching.
    public_surface = inventory.get("public_surface", {})
    ps_confidence = public_surface.get("confidence", "unknown")
    ps_import_paths = set(public_surface.get("classes", []))
    ps_short_names = {p.rsplit(".", 1)[-1] for p in ps_import_paths}
    ps_all_names = ps_import_paths | ps_short_names

    if ps_all_names and ps_confidence != "unknown":
        classes = [
            cls for cls in all_classes
            if (isinstance(cls, dict) and (
                cls.get("name", "") in ps_all_names
                or cls.get("import_path", "") in ps_all_names
            ))
            or (isinstance(cls, str) and cls in ps_all_names)
        ]
        if not classes:
            classes = all_classes  # Fallback if filter eliminated everything
    else:
        classes = all_classes

    if not classes:
        return ""

    lines: List[str] = []
    lines.append(
        "\n\nALLOWED API SYMBOLS (ONLY use these imports and class.method "
        "references in code examples — NEVER invent API names):"
    )

    pkg = inventory.get("package_name", "")
    if pkg:
        lines.append(f"- Package: {pkg}")

    modules = inventory.get("modules", [])
    if modules:
        lines.append(f"- Import roots: {', '.join(modules[:10])}")

    for cls in classes[:20]:  # Cap at 20 classes to avoid context overflow
        if isinstance(cls, dict):
            name = cls.get("name", "")
            imp = cls.get("import_path", "")
            methods = cls.get("methods", [])
            method_names = []
            for m in methods[:15]:  # Cap methods per class
                if isinstance(m, str):
                    method_names.append(m)
                elif isinstance(m, dict):
                    method_names.append(m.get("name", ""))
            method_str = ", ".join(n for n in method_names if n)
            if imp:
                lines.append(f"- {imp}: methods=[{method_str}]")
            elif name:
                lines.append(f"- {name}: methods=[{method_str}]")
        elif isinstance(cls, str):
            lines.append(f"- {cls}")

    lines.append(
        "If you need functionality NOT listed above, write comments-only "
        "pseudocode instead of inventing API names."
    )
    return "\n".join(lines) + "\n"


def _validate_code_fences_against_inventory(
    content: str,
    inventory: Dict[str, Any],
) -> List[Tuple[str, int, List[str]]]:
    """Validate Python code fences in content against API inventory.

    TC-2870: Now validates imports AND methods/constructors via shared library.

    Returns list of (code_str, match_start, error_messages) for invalid fences.
    """
    problems: List[Tuple[str, int, List[str]]] = []

    for match in _PYTHON_FENCE_RE_W5.finditer(content):
        code = match.group(1)
        issues = _validate_fence_core(
            code, inventory,
            check_methods=True,
            check_constructors=True,
        )
        if issues:
            errors = [f"{i.error_type}: {i.symbol}" for i in issues]
            problems.append((code, match.start(), errors))

    return problems


def _to_comments_only(code: str, errors: List[str]) -> str:
    """Convert a code block to comments-only pseudocode fallback.

    TC-2812: Used when code fence contains hallucinated API references
    that couldn't be validated against the api_inventory.
    """
    lines = code.strip().splitlines()
    comment_lines = ["# Code example (pseudocode — verify API references):"]
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            comment_lines.append(line)
        else:
            comment_lines.append(f"# {line}")
    return "\n".join(comment_lines)


def _sanitize_invalid_code_fences(
    content: str,
    inventory: Dict[str, Any],
) -> str:
    """Post-generation: validate and sanitize code fences against API inventory.

    TC-2812: Replaces code fences containing unknown imports with
    comments-only pseudocode. This is a last-resort safety net — the
    prompt injection (ALLOWED API SYMBOLS) should prevent most issues.
    """
    problems = _validate_code_fences_against_inventory(content, inventory)
    if not problems:
        return content

    # Process in reverse order to preserve character offsets
    result = content
    for code_str, match_start, errors in reversed(problems):
        logger.warning(
            "TC-2812: sanitizing code fence with %d unknown imports: %s",
            len(errors), "; ".join(errors[:3]),
        )
        # Find the full fence match (```python\n...\n```)
        fence_match = _PYTHON_FENCE_RE_W5.search(result, match_start)
        if fence_match and fence_match.start() == match_start:
            replacement = "```python\n" + _to_comments_only(code_str, errors) + "\n```"
            result = result[:fence_match.start()] + replacement + result[fence_match.end():]

    return result
