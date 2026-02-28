"""Guardrailed LLM planner — optional advisory layer for autopilot.

TC-3030: The LLM may suggest an earlier start worker than baseline
but can NEVER skip past the deterministic baseline. If it suggests
a later worker, the suggestion is rejected and baseline is used.

No mandatory dependency on LLM availability — returns None on failure.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Worker ordering for comparison (earlier = lower index)
_WORKER_ORDER = ("W1", "W3", "W4", "W5", "W8", "W9", "W10", "W11", "DONE")


@dataclass(frozen=True)
class PlannerSuggestion:
    """LLM planner output (validated and guardrailed)."""

    suggested_start_worker: str
    """Worker the LLM recommends starting from."""

    toggles: Dict[str, Any] = field(default_factory=dict)
    """Optional mode flags (e.g. heal_mode, regen_failed_only)."""

    rationale: str = ""
    """LLM's explanation for the recommendation."""

    guardrail_applied: bool = False
    """True if the original suggestion was rejected as later-than-baseline."""


def _worker_index(worker: str) -> int:
    """Return the position of a worker in pipeline order. -1 if unknown."""
    try:
        return _WORKER_ORDER.index(worker)
    except ValueError:
        return -1


def _validate_suggestion(
    raw: Dict[str, Any],
    baseline_start_worker: str,
) -> Optional[PlannerSuggestion]:
    """Validate and guardrail a parsed LLM suggestion.

    Returns PlannerSuggestion or None if the suggestion is invalid.
    The hard constraint is enforced here: suggested worker must be
    earlier or equal to baseline.
    """
    suggested = raw.get("suggested_start_worker", "")
    if not isinstance(suggested, str) or suggested not in _WORKER_ORDER:
        logger.warning(
            "llm_planner_invalid_worker: %r not in %s", suggested, _WORKER_ORDER
        )
        return None

    toggles = raw.get("toggles", {})
    if not isinstance(toggles, dict):
        toggles = {}

    rationale = str(raw.get("rationale", ""))

    baseline_idx = _worker_index(baseline_start_worker)
    suggested_idx = _worker_index(suggested)

    if suggested_idx > baseline_idx:
        # HARD CONSTRAINT: LLM cannot skip past baseline
        logger.warning(
            "llm_planner_rejected_later: suggested=%s (idx=%d) > baseline=%s (idx=%d)",
            suggested, suggested_idx, baseline_start_worker, baseline_idx,
        )
        return PlannerSuggestion(
            suggested_start_worker=baseline_start_worker,
            toggles=toggles,
            rationale=f"REJECTED_LATER_THAN_BASELINE: LLM suggested {suggested} but baseline is {baseline_start_worker}. {rationale}",
            guardrail_applied=True,
        )

    return PlannerSuggestion(
        suggested_start_worker=suggested,
        toggles=toggles,
        rationale=rationale,
        guardrail_applied=False,
    )


_LLM_PROMPT_TEMPLATE = """\
You are an operations advisor for a documentation pipeline.
Given the current pipeline state, suggest the best worker to start from.

RULES:
- You may suggest an EARLIER worker than baseline (to rerun more).
- You MUST NOT suggest a worker LATER than baseline.
- Output ONLY valid JSON with keys: suggested_start_worker, toggles, rationale.

Current state:
- Baseline start worker: {baseline_start_worker}
- Target repo SHA: {target_repo_sha}
- Available artifacts: {available_artifacts}
- Goal: {goal}
{validation_context}

Valid workers (in order): W1, W3, W4, W5, W8, W9, W10, W11, DONE
Respond with JSON only.
"""


def build_planner_context(
    baseline_start_worker: str,
    target_repo_sha: str,
    available_artifacts: list[str],
    goal: str = "draft",
    validation_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the prompt context string for the LLM planner."""
    validation_ctx = ""
    if validation_summary:
        validation_ctx = f"- Validation summary: {json.dumps(validation_summary)}"

    return _LLM_PROMPT_TEMPLATE.format(
        baseline_start_worker=baseline_start_worker,
        target_repo_sha=target_repo_sha[:12],
        available_artifacts=json.dumps(available_artifacts),
        goal=goal,
        validation_context=validation_ctx,
    )


def plan_with_llm(
    llm_client: Any,
    baseline_start_worker: str,
    context: str,
) -> Optional[PlannerSuggestion]:
    """Call the LLM for an advisory phase selection suggestion.

    Args:
        llm_client: Any object with a `chat(messages)` or `complete(prompt)` method.
            If None, returns None immediately.
        baseline_start_worker: The deterministic baseline from PhaseSelector.
        context: Pre-built prompt context from build_planner_context().

    Returns:
        PlannerSuggestion if valid, None if LLM unavailable or response invalid.
    """
    if llm_client is None:
        logger.info("llm_planner_skipped: no llm_client provided")
        return None

    try:
        # Try chat-style first, then complete-style
        if hasattr(llm_client, "chat"):
            response_text = llm_client.chat([{"role": "user", "content": context}])
        elif hasattr(llm_client, "complete"):
            response_text = llm_client.complete(context)
        else:
            logger.warning("llm_planner_unsupported_client: %s", type(llm_client).__name__)
            return None
    except Exception:
        logger.warning("llm_planner_call_failed", exc_info=True)
        return None

    # Parse response
    if not isinstance(response_text, str):
        response_text = str(response_text)

    # Extract JSON from response (may be wrapped in markdown fences)
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("llm_planner_invalid_json: %s", text[:200])
        return None

    if not isinstance(raw, dict):
        logger.warning("llm_planner_not_dict: %s", type(raw).__name__)
        return None

    return _validate_suggestion(raw, baseline_start_worker)
