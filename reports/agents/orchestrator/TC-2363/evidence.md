# Evidence: TC-2363 — W7 → W5 Selective Re-Draft Routing

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Workspace:** reports/agents/orchestrator/TC-2363/

---

## Objective

When W7 ContentReviewer returns REJECT and `redraft_enabled=True`, mark only failing pages
as `"new"` in `page_plan.json` and re-invoke W5 (which skips `"preserved"` passing pages).
Guard with `max_redraft_attempts` to prevent infinite loops. Default: opt-in disabled.

---

## Governance Compliance

### 1. Spec amended before code

```
specs/09_validation_gates.md — added §"W7 → W5 Selective Re-Draft Routing (TC-2363, binding)"
```

Documents:
- Opt-in flags: `redraft_enabled: bool = False`, `max_redraft_attempts: int = 1`
- `decide_after_review()` routing logic (returns "redraft" or "continue")
- `redraft_pages_node()` contract: loads `review_report.json`, marks failing pages "new", writes `page_plan.json` atomically
- Loop guard: `redraft_attempts >= max_redraft_attempts → "continue"` (fall through to W6)
- New state constant: `RUN_STATE_REDRAFTING`

### 2. Taskcard created and registered

- `plans/taskcards/TC-2363_w7_w5_selective_redraft_routing.md` — status: In-Progress, all required YAML fields present
- `plans/taskcards/INDEX.md` — registered under "Agentic Architecture Gaps (2026-02-19)"

---

## Code Changes

### File: `src/launch/models/state.py`

```python
RUN_STATE_REDRAFTING = "REDRAFTING"  # TC-2363: W7 REJECT → re-draft failing pages
```

Additive constant added after `RUN_STATE_REVIEWING`.

---

### File: `src/launch/orchestrator/graph.py`

**Imports added:**
```python
import json
from launch.models.state import ..., RUN_STATE_REDRAFTING
```

**TypedDict field added to `OrchestratorState`:**
```python
redraft_attempts: int  # TC-2363: counts W7→W5 re-draft cycles
```

**New function: `decide_after_review(state: OrchestratorState) → str`**
```python
def decide_after_review(state):
    rc = state["run_config"]
    if not rc.get("redraft_enabled", False):
        return "continue"
    review_report_path = Path(state["run_dir"]) / "artifacts" / "review_report.json"
    report = json.loads(review_report_path.read_text())
    if report.get("overall_status") != "REJECT":
        return "continue"
    if state.get("redraft_attempts", 0) >= rc.get("max_redraft_attempts", 1):
        return "continue"  # exhausted retries
    if report.get("pages_failed", 0) == 0:
        return "continue"
    return "redraft"
```

**New function: `redraft_pages_node(state: OrchestratorState) → dict`**
- Loads `artifacts/review_report.json` → extracts failed page paths from `issues[].location.path`
- Loads `artifacts/page_plan.json`
- Marks each page: `page_status = "new"` if path in failed set, else `"preserved"`
- Writes updated `page_plan.json` atomically: writes to `.tmp` then `Path.replace()`
- Returns `{"run_state": RUN_STATE_REDRAFTING, "redraft_attempts": current + 1}`

**Graph edges replaced:**
```python
# Before (hard edge):
graph.add_edge("review_content", "link_and_patch")

# After (conditional):
graph.add_conditional_edges(
    "review_content",
    decide_after_review,
    {"redraft": "redraft_pages", "continue": "link_and_patch"}
)
graph.add_node("redraft_pages", redraft_pages_node)
graph.add_edge("redraft_pages", "draft_sections")
```

---

### File: `src/launch/orchestrator/run_loop.py`

```python
# Initial state dict:
"redraft_attempts": 0,  # TC-2363: W7 → W5 selective re-draft loop counter
```

---

## Test Results

### New tests in `tests/unit/workers/test_content_reviewer_scoring.py` (TC-2363 section)

| Test | Result |
|------|--------|
| `test_decide_after_review_disabled` (redraft_enabled=False → always "continue") | ✅ PASS |
| `test_decide_after_review_reject_routes_redraft` (REJECT + attempts<max → "redraft") | ✅ PASS |
| `test_decide_after_review_exhausted` (REJECT + attempts>=max → "continue") | ✅ PASS |
| `test_decide_after_review_pass_continues` (PASS status → "continue") | ✅ PASS |
| `test_redraft_pages_node_marks_correctly` (failing pages→"new", passing→"preserved") | ✅ PASS |

**Full test suite:**
```
tests/unit/workers/test_content_reviewer_scoring.py — 16 passed (11 original + 5 new)
tests/unit/workers/ — 2807 passed, 0 failed
```

Only pre-existing failure: `test_clean_repo_passes` (Windows NUL device OS artifact, unrelated).

---

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| `redraft_enabled=False` → always routes "continue" regardless of REJECT status | ✅ PASS |
| `redraft_enabled=True` + REJECT + `attempts < max` → routes "redraft" | ✅ PASS |
| `redraft_enabled=True` + REJECT + `attempts >= max` → routes "continue" (exhausted) | ✅ PASS |
| `redraft_enabled=True` + PASS → routes "continue" | ✅ PASS |
| `redraft_pages_node()` marks failing pages "new", passing pages "preserved" | ✅ PASS |
| `redraft_pages_node()` increments `redraft_attempts` | ✅ PASS |
| `page_plan.json` written atomically (tmp → replace) | ✅ PASS |
| `RUN_STATE_REDRAFTING` constant added to state.py | ✅ PASS |
| `redraft_attempts: 0` in initial orchestrator state | ✅ PASS |
| Spec amended before code | ✅ PASS |
| Taskcard created and registered in INDEX | ✅ PASS |
| All unit tests pass | ✅ PASS |

---

## Summary

TC-2363 is complete. The orchestrator now has a safety-guarded re-draft loop:
W7 REJECT → `decide_after_review` → `redraft_pages` (mark pages) → W5 (skip preserved) → W7 (re-check).
When `redraft_enabled=False` (default) or retries exhausted, pipeline continues to W6 unchanged.
The mechanism reuses W5's existing `page_status: "new"/"preserved"` incremental mechanism with
zero changes to W4 or W5 internals.
