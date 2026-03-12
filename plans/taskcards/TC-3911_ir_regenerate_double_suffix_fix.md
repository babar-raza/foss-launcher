---
id: TC-3911
title: "ir_regenerate double-suffix fix + redundant mkdir cleanup + tests"
status: Done
priority: High
owner: "claude-agent"
updated: "2026-03-10"
tags: [bugfix, deploy, ir, regeneration]
depends_on: [TC-3906]
allowed_paths:
  - plans/taskcards/TC-3911_ir_regenerate_double_suffix_fix.md
  - src/launcher/shared/ir_regenerate.py
  - tests/shared/test_ir_regenerate.py
evidence_required:
  - reports/TC-3911/evidence.md
---

# Taskcard TC-3911 — ir_regenerate double-suffix fix + redundant mkdir cleanup + tests

## Objective

Fix a TC-3906 original bug where `rel.with_suffix(".md")` produces `slug.ir.md` instead of
`slug.md` for `slug.ir.json` inputs. Also remove a redundant `dest.parent.mkdir` call (already
handled by `atomic_write_text`), and add missing unit tests.

## Required spec references

- `src/launcher/shared/ir_regenerate.py` module docstring: path invariant
  `snapshots_dir / (content_path + ".ir.json") → output_dir / (content_path + ".md")`

## Scope

### In scope
- One-line path fix: `rel.with_suffix("").with_suffix(".md")`
- Remove redundant `dest.parent.mkdir(parents=True, exist_ok=True)` (already in `atomic_write_text`)
- Unit tests covering path transformation, nested paths, and non-IR file exclusion

### Out of scope
- `phase_promoter.py`, `promoter.py`, `deploy.py` — use string concat, not `with_suffix`; unaffected
- `atomic_write_text` internals — not changing

## Inputs

- `snapshots/` directory containing `*.ir.json` files (e.g. `guide.ir.json`, `sub/page.ir.json`)

## Outputs

- `output_dir/guide.md` (not `guide.ir.md`)
- `output_dir/sub/page.md` (nested paths preserved)
- `tests/shared/test_ir_regenerate.py` (new test file)

## Allowed paths

- plans/taskcards/TC-3911_ir_regenerate_double_suffix_fix.md
- src/launcher/shared/ir_regenerate.py
- tests/shared/test_ir_regenerate.py

### Allowed paths rationale
- `ir_regenerate.py`: contains both the bug fix and the redundant mkdir to remove
- `test_ir_regenerate.py`: new test coverage for the module (currently has zero tests)

## Implementation steps

### Step 1: Apply double-suffix fix (already done by linter)

`src/launcher/shared/ir_regenerate.py` line 65/67:
```python
# Before (bug):
dest = output_dir / rel.with_suffix(".md")

# After (fix):
dest = output_dir / rel.with_suffix("").with_suffix(".md")
```
`Path("guide.ir.json").with_suffix("").with_suffix(".md")` → `guide.md` ✓

### Step 2: Remove redundant mkdir (already done by linter)

`atomic_write_text` (atomic.py line 56) already calls `path.parent.mkdir(parents=True, exist_ok=True)`.
The explicit call in `ir_regenerate.py` before `atomic_write_text` is a no-op — remove it.

### Step 3: Add unit tests

Create `tests/shared/test_ir_regenerate.py` with tests covering:
1. Flat file: `slug.ir.json` → `slug.md` (not `slug.ir.md`)
2. Nested file: `sub/dir/page.ir.json` → `sub/dir/page.md`
3. `snapshot_manifest.json` is NOT processed (rglob pattern excludes plain `.json`)
4. Missing snapshots_dir returns `[]` without error
5. Bad IR JSON logs error and skips (returns `[]`)

## Failure modes

### Failure mode 1: with_suffix produces wrong extension

**Detection**: Test `test_path_flat` fails — output is `slug.ir.md` not `slug.md`
**Resolution**: Ensure both `.with_suffix("")` and `.with_suffix(".md")` are chained
**Gate**: Path invariant in module docstring

### Failure mode 2: snapshot_manifest.json processed as IR

**Detection**: `model_validate` raises on non-IR JSON; logged and skipped
**Resolution**: `rglob("*.ir.json")` naturally excludes plain `.json` files — verified
**Gate**: `_NON_IR_NAMES` guard was redundant; confirmed by testing

### Failure mode 3: nested dirs not created

**Detection**: `FileNotFoundError` inside `atomic_write_text.tmp.write_text`
**Resolution**: `atomic_write_text` line 56 calls `path.parent.mkdir(parents=True, exist_ok=True)` — confirmed
**Gate**: `test_path_nested` verifies nested output written successfully

## Task-specific review checklist

1. [x] `rel.with_suffix("").with_suffix(".md")` produces `slug.md` for `slug.ir.json` input
2. [x] Redundant `dest.parent.mkdir` removed — `atomic_write_text` already handles it
3. [x] `rglob("*.ir.json")` confirmed to exclude `snapshot_manifest.json` (plain `.json`)
4. [x] Path invariant (module docstring lines 6-8) matches actual behavior
5. [x] Tests pass: `test_path_flat`, `test_path_nested`, `test_non_ir_excluded`, `test_missing_dir`, `test_bad_json_skipped`
6. [x] No regression in existing test suite
7. [x] Docstrings updated (Path transform comment added at line 44)
8. [x] Spec: no spec drift — path invariant is internal to module
9. [x] Schema: no schema changes
10. [x] `docs/README.md` ownership map: no trigger event for this bugfix
11. [x] No new `docs/guides/` files added

## Deliverables

1. `src/launcher/shared/ir_regenerate.py` — fix applied, redundant mkdir removed
2. `tests/shared/test_ir_regenerate.py` — unit tests
3. `reports/TC-3911/evidence.md` — test output + verification

## Acceptance checks

1. [x] `test_path_flat`: `slug.ir.json` → `slug.md` exists, `slug.ir.md` does NOT exist
2. [x] `test_path_nested`: `sub/page.ir.json` → `sub/page.md` exists
3. [x] `test_non_ir_excluded`: `snapshot_manifest.json` produces no output file
4. [x] `test_missing_dir`: returns `[]` without raising
5. [x] 6/6 tests pass (`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_ir_regenerate.py`)

## Self-review

### Verification results
- [x] Tests: 6/6 PASS
- [x] Evidence captured: reports/TC-3911/evidence.md
- [x] Doc freshness: clean

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/shared/test_ir_regenerate.py -v
```

**Expected results**:
- All 5 tests pass
- No `*.ir.md` files produced in any test

## Integration boundary proven

**Upstream**: `phase_promoter.py` writes `snapshots/{content_path}.ir.json`
**Downstream**: `cli/deploy.py snapshot-regen` calls `regenerate_from_snapshots()` → writes `{content_path}.md`
**Contract**: `content_path + ".ir.json"` ↔ `content_path + ".md"` (path invariant in module docstring)
