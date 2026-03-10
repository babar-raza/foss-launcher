---
id: TC-4026
title: "HG-18: Restrict HG-16 to CamelCase identifiers only (require two-word minimum)"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, hallucination, post-generation-repair, bugfix]
depends_on: [TC-4025]
ruleset_version: "1.0"
spec_ref: "8b99e151"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4026_hg18-camelcase-class-detection.md
  - src/launcher/workers/generate/section_validator.py
  - tests/unit/workers/generate/test_section_validator.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4026 — HG-18: CamelCase-Only Class Detection

## Objective

HG-17 stripped comment lines before scanning, but `_CLASS_USAGE_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]+)\b')` still over-removes code blocks with single-word capitalized identifiers like `Author`, `Developer`, `Title`, `Installation`, `STL`, `ASCII`, `Export`, `Load` — these appear in actual code as variable names, string constants, or assignment LHS. HG-18 changes `_CLASS_USAGE_RE` to require CamelCase (at least two camel-case words: `[A-Z][a-z]+` followed by at least one `[A-Z][a-z0-9]*`). This correctly targets hallucinated Aspose class names (`StlFormat`, `StlSaveOptions`, `ObjLoadOptions`) while ignoring single-word capitals.

## Required spec references

- `phase_store/pilot_quality_report.md` — HG-17 pilot logs still showing `Author`, `Developer`, `Title`, `Installation`, `STL_ASCII` as false positives

## Scope

### In scope

- Change `_CLASS_USAGE_RE` from `r'\b([A-Z][A-Za-z0-9_]+)\b'` to `r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b'`
- Update affected unit tests whose test data uses single-word capitalized test identifiers

### Out of scope

- Changing the comment-stripping logic (HG-17, already in place)
- Changing the `_PYTHON_BUILTINS` set
- Changing wiring in worker.py

## Inputs

- `src/launcher/workers/generate/section_validator.py` — `_CLASS_USAGE_RE` definition
- HG-17 pilot log evidence showing remaining false positives

## Outputs

- Updated `section_validator.py` — CamelCase-only `_CLASS_USAGE_RE`
- Updated/new tests in `test_section_validator.py`

## Allowed paths

- plans/taskcards/TC-4026_hg18-camelcase-class-detection.md
- src/launcher/workers/generate/section_validator.py
- tests/unit/workers/generate/test_section_validator.py

## Implementation steps

### Step 1: Update `_CLASS_USAGE_RE` in `section_validator.py`

Change:
```python
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][A-Za-z0-9_]+)\b')
```
To:
```python
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b')
```

Pattern explanation:
- `[A-Z]` — first letter is uppercase
- `[a-z]+` — followed by one or more lowercase letters (first camel-word, e.g., "Stl", "Obj", "File")
- `(?:[A-Z][a-z0-9]*)+` — one or more additional camel-words starting with uppercase (e.g., "Format", "SaveOptions")

This matches: `StlFormat`, `StlSaveOptions`, `ObjLoadOptions`, `AnimationClip`, `FileFormat`, `KeyFrame`, `AssetInfo`, `PropertyCollection`
Does NOT match: `Scene`, `Node`, `Title`, `Author`, `Developer`, `STL`, `STL_ASCII`, `ASCII`, `Export`, `Load`, `Installation`, `My`

### Step 2: Update/add unit tests

The existing `test_hallucinated_class_code_block_removed` uses `ObjLoadOptions` — still valid (CamelCase).
The existing `test_valid_class_code_block_kept` uses `Scene` — still valid (in public_classes).
Add tests for the now-allowed single-word identifiers:

```python
def test_single_word_capitalized_variable_preserved(self):
    """HG-18: Block with single-word capitalized variable (not CamelCase) must be preserved."""
    from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
    public_classes = {"Scene"}
    # 'Author' and 'Title' are single-word capitalized — not CamelCase class names
    code = "Author = 'Aspose'\nTitle = 'Getting Started'\nscene = Scene()"
    blocks = [self._make_code_block(code)]
    result = _strip_hallucinated_code_blocks(blocks, public_classes)
    assert len(result) == 1, "Single-word capitalized variables must not trigger removal"

def test_all_caps_constant_preserved(self):
    """HG-18: All-caps constants (STL, ASCII, STL_ASCII) must not trigger removal."""
    from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
    public_classes = {"Scene"}
    code = "STL_FORMAT = 'stl'\nASCII_MODE = True\nscene = Scene()"
    blocks = [self._make_code_block(code)]
    result = _strip_hallucinated_code_blocks(blocks, public_classes)
    assert len(result) == 1, "All-caps constants must not trigger removal"
```

