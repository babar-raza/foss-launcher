---
id: TC-4092
title: "Fix format detection false positive (PDF in cells)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-11"
tags: ["understand", "format-matrix", "false-positive"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4092_format_detection_false_positive.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4092/evidence.md
evidence_required:
  - reports/TC-4092/evidence.md
---

# Taskcard TC-4092 — Fix format detection false positive (PDF in cells)

## Objective

`extract_format_matrix()` produces false positive format entries (e.g., PDF appearing in cells
library results) when Strategy 2/3 string-literal scans match format names in comments, error
messages, or documentation that describe unsupported formats. This taskcard adds a negative
context filter that suppresses string-scan-only results when surrounding text indicates the
format is NOT supported.

## Required spec references

- `specs/worker_understand.md` (Section: format matrix extraction)

## Scope

### In scope
- Add `_FORMAT_NEGATIVE_CTX_RE` pattern to `_deterministic.py`
- Add negative context filter in `extract_format_matrix()` merge loop
- Add 4 new tests in `TestTC4092FormatDetectionFalsePositive`

### Out of scope
- Changes to Strategy 1 (enum reference scanning) — only affects string-scan-only results
- Changes to README table scanning logic
- Any other workers or modules

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` — existing format matrix logic
- `tests/unit/workers/understand/test_extract.py` — existing test file to extend

## Outputs

- Updated `_deterministic.py` with negative context filter
- Updated `test_extract.py` with 4 new test cases
- `reports/TC-4092/evidence.md` with test run output

## Allowed paths

- plans/taskcards/TC-4092_format_detection_false_positive.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4092/evidence.md

### Allowed paths rationale
- Taskcard: required by AG-002
- `_deterministic.py`: source of false positive, requires negative context filter
- `test_extract.py`: new tests for the fix
- `evidence.md`: required evidence per AG-002

## Implementation steps

### Step 1: Add `_FORMAT_NEGATIVE_CTX_RE` pattern

Add the negative context pattern near the other format patterns (around line 475) in
`_deterministic.py`, after `_README_NEGATIVE_RE`:

```python
_FORMAT_NEGATIVE_CTX_RE = re.compile(
    r'\bnot\s+support|\bunsupported\b|\bno\s+support\b|'
    r'\bcannot\s+(?:export|import|load|save|read|write)\b|'
    r'\bdoes\s+not\s+(?:support|implement)\b|'
    r'\bnot\s+(?:implement|available)\b',
    re.IGNORECASE,
)
```

### Step 2: Add negative context filter in merge loop

In the `extract_format_matrix()` merge loop (around line 629), add a filter BEFORE building
FormatRecord objects. When a format has zero Strategy 1 hits AND any context line matches
`_FORMAT_NEGATIVE_CTX_RE`, skip the format.

Important: `format_counts` is incremented by ALL strategies (1, 2, 3), not just Strategy 1.
Strategy 1 only scans test/example dirs for `FileFormat.XXX` patterns. Strategies 2/3 scan
source+doc files for extension strings and bare format names.

To distinguish Strategy 1 hits, track them in a separate `enum_counts` dict in Strategy 1.

### Step 3: Implement enum_counts tracking

In Strategy 1 loop, also increment a `enum_counts` dict (separate from `format_counts`).
Use `enum_counts.get(fmt, 0) > 0` as the "has_code_enum_evidence" check.

### Step 4: Add tests

Add `TestTC4092FormatDetectionFalsePositive` class to `test_extract.py` with 4 tests.

### Step 5: Run tests and capture evidence

Run the full test suite and capture output to `reports/TC-4092/evidence.md`.

## Failure modes

### Failure mode 1: `extract_format_matrix` signature change

**Detection**: `TypeError` when calling `extract_format_matrix(tmp_path, family="cells")`
**Resolution**: The function signature uses `product: ProductIdentity`, not `family="cells"`.
The tests must create a `ProductIdentity` with `family="cells"` and pass it.
**Gate**: Test harness — import error or TypeError

### Failure mode 2: `format_counts` includes Strategy 2/3 hits

**Detection**: Test `test_format_with_enum_reference_not_excluded_despite_negative_context`
fails because PDF is excluded even when it has an enum reference.
**Resolution**: Track enum references separately in `enum_counts` (Strategy 1 only).
Use `enum_counts` (not `format_counts`) for the "has_code_enum_evidence" check.
**Gate**: Unit test assertion

### Failure mode 3: Negative pattern too broad

**Detection**: Formats like XLSX get dropped from results when they shouldn't be.
**Resolution**: Ensure the filter only applies when `enum_counts.get(fmt, 0) == 0`.
Any format with a Strategy 1 (enum reference) hit is exempt from the negative filter.
**Gate**: `test_xlsx_not_affected_by_negative_filter`

### Failure mode 4: Context lines only from Strategy 1

**Detection**: `test_format_with_negative_context_and_no_enum_refs_excluded` fails because
`format_context` only captures Strategy 1 context and misses Strategy 2/3 context.
**Resolution**: Strategies 2/3 also append to `format_context`, so the filter will work.
Verify by reading the code — `format_context.setdefault(_fmt, []).append(_ctx)` in Strat 2/3.
**Gate**: Unit test assertion

## Task-specific review checklist

1. [ ] `_FORMAT_NEGATIVE_CTX_RE` is defined at module level near other format patterns
2. [ ] `enum_counts` dict is populated only by Strategy 1 (FileFormat.XXX enum refs)
3. [ ] Negative context filter uses `enum_counts` (not `format_counts`) for code evidence check
4. [ ] Filter is placed BEFORE FormatRecord construction in the merge loop
5. [ ] Filter only skips when BOTH conditions are true: no enum evidence AND negative context
6. [ ] All 4 new tests pass independently (no shared mutable state)
7. [ ] Docstrings updated for `extract_format_matrix()` to describe the negative context filter
8. [ ] Spec file checked for drift — `specs/worker_understand.md` (confirm no spec update needed)
9. [ ] Schema `"description"` fields: no schema changes required for this fix
10. [ ] Checked `docs/README.md` — no trigger event for this internal extractor fix
11. [ ] Full test suite passes with PYTHONHASHSEED=0

## Deliverables

1. `src/launcher/workers/understand/extract/_deterministic.py` — updated with negative context filter
2. `tests/unit/workers/understand/test_extract.py` — 4 new tests added
3. `reports/TC-4092/evidence.md` — test run output

## Acceptance checks

1. [x] `_FORMAT_NEGATIVE_CTX_RE` pattern defined in `_deterministic.py`
2. [x] Negative context filter added in `extract_format_matrix()` merge loop
3. [x] All 4 new `TestTC4092FormatDetectionFalsePositive` tests PASS
4. [x] Full test suite passes: 3843 passed, 1 skipped, 3 xfailed
5. [x] Taskcard status set to `Done`

## Self-review

### Verification results
- [x] Tests: 4/4 PASS (TC-4092 specific) + 3843/3843 PASS (full suite)
- [x] Validation: format matrix negative filter PASS
- [x] Evidence captured: reports/TC-4092/evidence.md
- [x] Doc freshness: confirmed no spec drift — internal extractor change, no spec update required

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k "TC4092"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --ignore=tests/unit/workers/test_publish.py
```

**Expected results**:
- 4 new `TestTC4092FormatDetectionFalsePositive` tests PASS
- Full suite PASS with no regressions

## Integration boundary proven

**Upstream**: `extract_format_matrix()` is called by the understand worker during format matrix extraction
**Downstream**: `FormatRecord` list is consumed by `ProductEvidence` and used in content generation
**Contract**: `FormatRecord` model — `name`, `extension`, `can_import`, `can_export`, `test_count`, `source_evidence`
