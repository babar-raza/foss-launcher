---
id: TC-3776
title: "Move git clone from Understand/Scout to Intake worker"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-07"
tags: [architecture, intake, understand, clone]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3776_move_clone_to_intake.md
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/models/intake.py
  - specs/schemas/intake_bundle.schema.json
  - specs/worker_understand.md
  - tests/unit/workers/test_intake.py
  - tests/unit/workers/test_clone.py
  - reports/agents/B/TC-3776/evidence.md
evidence_required:
  - reports/agents/B/TC-3776/evidence.md
---

# Taskcard TC-3776 — Move git clone from Understand/Scout to Intake worker

## Objective

Move the repository cloning logic (SHA-based cached shallow clone) from
`understand/scout.py` into the Intake worker so that Intake performs
acquisition (clone + SHA pinning) and Understand performs only analysis.
This fixes the conceptual boundary violation where Understand does both
I/O acquisition and analysis, and eliminates the awkward empty `repo_sha`
in IntakeBundle.

## Required spec references

- `specs/worker_understand.md` (Phase A: Scout — defines clone as part of Understand)
- `specs/schemas/intake_bundle.schema.json` (IntakeBundle output schema)

## Scope

### In scope
- Extract clone functions from `scout.py` into `intake/clone.py`
- Intake worker calls clone, populates `repo_sha` and `repo_dir` in IntakeBundle
- IntakeBundle model gains `repo_dir: str` field
- IntakeBundle JSON schema updated with `repo_dir`
- Scout refactored to accept `repo_dir` parameter instead of cloning
- Remove duplicated `_build_product_identity()` from scout (Intake already does this)
- Update Understand worker to pass `repo_dir` from IntakeBundle to scout
- Update all tests
- Update `specs/worker_understand.md` to reflect clone removal from Phase A

### Out of scope
- File fingerprinting, content reading, manifest parsing (stay in Scout)
- Claim extraction, snippet extraction (stay in Understand)
- Any changes to Generate, Evaluate, or Publish workers
- Pipeline config changes (pipeline.yaml topology unchanged)

## Inputs

- `RunConfig` (family, platform, repo_url, launch_tier)
- `configs/families.yaml` (identity resolution)
- Git remote repository at `repo_url`

## Outputs

- `IntakeBundle` with `repo_sha` and `repo_dir` populated
- Refactored `run_scout()` that accepts `repo_dir` instead of cloning
- Updated JSON schema
- Updated tests

## Allowed paths

- plans/taskcards/TC-3776_move_clone_to_intake.md
- src/launcher/workers/intake/worker.py
- src/launcher/workers/intake/clone.py
- src/launcher/workers/understand/scout.py
- src/launcher/workers/understand/worker.py
- src/launcher/models/intake.py
- specs/schemas/intake_bundle.schema.json
- specs/worker_understand.md
- tests/unit/workers/test_intake.py
- tests/unit/workers/test_clone.py
- reports/agents/B/TC-3776/evidence.md

### Allowed paths rationale
- intake/clone.py: new module for extracted clone logic
- intake/worker.py: add clone call, populate repo_sha/repo_dir
- scout.py: remove clone + _build_product_identity, accept repo_dir param
- understand/worker.py: read repo_dir from IntakeBundle, pass to scout
- intake.py model: add repo_dir field
- schema: add repo_dir property
- spec: update Phase A description
- tests: verify new boundaries

## Implementation steps

### Step 1: Create `src/launcher/workers/intake/clone.py`

Extract from `scout.py`:
- `_CLONE_SHA_MARKER`
- `_check_remote_sha()`
- `_get_cache_dir()`
- `_clone_repo_cached()`
- `_get_repo_sha()`

Make `clone_repo_cached()` public (drop leading underscore).

### Step 2: Update IntakeBundle model

In `src/launcher/models/intake.py`:
- Add `repo_dir: str = ""` field

### Step 3: Update IntakeBundle JSON schema

In `specs/schemas/intake_bundle.schema.json`:
- Add `repo_dir` property (type: string)
- Update `repo_sha` description (now pinned at intake, not by scout)

### Step 4: Update Intake worker

In `src/launcher/workers/intake/worker.py`:
- Import `clone_repo_cached` from `intake/clone.py`
- In `run()`: call clone, populate `repo_sha` and `repo_dir` in bundle
- Add clone failure to self_review checks
- Worker now needs `context.run_dir` to compute cache path

### Step 5: Refactor Scout