## Failure modes

### Failure mode 1: Multi-word hallucinated class NOT matched by CamelCase requirement

**Detection**: A test shows `StlFormat` not being flagged after change.
**Assessment**: `StlFormat` = `Stl` (uppercase + lowercase) + `Format` (uppercase + lowercase) → IS CamelCase → IS matched. Cannot happen.
**Gate**: `test_hallucinated_class_code_block_removed` uses `ObjLoadOptions` which is CamelCase → still passes.

### Failure mode 2: Single-word class names (like `Scene`, `Node`, `Mesh`) falsely needed

**Detection**: Known API class names like `Scene` are single-word, and the new pattern doesn't match them.
**Assessment**: Single-word classes like `Scene`, `Node`, `Mesh` are in `public_classes`. The repair skips them because they're in `public_classes`. The pattern only matters for UNRECOGNIZED names. Single-word unrecognized capitalized identifiers are too likely to be false positives (English words, variables).
**Gate**: `test_valid_class_code_block_kept` uses `Scene` which IS in public_classes → still passes.

### Failure mode 3: New CamelCase pattern excludes needed true positives

**Detection**: New pattern misses a hallucinated class because it's not multi-camel-case.
**Risk**: If LLM hallucinates `Loader` (single-word) instead of `ObjLoader` or similar. These would now pass through undetected.
**Assessment**: Acceptable. Single-word class hallucinations are rare and hard to distinguish from valid code. The key hallucinations we're targeting (`ObjLoadOptions`, `StlFormat`, `StlSaveOptions`) are all CamelCase.
**Gate**: Pilot shows factual_accuracy findings decrease, not increase.

## Task-specific review checklist

1. [ ] `_CLASS_USAGE_RE` changed to CamelCase pattern `r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b'`
2. [ ] `StlFormat`, `StlSaveOptions`, `ObjLoadOptions` still match new pattern (verified in tests)
3. [ ] `Author`, `Title`, `Developer`, `STL`, `ASCII`, `Installation` do NOT match
4. [ ] 2 new unit tests pass for single-word and all-caps false positives
5. [ ] All 10 existing TestHG16 tests still pass
6. [ ] Full test suite passes with no new failures

## Deliverables

1. Updated `src/launcher/workers/generate/section_validator.py` — CamelCase `_CLASS_USAGE_RE`
2. 2 new tests in `tests/unit/workers/generate/test_section_validator.py`

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py::TestHG16HallucinatedCodeBlockRepair -v` — 10/10 tests PASS
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures
- [x] `section_validator.py` has `_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b')`
- [x] Pilot log shows no `Author`, `Title`, `Developer`, `Installation`, `STL`, `ASCII` as hallucinated

## Self-review

### Verification results
- [x] `_CLASS_USAGE_RE` changed to CamelCase pattern
- [x] Pre-test: pattern matches `StlFormat`, `ObjLoadOptions`, `AnimationClip` (True) and NOT `Scene`, `Title`, `Author`, `STL` (False)
- [x] 10/10 tests pass
- [x] Full suite: 3579 passed, 6 pre-existing failures only

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py::TestHG16HallucinatedCodeBlockRepair -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `section_validator.py` — CamelCase `_CLASS_USAGE_RE`
- `test_section_validator.py` — 2 new HG-18 tests (total 10 in TestHG16HallucinatedCodeBlockRepair)
- Full suite: 3579 passed (2 new), 6 pre-existing failures only

## Integration boundary proven

**Upstream**: `_strip_hallucinated_code_blocks()` receives Python code blocks from parse_and_validate_blocks()
**Fix**: `_CLASS_USAGE_RE` now only matches multi-word CamelCase identifiers → single-word variables (`Author`, `Title`) and all-caps constants (`STL`, `ASCII`) pass through unchanged
**Downstream**: Only true hallucinated Aspose-style class names are removed; valid variable names preserved
