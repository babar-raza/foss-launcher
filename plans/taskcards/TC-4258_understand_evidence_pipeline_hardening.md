---
id: TC-4258
title: "Understand evidence pipeline hardening: claim quality, snippet purity, accessor normalization"
status: In-Progress
priority: Critical
owner: "Codex"
updated: "2026-03-12"
tags: [understand, evidence, snippets, claims, self-review]
depends_on: [TC-4257, TC-4255, TC-4256]
allowed_paths:
  - plans/taskcards/TC-4258_understand_evidence_pipeline_hardening.md
  - src/launcher/shared/code_analyzer.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/extract/_snippets.py
  - src/launcher/workers/understand/extract/_validation.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/understand/test_extract.py
  - reports/agents/B_implementation/TC-4258/evidence.md
  - reports/agents/B_implementation/TC-4258/self_review.md
evidence_required:
  - reports/agents/B_implementation/TC-4258/evidence.md
---

# Taskcard TC-4258 - Understand evidence pipeline hardening

## Objective

Fix Understand at the evidence-pipeline root after Scout hardening. Remove polluted snippet sources, stop property accessors from surfacing as callable methods, bound docstring-claim flooding, make page evidence sufficiency role-aware, and strengthen review artifacts plus self-review so polluted or orphan-heavy outputs fail before downstream generation.

## Required spec references

- `CLAUDE.md` (AG-002, AG-016, AG-020)
- `agents.md` (Understand checkpoint review workflow)
- `plans/twinkly-puzzling-minsky.md` (Rule 1 self-review, Rule 2 reviewable artifacts, Rule 6 root-cause fixes)
- `specs/worker_understand.md` (Phase B extraction, evidence validation, reviewability)
- `specs/product_model.md` (API surface and property/method normalization)

## Scope

### In scope
- Filter polluted snippet and claim sources so meta/operator documents do not reach Understand evidence.
- Stop property accessors from being duplicated as callable methods in Python API extraction.
- Bound docstring harvesting so verified claims stay high-signal instead of flooding page evidence with hundreds of micro-claims.
- Rework page evidence sufficiency to be role-aware and topic-aware rather than global-count-only.
- Strengthen Understand self-review and `extraction_audit.json` so polluted snippet sources, severe orphaned snippets, accessor confusion, and weak claim mixes are visible and can fail the phase.
- Preserve phase reviewability by keeping summary artifacts separate from full review artifacts.

### Out of scope
- Generate prompt fixes or Evaluate threshold tuning.
- Planner changes beyond what existing `page_evidence_index` already consumes.
- Non-evidence cosmetic cleanup.

## Inputs

- Fresh post-Scout runs from `2026-03-12`:
  - `runs/260312_154408_cells_python_3606`
  - `runs/260312_154408_3d_python_814e`
- Cells findings:
  - `929` claims, `913` from `docstring`
  - `7` snippets, all from `README.md`
  - `page_evidence_index` marks most roles sufficient despite zero operation snippets
- 3D findings:
  - `41` claims, `21` from `docstring`
  - `2` snippets, both from `README.md`, with `1` orphaned snippet
  - `A3DObject.name`, `AnimationChannel.default_value`, `AnimationClip.name` still appear in both method and property lists

## Outputs

- Understand outputs with cleaner snippet sources, normalized API surface, bounded claim mix, stronger page evidence scores, and richer audit artifacts.
- Regression tests proving the defect classes do not return.
- Manual verification evidence for the two pilot runs.

## Allowed paths

- `plans/taskcards/TC-4258_understand_evidence_pipeline_hardening.md`
- `src/launcher/shared/code_analyzer.py`
- `src/launcher/workers/understand/worker.py`
- `src/launcher/workers/understand/extract/_api_surface.py`
- `src/launcher/workers/understand/extract/_entry.py`
- `src/launcher/workers/understand/extract/_snippets.py`
- `src/launcher/workers/understand/extract/_validation.py`
- `tests/unit/workers/test_understand.py`
- `tests/unit/workers/understand/test_extract.py`
- `reports/agents/B_implementation/TC-4258/evidence.md`
- `reports/agents/B_implementation/TC-4258/self_review.md`

### Allowed paths rationale

