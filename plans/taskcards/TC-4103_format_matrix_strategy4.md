---
id: TC-4103
title: "Format matrix: Strategy 4 — detect format class names in imports"
status: Done
priority: High
owner: Agent-B
updated: "2026-03-11"
tags: [understand, format-matrix, evidence]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4103_format_matrix_strategy4.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B/TC-4103/evidence.md
evidence_required:
  - reports/agents/B/TC-4103/evidence.md
---

# Taskcard TC-4103 — Format matrix: Strategy 4 — detect format class names in imports

## Objective

`extract_format_matrix()` returns 0 formats for aspose-3d-foss-python because the repo uses save-options class names (`FbxSaveOptions`, `ObjLoadOptions`, `GltfSaveOptions`) rather than `FileFormat.FBX` enum references. Strategy 4 scans source, import, and test files for class name patterns like `{Format}SaveOptions` / `{Format}LoadOptions` etc., extracts the format name from the class prefix, and adds this evidence to the format matrix — fixing the 0-format problem for repos using the options-class pattern.

## Required spec references

- `specs/worker_understand.md` (Section: Format matrix extraction strategies)
- `specs/schemas/understanding_bundle.schema.json` (Section: supported_formats / FormatRecord)

## Scope

### In scope
- Add Strategy 4 inside `extract_format_matrix()` in `src/launcher/workers/understand/extract/_deterministic.py`
- Scan source/import/test files for `{Format}(Save|Load|Import|Export)Options` class name patterns
- Merge Strategy 4 results into the final `FormatRecord` assembly
- Update `all_formats` union to include Strategy 4 format names
- Add unit tests in `tests/unit/workers/understand/test_extract.py`

### Out of scope
- Modifying Strategies 1, 2, or 3 of `extract_format_matrix()`
- Changing `FormatRecord` model structure
- Changes to any other extraction function

## Inputs

- `src/launcher/workers/understand/extract/_deterministic.py` — `extract_format_matrix()` implementation (lines 427–715)
- Source/import/test files in `_src_candidate_dirs` (same dirs scanned by Strategy 3)
- `tests/unit/workers/understand/test_extract.py`

## Outputs

- Updated `_deterministic.py` with Strategy 4 block
- New unit tests covering `FbxSaveOptions` → FBX can_export, `ObjLoadOptions` → OBJ can_import
- `reports/agents/B/TC-4103/evidence.md`

## Allowed paths

- plans/taskcards/TC-4103_format_matrix_strategy4.md
- src/launcher/workers/understand/extract/_deterministic.py
- tests/unit/workers/understand/test_extract.py
- reports/agents/B/TC-4103/evidence.md

### Allowed paths rationale

- `_deterministic.py` contains `extract_format_matrix()` where Strategy 4 is added
- `test_extract.py` is the existing extraction test module — new tests added here
- `evidence.md` captures the pytest run proving the fix

## Implementation steps

### Step 1: Read extract_format_matrix() fully

Read `_deterministic.py` lines 427–715 to understand the complete `extract_format_matrix()` implementation: Strategies 1/2/3, the `all_formats` union computation, and the final `FormatRecord` assembly loop. Identify where to insert Strategy 4 (BEFORE the "Build FormatRecord list" section) and where `all_formats` is assembled (UPDATE that line to include Strategy 4 format names).

### Step 2: Define the Strategy 4 pattern regex

Add a module-level constant (or function-local constant) `_FORMAT_OPTIONS_PATTERN`:

```python
_FORMAT_OPTIONS_PATTERN = re.compile(
    r'\b(fbx|obj|gltf|glb|stl|dae|3ds|usd|usda|dxf|ifc|step|iges|ply|x3d|'
    r'pdf|docx|xlsx|html|png|jpeg|jpg|bmp|tiff|collada|draco|amf)'
    r'(Save|Load|Import|Export)Options\b',
    re.IGNORECASE,
)
```

Group 1 = format name (normalized via `.upper()`). Group 2 = capability verb.

### Step 3: Add Strategy 4 block inside extract_format_matrix()

Before the "Build FormatRecord list" section, add:

```python
# Strategy 4: detect {Format}(Save|Load|Import|Export)Options class names
options_can_import: dict[str, bool] = {}
options_can_export: dict[str, bool] = {}
for _cand_file in _src_candidate_files:  # same list used by Strategy 3
    try:
        _text = _cand_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    for _m in _FORMAT_OPTIONS_PATTERN.finditer(_text):
        _fmt = _m.group(1).upper()
        _cap = _m.group(2).lower()
        if _cap in ("save", "export"):
            options_can_export[_fmt] = True
        else:  # load, import
            options_can_import[_fmt] = True
```

### Step 4: Merge Strategy 4 into FormatRecord assembly

In the final `FormatRecord` assembly loop, after the existing Strategy 1/2/3 merges for `can_import` and `can_export`, add:

