# TC-2377 Evidence: Quality Feedback Loop

## Implementation Summary
Added cross-run quality feedback: W9 writes feedback after validation, W2/W4 can read it next run.

## Files Modified
- `specs/42_quality_feedback_loop.md` — NEW: Spec defining feedback schema and behavior
- `src/launch/workers/w9_validator/worker.py` — Added `emit_quality_feedback()`, `_suggest_actions_for_page()`
- `src/launch/workers/w4_ia_planner/worker.py` — Added `read_quality_feedback()`, `adjust_top_k_from_feedback()`
- `src/launch/workers/w2_facts_builder/worker.py` — Added `adjust_snippet_threshold_from_feedback()`
- `tests/unit/workers/test_tc_2377_quality_feedback.py` — NEW: 14 unit tests

## Feature Flag
- `use_feedback: false` default — feedback is always WRITTEN but never READ unless enabled
- Zero impact on existing tests (no changes to existing function signatures)

## Feedback Schema
`{run_dir}/work/quality_feedback.json` with run_id, generated_at, pages[{output_path, error_count, warn_count, gate_issues, suggested_actions}]
