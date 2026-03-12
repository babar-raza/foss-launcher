---
id: TC-4020
title: "HG-12: Add Strategy 3 format matrix extraction for Python extension string literals"
status: Done
priority: High
owner: "understand"
updated: "2026-03-11"
tags: [humming-greeting-kay, understand, format-matrix, python]
depends_on: [TC-4002]
ruleset_version: "1.0"
spec_ref: "5234ff1"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4020_hg12-format-matrix-python.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/test_understand.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4020 — HG-12: Format Matrix Strategy 3

## Objective

The pilot (HG-02) found 0 format records for aspose-3d-foss-python. The existing Strategy 1 only matches `FileFormat.XXX` enum syntax (Aspose .NET/Java style), which Python SDKs do not use. Strategy 3 adds detection of file extension string literals (`"output.fbx"`) and bare format name strings (`"FBX"`) so Python libraries get populated format matrices.

## Required spec references

- `src/launcher/workers/understand/extract/_deterministic.py` — `extract_format_matrix()`
- `phase_store/pilot_quality_report.md` — Gap 5: format_matrix empty

## Scope

### In scope

- Add `_FORMAT_STRING_PATTERN` regex for extension string literals
- Add `_FORMAT_BARE_PATTERN` regex for bare format name strings
- Add Strategy 3 scanning src/, lib/, examples/, docs/ for both patterns
- Add 4 unit tests in `TestFormatMatrix`

### Out of scope

- Changing Strategy 1 or Strategy 2
- Adding non-Python platform format extraction

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` — `extract_format_matrix()`
- `phase_store/pilot_quality_report.md` — root cause

## Outputs

- Updated `src/launcher/workers/understand/extract/_deterministic.py`
- 4 new tests in `tests/unit/workers/test_understand.py::TestFormatMatrix`

## Allowed paths

- plans/taskcards/TC-4020_hg12-format-matrix-python.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/test_understand.py

### Allowed paths rationale

Only the deterministic extractor and its test file are changed. No model or worker changes needed.

## Implementation steps

### Step 1: Add regex patterns

Added `_FORMAT_STRING_PATTERN` for `.fbx`, `.obj`, etc. in string literals.
Added `_FORMAT_BARE_PATTERN` for `"FBX"`, `"OBJ"` etc. bare strings.

### Step 2: Add Strategy 3 scan

Added Strategy 3 after Strategy 1 — scans src/, lib/, examples/, docs/, tests/
for extension-based and bare format name strings.

### Step 3: Tests

Added 4 tests: extension literal detection, save context → can_export, open context → can_import, bare string detection.

## Failure modes

### Failure mode 1: Over-detection of common extension names

**Detection**: False positives from `.doc`, `.csv`, `.pdf` in non-format code
**Resolution**: Only count when extension is in `_FORMAT_EXTENSIONS`; context still required for can_import/can_export
**Gate**: Unit tests verify correct can_import/can_export flags

### Failure mode 2: Existing tests broken

**Detection**: Regression in `TestFormatMatrix.test_format_matrix_empty_on_no_test_files`
**Resolution**: Strategy 3 only runs when files exist; empty dir still returns []
**Gate**: Full test suite

### Failure mode 3: Performance regression from scanning more files

**Detection**: Understand worker takes >3x longer
**Resolution**: Files capped at 120 per call; early exits on errors
**Gate**: Pilot run timing

## Task-specific review checklist

- [x] `_FORMAT_STRING_PATTERN` matches `.fbx`, `.obj` in string literals
- [x] `_FORMAT_BARE_PATTERN` matches `"FBX"`, `"OBJ"` bare strings
- [x] Strategy 3 scans src/, lib/, examples/, docs/, tests/
- [x] Context detection (save/from_file) sets can_export/can_import correctly
- [x] 4 new unit tests all pass
- [x] Full test suite passes with no new failures
- [x] Existing Strategy 1 tests unchanged
- [x] Docstrings not broken
- [x] Schema not changed
- [x] Spec freshness checked

## Deliverables

1. Updated `src/launcher/workers/understand/extract/_deterministic.py`
2. 4 new tests in `tests/unit/workers/test_understand.py::TestFormatMatrix`

## Acceptance checks

- [x] `TestFormatMatrix::test_hg12_extension_string_literal_detected` PASS
- [x] `TestFormatMatrix::test_hg12_save_context_sets_can_export` PASS
- [x] `TestFormatMatrix::test_hg12_open_context_sets_can_import` PASS
- [x] `TestFormatMatrix::test_hg12_bare_format_string_detected` PASS
- [x] Full test suite: 3565 passed, 0 new failures (commit 5234ff10)

## Self-review

### Verification results
- [x] Tests: 8/8 PASS (TestFormatMatrix)
- [x] Full suite: 3565 passed, 6 pre-existing failures only
- [x] Evidence captured: git commit 5234ff10

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py::TestFormatMatrix -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- All 8 TestFormatMatrix tests passing
- 3565 total passing tests

## Integration boundary proven

**Upstream integration**: `extract/_deterministic.py::extract_format_matrix()` → called from extract pipeline before LLM.

**Downstream integration**: `product_evidence.limitations` → generate worker → section prompt (now injected via HG-11).
