# Evidence: TC-2374 — RD-07 Gate 20 Cross-Page Consistency Check

**Agent:** Orchestrator (Claude Code, session 2026-02-19)
**Date:** 2026-02-19
**Branch:** `healing/blkr-01-03-04-rd06`
**Status:** Done

---

## Summary

Added Gate 20 (Cross-Page Consistency) to W9 Validator. Three deterministic checks
detect duplicate prose blocks (G20-001), version contradictions (G20-002), and
class-name divergence (G20-003) across all published pages in a run.

---

## Root Cause

W7 validated pages in isolation. Pages could contradict each other (version ranges),
duplicate paragraphs verbatim (LLM paraphrasing), or use inconsistent names for the
same class — all undetected until manual review.

---

## Implementation

### `gate_20_cross_page_consistency.py`

Entry point: `run_gate_20(md_files: List[Path]) -> Tuple[bool, List[Dict]]`

**Check 1 — Duplicate block (G20-001, warn)**
- Strips frontmatter + code blocks from each page
- Splits into paragraphs on blank lines
- Exact string match; flags paragraphs ≥ 100 chars appearing in ≥ 2 pages
- Gate always passes on warn-only

**Check 2 — Version contradiction (G20-002, error)**
- Regex extracts Python `major.minor` versions from all pages
- Compares minimums across pages: conflicts when major differs OR minor differs > 1
- Gate fails when error issues exist

**Check 3 — Class name divergence (G20-003, warn)**
- Extracts backtick-quoted identifiers from pages
- Groups by normalized 6-char prefix
- Flags groups with 2+ distinct names (high-confidence divergence)

### Registration

- `gates/__init__.py`: added `"gate_20_cross_page_consistency"` to `__all__`
- `worker.py`: inline import after Gate 17, reuses `md_files_g17`; also added skip entry in `ValidatorArtifactMissingError` block

---

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w9_validator/gates/gate_20_cross_page_consistency.py` | New gate (3 checks) |
| `src/launch/workers/w9_validator/gates/__init__.py` | Added gate_20 to `__all__` |
| `src/launch/workers/w9_validator/worker.py` | Inline Gate 20 invocation after Gate 17; skip entry in missing-artifact block |
| `tests/unit/workers/test_gate_20_cross_page_consistency.py` | 4 new tests |
| `specs/09_validation_gates.md` | Added Gate 20 definition |

---

## Test Results

```
TestDuplicateBlockDetection:  2/2 pass
  - test_duplicate_block_detected   → G20-001 warn, gate passes
  - test_duplicate_block_clean      → 0 issues

TestVersionContradiction:  2/2 pass
  - test_version_contradiction_detected  → G20-002 error, gate fails
  - test_version_no_contradiction        → 0 issues, gate passes

Full suite: 4564 passed, 9 skipped, 0 failed
```

---

## Acceptance Criteria

| Check | Result |
|-------|--------|
| Duplicate ≥ 100-char paragraph in 2 pages → G20-001 warn | ✅ |
| Unique paragraphs → 0 G20-001 issues | ✅ |
| Python 3.8 vs 3.11 → G20-002 error, gate FAILS | ✅ |
| Consistent version → 0 G20-002 issues, gate PASSES | ✅ |
| Gate 20 registered in `__init__.py` and invoked in `worker.py` | ✅ |
| Additive: does not break existing Gate passes | ✅ |
| Full suite passes | ✅ 4564/4564 |
