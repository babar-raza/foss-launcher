"""LLM-based claim extraction: prompt building, LLM call, JSON parsing."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

from launcher.models.claims import Snippet
from launcher.models.product import ProductIdentity
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.understand.extract._deterministic import _extract_claims_deterministic

logger = logging.getLogger(__name__)

# Maximum characters of source material sent to the LLM per batch
_MAX_SOURCE_CHARS = 32_000

# Discovery-mode task instructions (backward-compatible default for claim_extractor.txt).
# TC-4245: when no ExtractionDatabase facts are available the LLM operates in open-ended
# discovery mode using these instructions. TC-4246 will replace this with bounded-description
# instructions once ExtractionDatabase facts are injected via {verified_facts_block}.
_DISCOVERY_TASK_INSTRUCTIONS = """Extract every distinct, verifiable factual claim from the SOURCE CONTEXT above.
Each claim must be a single assertion that could be independently verified by
reading the source code, documentation, or configuration files.

RULES:
- Extract facts only — do NOT infer, speculate, or generalize
- Each claim must have at least one evidence anchor (source_file + line range or snippet)
- Use claim_id format: CLM-{family_slug}-NNN (zero-padded 3-digit sequence)
- Mark visibility as "internal" for implementation details not relevant to end users
- Set tier_relevance to "all" unless the claim only applies to a specific launch tier
- Do NOT merge multiple facts into a single claim — one assertion per claim
- Do NOT extract claims from test files unless they document public behavior"""

_DESCRIPTION_TASK_INSTRUCTIONS = """For each VERIFIED FACT above, write one user-facing claim statement describing that fact.

RULES:
1. Each claim MUST be derived from at least one VERIFIED FACT. Cite its fact_id in source_fact_id.
2. Claims about API classes/methods MUST use the exact class and method name from VERIFIED API FACTS.
   Do NOT use any class or method name not listed in VERIFIED API FACTS.
3. Claims about format support MUST use a format name from VERIFIED FORMAT FACTS.
   Do NOT claim support for formats not listed in VERIFIED FORMAT FACTS.
