"""TC-PROSE-01: Specialized LLM prose quality review.

Evaluates writing quality separately from the main editorial review (Phase B).
Produces only ``prose_quality`` findings capped at MEDIUM severity.

Uses the same LLM call infrastructure as ``llm_review.py`` but with a
dedicated prompt focused on 5 prose dimensions: opening quality, narrative
flow, sentence variety, code integration, and specificity.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from launcher.models.evaluation import Finding
from launcher.orchestrator.worker_contract import WorkerContext
from launcher.workers.evaluate.llm_review import _prepare_content, _call_llm

logger = logging.getLogger(__name__)

_PROSE_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "review_prompt_prose.txt"

# Only this check name is accepted from the prose review LLM.
_ALLOWED_CHECK = "prose_quality"

# Minimum confidence to keep a finding.
_MIN_CONFIDENCE = 0.5

# Maximum severity allowed for prose findings.
_MAX_SEVERITY = "medium"

# Valid severity values in order of decreasing importance.
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _cap_severity(severity: str) -> str:
    """Cap severity to _MAX_SEVERITY."""
    sev = severity.lower()
    if sev not in _SEVERITY_ORDER:
        return _MAX_SEVERITY
    if _SEVERITY_ORDER.get(sev, 3) < _SEVERITY_ORDER[_MAX_SEVERITY]:
        return _MAX_SEVERITY
    return sev


async def prose_review_page(
    content: str,
    slug: str,
    page_role: str,
    page_title: str,
    product_name: str,
    platform: str,
    context: WorkerContext,
    *,
    phase_a_prose_findings: list[Finding] | None = None,
) -> list[Finding]:
    """Run specialized prose quality LLM review on a single page.

    Returns a list of ``prose_quality`` findings, each capped at MEDIUM severity
    and filtered by confidence threshold.

    Args:
        content: Rendered markdown content.
        slug: Page slug.
        page_role: Page role for role-aware judgment.
        page_title: Page title.
        product_name: Product display name.
        platform: Platform (python, java, etc.).
        context: Worker context with LLM config.
        phase_a_prose_findings: Optional deterministic prose findings from Phase A
            (injected into prompt for LLM awareness).

    Returns:
        List of prose_quality findings.
    """
    if not context.llm_config:
        return []

    # Load and format prompt
    try:
        template = _PROSE_PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        logger.warning("[ProseReview] Could not load prose review prompt")
        return []

    prepared_content, is_truncated = _prepare_content(content)
    content_note = "(Content was truncated for review.)" if is_truncated else ""
    word_count = len(content.split())

    prompt = template.format(
        display_name=product_name,
        platform=platform,
        page_title=page_title,
        page_role=page_role,
        word_count=word_count,
        page_content=prepared_content,
        content_note=content_note,
    )

    # Call LLM (force standard model — no reasoning overhead for prose review)
    raw = _call_llm(prompt, context, force_standard=True)
    if not raw:
        return []

    # Parse response
    return _parse_prose_response(raw, slug)


def _parse_prose_response(raw: str, slug: str) -> list[Finding]:
    """Parse the prose review LLM response into typed findings."""
    # Extract JSON from potential markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            logger.debug("[ProseReview] No JSON found in LLM response")
            return []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            logger.debug("[ProseReview] JSON parse failed")
            return []

    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), None)
        if data is None:
            return []

    findings: list[Finding] = []
    for f in data.get("prose_findings", []):
        if not isinstance(f, dict):
            continue

        # Validate check name
        check_name = f.get("check", "")
        if check_name != _ALLOWED_CHECK:
            logger.debug(
                "[ProseReview] Discarding finding with check name '%s' (expected '%s')",
                check_name, _ALLOWED_CHECK,
            )
            continue

        # Filter by confidence
        confidence = f.get("confidence", 0.0)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < _MIN_CONFIDENCE:
            continue

        # Cap severity
        severity = _cap_severity(f.get("severity", "medium"))

        findings.append(Finding(
            check=_ALLOWED_CHECK,
            message=f.get("message", ""),
            severity=severity,
            location=f.get("location", slug),
        ))

    return findings
