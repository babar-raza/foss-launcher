"""Phase B -- Typed LLM evaluation (sandwich model)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from launcher.models.evaluation import Finding, Grade
from launcher.orchestrator.worker_contract import WorkerContext

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "review_prompt.txt"
_LITE_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "review_prompt_lite.txt"

# TC-3882 Wave 4 (E7): Content chunking thresholds.
_PHASE_B_FULL_CHARS = 28_000   # send full content up to this limit
_PHASE_B_SAMPLE_CHARS = 80_000  # use section-weighted sampling beyond this


def _prepare_content(content: str, max_chars: int = _PHASE_B_FULL_CHARS) -> tuple[str, bool]:
    """Prepare content for Phase B review with chunking for large pages.

    TC-3882 Wave 4 (E7): Replaces hard 8000-char truncation with tiered chunking:
    - Tier 1 (≤max_chars): full content, truncated=False
    - Tier 2 (≤_PHASE_B_SAMPLE_CHARS): section-weighted sampling + all code blocks
    - Tier 3 (>_PHASE_B_SAMPLE_CHARS): first max_chars chars with note, truncated=True

    Returns (prepared_content, is_truncated).
    """
    if len(content) <= max_chars:
        return content, False

    if len(content) <= _PHASE_B_SAMPLE_CHARS:
        # Tier 2: section-weighted sampling — keep first 400 prose chars per section + all code blocks.
        sections = re.split(r"\n(?=## )", content)
        parts: list[str] = []
        code_blocks: list[str] = re.findall(r"```[\w]*\n.*?```", content, re.DOTALL)

        for section in sections:
            # Extract first 400 chars of prose (no code blocks)
            prose = re.sub(r"```[\w]*\n.*?```", "", section, flags=re.DOTALL).strip()
            parts.append(prose[:400])

        # Re-append all code blocks at end (they may be spread across sections)
        if code_blocks:
            parts.append("\n\n[CODE BLOCKS EXTRACTED]\n" + "\n\n".join(code_blocks[:10]))

        sampled = "\n\n".join(p for p in parts if p)
        return sampled[:max_chars], True

    # Tier 3: simple truncation
    return content[:max_chars], True


async def llm_review_page(
    content: str,
    slug: str,
    page_role: str,
    page_title: str,
    assigned_claims: list[str],
    product_name: str,
    canonical_import: str,
    platform: str,
    context: WorkerContext,
    *,
    api_surface_summary: str = "",
    skills_criteria: str = "",
    phase_a_findings: "list[Finding] | None" = None,
    heal_context: str = "",
    use_lite_mode: bool = False,
) -> tuple[Grade | None, list[Finding]]:
    """Run typed LLM evaluation on a single page.

    TC-3882 Wave 4 (E7/E8/H4):
    - E7: Content chunking (replace 8000-char truncation)
    - E8: Lite mode for non-final heal steps (4 checks only)
    - H4: Phase A findings and heal context passed to Phase B prompt

    Returns (grade, findings) or (None, []) if LLM unavailable.
    """
    if not context.llm_config:
        return None, []

    # Pre-LLM: build prompt
    body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
    word_count = len(body.split())
    sections = re.findall(r"^##\s+", body, re.MULTILINE)

    # E7: Content chunking (replaces content[:8000] truncation)
    prepared_content, is_truncated = _prepare_content(content)
    content_note = (
        "\n[NOTE: Content was truncated for context window. Later sections may not be reviewed.]\n"
        if is_truncated else ""
    )

    # E8: Select prompt template (lite vs full)
    if use_lite_mode and _LITE_PROMPT_PATH.exists():
        prompt_template = _LITE_PROMPT_PATH.read_text(encoding="utf-8")
    else:
        prompt_template = _PROMPT_PATH.read_text(encoding="utf-8")

    # H4: Phase A findings summary
    phase_a_summary = ""
    if phase_a_findings:
        phase_a_top = sorted(
            phase_a_findings,
            key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(f.severity, 4),
        )[:10]
        phase_a_summary = "\n".join(
            f"- [{f.severity.upper()}] {f.check}: {f.message[:120]}"
            for f in phase_a_top
        )

    # H4: Heal context block
    heal_context_block = f"\nHEAL CONTEXT:\n{heal_context}\n" if heal_context else ""

    prompt = prompt_template.format(
        display_name=product_name,
        canonical_import=canonical_import,
        platform=platform,
        page_title=page_title,
        page_role=page_role,
        word_count=word_count,
        section_count=len(sections),
        page_content=prepared_content,
        content_note=content_note,
        assigned_claims="\n".join(f"- {c}" for c in assigned_claims) or "(none)",
        api_surface=api_surface_summary or "(API surface not available for this product)",
        skills_criteria_block=skills_criteria,
        phase_a_summary=phase_a_summary or "(none)",
        heal_context_block=heal_context_block,
    )

    # LLM call
    raw = _call_llm(prompt, context)
    if not raw:
        return None, []

    # Post-LLM: parse and validate
    return _parse_review_response(raw, slug)


def _parse_review_response(raw: str, slug: str) -> tuple[Grade | None, list[Finding]]:
    """Parse LLM review JSON response."""
    # Extract JSON from potential markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try finding a JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return None, []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return None, []

    # Unwrap if LLM returned a JSON array instead of a dict
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), None)
        if data is None:
            return None, []

    # Extract grade
    grade_str = data.get("grade", "").upper()
    try:
        grade = Grade(grade_str)
    except ValueError:
        grade = None

    # Extract findings
    findings: list[Finding] = []
    for f in data.get("findings", []):
        if isinstance(f, dict):
            findings.append(Finding(
                check=f.get("check", "llm_review"),
                message=f.get("message", ""),
                severity=f.get("severity", "medium"),
                location=f.get("location", slug),
            ))

    return grade, findings


def _call_llm(prompt: str, context: WorkerContext) -> str | None:
    """Call LLM for review. Returns raw response or None."""
    if not context.llm_config:
        return None
    try:
        from launcher.clients.llm_provider import LLMProviderClient

        client = LLMProviderClient(
            api_base_url=context.llm_config.primary.base_url,
            model=context.llm_config.primary.model,
            run_dir=context.run_dir,
            temperature=context.llm_config.temperature,
            max_tokens=context.llm_config.max_tokens,
            reasoning_model=(
                context.llm_config.reasoning.model if context.llm_config.reasoning else None
            ),
            routing=context.llm_config.routing,
            telemetry_client=context.telemetry_client,
            telemetry_run_id=context.run_id,
            telemetry_trace_id=context.telemetry_trace_id,
            telemetry_parent_span_id="",
        )
        messages = [{"role": "user", "content": prompt}]
        response = client.chat_completion(messages, task_type="review")
        return response.get("content", "")
    except Exception as e:
        logger.warning("[Evaluate] LLM review failed: %s", e)
        return None
