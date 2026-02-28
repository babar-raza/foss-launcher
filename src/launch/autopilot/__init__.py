"""Autopilot phase selection for pipeline resume automation."""

from .phase_selector import PhaseDecision, select_phase

__all__ = ["PhaseDecision", "select_phase"]

# LLM planner is optional — import only when explicitly needed
# from .llm_planner import PlannerSuggestion, plan_with_llm
