---
id: TC-4028
title: "HG-20: Extend _CLASS_USAGE_RE to catch PascalCase+digit class names (Vector3, Matrix4)"
status: Done
priority: High
owner: "generate"
updated: "2026-03-11"
tags: [humming-greeting-kay, generate, hallucination, post-generation-repair, bugfix]
depends_on: [TC-4026]
ruleset_version: "1.0"
spec_ref: "d0f708ac"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4028_hg20-pascal-digit-class-detection.md
  - src/launcher/workers/generate/section_validator.py
  - tests/unit/workers/generate/test_section_validator.py
evidence_required:
  - phase_store/pilot_quality_report.md
---

# Taskcard TC-4028 — HG-20: PascalCase+Digit Class Detection

## Objective

The current `_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b')` (HG-18) requires
at least two CamelCase words, so it correctly matches `StlFormat`, `ObjLoadOptions`, `AnimationClip`
but does NOT match `Vector3`, `Vector2`, `Matrix4` — patterns where the second "word" is a trailing
digit. Pilot results show `factual_accuracy/high` findings for `Vector3`/`Vector2` (not in aspose-3d
API surface); the LLM hallucinates these from training data. HG-20 extends the regex with an
alternation for `PascalCase+digit` names: `[A-Z][a-z]+\d+`.

## Required spec references

- `phase_store/pilot_quality_report.md` — HG-19 pilot showing Vector3/Vector2 as remaining FA findings

## Scope

### In scope

- Extend `_CLASS_USAGE_RE` from `r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b'` to
  `r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b'`
- Add 2 unit tests: PascalCase+digit hallucinated class removed, single-word+digit constant preserved

### Out of scope

- Changing comment-stripping logic (HG-17)
- Changing `_PYTHON_BUILTINS` set
- Changing wiring in worker.py
- Method name canonicalization (separate task)

## Inputs

- `src/launcher/workers/generate/section_validator.py` — `_CLASS_USAGE_RE` at line ~693
- HG-19 pilot log showing `Vector3`, `Vector2` as hallucinated class false-negative findings

## Outputs

- Updated `section_validator.py` — extended `_CLASS_USAGE_RE`
- 2 new tests in `test_section_validator.py`

## Allowed paths

- plans/taskcards/TC-4028_hg20-pascal-digit-class-detection.md
- src/launcher/workers/generate/section_validator.py
- tests/unit/workers/generate/test_section_validator.py

### Allowed paths rationale

`section_validator.py` contains the regex being extended. `test_section_validator.py` contains
the HG-16 test class where new tests are added.

## Implementation steps

### Step 1: Extend `_CLASS_USAGE_RE` in `section_validator.py`

Change (line ~693):
```python
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+)\b')
```
To:
```python
_CLASS_USAGE_RE = re.compile(r'\b([A-Z][a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z]+\d+)\b')
```

Pattern explanation:
- First alternative `[A-Z][a-z]+(?:[A-Z][a-z0-9]*)+` — existing HG-18 CamelCase (StlFormat, ObjLoadOptions)
- Second alternative `[A-Z][a-z]+\d+` — PascalCase+digit (Vector3, Vector2, Matrix4, Quaternion4)

This matches: `StlFormat`, `ObjLoadOptions`, `Vector3`, `Vector2`, `Matrix4`, `Quaternion4`, `Buffer2`
Does NOT match: `Scene`, `Node`, `V3`, `STL3`, `abc3`, `Author`, `Title`, `ASCII`

### Step 2: Add unit tests in `test_section_validator.py`

Add to `TestHG16HallucinatedCodeBlockRepair`:

```python
# HG-20: PascalCase+digit detection tests

def test_pascal_digit_hallucinated_class_removed(self):
    """HG-20: PascalCase+digit class names (Vector3, Matrix4) not in public_classes are removed."""
    from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
    public_classes = {"Scene", "Node"}
    # Vector3 is NOT in public_classes — should be detected and block removed
    code = "scene = Scene()\npos = Vector3(1.0, 2.0, 3.0)"
    blocks = [self._make_code_block(code)]
    result = _strip_hallucinated_code_blocks(blocks, public_classes)
    assert len(result) == 0, "Vector3 not in public_classes must trigger block removal"

def test_pascal_digit_in_public_classes_preserved(self):
    """HG-20: PascalCase+digit class in public_classes must NOT trigger removal."""
    from launcher.workers.generate.section_validator import _strip_hallucinated_code_blocks
    public_classes = {"Scene", "Vector3"}
    # Vector3 IS in public_classes — block should be preserved
    code = "scene = Scene()\npos = Vector3(1.0, 2.0, 3.0)"
    blocks = [self._make_code_block(code)]
    result = _strip_hallucinated_code_blocks(blocks, public_classes)
    assert len(result) == 1, "Vector3 in public_classes must preserve block"
```

