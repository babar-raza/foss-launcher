---
id: TC-4096
title: "Fix format detection: exclude URL-embedded file extensions from Strategy 3"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase5, understand, formats, false-positive]
depends_on: [TC-4092]
allowed_paths:
  - plans/taskcards/TC-4096_format_url_exclusion.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4096/evidence.md
evidence_required:
  - reports/TC-4096/evidence.md
---

# Taskcard TC-4096 — Fix format detection: exclude URL-embedded file extensions

## Objective

TC-4092 added a negative-context filter for string-scan-only format detections, but PDF is still
a false positive in the aspose-cells pilot because `_FORMAT_STRING_PATTERN` matches `.pdf` inside
a hyperlink URL (`"file:///C:/Documents/report.pdf"`), which puts a Strategy 3 count > 0,
bypassing the TC-4092 filter. The URL-embedded extension is not a format I/O operation.

## Required spec references

- `specs/worker_understand.md` (Phase B.1b: format matrix extraction)

## Scope

### In scope
- Exclude strings matched by `_FORMAT_STRING_PATTERN` that look like URLs (contain `://`)
- Applies only to Strategy 3 string-extension matches in `extract_format_matrix()`

### Out of scope
- `_FORMAT_BARE_PATTERN` matches (bare quoted format names like `"PDF"`)
- Strategy 1 enum reference matches
- Strategy 2 README table matches

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` — Strategy 3 string scan loop

## Outputs

- Fixed `src/launcher/workers/understand/extract/_deterministic.py`
- Updated tests in `tests/unit/workers/understand/test_extract.py`
- `reports/TC-4096/evidence.md`

## Allowed paths

- plans/taskcards/TC-4096_format_url_exclusion.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4096/evidence.md

## Implementation steps

### Step 1: Exclude URL-embedded extensions in Strategy 3

In the `_FORMAT_STRING_PATTERN` loop (around line 587), add URL exclusion:

```python
for _m in _FORMAT_STRING_PATTERN.finditer(_content):
    _ext_str = _m.group(1).upper()
    _fmt = _ext_to_fmt.get(_ext_str)
    if not _fmt:
        continue
    # TC-4096: Skip if matched string is a URL (file:// http:// https:// ftp://)
    # These are hyperlink targets, not format I/O operations.
    if re.search(r'(?:file|http|https|ftp)://', _m.group(0), re.IGNORECASE):
        continue
    format_counts[_fmt] = format_counts.get(_fmt, 0) + 1
    ...
```

## Failure modes

### Failure mode 1: Real format-file URLs are excluded
**Detection**: A repo that does `workbook.save("http://example.com/output.xlsx")` loses XLSX detection.
**Resolution**: Such repos also have local file saves; XLSX will still be detected from local paths.
**Gate**: XLSX, CSV, JSON still detected in cells pilot re-run.

### Failure mode 2: URL check too broad, misses other false-positive URL patterns
**Detection**: Other URL patterns (e.g., `smb://`) not covered.
**Resolution**: The common cases are `file://`, `http://`, `https://`, `ftp://` — sufficient for current corpus.
**Gate**: No regressions in existing format detection tests.

### Failure mode 3: Regex import missing
**Detection**: `re.search` used without `import re` in scope.
**Resolution**: `re` is already imported at top of `_deterministic.py`.
**Gate**: Module imports successfully.

## Task-specific review checklist

1. [ ] URL-embedded `.pdf` in hyperlink string → PDF NOT added to format_counts
2. [ ] Normal local path `.pdf` string → still adds to format_counts (if no negative context)
3. [ ] XLSX, CSV, JSON detection unaffected in cells pilot
4. [ ] Existing format detection tests all pass
5. [ ] PDF removed from `supported_formats` and `input_formats` in pilot re-run
6. [ ] No exception when URL pattern regex applied

## Deliverables

1. Fixed `src/launcher/workers/understand/extract/_deterministic.py`
2. New test in `tests/unit/workers/understand/test_extract.py`
3. `reports/TC-4096/evidence.md`

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q`
2. [ ] Cells pilot re-run: PDF NOT in `supported_formats`
3. [ ] Cells pilot re-run: XLSX, CSV, JSON still in `supported_formats`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: PASS
- [ ] Evidence captured: reports/TC-4096/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v
```

## Integration boundary proven

**Upstream**: `extract_format_matrix()` processes cloned repo files
**Downstream**: `api_surface.format_matrix` → `product_evidence.supported_formats`
**Contract**: Hyperlink URL paths containing file extensions are not treated as format I/O evidence
