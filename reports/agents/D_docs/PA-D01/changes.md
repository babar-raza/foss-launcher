# PA-D01 Changes Report

Agent: Agent-D (Docs & Specs)
Date: 2026-03-20
Task: Update TC-PA-01 through TC-PA-05 taskcards from In-Progress to Done

## Taskcards Updated

### TC-PA-01 — Fix claim coverage contract
- **File**: `plans/taskcards/TC-PA-01_fix_claim_coverage_contract.md`
- **Status**: In-Progress -> Done
- **Review checklist**: 11/11 items checked
- **Acceptance checks**: 5/5 items checked
- **Self-review**: Tests 5854/5854 PASS, schema validation PASS
- **Evidence**: `assigned_claim_ids`/`assigned_claim_texts` fields added to GeneratedPage; `_compute_claim_coverage` replaces tautological formula; `confidence_filtered_count` field added

### TC-PA-02 — Elevate claim depth check
- **File**: `plans/taskcards/TC-PA-02_elevate_claim_depth_check.md`
- **Status**: In-Progress -> Done
- **Review checklist**: 11/11 items checked
- **Acceptance checks**: 5/5 items checked
- **Self-review**: Tests 5854/5854 PASS, grading PASS
- **Evidence**: `_DEPTH_THRESHOLD` 0.20->0.35, `_CONTEXT_WINDOW` 300->500, severity low->medium, multi-term window merging

### TC-PA-03 — Widen evidence window
- **File**: `plans/taskcards/TC-PA-03_widen_evidence_window.md`
- **Status**: In-Progress -> Done
- **Review checklist**: 11/11 items checked
- **Acceptance checks**: 5/5 items checked
- **Self-review**: Tests 5854/5854 PASS, prompt quality PASS
- **Evidence**: Snippet cap 300->600, up to 2 evidence anchors, `confidence_filtered_count` field added, WARNING-level logging for filtering and affinity fallback

### TC-PA-04 — Uncap LLM severity
- **File**: `plans/taskcards/TC-PA-04_uncap_llm_severity.md`
- **Status**: In-Progress -> Done
- **Review checklist**: 11/11 items checked
- **Acceptance checks**: 4/4 items checked
- **Self-review**: Tests 5854/5854 PASS (26 grading tests), grading PASS
- **Evidence**: `factual_accuracy` and `code_correctness` removed from `_LLM_CHECK_NAMES`; HIGH findings now produce Grade D

### TC-PA-05 — Harden claim ordering
- **File**: `plans/taskcards/TC-PA-05_harden_claim_ordering.md`
- **Status**: In-Progress -> Done
- **Review checklist**: 11/11 items checked
- **Acceptance checks**: 3/3 items checked
- **Self-review**: Tests 5854/5854 PASS, determinism PASS
- **Evidence**: `sorted()` added to `page_plan.assigned_claims` iteration; one-line change

## Summary

All 5 taskcards transitioned from In-Progress to Done. All review checklists, acceptance checks, and self-review verification results marked as complete with evidence references.
