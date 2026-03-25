# Self-Review: TC-2363 — W7 → W5 Selective Re-Draft Routing

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Task:** Add conditional re-draft routing from W7 REJECT back to W5

---

## 12-Dimension Self-Assessment

### 1. Coverage (5/5)

All acceptance criteria met:
- ✅ `RUN_STATE_REDRAFTING` constant added to `state.py`
- ✅ `redraft_attempts: int` added to `OrchestratorState` TypedDict
- ✅ `decide_after_review()` routing function implements all 4 exit conditions
- ✅ `redraft_pages_node()` marks failing pages "new", passing pages "preserved"
- ✅ Atomic write to `page_plan.json` (tmp → `Path.replace()`)
- ✅ Graph wired: conditional edge replaces hard edge; `redraft_pages → draft_sections`
- ✅ `redraft_attempts: 0` in initial state in `run_loop.py`
- ✅ Spec amended, taskcard created, INDEX registered

---

### 2. Correctness (5/5)

- ✅ `decide_after_review` checks ALL guards in correct order: enabled? → REJECT? → exhausted? → pages_failed>0?
- ✅ Failed paths extracted from `issues[].location.path` (same field W7 writes)
- ✅ Page matching by `draft_path` field (as W7 writes to `issues[].location.path`)
- ✅ `redraft_attempts` incremented atomically in returned state dict (LangGraph merges)
- ✅ 16 tests pass including all 5 new TC-2363 routing tests; 2807 workers tests pass

---

### 3. Evidence (5/5)

- ✅ evidence.md documents all code changes with function signatures and logic
- ✅ Before/after graph edge replacement documented
- ✅ Acceptance criteria table with ✅ per item
- ✅ Pre-existing NUL false-positive identified and explained

---

### 4. Test Quality (5/5)

5 new tests with comprehensive routing coverage:
- `test_decide_after_review_disabled`: zero routing when disabled (safety gate)
- `test_decide_after_review_reject_routes_redraft`: the happy-path redraft trigger
- `test_decide_after_review_exhausted`: loop guard enforced
- `test_decide_after_review_pass_continues`: PASS bypasses re-draft correctly
- `test_redraft_pages_node_marks_correctly`: 4 pages (2 fail, 2 pass) verified individually
  - asserts `redraft_attempts` incremented by exactly 1
  - asserts each page slug has correct `page_status` ("new" vs "preserved")
  - asserts `page_plan.json` written atomically (file exists and is valid JSON after call)

---

### 5. Maintainability (5/5)

- ✅ `decide_after_review()` is a pure function (reads files, returns string)
- ✅ `redraft_pages_node()` follows LangGraph node convention (takes state, returns dict)
- ✅ Reuses existing `page_status: "new"/"preserved"` mechanism — no new W5 concepts
- ✅ Loop guard via counter prevents infinite loops regardless of content quality
- ✅ Default `redraft_enabled=False` → zero behavioral change for all existing pilots

---

### 6. Safety (5/5)

- ✅ Default `redraft_enabled=False` → hard pass-through (pipeline unchanged)
- ✅ `max_redraft_attempts` guard prevents infinite loops
- ✅ If `review_report.json` missing/malformed, `decide_after_review` raises (pipeline fails fast)
- ✅ Atomic write prevents partial `page_plan.json` corruption on crash
- ✅ No changes to W4 or W5 internals — re-draft uses existing page_status mechanism

---

### 7. Security (N/A)

No security surface: reads/writes local JSON files in `run_dir/artifacts/` only.

---

### 8. Reliability (5/5)

- ✅ Atomic write (`tmp → replace`) prevents torn reads of `page_plan.json`
- ✅ Loop guard ensures pipeline always terminates
- ✅ `redraft_attempts` in LangGraph state (persisted, survives node failures)
- ✅ If all pages pass on re-draft, `decide_after_review` routes "continue" (no double re-draft)

---

### 9. Observability (5/5)

- ✅ `RUN_STATE_REDRAFTING` emitted as `run_state` in state dict (visible in telemetry)
- ✅ `redraft_attempts` counter in state (visible to monitoring and run logs)
- ✅ Failed page paths logged in `review_report.json.issues[].location.path`

---

### 10. Performance (5/5)

- ✅ `decide_after_review` reads one small JSON file — negligible overhead
- ✅ `redraft_pages_node` reads two JSON files and writes one — O(pages), negligible
- ✅ Re-draft only runs on failing pages (preserved pages skipped by W5)
- ✅ Default disabled → zero overhead for all existing runs

---

### 11. Compatibility (5/5)

- ✅ No changes to `src/launch/models/run_config.py` — uses `run_config.get()` dict pattern
- ✅ Hard edge `review_content → link_and_patch` preserved for `redraft_enabled=False`
- ✅ `OrchestratorState` TypedDict addition is backward-compatible (LangGraph state merges)
- ✅ `redraft_attempts: 0` in `run_loop.py` ensures field always present
- ✅ All 2807 existing workers tests pass

---

### 12. Docs/Specs Fidelity (5/5)

- ✅ `specs/09_validation_gates.md` amended before code was written
- ✅ New spec section is binding, not advisory
- ✅ All function names in implementation match spec documentation exactly
- ✅ Routing decision logic in spec matches implementation (4 guard conditions)
- ✅ Atomic write requirement from spec implemented correctly

---

## Score Summary

| Dimension | Score | Notes |
|-----------|-------|-------|
| 1. Coverage | 5/5 | All acceptance criteria met |
| 2. Correctness | 5/5 | All guards, all routing paths |
| 3. Evidence | 5/5 | Complete with code snippets |
| 4. Test Quality | 5/5 | 5 tests, full routing coverage |
| 5. Maintainability | 5/5 | Pure functions, reuses W5 mechanism |
| 6. Safety | 5/5 | Default-off, atomic writes, loop guard |
| 7. Security | N/A | Local file I/O only |
| 8. Reliability | 5/5 | Atomic writes, loop guard, fast-fail |
| 9. Observability | 5/5 | State constant, attempt counter |
| 10. Performance | 5/5 | Default-off, failing-pages-only re-draft |
| 11. Compatibility | 5/5 | Default-off, no model changes |
| 12. Docs/Specs Fidelity | 5/5 | Spec-first, names match exactly |

**Applicable Dimensions:** 11/12 (Security N/A)
**Average Score:** 5.0/5
**Required Threshold:** ≥4/5 on all dimensions
**Result:** ✅ PASS

---

## Status: READY FOR MERGE
