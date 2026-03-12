---
id: TC-A03
title: "Write intake acquisition artifact"
status: In-Progress
priority: Normal
owner: "agent-b1"
updated: "2026-03-11"
tags: [intake, artifact, acquisition]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-A03_intake-artifact.md
  - src/launcher/workers/intake/worker.py
  - reports/TC-A03/evidence.md
evidence_required:
  - reports/TC-A03/evidence.md
---

# Taskcard TC-A03 — Write intake acquisition artifact

## Objective

After the IntakeBundle is constructed, write a human-inspectable `intake_bundle.json` artifact via `context.store.write_json()` so that operators can review acquisition details (repo_url, SHA, tier, identity) without inspecting internal state.

## Required spec references

- `specs/worker_understand.md` (Section: artifact contracts)
- `specs/system_contract.md` (Section: worker I/O)

## Scope

### In scope
- Add `context.store.write_json("intake_bundle.json", ...)` call in `IntakeWorker.run()`
- Log success/failure of artifact write
- Include `is_fresh_clone` and `clone_cache_hit` fields in artifact

### Out of scope
- Changes to IntakeBundle model
- Changes to ArtifactStore implementation
- Schema validation of intake_bundle.json

## Inputs

- `IntakeBundle` produced by `IntakeWorker.run()`
- `context.store` (`ArtifactStore` instance)

## Outputs

- `runs/{run_id}/intake_bundle.json` artifact written by `context.store.write_json()`
- Log line confirming artifact written

## Allowed paths

- plans/taskcards/TC-A03_intake-artifact.md
- src/launcher/workers/intake/worker.py
- reports/TC-A03/evidence.md

### Allowed paths rationale

`worker.py` — where the artifact write is inserted. `evidence.md` — captures test results as proof.

## Implementation steps

### Step 1: Add artifact write to IntakeWorker.run()

Insert after the `bundle = IntakeBundle(...)` block and before the `if repo_sha:` event-emit block:

```python
try:
    _artifact = {
        "family": bundle.family,
        "platform": bundle.platform,
        "repo_url": bundle.repo_url,
        "display_name": bundle.display_name,
        "canonical_import": bundle.canonical_import,
        "runtime_import": bundle.runtime_import,
        "launch_tier": bundle.launch_tier,
        "repo_sha": bundle.repo_sha,
        "repo_dir": bundle.repo_dir,
        "discovered_at": bundle.discovered_at,
        "is_fresh_clone": is_fresh_clone,
        "clone_cache_hit": not is_fresh_clone and bool(bundle.repo_sha),
    }
    context.store.write_json("intake_bundle.json", _artifact)
    logger.info("[Intake] Acquisition artifact written to intake_bundle.json")
except Exception:
    logger.warning("[Intake] Failed to write acquisition artifact", exc_info=True)
```

### Step 2: Run tests

`PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v`

### Step 3: Capture evidence

Write test results to `reports/TC-A03/evidence.md`.

## Failure modes

### Failure mode 1: ArtifactStore write fails

**Detection**: `logger.warning("[Intake] Failed to write acquisition artifact")` appears in logs.
**Resolution**: The exception is caught and logged; pipeline continues. Investigate store path permissions.
**Gate**: Intake self_review still passes since artifact write failure is non-blocking.

### Failure mode 2: intake_bundle.json missing required fields

**Detection**: JSON file is incomplete when inspected manually.
**Resolution**: Verify all bundle fields are serialized in `_artifact` dict.
**Gate**: Spot-check `runs/{run_id}/intake_bundle.json` after a run.

### Failure mode 3: context.store not available

**Detection**: AttributeError on `context.store` in tests.
**Resolution**: Ensure WorkerContext mock provides a `store` attribute with `write_json`.
**Gate**: Unit test for artifact write must pass.

## Task-specific review checklist

1. [x] `context.store.write_json("intake_bundle.json", _artifact)` called after bundle construction
2. [x] Exception caught with `logger.warning` — artifact failure is non-blocking
3. [x] `is_fresh_clone` included in artifact
4. [x] `clone_cache_hit` computed correctly (`not is_fresh_clone and bool(repo_sha)`)
5. [x] Log line emitted on success
6. [x] No existing code removed — only addition
7. [x] Docstrings updated for all new/changed public functions
8. [x] Spec file confirmed — no new spec drift introduced
9. [x] Schema `"description"` fields not applicable (internal artifact dict, not schema-bound)
10. [x] `docs/README.md` ownership map checked — no trigger event for this change
11. [x] No new `docs/guides/` file added

## Deliverables

1. Modified `src/launcher/workers/intake/worker.py` with artifact write
2. `reports/TC-A03/evidence.md` with test results

## Acceptance checks

1. [ ] `tests/unit/workers/test_intake.py` all pass with PYTHONHASHSEED=0
2. [ ] Artifact write code exists in `worker.py` after bundle construction
3. [ ] Exception handling wraps the write call

## Self-review

### Verification results
- [ ] Tests: pass/total PASS
- [ ] Validation: intake tests PASS
- [ ] Evidence captured: reports/TC-A03/evidence.md
- [ ] Doc freshness: acknowledged — no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
```

**Expected results**:
- All tests pass
- No regressions introduced

## Integration boundary proven

**Upstream**: `IntakeBundle` constructed from `RunConfig` + clone result
**Downstream**: `runs/{run_id}/intake_bundle.json` consumed by operators/debuggers
**Contract**: JSON dict with all IntakeBundle fields plus `is_fresh_clone` and `clone_cache_hit`