4. Synthesis claims combining 2-3 related facts are allowed; cite all contributing fact_ids.
5. If VERIFIED FACTS are sparse, produce fewer claims. Do NOT compensate by inventing content.
6. Use claim_id format: CLM-{family_slug}-NNN (zero-padded 3-digit sequence)"""

# Snippet context parameters for claim extraction enrichment
_SNIPPET_SAMPLE_MAX: int = 30
_SNIPPET_CHAR_BUDGET: int = 3_000  # Reduced from 8K: large prompts cause LLM read timeouts


def _build_snippet_context(snippets: "list[Snippet]") -> str:
    """Build a code-examples block for the LLM claim extractor.

    Selects up to _SNIPPET_SAMPLE_MAX snippets, deduplicates by SHA-256 hash of
    the full code body (TC-4210: replaces code[:200] prefix key which failed for
    long snippets sharing a common header), caps total characters at
    _SNIPPET_CHAR_BUDGET.  Returns empty string when no snippets are available.
    """
    if not snippets:
        return ""
    seen: set[str] = set()
    selected: list[str] = []
    total_chars = 0
    for s in snippets:
        key = hashlib.sha256(s.code.encode()).hexdigest()  # dedup by full body hash (TC-4210)
        if key in seen:
            continue
        seen.add(key)
        lang_tag = s.language or "python"  # TC-4061: use actual snippet language, not hardcoded python
        block = f"```{lang_tag}\n{s.code}\n```"
        if total_chars + len(block) > _SNIPPET_CHAR_BUDGET:
            break
        selected.append(block)
        total_chars += len(block)
        if len(selected) >= _SNIPPET_SAMPLE_MAX:
            break
    if not selected:
        return ""
    return (
        "\n\n## CODE EXAMPLES (extract API-level claims from these)\n\n"
        + "\n\n".join(selected)
    )


def _build_verified_facts_block(extraction_db: "Any", max_chars: int = 16_000) -> str:
    """Serialize ExtractionDatabase into a structured verified-facts block for the LLM.

    Produces VERIFIED API FACTS (class.member signatures + docstring),
    VERIFIED FORMAT FACTS (format name + import/export flags), and
    VERIFIED LIMITATION FACTS. Prioritizes higher-confidence facts first.
    Truncates at max_chars.

    TC-4246: replaces the 4000-char flat evidence context string in bounded-description mode.
    """
    if extraction_db is None:
        return ""
    parts: list[str] = []
    total = 0

    # API facts — highest priority
    api_facts = getattr(extraction_db, "api_facts", [])
    if api_facts:
        api_lines = ["VERIFIED API FACTS:"]
        for f in sorted(api_facts, key=lambda x: -getattr(x, "confidence", 1.0)):
            sig = getattr(f, "signature", "") or f"{getattr(f, 'class_name', '')}.{getattr(f, 'member_name', '')}"
            doc = getattr(f, "docstring", "")
            doc_preview = doc[:120].rstrip() if doc else ""
            line = f"  [{getattr(f, 'fact_id', '')}] {sig}"
            if doc_preview:
                line += f' — "{doc_preview}"'
            api_lines.append(line)
        block = "\n".join(api_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    # Format facts
    format_facts = getattr(extraction_db, "format_facts", [])
    if format_facts:
        fmt_lines = ["VERIFIED FORMAT FACTS:"]
        for f in sorted(format_facts, key=lambda x: -getattr(x, "confidence", 1.0)):
            can_import = getattr(f, "can_import", False)
            can_export = getattr(f, "can_export", False)
            flags: list[str] = []
            if can_import:
                flags.append("import")
            if can_export:
                flags.append("export")
            flags_str = "+".join(flags) if flags else "read"
            ext = getattr(f, "extension", "") or "no ext"
            conf = getattr(f, "confidence", 1.0)
            line = f"  [{getattr(f, 'fact_id', '')}] {getattr(f, 'format_name', '')} ({ext}): {flags_str} [conf={conf:.2f}]"
            fmt_lines.append(line)
        block = "\n".join(fmt_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    # Limitation facts
    limitation_facts = getattr(extraction_db, "limitation_facts", [])
    if limitation_facts:
        lim_lines = ["VERIFIED LIMITATION FACTS:"]
        for f in limitation_facts[:20]:
            feature = getattr(f, "feature", "")
            constraint = getattr(f, "constraint", "")
            line = f"  [{getattr(f, 'fact_id', '')}] {feature}: {constraint}"
            lim_lines.append(line)
        block = "\n".join(lim_lines)
        if total + len(block) <= max_chars:
            parts.append(block)
            total += len(block)

    if not parts:
        return ""
    return "\n\n".join(parts)


_MAX_RETRIES = 3  # TC-4224: retry before deterministic fallback


async def _extract_claims_llm(
    doc_contexts: list[dict[str, str]],
    product: ProductIdentity,
    context: WorkerContext,
    snippets: "list[Snippet] | None" = None,
    evidence_context: str = "",
    extraction_db: "Any" = None,
) -> list[dict[str, Any]]:
    """Attempt LLM-based claim extraction; fall back to deterministic parsing.

    The LLM call uses the ``claim_extractor.txt`` prompt template.
    TC-4002: evidence_context is injected into the prompt so the LLM
    sees source-verified facts before generating claims.
    TC-4224: retries up to _MAX_RETRIES times before falling back to
    deterministic extraction, to avoid transient failures producing
    low-confidence llm_fallback claims.
    """
    if context.llm_config and doc_contexts:
        for _attempt in range(1, _MAX_RETRIES + 1):
            try:
                llm_claims = _call_llm_extract(
                    doc_contexts, product, context,
                    snippets=snippets, evidence_context=evidence_context,
                    extraction_db=extraction_db,
                )
                if llm_claims:
                    for c in llm_claims:
                        c.setdefault("claim_source", "llm")
                    return llm_claims
                logger.warning(
                    "LLM claim extraction returned 0 claims (attempt %d/%d)",
                    _attempt, _MAX_RETRIES,
                )
            except Exception as exc:
                logger.warning(
                    "LLM claim extraction failed (attempt %d/%d): %s",
                    _attempt, _MAX_RETRIES, exc,
                )
        logger.warning("LLM claim extraction failed after %d attempts", _MAX_RETRIES)

    logger.warning(
        "llm_extraction_failed: LLM call failed or returned 0 claims — "
        "falling back to deterministic extraction. "
        "All fallback claims will be subject to strict api-kind filtering in run_extract(). "
        "[TC-HAL-04]"
    )
    fallback = _extract_claims_deterministic(doc_contexts, product)
    for c in fallback:
        c.setdefault("claim_source", "llm_fallback")
    return fallback


def _call_llm_extract(
    doc_contexts: list[dict[str, str]],
    product: ProductIdentity,
    context: WorkerContext,
    snippets: "list[Snippet] | None" = None,
    evidence_context: str = "",
    extraction_db: "Any" = None,
) -> list[dict[str, Any]]:
    """Call the LLM provider with the claim_extractor prompt.

    TC-4245: The prompt template now supports two operating modes via new template
    variables:
    - ``verified_facts_block``: Empty string for backward-compatible discovery mode;
      structured ExtractionDatabase facts for bounded-description mode (injected by
      TC-4246).
    - ``source_context_block``: Wraps ``source_material`` with the appropriate section
      label (``SOURCE CONTEXT`` in discovery mode; ``DOCUMENTATION CONTEXT`` in
      bounded-description mode).
    - ``task_instructions``: Either ``_DISCOVERY_TASK_INSTRUCTIONS`` (discovery mode)
      or the bounded-description instructions provided by TC-4246.

    Until TC-4246 is complete, all three new variables default to backward-compatible
    values so the prompt is a drop-in replacement for the previous version.
    """
    from launcher.clients.llm_provider import LLMProviderClient

    llm_cfg = context.llm_config
    assert llm_cfg is not None

    client = LLMProviderClient(
        api_base_url=llm_cfg.primary.base_url,
        model=llm_cfg.primary.model,
        run_dir=context.run_dir,
        api_key=os.environ.get("litellm_key"),
        temperature=0.0,  # U-3: pin temperature for deterministic claim extraction [TC-4226]
        max_tokens=llm_cfg.max_tokens,
        timeout=llm_cfg.request_timeout_s,
        fallback_api_base_url=(
            llm_cfg.fallback.base_url if llm_cfg.fallback else None
        ),
        fallback_model=(
            llm_cfg.fallback.model if llm_cfg.fallback else None
        ),
        reasoning_model=(
            llm_cfg.reasoning.model if llm_cfg.reasoning else None
        ),
        routing=llm_cfg.routing,
        telemetry_client=context.telemetry_client,
        telemetry_run_id=context.run_id,
        telemetry_trace_id=context.telemetry_trace_id,
        telemetry_parent_span_id="",
    )

    # Load prompt template
    prompt_path = Path(__file__).resolve().parents[3] / "prompts" / "claim_extractor.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")

    # Build source material from doc contexts
    source_parts: list[str] = []
    for ctx in doc_contexts:
        source_parts.append(f"--- {ctx['path']} ---\n{ctx['content']}")
    source_material = "\n\n".join(source_parts)

    # Append code snippet block to source material
    snippet_block = _build_snippet_context(snippets or [])
    if snippet_block:
        source_material = source_material + snippet_block

    # TC-4002: Inject evidence context (format matrix, limitations, API summary)
    if evidence_context:
        source_material = evidence_context + "\n\n" + source_material
        logger.info("evidence_context injected: %d chars", len(evidence_context))

    family_slug = re.sub(r"[^a-z0-9]", "-", product.family.lower()).strip("-")

    # Resolve the discovery instructions, expanding {family_slug} placeholder inside
    # the constant (the constant itself uses a {family_slug} format placeholder).
    discovery_instructions = _DISCOVERY_TASK_INSTRUCTIONS.format(
        family_slug=family_slug
    )

    # TC-4246: Activate bounded-description mode when ExtractionDatabase has verified facts.
    # Otherwise fall back to discovery mode (backward-compatible with TC-4245 defaults).
    _has_verified_facts = bool(
        extraction_db is not None
        and (getattr(extraction_db, "api_facts", None) or getattr(extraction_db, "format_facts", None))
    )
    if _has_verified_facts:
        verified_facts_block = _build_verified_facts_block(extraction_db, max_chars=16_000)
        source_context_block = (
            f"DOCUMENTATION CONTEXT (for wording only — do NOT extract new facts):\n{source_material}"
        )
        task_instructions = _DESCRIPTION_TASK_INSTRUCTIONS.format(family_slug=family_slug)
        logger.info(
            "bounded_description_mode_active: verified_facts_block=%d chars",
            len(verified_facts_block),
        )
    else:
        verified_facts_block = ""
        source_context_block = f"SOURCE CONTEXT:\n{source_material}"
        task_instructions = discovery_instructions
        logger.info("discovery_mode_active: no ExtractionDatabase facts available")

    prompt = prompt_template.format(
        family=product.family,
        platform=product.platform,
        repo_url=product.repo_url,
        family_slug=family_slug,
        # TC-4245/TC-4246 variables
        verified_facts_block=verified_facts_block,
        source_context_block=source_context_block,
        task_instructions=task_instructions,
        # Keep source_material for any legacy references in the template
        source_material=source_material,
    )

    response = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        call_id=f"extract-claims-{family_slug}",
        task_type="extract",
        timeout=720,  # TC-3885: 20K-token response at ~50-80 tok/s needs 250-400s; 720s gives 2x headroom
        max_tokens=20_000,  # Override: snippet-enriched prompts yield more claims; avoid finish_reason=length (TC-3884)
    )

    # Parse JSON from response
    text = response.get("content", "")
    return _parse_claims_json(text, product)


def _repair_json(text: str) -> str:
    """Attempt to fix common LLM JSON errors."""
    # Remove trailing commas before ] or }
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # Remove JS-style line comments (only at line start, to preserve URLs)
    text = re.sub(r"(?m)^\s*//[^\n]*", "", text)
    return text


def _parse_claims_json(text: str, product: ProductIdentity) -> list[dict[str, Any]]:
    """Extract and parse a JSON array of claims from LLM output text."""
    import json

    # Try to find JSON array in the response
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE)

    # Find the outermost JSON array
    bracket_start = cleaned.find("[")
    bracket_end = cleaned.rfind("]")

    if bracket_start == -1 or bracket_end == -1 or bracket_end <= bracket_start:
        logger.warning("No JSON array found in LLM response, falling back to empty")
        return []

    json_str = cleaned[bracket_start : bracket_end + 1]
    try:
        raw = json.loads(json_str)
    except json.JSONDecodeError:
        # Try repair
        repaired = _repair_json(json_str)
        try:
            raw = json.loads(repaired)
            logger.info("JSON repair succeeded for LLM claims")
        except json.JSONDecodeError as exc2:
            logger.warning("Failed to parse LLM claims JSON after repair: %s", exc2)
            return []

    if not isinstance(raw, list):
        return []

    return [item for item in raw if isinstance(item, dict)]
