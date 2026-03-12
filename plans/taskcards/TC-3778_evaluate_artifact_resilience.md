---
id: TC-3778
title: "Evaluate worker artifact resilience — per-page + summary disk writes"
status: Done
priority: Normal
owner: "claude-agent"
updated: "2026-03-07"
tags: [evaluate, artifacts, resilience]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3778_evaluate_artifact_resilience.md
  - src/launcher/io/run_layout.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/test_evaluate.py
evidence_required:
  - reports/TC-3778/evidence.md
---

# Taskcard TC-3778 — Evaluate worker artifact resilience

## Objective

Make the Evaluate worker write per-page evaluation JSONs and a summary report directly to disk during execution, mirroring how Generate writes per-page `.ir.json` files. This adds crash resilience (partial results survive) and debuggability (inspect individual page evaluations).

## Required spec references

- `specs/evaluation.md` (Section: evaluation pipeline, artifact outputs)
- `specs/io_and_artifacts.md` (Section: artifact store, run layout)

## Scope

### In scope
- Add `evaluation_dir` property to `RunLayout`
- Write per-page `{slug}.eval.json` files inside the evaluate worker loop
- Write `evaluation_summary.json` at end of worker (before returning)
- Update tests to verify artifacts on disk

### Out of scope
- Changing the orchestrator checkpoint mechanism (stays as-is)
- Adding new models or schemas (existing `PageEvaluation` and `EvaluationReport` serialize fine)
- LLM review raw response capture (separate taskcard)

## Inputs

- `ContentManifest` from Generate worker (existing)
- Generated `.md` files on disk (existing)

## Outputs

- `evaluation/pages/{slug}.eval.json` — per-page evaluation artifact
- `evaluation/evaluation_summary.json` — full evaluation report

## Allowed paths

- plans/taskcards/TC-3778_evaluate_artifact_resilience.md
- src/launcher/io/run_layout.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/test_evaluate.py

### Allowed paths rationale
- run_layout.py: Add `evaluation_dir` property
- worker.py: Add artifact write calls
- test_evaluate.py: Verify artifacts written to disk

## Implementation steps

### Step 1: Add evaluation_dir to RunLayout

Add a `evaluation_dir` property to `RunLayout` returning `run_dir / "evaluation"`.

### Step 2: Write per-page eval artifacts in worker loop

After each `PageEvaluation` is created (line ~108), write it to `evaluation/pages/{slug}.eval.json` via `context.store.write_json()`. Create the directory once before the loop.

### Step 3: Write summary report before returning

After `final_report` is assembled, write it to `evaluation/evaluation_summary.json`.

### Step 4: Add defensive slug sanitization

Sanitize slugs used in file paths to prevent path traversal (replace `/`, `\`, `..` with `_`).

### Step 5: Update tests

Add test assertions verifying per-page and summary artifacts exist on disk after worker runs.

## Failure modes

### Failure mode 1: Slug contains path-traversal characters

**Detection**: Slug like `../../etc/passwd` used as filename
**Resolution**: Sanitize slug before constructing file path — replace non-`[a-zA-Z0-9_-]` with `_`
**Gate**: SEO check already validates slugs, but defense-in-depth at write time

### Failure mode 2: Disk write failure mid-evaluation

**Detection**: `write_json` raises `OSError` or `PermissionError`
**Resolution**: Log warning and continue evaluation (artifact writes are non-blocking)
**Gate**: Worker still returns `EvaluationReport` in memory; orchestrator checkpoint still works

### Failure mode 3: ArtifactStore not available on WorkerContext

**Detection**: `context.store` is None or missing
**Resolution**: Guard artifact writes with `hasattr(context, 'store') and context.store`
**Gate**: Worker degrades gracefully to pre-change behavior

## Task-specific review checklist

1. [ ] `evaluation_dir` property added to `RunLayout`
2. [ ] Per-page `.eval.json` written for each page in the loop
3. [ ] `evaluation_summary.json` written before `return`
4. [ ] Slug sanitization prevents path traversal
5. [ ] Artifact write failures are caught and logged (non-fatal)
6. [ ] Tests verify artifacts on disk
7. [ ] No regression in existing test suite

## Deliverables

1. Modified `src/launcher/io/run_layout.py` with `evaluation_dir`
2. Modified `src/launcher/workers/evaluate/worker.py` with artifact writes
3. Updated `tests/unit/workers/test_evaluate.py` with artifact verification
4. Evidence at `reports/TC-3778/evidence.md`

## Acceptance checks

1. [ ] `.venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` all pass
2. [ ] Full test suite passes with PYTHONHASHSEED=0
3. [ ] Per-page `.eval.json` files created during test runs
4. [ ] `evaluation_summary.json` created during test runs
5. [ ] No new imports or dependencies added

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3778/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v
```

**Expected results**:
- All existing tests pass
- New artifact verification tests pass
- Per-page JSON files contain slug, grade, findings, check_results

## Integration boundary proven

**Upstream**: Generate worker produces `ContentManifest` + `.md` files
**Downstream**: Orchestrator reads `EvaluationReport` (unchanged); artifacts are for debugging/resilience
**Contract**: `PageEvaluation.model_dump(mode="json")` for per-page; `EvaluationReport.model_dump(mode="json")` for summary
