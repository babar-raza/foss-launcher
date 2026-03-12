---
id: TC-4104
title: "phase_store: write scout.json + understanding_bundle.json for all phases"
status: Done
priority: High
owner: Agent-B
updated: "2026-03-11"
tags: [scout, understand, phase-store, observability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4104_phase_store_all_phases.md
  - src/launcher/workers/scout/worker.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/deploy/phase_promoter.py
  - tests/unit/deploy/
  - reports/agents/B/TC-4104/evidence.md
evidence_required:
  - reports/agents/B/TC-4104/evidence.md
---

# Taskcard TC-4104 — phase_store: write scout.json + understanding_bundle.json for all phases

## Objective

Currently only `plan.json`, `generate.json`, and `evaluate.json` are promoted to `phase_store/{family}/{platform}/`. The promoter already has an entry `"understand.json": layout.understanding_bundle` but Understand never writes `understanding_bundle.json` to the run dir, so it is silently skipped. Scout writes `scout_bundle.json` but the promoter does not include it. This taskcard fixes all three gaps: Scout writes a `scout.json` summary, Understand writes an `understanding_bundle.json` summary, and the promoter adds `scout.json` to `phase_sources`.

## Required spec references

- `specs/worker_understand.md` (Section: Worker output artifacts)
- `specs/state_events_checkpoints.md` (Section: Phase store promotion — what gets promoted)
- `specs/system_overview.md` (Section: phase_store layout — `{family}/{platform}/`)

## Scope

### In scope
- Scout `worker.py`: write `scout.json` (summary artifact) to run dir after existing `scout_bundle.json` write
- Understand `worker.py`: write `understanding_bundle.json` (metrics summary, NOT full bundle) to run dir
- Phase promoter `phase_promoter.py`: add `"scout.json"` entry to `phase_sources` dict
- One new deploy unit test in `tests/unit/deploy/`

### Out of scope
- Changing the full `UnderstandingBundle` serialization format
- Changing existing `phase_sources` entries for `plan.json`, `generate.json`, `evaluate.json`
- Adding new phase_store entries beyond `scout.json` and `understand.json`

## Inputs

- `src/launcher/workers/scout/worker.py` — existing `scout_bundle.json` write location
- `src/launcher/workers/understand/worker.py` — existing `extraction_audit.json` write location; available variables (`claims`, `snippets`, `extract_evidence`, `api_surface`, `product_evidence`, `richness`)
- `src/launcher/deploy/phase_promoter.py` — `_update_phase_store()` and `phase_sources` dict

## Outputs

- `scout.json` in run dir (identical content to `scout_bundle.json`)
- `understanding_bundle.json` in run dir (summary metrics dict)
- `phase_store/{family}/{platform}/scout.json` after promote
- `phase_store/{family}/{platform}/understand.json` after promote
- Deploy unit test verifying both files are copied
- `reports/agents/B/TC-4104/evidence.md`

## Allowed paths

- plans/taskcards/TC-4104_phase_store_all_phases.md
- src/launcher/workers/scout/worker.py
- src/launcher/workers/understand/worker.py
- src/launcher/deploy/phase_promoter.py
- tests/unit/deploy/
- reports/agents/B/TC-4104/evidence.md

### Allowed paths rationale

- `scout/worker.py` — where the `scout.json` write is added
- `understand/worker.py` — where the `understanding_bundle.json` summary write is added
- `phase_promoter.py` — where `scout.json` is added to `phase_sources`
- `tests/unit/deploy/` — new deploy unit test directory

## Implementation steps

### Step 1: Scout worker — write scout.json

Read `src/launcher/workers/scout/worker.py`. After the existing `context.store.write_json("scout_bundle.json", scout_artifact)` call (or equivalent), add:

```python
context.store.write_json("scout.json", scout_artifact)
```

The content is identical to `scout_bundle.json`. No new data structure needed.

### Step 2: Understand worker — write understanding_bundle.json summary

Read `src/launcher/workers/understand/worker.py`. After the existing `extraction_audit.json` write, add a summary write:

```python
understanding_summary = {
    "run_id": getattr(context, "run_id", "") or "",
    "family": product.family,
    "platform": product.platform,
    "claims": len(claims),
    "snippets": len(snippets),
    "limitations": len(extract_evidence.limitations),
    "install_recipe": (
        extract_evidence.install_recipe.install_command
        if extract_evidence.install_recipe else None
    ),
    "format_matrix_count": len(product_evidence.supported_formats),
    "class_briefs_count": len(api_surface.class_briefs),
    "typed_methods_classes": sum(
        1 for b in api_surface.class_briefs if b.typed_methods
    ),
    "richness_tier": richness.tier.value,
    "api_confidence": api_surface.confidence,
    "missing_info": (
        len(extract_evidence.missing_info)
        if hasattr(extract_evidence, "missing_info") else 0
    ),
}
context.store.write_json("understanding_bundle.json", understanding_summary)
```

### Step 3: Phase promoter — add scout.json to phase_sources

Read `src/launcher/deploy/phase_promoter.py`. In `_update_phase_store()`, locate the `phase_sources` dict. Add the `scout.json` entry:

```python
"scout.json": run_dir / "scout.json",
```

The existing `"understand.json": layout.understanding_bundle` entry already points to `run_dir / "understanding_bundle.json"` (via `layout.understanding_bundle`) — confirm this is correct and no further change is needed for the understand entry. If `layout.understanding_bundle` is not defined, add it as `run_dir / "understanding_bundle.json"`.

### Step 4: Create deploy unit test

Create `tests/unit/deploy/__init__.py` (empty) and `tests/unit/deploy/test_phase_promoter.py`:
- Create a `tmp_path` run dir with `scout.json` and `understanding_bundle.json` present
- Create a `tmp_path` phase_store dir
- Call `_update_phase_store()` with the test paths
- Assert `phase_store/3d/python/scout.json` exists
- Assert `phase_store/3d/python/understand.json` exists (copied from `understanding_bundle.json`)
- Assert existing entries (`plan.json`, `generate.json`, `evaluate.json`) are unaffected

## Failure modes

### Failure mode 1: context.run_id is None or missing

**Detection**: `understanding_summary["run_id"]` would be `None` or raise `AttributeError`.
**Resolution**: Use `getattr(context, "run_id", "") or ""` — safe for missing or None values.
**Gate**: `specs/worker_understand.md` — summary must serialize without error.

### Failure mode 2: extract_evidence.install_recipe is None

**Detection**: `extract_evidence.install_recipe.install_command` raises `AttributeError`.
**Resolution**: Use conditional: `extract_evidence.install_recipe.install_command if extract_evidence.install_recipe else None`.
**Gate**: `specs/worker_understand.md` — optional fields must handle None gracefully.

### Failure mode 3: Phase promoter silently skips missing files

**Detection**: `run_dir / "scout.json"` doesn't exist on old run dirs (runs before this TC was deployed) — the file is never copied, but no error is raised.
**Resolution**: The existing `if not src.exists(): continue` guard in the promoter handles this silently — old run dirs simply don't get `scout.json` promoted. No breakage for historical runs.
**Gate**: `specs/state_events_checkpoints.md` — phase store promotion is idempotent and non-failing.

### Failure mode 4: tests/unit/deploy/ directory doesn't exist

**Detection**: `ModuleNotFoundError` when importing test or `FileNotFoundError` when creating test file.
**Resolution**: Create `tests/unit/deploy/__init__.py` (empty) alongside the test file.
**Gate**: Test infrastructure — pytest discovers tests in directories with `__init__.py`.

## Task-specific review checklist

1. [ ] Scout worker writes `scout.json` with identical content to `scout_bundle.json`
2. [ ] Understand worker writes `understanding_bundle.json` with all 11 summary fields
3. [ ] `install_recipe` field handles None safely (conditional expression)
4. [ ] `run_id` field handles None/missing safely (`getattr(..., "") or ""`)
5. [ ] Phase promoter `phase_sources` has `"scout.json"` entry pointing to correct path
6. [ ] Existing `phase_sources` entries (`plan.json`, `generate.json`, `evaluate.json`) are unchanged
7. [ ] Deploy unit test verifies both `scout.json` and `understand.json` exist in phase_store after promote
8. [ ] `tests/unit/deploy/__init__.py` created
9. [ ] Spec file `specs/state_events_checkpoints.md` reviewed — no spec drift
10. [ ] Checked `docs/README.md` ownership map — no guide update required for artifact addition
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated (N/A)

## Deliverables

1. Updated `src/launcher/workers/scout/worker.py` — writes `scout.json`
2. Updated `src/launcher/workers/understand/worker.py` — writes `understanding_bundle.json`
3. Updated `src/launcher/deploy/phase_promoter.py` — `scout.json` in `phase_sources`
4. `tests/unit/deploy/__init__.py` and `tests/unit/deploy/test_phase_promoter.py`
5. `reports/agents/B/TC-4104/evidence.md`

## Acceptance checks

- [ ] Scout run produces `scout.json` in run dir (same content as `scout_bundle.json`)
- [ ] Understand run produces `understanding_bundle.json` in run dir with correct metrics
- [ ] After deploy, `phase_store/{family}/{platform}/scout.json` exists
- [ ] After deploy, `phase_store/{family}/{platform}/understand.json` exists (promoted from `understanding_bundle.json`)
- [ ] Deploy unit test passes: both files copied, existing entries unaffected
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v` — 0 failures
- [ ] Existing `plan.json`/`generate.json`/`evaluate.json` promotion unaffected

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: phase_store promotion PASS
- [ ] Evidence captured: `reports/agents/B/TC-4104/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/deploy/ -v
```

**Expected results**:
- New deploy unit test PASS: `scout.json` and `understand.json` exist in `phase_store/3d/python/` after promote
- Existing plan/generate/evaluate entries unaffected

## Integration boundary proven

**Upstream**: Scout worker produces `scout.json`; Understand worker produces `understanding_bundle.json` — both during normal pipeline runs
**Downstream**: Phase promoter copies both files to `phase_store/{family}/{platform}/` as `scout.json` and `understand.json` respectively
**Contract**: Promoter uses `if not src.exists(): continue` guard — backward compatible with old run dirs that lack these new artifacts
