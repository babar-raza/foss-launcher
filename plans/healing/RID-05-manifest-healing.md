# RID-04 Manifest Healing — Gap Index + Taskcards

## Context

Self-review of RID-04 (run_manifest.json) found 4 gaps: missing test,
resume-overwrite bug, missing `config_path` field, and TC-3805 taskcard
not updated to cover manifest scope. Two are bugs, one is a test gap,
one is governance.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-MF-01 | No test for manifest file creation or content | Test gap/High | MF-01 |
| G-MF-02 | Resume overwrites manifest — `created_utc` lost | Bug/High | MF-02 |
| G-MF-03 | Missing `config_path` field from manifest (plan spec included it) | Spec drift/Medium | MF-02 |
| G-MF-04 | TC-3805 taskcard doesn't mention manifest in scope/deliverables | Governance/Low | MF-03 |

---

## MF-01: Manifest Test Coverage

### Status: Done

### Gap Linkage
- G-MF-01: No test for manifest file creation or content

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Add tests verifying that `run_manifest.json` is written with correct
content after a pipeline run. Tests should cover:
1. Manifest exists after a fresh run via `execute_run`
2. Manifest contains expected keys (`run_id`, `family`, `platform`, `created_utc`)
3. Manifest values match the RunConfig input
4. Manifest is NOT overwritten on resume (regression test for G-MF-02, after MF-02 lands)

#### Allowed paths
- `tests/unit/orchestrator/test_run_manifest.py` (new file)

#### Forbidden
- Any other file/path

### Acceptance Checks

#### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_manifest.py -v` — all pass

#### Tests
- ≥3 test functions: fresh-run manifest exists, content correct, resume preserves original
- Happy path: fresh run produces manifest with matching family/platform
- Regression path: resumed run does NOT overwrite existing manifest

#### Config respected end-to-end
- Tests use `minimal_run_config` fixture (same as `test_run_id_guard.py`)

#### No mock data in production paths
- Tests use `tmp_path` and mock workers only

### Deliverables
- `tests/unit/orchestrator/test_run_manifest.py` with ≥3 test functions
- Tests cover happy path + resume regression

### Hard Rules
- No network in offline tests
- Deterministic via `PYTHONHASHSEED=0`
- No new deps
- Tests must work with both entrypoints' manifest format

### Review Dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | Fresh-run, content-check, and resume-preservation tests all present |
| Testability | Each test independent, fast (<1s), uses tmp_path |
| Correctness | Asserts exact key set and value types |
| Robustness | Resume regression test catches future overwrites |
| Minimality | 1 new file, no production code changes |

### Now (Runbook)

```bash
# 1. Create tests/unit/orchestrator/test_run_manifest.py
# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_manifest.py -v
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## MF-02: Manifest Resume Guard + Config Path Field

### Status: Done

### Gap Linkage
- G-MF-02: Resume overwrites manifest — `created_utc` lost
- G-MF-03: Missing `config_path` field from manifest

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
1. **Resume guard**: In `run_loop.py`, wrap manifest write in
   `if not resume_from:` so resumed runs preserve the original manifest.
   In `run_pilot.py`, wrap in equivalent guard using the existing
   `resume_from` variable.
2. **Add `config_path` field**: Include the config file path in the
   manifest dict. In `run_loop.py`, use `str(pipeline_config_path)` or
   a new parameter. In `run_pilot.py`, use `config_path` (the arg).
   Note: `run_loop.py`'s `execute_run` receives `config: RunConfig`
   not the config file path — so use `config.family` context only, or
   thread the config path through. Simpler: in `run_pilot.py` it's
   available as `config_path` arg; in `run_loop.py` the caller
   (`cli/main.py`) has the path. Add an optional `config_path` param
   to `execute_run` and pass it through.

#### Allowed paths
- `src/launcher/orchestrator/run_loop.py` (manifest block, ~lines 313-319; `execute_run` signature)
- `scripts/run_pilot.py` (manifest block, ~lines 98-107)
- `src/launcher/cli/main.py` (pass `config_path` to `execute_run`)

#### Forbidden
- Any other file/path

### Acceptance Checks

#### CLI
- Fresh run: `cat runs/<id>/run_manifest.json` shows `created_utc` and `config_path`
- Resumed run: `cat runs/<id>/run_manifest.json` still shows ORIGINAL `created_utc`

#### Tests
- MF-01 resume regression test passes (depends on MF-01)
- Existing `test_run_id_guard.py` still passes

#### Config respected end-to-end
- `config_path` field reflects actual config file used

#### No mock data in production paths
- No hardcoded paths in manifest

### Deliverables
- Patched `run_loop.py`: resume guard + `config_path` field + optional param
- Patched `run_pilot.py`: resume guard + `config_path` field
- Patched `cli/main.py`: thread config path to `execute_run`

### Hard Rules
- Keep `execute_run` signature backward-compatible (new param is optional with default `""`)
- Keep entrypoints in parity
- No new deps
- Code/docs/tests in sync

### Review Dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Correctness | Resume preserves original manifest; fresh run includes config_path |
| Robustness | Guard prevents data loss on resume |
| Consistency | Both entrypoints have identical guard logic and field set |
| Integration fit | `execute_run` signature stays backward-compatible |
| Minimality | ~5 lines changed per file, 1 optional param added |

### Now (Runbook)

```bash
# 1. Add `config_path: str = ""` param to execute_run in run_loop.py
# 2. Wrap manifest write in `if not resume_from:`, add config_path field
# 3. Same guard + config_path in run_pilot.py
# 4. Thread config path in cli/main.py
# 5. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/ -v
# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## MF-03: Update TC-3805 Scope for Manifest

### Status: Done

### Gap Linkage
- G-MF-04: TC-3805 taskcard doesn't mention manifest in scope/deliverables

### Role
Senior engineer. Drop-in, production-ready.

### Scope

#### Fix
Update `plans/taskcards/TC-3805_run_id_unification.md` to include:
- `run_manifest.json` in the "In scope" section
- Both manifest write locations in "Implementation steps"
- Manifest test in "Deliverables"
- `src/launcher/cli/main.py` in "Allowed paths" (for config_path threading)

#### Allowed paths
- `plans/taskcards/TC-3805_run_id_unification.md`

#### Forbidden
- Any other file/path

### Acceptance Checks

#### CLI
- `grep -c "manifest" plans/taskcards/TC-3805_run_id_unification.md` returns ≥3

#### Tests
- N/A (governance artifact)

### Deliverables
- Updated TC-3805 with manifest scope additions

### Hard Rules
- No code changes
- Keep all existing content, only add manifest references

### Review Dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All manifest-related work reflected in taskcard |
| Consistency | Allowed paths match actual files modified |
| Minimality | Additions only, no removals |

### Now (Runbook)

```bash
# 1. Edit TC-3805 to add manifest scope
# 2. Verify
grep -c "manifest" plans/taskcards/TC-3805_run_id_unification.md
```
