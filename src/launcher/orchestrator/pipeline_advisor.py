"""TC-3918: Pipeline routing advisor — LLM-driven post-evaluate routing.

After evaluate emits verdict=NO_GO, this module is called to decide the next
pipeline step: publish (override), heal_generate (re-run generate), or stop.

Pattern source: src/launcher/cli/heal.py (_call_llm_sync, _parse_heal_decision).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from launcher.models.evaluation import EvaluationReport

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "pipeline_advisor.txt"


def _build_advisor_prompt(
    report: "EvaluationReport",
    re_run_count: int,
    max_re_runs: int,
) -> str:
    """Build the advisor prompt from pipeline_advisor.txt template."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")

    re_run_status = {
        "re_run_count": re_run_count,
        "max_re_runs": max_re_runs,
        "budget_remaining": max_re_runs - re_run_count,
    }

    # Build eval_summary from report
    summary = report.model_dump(mode="json") if hasattr(report, "model_dump") else {}
    # Extract key quality metrics for brevity
    eval_summary = {
        "verdict": summary.get("verdict", "NO_GO"),
        "critical_count": summary.get("critical_count", 0),
        "high_count": summary.get("high_count", 0),
        "pages_reviewed": summary.get("pages_reviewed", 0),
        "ab_rate": summary.get("ab_rate", 0.0),
        "df_rate": summary.get("df_rate", 0.0),
    }

    # Build failing_checks list
    findings = summary.get("findings", []) or []
    failing_checks = [
        {"check": f.get("check", ""), "severity": f.get("severity", ""), "count": f.get("count", 1)}
        for f in findings
        if f.get("severity") in ("CRITICAL", "HIGH", "MEDIUM")
    ][:20]  # cap at 20 to avoid prompt bloat

    return template.format(
        re_run_status=json.dumps(re_run_status, indent=2),
        eval_summary=json.dumps(eval_summary, indent=2),
        failing_checks=json.dumps(failing_checks, indent=2),
    )


def _call_llm(prompt: str, run_dir: Path) -> str | None:
    """Call qwen3-next (temp=0.0) with the advisor prompt. Return None on any failure."""
    try:
        import os
        api_key = os.environ.get("litellm_key", "")
        if not api_key:
            logger.debug("pipeline_advisor: litellm_key not set, skipping LLM call")
            return None

        base_url = os.environ.get("FOSS_LAUNCHER_LLM_BASE_URL", "https://llm.professionalize.com/v1")

        from launcher.clients.llm_provider import LLMProviderClient

        provider = LLMProviderClient(
            api_base_url=base_url,
            model="qwen3-next",
            run_dir=run_dir,
            api_key=api_key,
            temperature=0.0,
        )
        messages = [
            {"role": "system", "content": "You are a pipeline routing advisor."},
            {"role": "user", "content": prompt},
        ]
        result = provider.chat_completion(messages, max_tokens=2048, task_type="advisor")
        return result.get("content") if isinstance(result, dict) else str(result)
    except Exception as exc:
        logger.warning("pipeline_advisor: LLM call failed: %s", exc)
        return None


def _parse_advice(response: str) -> "PipelineAdvice | None":
    """Strip markdown fences, parse JSON, validate model. Return None if confidence < 0.6."""
    from launcher.models.evaluation import PipelineAdvice
    from pydantic import ValidationError

    text = response.strip()
    # Strip markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("pipeline_advisor: JSON parse failed: %s", exc)
        return None

    try:
        advice = PipelineAdvice.model_validate(data)
    except ValidationError as exc:
        logger.warning("pipeline_advisor: schema validation failed: %s", exc)
        return None

    if advice.confidence < 0.6:
        logger.info(
            "pipeline_advisor: confidence %.2f < 0.6, using fallback", advice.confidence
        )
        return None

    return advice


def _extract_failing_slugs(report: "EvaluationReport | None") -> list[str]:
    """Return sorted list of C/D/F-grade slugs from *report*."""
    if report is None:
        return []
    from launcher.models.evaluation import Grade

    _FAILING = {Grade.C, Grade.D, Grade.F}
    return sorted(p.slug for p in (report.pages or []) if p.grade in _FAILING)


def _static_fallback(
    re_run_count: int,
    max_re_runs: int,
    *,
    report: "EvaluationReport | None" = None,
) -> "PipelineAdvice":
    """Return deterministic PipelineAdvice when LLM unavailable."""
    from launcher.models.evaluation import PipelineAdvice

    if re_run_count < max_re_runs:
        target = _extract_failing_slugs(report) if report is not None else []
        return PipelineAdvice(
            routing="heal_generate",
            analysis="LLM unavailable; defaulting to heal_generate (budget remains).",
            confidence=1.0,
            target_pages=target,
            strategy="Re-generate all pages with lowest grades.",
            priority_checks=[],
            stop_reason=None,
        )
    return PipelineAdvice(
        routing="stop",
        analysis="LLM unavailable; budget exhausted, stopping pipeline.",
        confidence=1.0,
        target_pages=[],
        strategy="",
        priority_checks=[],
        stop_reason="Budget exhausted and LLM unavailable for routing decision.",
    )


