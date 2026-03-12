# SNP — Snippet Curation Healing Gap Index

**Source**: Self-review of TC-4062 (remove synthetic snippets) + TC-4063 (snippet provenance + dedup)
**Date**: 2026-03-11
**Reviewer**: agent (AG-020 protocol)

## Summary of Gaps

Six gaps were identified across testability, observability, code quality, and model hygiene dimensions.

| ID | Title | Severity | Priority |
|----|-------|----------|----------|
| SNP-01 | Missing test coverage for dedup and source_file | Blocker | High | **Done** |
| SNP-02 | Dedup skip counter missing from extraction logs | Moderate | Normal | **Done** |
| SNP-03 | snippet_extraction_complete event deleted without replacement | Moderate | Normal | **Done** |
| SNP-04 | `source_type: "synthetic"` literal has no producer — needs deprecation note | Low | Low | **Done** |
| SNP-05 | `_dedup_key` nested inside `_extract_snippets` — should be module-level + encoding safety | Low | Normal | **Done** |
| SNP-06 | `line_start`/`line_end` always None — no documentation or future-work note | Low | Low | **Done** |

## Execution order

1. SNP-01 (blocker — tests must exist before code ships)
2. SNP-02 + SNP-03 (can be done in parallel — both in observability track)
3. SNP-05 (code quality — prerequisite for SNP-02 if dedup_key is extracted)
4. SNP-04 + SNP-06 (low priority, documentation-only changes)

## Files touched across all SNP taskcards

- `tests/unit/workers/understand/test_extract.py` (SNP-01)
- `src/launcher/workers/understand/extract/_snippets.py` (SNP-02, SNP-05, SNP-06)
- `src/launcher/workers/understand/extract/_entry.py` (SNP-03)
- `src/launcher/models/claims.py` (SNP-04)