```python
if fmt in options_can_import:
    can_import = True
if fmt in options_can_export:
    can_export = True
```

### Step 5: Update all_formats union

Change the `all_formats` computation to include Strategy 4 format names:

```python
all_formats = (
    set(format_counts.keys())
    | set(readme_caps.keys())
    | set(options_can_import.keys())
    | set(options_can_export.keys())
)
```

### Step 6: Write unit tests

In `tests/unit/workers/understand/test_extract.py`, add:
1. A test with a `tmp_path` Python file containing `from aspose.threed import FbxSaveOptions, ObjLoadOptions`. Call `extract_format_matrix()` and assert: FBX record exists with `can_export=True`; OBJ record exists with `can_import=True`.
2. A test that Strategy 4 does NOT create false positives for non-format words (e.g., no `FooSaveOptions` where "foo" is not in the format list).

## Failure modes

### Failure mode 1: Format name prefix false positive (e.g., PDFSaveOptions in a report generator)

**Detection**: `PDF` is added to format matrix with `can_export=True` for a repo that produces PDF reports — but may not actually support PDF import/export in the FOSS library sense.
**Resolution**: Strategy 4 only ADDS evidence to the matrix; it does not override negative context filters from Strategies 1-3. If Strategy 1 already excluded PDF via a negative context filter, Strategy 4 should not re-add it. Add a guard: Strategy 4 results are only applied if no negative context for that format exists in `_negative_context_formats` (the set already computed by earlier strategies).
**Gate**: `specs/worker_understand.md` — format matrix must not claim formats unsupported by the library.

### Failure mode 2: Mixed case — FbxSaveOptions vs FBXSaveOptions

**Detection**: Either variant must be detected consistently.
**Resolution**: `re.IGNORECASE` handles both. Group 1 is normalized via `.upper()` so both resolve to `"FBX"`.
**Gate**: Unit test coverage — both variants tested.

### Failure mode 3: Regex too broad — unknown format prefix matches

**Detection**: A class like `XmlSaveOptions` would match `xml` if `xml` were in the list — but it is not. The list is explicit and bounded to known 3D/document formats.
**Resolution**: The format name list is fully explicit in the regex pattern. No wildcards. Only add formats to the list when they are confirmed supported formats for the target product families.
**Gate**: `specs/worker_understand.md` — extraction must be evidence-based, not speculative.

## Task-specific review checklist

1. [ ] Strategy 4 is inserted BEFORE the "Build FormatRecord list" section, not inside it
2. [ ] `all_formats` union updated to include `options_can_import.keys()` and `options_can_export.keys()`
3. [ ] `re.IGNORECASE` applied to `_FORMAT_OPTIONS_PATTERN`
4. [ ] Group 1 format name normalized via `.upper()` before use as dict key
5. [ ] Strategy 4 results only apply for formats not already negated by context filters
6. [ ] Unit test: `FbxSaveOptions` → FBX can_export=True
7. [ ] Unit test: `ObjLoadOptions` → OBJ can_import=True
8. [ ] Docstring for `extract_format_matrix()` updated to document Strategy 4
9. [ ] Spec file `specs/worker_understand.md` reviewed — no spec drift introduced
10. [ ] Schema `specs/schemas/understanding_bundle.schema.json` reviewed — FormatRecord structure unchanged
11. [ ] Checked `docs/README.md` ownership map — format extraction change does not require guide update

## Deliverables

1. Updated `src/launcher/workers/understand/extract/_deterministic.py` with Strategy 4
2. New unit tests in `tests/unit/workers/understand/test_extract.py`
3. `reports/agents/B/TC-4103/evidence.md` with pytest output

## Acceptance checks

- [ ] Unit test: `FbxSaveOptions` in code → FBX record with `can_export=True`
- [ ] Unit test: `ObjLoadOptions` in code → OBJ record with `can_import=True`
- [ ] Full test suite: 0 regressions
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v` — 0 failures
- [ ] When run against aspose-3d-foss pilot: `format_matrix_count > 0` (to be verified in next pipeline run)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Strategy 4 format detection PASS
- [ ] Evidence captured: `reports/agents/B/TC-4103/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v
```

**Expected results**:
- All pre-existing `test_extract.py` tests PASS
- New Strategy 4 test PASS: FBX can_export=True, OBJ can_import=True from options class names
- No false positives from non-format class names

## Integration boundary proven

**Upstream**: `extract_format_matrix()` scans the same `_src_candidate_files` used by Strategy 3 — no new file discovery needed
**Downstream**: `FormatRecord` list is consumed by `ProductEvidence.supported_formats` and injected into section prompts by the Generate worker
**Contract**: `FormatRecord` structure is unchanged; Strategy 4 only populates existing `can_import`/`can_export` fields — schema-compatible by design
