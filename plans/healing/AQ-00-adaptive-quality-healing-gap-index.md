# Adaptive Quality Healing — Gap Index

**Context**: Self-review of TC-3816 + TC-3817 implementation (8 coordinated changes for adaptive content quality). The implementation passes all 2067 tests but has spec deviations, pipeline integrity issues, and robustness gaps that must be resolved before pilot verification.

**Source self-review date**: 2026-03-07
**Taskcards healed**: TC-3816 (understand), TC-3817 (generate/planner)

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| GAP-01 | **Critical** | Docstring claims bypass validation pipeline (sandwich model violation) | AQ-01 |
| GAP-02 | **Critical** | `_distribute_claims` wrap-around not implemented — sections still get 0 claims | AQ-02 |
| GAP-03 | **High** | Page-relevant class selection not implemented — all pages get same 15 classes | AQ-03 |
| GAP-04 | **High** | `_validate_identifiers` strips Python builtins (`str`, `int`, `Path`, `None`) | AQ-04 |
| GAP-05 | **Medium** | Bare `list` type annotations on `class_briefs` parameters (4 functions) | AQ-05 |
| GAP-06 | **Medium** | `_is_internal_class` hardcoded to Aspose markers — not generalizable | AQ-05 |
| GAP-07 | **Medium** | `_validate_identifiers` reconstructs BlockIR field-by-field (fragile) | AQ-05 |
| GAP-08 | **Medium** | No logging in `_extract_api_surface` for filter stage counts | AQ-06 |
| GAP-09 | **Medium** | Synthetic snippets assume flat `{canonical_import}.{Class}()` import path | AQ-05 |
| GAP-10 | **Low** | No `context.emit_event` calls for new pipeline stages | AQ-06 |
| GAP-11 | **Low** | Duplicate API surface filtering in extract + generate worker | AQ-05 |
| GAP-12 | **Low** | Missing integration test for class_briefs end-to-end flow | AQ-07 |
| GAP-13 | **Low** | Evidence files not written, taskcard acceptance checks not ticked | AQ-08 |

---

## Taskcard Summary

| Taskcard | Title | Gaps Fixed | Priority |
|----------|-------|------------|----------|
| AQ-01 | Route docstring claims through validation pipeline | GAP-01 | Critical |
| AQ-02 | Implement claim distribution wrap-around | GAP-02 | Critical |
| AQ-03 | Page-relevant class selection in API surface prompt | GAP-03 | High |
| AQ-04 | Builtin identifier allowlist in method validation | GAP-04 | High |
| AQ-05 | Code quality: type annotations, BlockIR copy, internal markers, import paths | GAP-05, GAP-06, GAP-07, GAP-09, GAP-11 | Medium |
| AQ-06 | Observability: filter stage logging + pipeline events | GAP-08, GAP-10 | Medium |
| AQ-07 | Integration test: class_briefs end-to-end flow | GAP-12 | Low |
| AQ-08 | Taskcard governance: evidence files + acceptance checks | GAP-13 | Low |
