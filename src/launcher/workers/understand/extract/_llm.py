"""LLM-based claim extraction: prompt building, LLM call, JSON parsing."""
from __future__ import annotations

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

# Snippet context parameters for claim extraction enrichment
_SNIPPET_SAMPLE_MAX: int = 30
_SNIPPET_CHAR_BUDGET: int = 3_000  # Reduced from 8K: large prompts cause LLM read timeouts


def _build_snippet_context(snippets: "list[Snippet]") -> str:
    """Build a code-examples block for the LLM claim extractor.

    Selects up to _SNIPPET_SAMPLE_MAX snippets, deduplicates by code content,
    caps total characters at _SNIPPET_CHAR_BUDGET.  Returns empty string when
    no snippets are available.
    """
    if not snippets:
        return ""
    seen: set[str] = set()
    selected: list[str] = []
    total_chars = 0
    for s in snippets:
        key = s.code[:200]  # dedup by first 200 chars
        if key in seen:
            continue
        seen.add(key)
        block = f"```python\n{s.code}\n```"
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


async def _extract_claims_llm(
    doc_contexts: list[dict[str, str]],
    product: ProductIdentity,
    context: WorkerContext,
    snippets: "list[Snippet] | None" = None,
    evidence_context: str = "",
) -> list[dict[str, Any]]:
    """Attempt LLM-based claim extraction; fall back to deterministic parsing.

    The LLM call uses the ``claim_extractor.txt`` prompt template.
    TC-4002: evidence_context is injected into the prompt so the LLM
    sees source-verified facts before generating claims.
    """
    if context.llm_config and doc_contexts:
        try:
            llm_claims = _call_llm_extract(
                doc_contexts, product, context,
                snippets=snippets, evidence_context=evidence_context,
            )
            if llm_claims:
                return llm_claims
            logger.warning(
                "LLM claim extraction returned 0 claims, falling back to deterministic"
            )
        except Exception as exc:
            logger.warning(
                "LLM claim extraction failed, falling back to deterministic: %s", exc
            )

    return _extract_claims_deterministic(doc_contexts, product)


def _call_llm_extract(
    doc_contexts: list[dict[str, str]],
    product: ProductIdentity,
    context: WorkerContext,
    snippets: "list[Snippet] | None" = None,
    evidence_context: str = "",
) -> list[dict[str, Any]]:
    """Call the LLM provider with the claim_extractor prompt."""
    from launcher.clients.llm_provider import LLMProviderClient

    llm_cfg = context.llm_config
    assert llm_cfg is not None

    client = LLMProviderClient(
        api_base_url=llm_cfg.primary.base_url,
        model=llm_cfg.primary.model,
        run_dir=context.run_dir,
        api_key=os.environ.get("litellm_key"),
        temperature=llm_cfg.temperature,
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
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "claim_extractor.txt"
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

    prompt = prompt_template.format(
        family=product.family,
        platform=product.platform,
        repo_url=product.repo_url,
        source_material=source_material,
        family_slug=family_slug,
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