## Failure modes

### Failure mode 1: Single-digit false positive (e.g., `F3` or `V3`)

**Detection**: A test shows an identifier like `V3` triggering removal.
**Assessment**: `V3` = `[A-Z]` + `\d+` — pattern requires `[A-Z][a-z]+\d+`, so single uppercase + digits
is NOT matched. `V3` fails because there are no lowercase letters after the initial uppercase.
Cannot happen.
**Gate**: Pattern requires `[a-z]+` (one or more lowercase) between uppercase start and digit suffix.

### Failure mode 2: Valid API class with digit suffix

**Detection**: A real API class `Matrix4x4` is in `public_classes` and block is wrongly removed.
**Assessment**: `Matrix4x4` = `[A-Z][a-z]+\d+\w+` — this is matched by `[A-Z][a-z]+\d+` portion
(matches up to `Matrix4`). However since `Matrix4x4` IS in `public_classes`, it will be skipped
during the "not in public_classes" check. Only classes NOT in `public_classes` trigger removal.
**Gate**: `test_pascal_digit_in_public_classes_preserved` verifies this behavior.

### Failure mode 3: Existing HG-18 tests regress

**Detection**: Tests `test_single_word_capitalized_variable_preserved` or `test_all_caps_constant_preserved` fail.
**Assessment**: HG-20 adds an alternation but preserves the original pattern. Single-word
capitalized (e.g., `Author`, `Title`) still don't match `[A-Z][a-z]+(?:[A-Z][a-z0-9]*)+` (no
second camel-word) and also don't match `[A-Z][a-z]+\d+` (no trailing digit). All-caps (`STL`, `ASCII`)
start with `[A-Z]` but are followed by uppercase letters, not `[a-z]+`. Cannot regress.
**Gate**: All 10 existing HG-16/17/18 tests must still pass.

## Task-specific review checklist

1. [ ] `_CLASS_USAGE_RE` changed to include `|[A-Z][a-z]+\d+` alternation
2. [ ] `Vector3`, `Matrix4`, `Quaternion4` match new pattern (verified in tests)
3. [ ] `Author`, `Title`, `STL`, `ASCII`, `V3` do NOT match new pattern
4. [ ] `Vector3` in public_classes preserves the block (test_pascal_digit_in_public_classes_preserved)
5. [ ] 2 new unit tests pass
6. [ ] All 10 existing TestHG16 tests still pass
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Updated `src/launcher/workers/generate/section_validator.py` — extended `_CLASS_USAGE_RE`
2. 2 new tests in `tests/unit/workers/generate/test_section_validator.py`

## Acceptance checks

- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py::TestHG16HallucinatedCodeBlockRepair -v` — 12/12 tests PASS
- [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q` — no new failures (3583 passed)
- [x] `section_validator.py` has `_CLASS_USAGE_RE` with `[A-Z][a-z]+\d+` alternation

## Self-review

### Verification results
- [x] `_CLASS_USAGE_RE` extended with `|[A-Z][a-z]+\d+` alternation
- [x] Pre-test: pattern matches `Vector3`, `Matrix4` (True) and NOT `V3`, `Author`, `STL` (False)
- [x] 12/12 tests pass
- [x] Full suite: 3583 passed, 6 pre-existing failures only

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_validator.py::TestHG16HallucinatedCodeBlockRepair -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `section_validator.py` — extended `_CLASS_USAGE_RE` with PascalCase+digit alternation
- `test_section_validator.py` — 2 new HG-20 tests (total 12 in TestHG16HallucinatedCodeBlockRepair)
- Full suite: 3583 passed (2 new), 6 pre-existing failures only

## Integration boundary proven

**Upstream**: `parse_and_validate_blocks()` calls `_strip_hallucinated_code_blocks()`
**Fix**: `_CLASS_USAGE_RE` now also detects `Vector3`/`Matrix4`-style hallucinated API names
**Downstream**: Code blocks using hallucinated PascalCase+digit classes removed before output
