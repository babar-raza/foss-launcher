---
id: TC-3784
title: "Fix false permalink collision detection and artifact overwrite"
status: Done
priority: High
owner: agent
updated: "2026-03-07"
tags: [evaluate, collision, hugo]
depends_on: [TC-3778]
allowed_paths:
  - plans/taskcards/TC-3784_false_permalink_collision.md
  - src/launcher/models/evaluation.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - reports/TC-3784/evidence.md
---

# Taskcard TC-3784 — Fix false permalink collision detection and artifact overwrite

## Objective

Fix the Evaluate worker's permalink collision check which falsely flags pages with the same `slug` but different `content_path` values (e.g., `_index.md` at multiple Hugo directory levels). Also fix the artifact filename derivation which causes overwrites when multiple pages share a slug.

## Required spec references

- `specs/content_manifest.md` (Section: GeneratedPage schema — defines content_path)
- `specs/evaluate_worker.md` (Section: permalink collision detection)

## Scope

### In scope
- Add `content_path: str = ""` to `PageEvaluation` model
- Populate `content_path` from `GeneratedPage` when constructing `PageEvaluation`
- Fix collision detection to group by `content_path` (not bare `slug`)
- Fix artifact filename to use `content_path` for uniqueness
- Update existing collision tests; add same-slug-different-path test

### Out of scope
- Changes to Planner, Generate, or Publish workers
- Changes to `GeneratedPage` model or `RunLayout`
- Fixing genuine quality issues (semantic_structure, code checks, etc.)

## Inputs

- `ContentManifest` with `GeneratedPage` entries containing `content_path` and `slug`
- Existing pilot run at `runs/pilot_cells_20260306T195001/`

## Outputs

- Updated `PageEvaluation` model with `content_path` field
- Corrected collision detection logic
- Unique per-page evaluation artifacts (no overwrites)
- Updated test suite

## Allowed paths

- plans/taskcards/TC-3784_false_permalink_collision.md
- src/launcher/models/evaluation.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale
- evaluation.py: Add `content_path` field to `PageEvaluation`
- worker.py: Fix collision detection grouping key and artifact filename derivation
- test_evaluate.py: Update collision tests for new behavior

## Implementation steps

### Step 1: Add `content_path` to `PageEvaluation`

In `src/launcher/models/evaluation.py`, add `content_path: str = ""` after `slug` in the `PageEvaluation` class.

### Step 2: Populate `content_path` in worker

In `src/launcher/workers/evaluate/worker.py`, pass `content_path=gen_page.content_path` when constructing `PageEvaluation` in both the main loop and the missing-file branch.

### Step 3: Fix collision detection

Change grouping key from `pe.slug` to `pe.content_path or pe.slug`. Pages at different content paths are NOT collisions even if they share a slug.

### Step 4: Fix artifact filenames

In `_write_page_artifact`, use `page_eval.content_path or page_eval.slug` as the key for `_safe_slug()` to produce unique filenames.

### Step 5: Update tests

- Fix `test_slug_collision_detected` to use same `content_path` for real collisions
- Add `test_same_slug_different_content_path_no_collision`
- Update `test_collision_artifact_has_correct_grade` for new collision key
- Verify `content_path` round-trips through serialization

## Failure modes

### Failure mode 1: Backward-compatible deserialization

**Detection**: Existing serialized `PageEvaluation` JSON (without `content_path`) fails `model_validate`
**Resolution**: Field defaults to `""` so old data deserializes fine — verify with unit test
**Gate**: Schema validation at boundary

### Failure mode 2: Empty content_path fallback

**Detection**: Pages with `content_path=""` bypass collision detection entirely
**Resolution**: Fallback `pe.content_path or pe.slug` ensures slug-based grouping when content_path is absent
**Gate**: Collision check correctness

### Failure mode 3: Artifact filename uniqueness

**Detection**: Two pages with different content_paths but same _safe_slug output
**Resolution**: `_safe_slug` replaces `/` and `.` with `_`, producing distinct filenames for different paths
**Gate**: G-01 artifact correctness (verify_healing.py)

## Task-specific review checklist

1. [ ] `content_path` added to `PageEvaluation` with `""` default
2. [ ] `content_path` populated from `gen_page.content_path` in main loop
3. [ ] `content_path` populated from `gen_page.content_path` in missing-file branch
4. [ ] Collision detection groups by `content_path or slug`, not bare slug
5. [ ] `_write_page_artifact` uses `content_path or slug` for filename
6. [ ] Collision re-grading preserves `content_path` on rebuilt `PageEvaluation`
7. [ ] Test: same slug + different content_path → no collision
8. [ ] Test: same content_path → collision detected
9. [ ] All evaluate tests pass

## Deliverables

1. Modified `src/launcher/models/evaluation.py`
2. Modified `src/launcher/workers/evaluate/worker.py`
3. Modified `tests/unit/workers/test_evaluate.py`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — full suite passes
3. [ ] No false permalink collision for `_index` pages with different `content_path`
4. [ ] Distinct artifact files for each `_index` page

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: evaluate worker PASS
- [ ] Evidence captured: reports/TC-3784/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All evaluate tests pass including new same-slug-different-path test
- Full suite passes with no regressions
- 4 `_index` pages at different content_paths produce 4 distinct artifacts

## Integration boundary proven

**Upstream**: Generate worker produces `ContentManifest` with `content_path` on each `GeneratedPage`
**Downstream**: Evaluation artifacts consumed by `verify_healing.py` and pipeline reporting
**Contract**: `PageEvaluation.content_path` mirrors `GeneratedPage.content_path` — optional field, defaults to `""`