- `code_analyzer.py`: root cause for Python property/method duplication.
- `_entry.py`, `_validation.py`, `_snippets.py`, `_api_surface.py`: claim harvesting, snippet filtering, API normalization, and evidence scoring live here.
- `worker.py`: review artifacts, self-review, and page-evidence summaries are emitted here.
- tests: regression coverage for semantics the user explicitly requested.

## Implementation steps

### Step 1: Normalize Python API surface

Fix property detection so accessor-like members remain properties and do not also populate callable method lists.

### Step 2: Filter polluted snippet sources

Ensure meta/operator documents and semantically weak README boilerplate do not dominate snippet extraction or survive into audit artifacts unnoticed.

### Step 3: Bound docstring-claim harvesting

Replace global-volume harvesting with high-signal selection so docstrings complement evidence instead of overwhelming it.

### Step 4: Rework page evidence sufficiency

Score sufficiency by role/topic needs, with meaningful requirements for operation snippets, format evidence, and verified claim diversity.

### Step 5: Strengthen review artifacts and self-review

Expose actual snippet source files, claim-source distribution, orphan counts, and accessor-confusion signals in `extraction_audit.json` and fail the phase on severe pollution.

### Step 6: Manual verification on both pilots

Run:

```powershell
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml --stop-after understand
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml --stop-after understand
```

Inspect `understand_checkpoint.json`, `understanding_bundle.json`, and `extraction_audit.json` for claim mix, snippet source purity, orphan rate, class briefs, and page evidence scores.

## Failure modes

### Failure mode 1: Claim cap removes genuinely useful evidence

Over-aggressive docstring pruning could starve thin repos.

Resolution: bound by per-class/per-role quotas and preserve high-confidence non-docstring evidence first.

### Failure mode 2: Accessor normalization strips legitimate methods

Some APIs expose both a property and a method intentionally.

Resolution: normalize using decorator or AST evidence rather than name-only deduplication.

### Failure mode 3: Snippet filtering over-prunes README examples

README may still contain the only valid public examples in thin repos.

Resolution: filter by source quality and linkage, not by README origin alone.

### Failure mode 4: New self-review blocks too many repos

Severity thresholds may overfit these pilots.

Resolution: fail only on strong structural signals such as polluted sources, orphan-heavy snippets, or accessor duplication, while keeping softer shortages as warnings.

## Task-specific review checklist

- [ ] Meta/operator docs no longer appear in snippet sources.
- [ ] Python properties do not appear as callable methods in class briefs.
- [ ] Cells no longer floods >900 mostly-docstring claims into page evidence.
- [ ] `page_evidence_index` differentiates roles using meaningful requirements, not just the same giant claim pool.
- [ ] `extraction_audit.json` lists snippet source files and claim-source distribution clearly.
- [ ] Polluted or orphan-heavy Understand outputs fail self-review.
- [ ] Regression tests fail without the fix.

## Deliverables

1. Updated Understand extraction and validation logic.
2. Updated Understand review artifacts and self-review.
3. Regression tests for polluted sources, accessor duplication, claim flooding bounds, and self-review failure conditions.
4. Evidence file at `reports/agents/B_implementation/TC-4258/evidence.md`.
5. Self-review file at `reports/agents/B_implementation/TC-4258/self_review.md`.

## Acceptance checks

1. [ ] Cells Understand run shows materially reduced docstring dominance.
2. [ ] 3D Understand run no longer emits accessor properties as callable methods.
3. [ ] `extraction_audit.json` exposes snippet source files, claim-source counts, and orphan counts.
4. [ ] Polluted snippet sources or severe orphan rates fail self-review.
5. [ ] Regression tests pass with `PYTHONHASHSEED=0`.

## Self-review

- Pending implementation.
- Must include manual artifact inspection for both pilots.

## E2E verification

- Baseline runs captured on `2026-03-12`:
  - `runs/260312_154408_cells_python_3606`
  - `runs/260312_154408_3d_python_814e`
- Post-change verification will compare those artifact families directly.

## Integration boundary proven

- Upstream: Scout now supplies clean `doc_paths` and `example_paths`; Understand must honor that evidence boundary.
- Downstream: Planner and Evaluate consume `claims`, `snippets`, `api_surface`, and `page_evidence_index`, so fixes must preserve model compatibility while improving semantics.
