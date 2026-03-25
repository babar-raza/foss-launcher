"""Pipeline-level metrics derivation from events.ndjson.

Calculates the 8 metrics defined in specs/toolchain_ci_telemetry.md:
  total_duration_s, worker_durations, llm_call_count, llm_total_tokens,
  fallback_count, cache_hit_rate, gate_pass_rate, re_run_count.

All operations are non-fatal: errors return zeroed metrics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from launcher.state.event_log import read_events

logger = logging.getLogger(__name__)


def calculate_pipeline_metrics(events_path: Path) -> Dict[str, Any]:
    """Derive pipeline metrics from events.ndjson.

    Args:
        events_path: Path to events.ndjson file.

    Returns:
        Dict with the 8 spec-defined metric keys plus a metadata key.
        Returns zeroed metrics on any error.
    """
    zeroed: Dict[str, Any] = {
        "total_duration_s": 0.0,
        "worker_durations": {},
        "llm_call_count": 0,
        "llm_total_tokens": 0,
        "fallback_count": 0,
        "cache_hit_rate": 0.0,
        "gate_pass_rate": 0.0,
        "re_run_count": 0,
    }

    try:
        events = read_events(events_path)
    except Exception:
        logger.warning("Failed to read events for metrics", exc_info=True)
        return zeroed

    if not events:
        return zeroed

    # -- total_duration_s: first run_created to last worker_completed --------
    run_created_ts = ""
    last_worker_ts = ""
    for evt in events:
        if evt.type == "run_created" and not run_created_ts:
            run_created_ts = evt.ts
        if evt.type == "worker_completed":
            last_worker_ts = evt.ts

    total_duration_s = 0.0
    if run_created_ts and last_worker_ts:
        total_duration_s = _iso_diff_seconds(run_created_ts, last_worker_ts)

    # -- worker_durations: from worker_started/completed pairs ---------------
    worker_starts: Dict[str, str] = {}
    worker_durations: Dict[str, float] = {}

    for evt in events:
        worker_name = evt.data.get("worker", "")
        if evt.type == "worker_started" and worker_name:
            worker_starts[worker_name] = evt.ts
        elif evt.type == "worker_completed" and worker_name:
            start_ts = worker_starts.get(worker_name, "")
            if start_ts:
                duration_ms = evt.data.get("duration_ms")
                if duration_ms is not None:
                    worker_durations[worker_name] = float(duration_ms)
                else:
                    worker_durations[worker_name] = _iso_diff_seconds(start_ts, evt.ts) * 1000

    # -- llm_call_count and llm_total_tokens ---------------------------------
    llm_call_count = 0
    llm_total_tokens = 0
    fallback_count = 0

    for evt in events:
        if evt.type == "llm_call_completed":
            llm_call_count += 1
            usage = evt.data.get("token_usage", {})
            if isinstance(usage, dict):
                llm_total_tokens += usage.get("total_tokens", 0)
            else:
                llm_total_tokens += evt.data.get("total_tokens", 0)

            # Check for fallback
            if evt.data.get("endpoint", "").lower().find("fallback") >= 0:
                fallback_count += 1
            if evt.data.get("is_fallback", False):
                fallback_count += 1

    # -- cache_hit_rate: from in-memory cache stats --------------------------
    cache_hit_rate = 0.0
    try:
        from launcher.shared.cache_telemetry import get_cache_stats

        stats = get_cache_stats()
        hits = stats.get("hit", 0)
        misses = stats.get("miss", 0)
        total = hits + misses
        if total > 0:
            cache_hit_rate = round(hits / total, 4)
    except Exception:
        pass

    # -- gate_pass_rate: from gate_executed events ---------------------------
    gate_total = 0
    gate_passed = 0
    for evt in events:
        if evt.type == "gate_executed":
            gate_total += 1
            if evt.data.get("passed", False):
                gate_passed += 1

    gate_pass_rate = 0.0
    if gate_total > 0:
        gate_pass_rate = round(gate_passed / gate_total, 4)

    # -- re_run_count: count of re_run_triggered events ---------------------
    re_run_count = sum(1 for evt in events if evt.type == "re_run_triggered")

    return {
        "total_duration_s": round(total_duration_s, 2),
        "worker_durations": worker_durations,
        "llm_call_count": llm_call_count,
        "llm_total_tokens": llm_total_tokens,
        "fallback_count": fallback_count,
        "cache_hit_rate": cache_hit_rate,
        "gate_pass_rate": gate_pass_rate,
        "re_run_count": re_run_count,
    }


def calculate_golden_metrics(events_path: Path) -> Dict[str, Any]:
    """Derive golden-resolution metrics from events.ndjson.

    Scans for ``golden_resolution`` events and computes:
      - golden_total_sections: total golden resolution events
      - golden_match_rate: fraction with match_level in (exact, substring)
      - golden_fallback_rate: fraction with match_level == role_fallback
      - golden_miss_rate: fraction with match_level == miss
      - golden_match_level_distribution: {level: count}
      - golden_miss_by_role: {role: miss_count}
      - golden_heal_sections: count of heal-mode events
      - golden_heal_escalation_rate: fraction of heal events with attempt > 1
    """
    zeroed: Dict[str, Any] = {
        "golden_total_sections": 0,
        "golden_match_rate": 0.0,
        "golden_fallback_rate": 0.0,
        "golden_miss_rate": 0.0,
        "golden_match_level_distribution": {},
        "golden_miss_by_role": {},
        "golden_heal_sections": 0,
        "golden_heal_escalation_rate": 0.0,
    }

    try:
        events = read_events(events_path)
    except Exception:
        logger.warning("Failed to read events for golden metrics", exc_info=True)
        return zeroed

    golden_events = [e for e in events if e.type == "golden_resolution"]
    if not golden_events:
        return zeroed

    total = len(golden_events)
    match_count = 0
    fallback_count = 0
    miss_count = 0
    level_dist: Dict[str, int] = {}
    miss_by_role: Dict[str, int] = {}
    heal_sections = 0
    heal_escalated = 0

    for evt in golden_events:
        data = evt.data
        level = data.get("match_level", "miss")
        level_dist[level] = level_dist.get(level, 0) + 1

        if level in ("exact", "substring"):
            match_count += 1
        elif level == "role_fallback":
            fallback_count += 1
        elif level == "miss":
            miss_count += 1
            role = data.get("page_role", "unknown")
            miss_by_role[role] = miss_by_role.get(role, 0) + 1

        if data.get("is_heal_mode", False):
            heal_sections += 1
            if data.get("heal_attempt", 0) > 1:
                heal_escalated += 1

    return {
        "golden_total_sections": total,
        "golden_match_rate": round(match_count / total, 4) if total else 0.0,
        "golden_fallback_rate": round(fallback_count / total, 4) if total else 0.0,
        "golden_miss_rate": round(miss_count / total, 4) if total else 0.0,
        "golden_match_level_distribution": level_dist,
        "golden_miss_by_role": miss_by_role,
        "golden_heal_sections": heal_sections,
        "golden_heal_escalation_rate": round(heal_escalated / heal_sections, 4) if heal_sections else 0.0,
    }


def _iso_diff_seconds(start_iso: str, end_iso: str) -> float:
    """Calculate seconds between two ISO8601 timestamps."""
    from datetime import datetime, timezone

    try:
        # Handle various ISO formats
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
        return max(0.0, (end - start).total_seconds())
    except Exception:
        return 0.0
