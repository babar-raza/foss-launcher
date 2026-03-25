# TC-3614 Evidence Report — Heal Auditability Hardening

**Date**: 2026-02-28
**Session**: mossy-wiggling-kay (continued)
**Status**: Complete

---

## What Was Implemented

### Phase 1: Stable `recommendation_id` in triage.py

`recommend_action()` in `src/launch/cli/triage.py` now produces an `"id"` field on every recommendation dict:

```python
rec_id = f"triage:{rule['match'].__name__}->{rule['worker']}"
recommendations.append({
    "command": ...,
    "reason": rule["label"],
    "id": rec_id,  # TC-3614: stable id
})
# Fallback:
recommendations.append({
    "command": ...,
    "reason": "General re-validation ...",
    "id": "triage:fallback->W9",
})
```

Format: `"triage:<match_function_name>-><worker>"`. Examples:
- `"triage:_match_truth->W2"`
- `"triage:_match_scaffold_or_fmt->W10"`
- `"triage:_match_frontmatter_required_fields->W10"`
- `"triage:fallback->W9"`

### Phase 2: Quarantine key changed to stable rec_id

`_get_quarantine_key()` helper added to `src/launch/cli/heal.py`:

```python
def _get_quarantine_key(candidate: Dict[str, str], worker: str) -> str:
    rec_id = candidate.get("id", "")
    if rec_id:
        return rec_id
    fallback = f"missing-id:{worker}"
    logger.warning("[Heal] Recommendation ... has no stable 'id' field; ...")
    return fallback
```

`choose_worker()` and `run_heal_loop()` now use `(worker, rec_id)` as the quarantine key instead of `(worker, reason_text)`. Rewording a rule label no longer silently disables quarantine.

### Phase 3: Per-step issue metrics persisted in heal_plan.json

Three new fields added to `HealStep` dataclass:
- `recommendation_id: str = ""` — stable quarantine/audit key
- `before_metrics: Optional[Dict[str, Any]] = None` — snapshot before step
- `after_metrics: Optional[Dict[str, Any]] = None` — snapshot after step

New helper `_metrics_to_dict(m: Optional[ReportMetrics]) -> Optional[Dict]` converts a frozen dataclass snapshot to a JSON-serializable dict with sorted `failed_gate_ids`.

In `run_heal_loop()`:
```python
step = HealStep(
    ...
    recommendation_id=rec_id,
    before_metrics=_metrics_to_dict(metrics_before),
)
# After execution:
step.after_metrics = _metrics_to_dict(metrics_after)
```

### Schema Update (`specs/schemas/heal_plan.schema.json`)

Added:
- `$defs/step_metrics` sub-schema with 4 required fields
- `recommendation_id` (optional string) to `heal_step`
- `before_metrics` and `after_metrics` (optional `null|step_metrics`) to `heal_step`
- `"id"` field to `triage_snapshot` items

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/cli/triage.py` | Added `"id"` field to all recommendations |
| `src/launch/cli/heal.py` | `_get_quarantine_key()`, `_metrics_to_dict()`, `HealStep` new fields, quarantine key updated |
| `specs/schemas/heal_plan.schema.json` | `$defs/step_metrics`, new optional fields |
| `plans/taskcards/TC-3614_heal_auditability_hardening.md` | Created |
| `plans/taskcards/INDEX.md` | Registered TC-3614 |

---

## Tests Added / Updated

### New tests (TC-3614)

**`tests/unit/cli/test_triage.py` — `TestRecommendationId` (5 tests)**:
- `test_all_recommendations_have_id`
- `test_fallback_recommendation_has_id`
- `test_recommendation_id_is_deterministic`
- `test_recommendation_id_independent_of_reason_wording`
- `test_w10_recommendations_have_distinct_ids_per_rule`

**`tests/unit/cli/test_heal_regression_guard.py` — `TestStableQuarantineKey` (2 tests)**:
- `test_quarantine_stable_changing_reason_does_not_unblock`
- `test_different_rec_ids_same_worker_independent`

**`tests/unit/cli/test_heal_regression_guard.py` — `TestQuarantine` updated (6 tests)**:
- `_make_rec()` now includes `id` field
- Quarantine sets use `(worker, rec_id)` keys

**`tests/unit/cli/test_heal.py` — `TestStepMetricsPersisted` (6 tests)**:
- `test_metrics_to_dict_converts_report_metrics`
- `test_metrics_to_dict_returns_none_for_none`
- `test_heal_step_to_dict_includes_all_tc3614_fields`
- `test_heal_plan_json_has_before_after_metrics`
- `test_heal_plan_json_metrics_show_issue_count_drop` (E2E)
- `test_recommendation_id_in_heal_plan_json`

### Updated tests

**`tests/unit/cli/test_heal_convergence_e2e.py`**:
- `_make_rec()` updated to include deterministic `id` field
- `test_quarantine_does_not_block_different_reason` updated to use rec_id quarantine key

---

## Test Results

```
PYTHONHASHSEED=0 pytest tests/ -q
7832 passed, 13 skipped, 3 xfailed, 0 failed
```

Previous baseline: 7786 passed, 13 skipped, 3 xfailed, 0 failed
**Net new tests: +46**

---

## Sample heal_plan.json (showing new fields)

```json
{
  "schema_version": "1.0",
  "run_id": "r_test",
  "mode": "strict",
  "steps": [
    {
      "step_idx": 0,
      "chosen_worker": "W10",
      "reason": "Scaffold/prompt leak or formatting issues (W10 auto-fixable)",
      "recommendation_id": "triage:_match_scaffold_or_fmt->W10",
      "before_metrics": {
        "failed_gate_count": 2,
        "failed_gate_ids": ["gate_17_formatting_quality", "gate_scaffold_leak"],
        "open_critical_issue_count": 2,
        "open_total_issue_count": 2
      },
      "after_metrics": {
        "failed_gate_count": 0,
        "failed_gate_ids": [],
        "open_critical_issue_count": 0,
        "open_total_issue_count": 0
      },
      "outcome": "improved"
    }
  ],
  "stop_reason": "all_gates_pass",
  "final_failed_gate_count": 0
}
```
