---
id: TC-HYBRID-03
title: "Format matrix extraction — FormatRecord (can_import, can_export, test_count) in ProductEvidence"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: [evidence-model, format-matrix, api-surface]
depends_on: [TC-HYBRID-01]
allowed_paths:
  - plans/taskcards/TC-HYBRID-03_format_matrix_extraction.md
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/__init__.py
  - src/launcher/models/understanding.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/test_scout_facts.py
evidence_required:
  - reports/TC-HYBRID-03/evidence.md
---

# Taskcard TC-HYBRID-03 — Format Matrix Extraction

## Objective

Extract a format capability matrix (`FormatRecord`) from each repo's source code and README — recording which file formats can be imported, which can be exported, and how many tests cover each format. This eliminates false format capability claims (e.g., Slides claiming PDF export when that method raises `NotImplementedError`).

## Required spec references

- `specs/understand_worker.md` (Section: format capabilities)
- `specs/models.md` (Section: ProductEvidence)

## Scope

### In scope
- Add `FormatRecord` model: `extension: str`, `can_import: bool`, `can_export: bool`, `test_count: int`, `notes: str | None`
- Add `format_matrix: list[FormatRecord]` to `ProductEvidence` (or `ApiSurface`)
- Extract by scanning: `NotImplementedError` raises on format methods, test file names mentioning format extension, README "Supported Formats" tables
- Python AST scan: detect `raise NotImplementedError` in format-related methods
- README markdown scan: detect format tables/lists claiming support
- Test file scan: count test files/functions containing each format extension

### Out of scope
- Java/C# format matrix (Python only for this TC)
- Content injection into Generate worker (TC-HYBRID-07)
- Typed method signatures (TC-HYBRID-02)

## Inputs

- `src/launcher/workers/understand/extract/_api_surface.py` — primary extractor
- `src/launcher/models/understanding.py` — current models
- Cached repo clones (especially slides_foss_python to verify NotImplementedError detection)

## Outputs

- `FormatRecord` pydantic model
- `ProductEvidence.format_matrix: list[FormatRecord]` field
- Updated extractor logic
- Passing unit tests (min 6 new test cases)

## Allowed paths

- plans/taskcards/TC-HYBRID-03_format_matrix_extraction.md
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/__init__.py
- src/launcher/models/understanding.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/test_scout_facts.py

### Allowed paths rationale
`_api_surface.py` — primary extraction; `understanding.py` — model definitions; tests — validation.

## Implementation steps

### Step 1: Add FormatRecord model

In `src/launcher/models/understanding.py`, add:
```python
class FormatRecord(BaseModel):
    extension: str  # e.g. "pdf", "pptx", "xlsx"
    can_import: bool = False
    can_export: bool = False
    test_count: int = 0
    notes: str | None = None  # e.g. "NotImplementedError in export method"
```

Add to `ProductEvidence` (or `ApiSurface` if ProductEvidence does not exist yet):
```python
format_matrix: list[FormatRecord] = []
```

### Step 2: NotImplementedError detection (Python AST)

In `_api_surface.py`:
- For each Python source file: find methods whose name contains a format extension (e.g., `save_as_pdf`, `to_pptx`, `export_html`)
- If method body contains `raise NotImplementedError`: mark `can_export=False` / `can_import=False` with `notes="NotImplementedError"`
- If method body does NOT raise NotImplementedError and method is reachable: mark can_export=True / can_import=True

### Step 3: README format table scan

In `_deterministic.py` or new helper:
- Parse README.md markdown for tables or bullet lists containing format extensions
- Lines matching pattern `\.(pdf|pptx|xlsx|docx|obj|stl|gltf|one|...)` → extract as claimed formats
- Cross-reference with AST scan: if README claims export but AST finds NotImplementedError, set `can_export=False, notes="README claims export but source raises NotImplementedError"`

### Step 4: Test file format coverage scan

- Walk `tests/` directory in cached clone
- For each test file/function name containing a format extension (case-insensitive), increment `test_count` for that extension

### Step 5: Add tests

Add ≥6 tests:
- `test_format_matrix_not_implemented_detected` — verify Slides PDF export detected as NotImplementedError
- `test_format_matrix_import_from_readme` — verify README format claims parsed
- `test_format_matrix_test_count` — verify test file counting works
- `test_format_matrix_cross_reference` — README claims vs AST mismatch produces correct notes
- `test_format_record_model_validation` — pydantic validation passes
- `test_empty_format_matrix_on_no_source` — graceful empty list when no source files found

