# Evidence: TC-2373 — RD-04 Priority-Weighted Token Allocation in W5

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Branch:** `healing/blkr-01-03-04-rd06`
**Status:** Done

---

## Summary

Added `_compute_token_budget()` and `SECTION_TYPE_WEIGHTS` to W5 `worker.py`.
High-priority pages (getting_started, tutorial) receive up to 2× the base token budget;
low-priority pages (toc, landing) receive 0.5–0.8×. Budget is computed before the LLM
call and logged at DEBUG level and recorded in the draft manifest.

---

## Root Cause

W4 already writes `content_strategy.priority_weight` to `page_plan.json` but W5 never
read it. Equal token distribution caused critical sections to be under-resourced while
boilerplate sections were padded.

---

## Implementation

### `SECTION_TYPE_WEIGHTS` (module-level, worker.py)

```python
SECTION_TYPE_WEIGHTS: Dict[str, float] = {
    "getting_started": 1.8, "tutorial": 1.6, "comprehensive_guide": 1.5,
    "api_reference": 1.4, "troubleshooting": 1.3, "feature_showcase": 1.2,
    "best_practices": 1.2, "workflow_page": 1.1, "faq": 1.0,
    "howto_article": 1.0, "format_conversion": 0.9, "feature_blog": 0.9,
    "landing": 0.8, "toc": 0.5,
}
```

### `_compute_token_budget(page, run_config) -> int`

```python
base = int(run_config.get("token_budget", 2048))
weight = page.get("content_strategy", {}).get("priority_weight") or SECTION_TYPE_WEIGHTS.get(page.get("page_type", ""), 1.0)
effective = max(int(base * 0.5), min(int(base * 2.0), int(base * weight)))
```

### `_generate_single_page()` wire-in

- Calls `_compute_token_budget(page, run_config)` before `generate_section_content()`
- Logs: `[W5] <slug>: base=N weight=W effective=M`
- Manifest entry includes `"effective_token_budget": int`

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/worker.py` | `SECTION_TYPE_WEIGHTS` dict, `_compute_token_budget()` function, wire-in in `_generate_single_page()`, manifest field |
| `tests/unit/workers/test_tc_440_section_writer.py` | 3 new tests: from-field, fallback-to-type, clamp-at-2x |
| `specs/21_worker_contracts.md` | Added "Priority-Weighted Token Allocation" subsection |

---

## Test Results

```
TestTokenBudget: 3/3 pass
  - test_token_budget_from_priority_weight
  - test_token_budget_fallback_to_section_type
  - test_token_budget_clamp_at_2x

Full suite: 4564 passed, 9 skipped, 0 failed
```

---

## Acceptance Criteria

| Check | Result |
|-------|--------|
| `_compute_token_budget` with weight=2.0, base=1000 → 2000 | ✅ |
| Fallback to SECTION_TYPE_WEIGHTS when priority_weight absent | ✅ |
| Clamp: weight=5.0, base=1000 → 2000 (max 2×) | ✅ |
| DEBUG log per page | ✅ |
| Manifest entry includes `effective_token_budget` | ✅ |
| Full suite passes | ✅ 4564/4564 |