In `src/launcher/workers/understand/scout.py`:
- Remove `_clone_repo_cached`, `_check_remote_sha`, `_get_cache_dir`, `_get_repo_sha`, `_CLONE_SHA_MARKER`
- Remove `_build_product_identity` (duplicated with Intake)
- Change `run_scout()` signature: accept `repo_dir: Path` and `product: ProductIdentity` instead of `config: RunConfig`
- Remove `is_fresh_clone` from return tuple (Intake concern)
- Return: `(RepoInfo, dict[str, str])` — repo_info and repo_content

### Step 6: Update Understand worker

In `src/launcher/workers/understand/worker.py`:
- Read `repo_dir` and product identity from IntakeBundle input
- Pass them to `run_scout(repo_dir, product)` instead of `run_scout(config)`
- Set `context.repo_dir` and `context.repo_content` as before

### Step 7: Update tests

- `test_intake.py`: mock subprocess/clone, verify `repo_sha` and `repo_dir` populated
- New `test_clone.py`: unit tests for clone cache logic
- `test_scout_facts.py`: no change needed (tests `_extract_shared_facts` which stays)

### Step 8: Update spec

- `specs/worker_understand.md`: Phase A no longer mentions cloning

## Failure modes

### Failure mode 1: Clone fails at Intake time

**Detection**: `subprocess.CalledProcessError` from `git clone`
**Resolution**: Intake worker catches exception, returns error via self_review failure. Orchestrator stops pipeline early (fail-fast benefit).
**Gate**: Intake self-review

### Failure mode 2: repo_dir path stale after serialization

**Detection**: Understand worker receives IntakeBundle with `repo_dir` pointing to non-existent path
**Resolution**: Scout validates `repo_dir` exists before proceeding. If not, raises clear error.
**Gate**: Understand Phase A entry validation

### Failure mode 3: Schema validation rejects new field

**Detection**: `validate()` in graph_builder rejects IntakeBundle with unknown `repo_dir` field
**Resolution**: Update `intake_bundle.schema.json` to include `repo_dir` property BEFORE implementation.
**Gate**: Schema validation at worker boundary

## Task-specific review checklist

1. [ ] `repo_sha` is populated (non-empty) in IntakeBundle after clone
2. [ ] `repo_dir` path exists on disk when Understand receives it
3. [ ] Scout no longer imports subprocess or calls git
4. [ ] `_build_product_identity` removed from scout.py (no duplication)
5. [ ] IntakeBundle JSON schema validates with new `repo_dir` field
6. [ ] All existing tests pass with PYTHONHASHSEED=0
7. [ ] New clone tests cover cache hit, cache miss, and ls-remote failure
8. [ ] Understand worker reads repo_dir from IntakeBundle, not from clone

## Deliverables

1. `src/launcher/workers/intake/clone.py` — extracted clone module
2. Updated `src/launcher/workers/intake/worker.py` — calls clone
3. Updated `src/launcher/models/intake.py` — `repo_dir` field
4. Updated `specs/schemas/intake_bundle.schema.json`
5. Refactored `src/launcher/workers/understand/scout.py`
6. Updated `src/launcher/workers/understand/worker.py`
7. `tests/unit/workers/test_clone.py` — clone unit tests
8. Updated `tests/unit/workers/test_intake.py`
9. Updated `specs/worker_understand.md`
10. `reports/agents/B/TC-3776/evidence.md`

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v` — all pass
2. [ ] `repo_sha` non-empty in IntakeBundle output
3. [ ] `repo_dir` points to valid directory in IntakeBundle output
4. [ ] Scout has zero git/subprocess imports
5. [ ] No `_build_product_identity` in scout.py
6. [ ] JSON schema validates IntakeBundle with repo_dir

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: intake schema PASS
- [ ] Evidence captured: reports/agents/B/TC-3776/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/workers/test_clone.py tests/unit/workers/test_scout_facts.py -v
```

**Expected results**:
- All intake tests pass with repo_sha and repo_dir populated
- All clone tests pass (cache hit/miss/failure scenarios)
- All scout_facts tests pass (unchanged functionality)

## Integration boundary proven

**Upstream**: RunConfig provides repo_url; git remote provides repository
**Downstream**: Understand worker receives IntakeBundle with repo_dir and repo_sha; Scout uses repo_dir for fingerprinting
**Contract**: IntakeBundle pydantic model + intake_bundle.schema.json enforces the boundary