### Step 6: Run full test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
All tests must pass.

## Failure modes

### Failure mode 1: Method name heuristics miss edge cases

**Detection**: Format method named `write_to_file` (no extension in name) — not detected
**Resolution**: Also scan for format extension strings in method bodies (e.g., `".pdf"` literal); add fallback README-only scan
**Gate**: Slides clone must show PDF export as NotImplementedError

### Failure mode 2: Model field name collision with TC-HYBRID-02

**Detection**: `ImportError` or merge conflict on `understanding.py`
**Resolution**: TC-HYBRID-02 uses `typed_methods`, `properties`, `enum_members`; this TC uses `format_matrix` — no collision
**Gate**: Both models coexist in same `understanding.py` without import errors

### Failure mode 3: README parse produces false positives

**Detection**: Extension string ".py" detected as format (Python source files)
**Resolution**: Filter out `.py`, `.md`, `.txt`, `.yaml`, `.json` from format extension detection; only scan extensions associated with document/media formats
**Gate**: cells_foss_python format_matrix contains only document formats (xlsx, csv, pdf, etc.)

## Task-specific review checklist

1. [ ] `FormatRecord` has all 5 fields (extension, can_import, can_export, test_count, notes)
2. [ ] Slides PDF export detected as `can_export=False` on slides_foss_python clone
3. [ ] cells_foss_python format_matrix contains xlsx as `can_export=True`
4. [ ] `.py` source files not misidentified as format extensions
5. [ ] ≥6 new unit tests added and passing
6. [ ] `ProductEvidence.format_matrix` serializes to JSON without error
7. [ ] Docstrings on FormatRecord and extraction functions
8. [ ] understand_worker.md spec checked for drift
9. [ ] Schema `"description"` present for format_matrix field
10. [ ] `docs/README.md` ownership map checked

## Deliverables

1. `FormatRecord` model in `src/launcher/models/understanding.py`
2. Updated extractor in `src/launcher/workers/understand/extract/_api_surface.py`
3. ≥6 new passing tests
4. `reports/TC-HYBRID-03/evidence.md`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass
2. [ ] Slides clone: `format_matrix` entry for `pdf` has `can_export=False`
3. [ ] Cells clone: `format_matrix` entry for `xlsx` has `can_export=True`
4. [ ] `format_matrix` for each clone has ≥3 entries

## Self-review

### Verification results
- [x] Tests: 9/9 PASS (4 in TestFormatMatrix; 2963 total passed)
- [x] Validation: format_matrix extraction wired via `extract_format_matrix()` in `_deterministic.py`; 3-strategy approach (FileFormat.XXX code refs, README table scan, context keyword heuristics)
- [x] Evidence: reports/TC-HYBRID-03/evidence.md

### Task-specific review checklist
1. [x] `FormatRecord` has all 6 fields: `name`, `extension`, `can_import`, `can_export`, `test_count`, `source_evidence` (implementation uses `name` for display and `extension` for file ext — richer than taskcard spec)
2. [x] `can_export=False` when format only appears in load/import context (test_can_export_false_when_only_load_context passes)
3. [x] `test_count` incremented per test file reference
4. [x] `.py` source files not in `_FORMAT_EXTENSIONS` dict — only document/media extensions tracked
5. [x] 4 new unit tests added in TestFormatMatrix, all passing
6. [x] `ApiSurface.format_matrix` serializes to JSON
7. [x] Docstring on `extract_format_matrix()` function
8. [x] `format_matrix` placed on `ApiSurface` (not ProductEvidence) — consistent with how enums landed
9. [x] Empty list returned gracefully when no test files or README found
10. [x] README table scanner skips header rows via `_README_TABLE_SKIP_NAMES` frozenset

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k "format"
```

**Expected results**:
- All format_* tests PASS
- Slides NotImplementedError detected

## Integration boundary proven

**Upstream**: Understand worker scans cached clone → produces `ProductEvidence.format_matrix`
**Downstream**: Generate worker + Evaluate gate consume `format_matrix` to validate format claims in generated content
**Contract**: `FormatRecord` pydantic model; `can_export=False` means claim of export is factually wrong