def route_after_evaluate(
    report: "EvaluationReport",
    re_run_count: int,
    max_re_runs: int,
) -> "PipelineAdvice":
    """Deterministic routing decision after evaluate emits NO_GO.

    Decision rules (in priority order):
    1. Budget exhausted → stop
    2. extraction_quality HIGH findings on first re-run → heal_understand
       (re-run understand + planner + generate to fix thin API extraction)
    3. CRITICAL finding rate > 50% → stop (LLM cannot fix structural issues)
    4. Default → heal_generate

    Does NOT require an LLM call. Deterministic and reproducible.
    """
    from launcher.models.evaluation import PipelineAdvice, Grade

    # Rule 1: Budget exhausted
    if re_run_count >= max_re_runs:
        return PipelineAdvice(
            routing="stop",
            analysis=f"Heal budget exhausted ({re_run_count}/{max_re_runs} re-runs used).",
            confidence=1.0,
            target_pages=[],
            strategy="",
            priority_checks=[],
            stop_reason="Budget exhausted.",
        )

    all_pages = report.pages or []
    all_findings = [f for p in all_pages for f in (p.findings or [])]
    total_pages = len(all_pages) or 1

    # Rule 2: extraction_quality HIGH on first re-run → heal_understand
    # Only on re_run_count == 0: if understand was already re-run and extraction
    # is still thin, fall through to heal_generate (then stop on next budget check).
    extraction_high = [
        f for f in all_findings
        if getattr(f, "check", "") == "extraction_quality"
        and getattr(f, "severity", "") == "high"
    ]
    if extraction_high and re_run_count == 0:
        logger.info(
            "TC-5311: extraction_quality HIGH on %d finding(s) — routing heal_understand. "
            "Will re-run understand + planner + generate with fresh API extraction.",
            len(extraction_high),
        )
        return PipelineAdvice(
            routing="heal_understand",
            analysis=(
                f"extraction_quality HIGH on {len(extraction_high)} finding(s). "
                "API surface extraction is near-empty. Re-running understand before generate."
            ),
            confidence=1.0,
            target_pages=sorted(set(getattr(f, "location", "") for f in extraction_high)),
            strategy="Re-extract API surface, then re-run planner and generate.",
            priority_checks=["extraction_quality"],
            stop_reason=None,
        )

    # Rule 3: CRITICAL finding rate > 50% → stop
    critical_pages = sum(
        1 for p in all_pages
        if any(getattr(f, "severity", "") == "critical" for f in (p.findings or []))
    )
    if critical_pages / total_pages > 0.5:
        return PipelineAdvice(
            routing="stop",
            analysis=(
                f"{critical_pages}/{total_pages} pages have CRITICAL findings. "
                "Re-generating will not fix structural issues."
            ),
            confidence=1.0,
            target_pages=[],
            strategy="",
            priority_checks=[],
            stop_reason=f"CRITICAL rate {critical_pages/total_pages:.0%} exceeds 50% threshold.",
        )

    # Rule 4: Default → heal_generate
    _FAILING_GRADES = {Grade.C, Grade.D, Grade.F}
    failing = [
        p.slug for p in all_pages
        if p.grade in _FAILING_GRADES
    ]
    return PipelineAdvice(
        routing="heal_generate",
        analysis=(
            f"{len(failing)}/{total_pages} pages below threshold. "
            "Re-generating with current evidence."
        ),
        confidence=1.0,
        target_pages=sorted(set(failing)),
        strategy="Re-generate failing pages.",
        priority_checks=[],
        stop_reason=None,
    )


def call_pipeline_advisor(
    report: "EvaluationReport",
    re_run_count: int,
    max_re_runs: int,
    run_dir: Path,
) -> "PipelineAdvice":
    """Public entry — deterministic routing with optional LLM override for heal_generate cases.

    TC-5311: Runs route_after_evaluate() first. Only calls LLM when routing is heal_generate
    and budget remains — avoiding LLM non-determinism for clear-cut stop/budget decisions.
    Never raises.
    """
    try:
        # Deterministic routing runs first — always fast and reproducible.
        deterministic = route_after_evaluate(report, re_run_count, max_re_runs)

        # LLM override: only for heal_generate (borderline cases). Skip LLM for stop decisions.
        if deterministic.routing == "heal_generate" and re_run_count < max_re_runs:
            try:
                prompt = _build_advisor_prompt(report, re_run_count, max_re_runs)
                response = _call_llm(prompt, run_dir)
                if response:
                    advice = _parse_advice(response)
                    if advice is not None:
                        logger.info(
                            "pipeline_advisor: LLM routing=%s (deterministic was %s)",
                            advice.routing, deterministic.routing,
                        )
                        return advice
            except Exception as llm_exc:
                logger.warning(
                    "pipeline_advisor: LLM call failed, using deterministic: %s", llm_exc
                )

        return deterministic

    except Exception as exc:
        logger.error(
            "pipeline_advisor: unexpected error in route_after_evaluate (falling back): %s",
            exc, exc_info=True,
        )
        return _static_fallback(re_run_count, max_re_runs, report=report)
