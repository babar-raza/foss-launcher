# TC-670 Report: Fix W4 Path Resolution to Match site_layout

**Agent**: VSCODE_AGENT
**Date**: 2026-01-30
**Status**: COMPLETE

## Summary

Fixed W4 IAPlanner to use `site_layout.subdomain_roots[section]` for subdomain routing and `run_config.family` for the family path segment.

## Changes Made

### 1. Modified `compute_output_path()` (worker.py:369-397)

**Before**:
```python
def compute_output_path(
    section: str,
    slug: str,
    product_slug: str,
    subdomain: str = "docs.aspose.org",  # Hardcoded!
    ...
```

**After**:
```python
def compute_output_path(
    section: str,
    slug: str,
    family: str,
    subdomain_roots: Dict[str, str],  # From run_config.site_layout
    ...
```

### 2. Modified `plan_pages_for_section()` (worker.py:400+)

Updated signature and all calls to pass `family` and `subdomain_roots`.

### 3. Modified `execute_ia_planner()` (worker.py:820+)

- Extract `family` from `run_config` (required, with fallback)
- Extract `subdomain_roots` from `run_config.site_layout`
- Extract `platform` from `run_config.target_platform`
- Extract `locale` from `run_config.locales[0]`

## Wrong vs Fixed Path Examples

| Section | WRONG (Before) | FIXED (After) |
|---------|----------------|---------------|
| products | `content/docs.aspose.org//en/python/overview.md` | `content/products.aspose.org/note/en/python/overview.md` |
| docs | `content/docs.aspose.org//en/python/docs/getting-started.md` | `content/docs.aspose.org/note/en/python/getting-started.md` |
| reference | `content/docs.aspose.org//en/python/reference/api-overview.md` | `content/reference.aspose.org/note/en/python/api-overview.md` |
| kb | `content/docs.aspose.org//en/python/kb/faq.md` | `content/kb.aspose.org/note/en/python/faq.md` |
| blog | `content/docs.aspose.org//en/python/blog/announcement.md` | `content/blog.aspose.org/note/python/announcement/index.md` |

## Page Counts Per Subdomain (Pilot-2 Note)

| Subdomain | Page Count |
|-----------|------------|
| products.aspose.org | 1 |
| docs.aspose.org | 1 |
| reference.aspose.org | 1 |
| kb.aspose.org | 1 |
| blog.aspose.org | 1 |
| **Total** | **5** |

## validation_report.json Produced

**YES** - Path: `runs/r_20260130T06XXXX_note-python_.../artifacts/validation_report.json`

## Determinism Proof

- page_plan.json SHA256: c799e652507ecd0b... (DETERMINISTIC - identical across runs)
- validation_report.json: Contains run-specific paths (expected non-deterministic)

## Test Results

- TC-670 unit tests: 23/23 PASS
- TC-430 tests (updated): 30/30 PASS
- Full pytest: 1 unrelated failure (telemetry API test)

## Files Modified

1. `src/launch/workers/w4_ia_planner/worker.py` - Path computation logic
2. `tests/unit/workers/test_tc_670_w4_paths.py` - New unit tests
3. `tests/unit/workers/test_tc_430_ia_planner.py` - Updated existing tests
4. `scripts/run_pilot.py` - Fixed run_dir parsing
5. `specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json` - Updated golden
6. `specs/pilots/pilot-aspose-note-foss-python/expected_validation_report.json` - Updated golden

## Acceptance Criteria Status

| ID | Criterion | Status |
|----|-----------|--------|
| A | W4 output_path uses subdomain_roots[section] | PASS |
| B | W4 output_path uses run_config.family | PASS |
| C | No double slashes | PASS |
| D | Family segment always present | PASS |
| E | No section folder inside subdomain root | PASS |
| F | Blog uses bundle style (index.md) | PASS |
| G | Blog has no locale segment | PASS |
| H | pytest tests/unit/workers/test_tc_670_w4_paths.py PASS | PASS |
| I | Pilot-2 E2E page_plan MATCH | PASS |
