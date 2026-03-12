---
id: TC-3911
title: "Remove orphaned / dead-code files"
status: Done
priority: Normal
owner: agent
updated: "2026-03-09"
tags: [housekeeping, dead-code]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3911_remove-orphaned-files.md
  - src/launcher/shared/extract_claims.py
  - src/launcher/shared/context_validator.py
  - src/launcher/shared/markdown_zones.py
  - src/launcher/shared/policy_check.py
  - src/launcher/shared/rich_context.py
  - src/launcher/util/diff_analyzer.py
  - src/launcher/validation_engine/
evidence_required:
  - reports/TC-3911/evidence.md
---

# Taskcard TC-3911 — Remove orphaned / dead-code files

## Objective

Delete 6 individual files and 1 entire sub-package that are never imported anywhere
in the production code or tests. Removing them eliminates maintenance debt, prevents
accidental imports, and keeps the dependency graph clean.

## Required spec references

- None (housekeeping; no spec behavior changes)

## Scope

### In scope
- Delete `src/launcher/shared/extract_claims.py` (compat shim, explicitly labelled orphan)
- Delete `src/launcher/shared/context_validator.py` (0 references)
- Delete `src/launcher/shared/markdown_zones.py` (0 references)
- Delete `src/launcher/shared/policy_check.py` (0 references)
- Delete `src/launcher/shared/rich_context.py` (self-references only)
- Delete `src/launcher/util/diff_analyzer.py` (0 references)
- Delete `src/launcher/validation_engine/` entire package (internal cross-refs only; never imported from outside)

### Out of scope
- Any file that is imported by production code, tests, or configs
- Refactoring of the remaining modules

## Inputs

- Confirmed orphan list from codebase sweep (grep verified against `src/`, `tests/`, `configs/`)

## Outputs

- 13 fewer files in the repository
- Clean grep: no remaining references to deleted modules

## Allowed paths

- plans/taskcards/TC-3911_remove-orphaned-files.md
- src/launcher/shared/extract_claims.py (DELETE)
- src/launcher/shared/context_validator.py (DELETE)
- src/launcher/shared/markdown_zones.py (DELETE)
- src/launcher/shared/policy_check.py (DELETE)
- src/launcher/shared/rich_context.py (DELETE)
- src/launcher/util/diff_analyzer.py (DELETE)
- src/launcher/validation_engine/ (DELETE entire directory)

### Allowed paths rationale
All paths are files being deleted; no content is being written to protected paths.

## Implementation steps

### Step 1: Delete individual shared/ orphans
Delete the 5 orphaned files in `src/launcher/shared/`.

### Step 2: Delete util/ orphan
Delete `src/launcher/util/diff_analyzer.py`.

### Step 3: Delete validation_engine/ package
Delete the entire `src/launcher/validation_engine/` directory.

### Step 4: Verify no lingering references
Run grep across `src/` and `tests/` for the deleted module names — expect 0 hits.

### Step 5: Run tests
`.venv/Scripts/python.exe -m pytest tests/ -x -q` with PYTHONHASHSEED=0.

## Failure modes

### Failure mode 1: Hidden import found after deletion
**Detection**: `ImportError` during test run mentioning a deleted module.
**Resolution**: Restore the deleted file, find the import, decide whether to remove the importer or restore the file.
**Gate**: Test suite pass.

### Failure mode 2: `__init__.py` re-exports a deleted module
**Detection**: `ImportError: cannot import name 'X' from 'launcher.shared'`
**Resolution**: Remove the re-export line from the relevant `__init__.py`.
**Gate**: Smoke import `python -c "import launcher"` passes.

### Failure mode 3: YAML/config references a deleted module by name
**Detection**: Runtime `ModuleNotFoundError` when loading configs.
**Resolution**: Remove or replace the config entry.
**Gate**: Config loading smoke test passes.

## Task-specific review checklist

1. [ ] All 6 individual files deleted
2. [ ] `validation_engine/` directory fully deleted (all 7+ files)
3. [ ] `src/launcher/shared/__init__.py` confirmed — no re-exports of deleted modules
4. [ ] `src/launcher/util/__init__.py` confirmed — no re-exports of deleted modules
5. [ ] Grep for deleted module names returns 0 hits in `src/` and `tests/`
6. [ ] All existing tests pass (PYTHONHASHSEED=0)
7. [ ] Docstrings updated for all new/changed public functions — N/A (deletions only)
8. [ ] Spec file updated if worker behavior changed — N/A (no behavior change)
9. [ ] Schema `"description"` fields present for all new/changed properties — N/A
10. [ ] Checked `docs/README.md` ownership map — N/A (deletions only)
11. [ ] If a new `docs/guides/` file was added — N/A

## Deliverables

1. Deleted files (git shows them as removed)
2. Passing test suite

## Acceptance checks

1. [ ] `grep -r "extract_claims\|context_validator\|markdown_zones\|policy_check\|rich_context\|diff_analyzer\|validation_engine" src/ tests/` returns 0 hits for import-style references
2. [ ] All tests pass with PYTHONHASHSEED=0
3. [ ] `python -c "import launcher"` succeeds

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3911/evidence.md
- [ ] Doc freshness: N/A (deletions only, no behavior changes)

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- All tests pass
- No ImportError for deleted modules

## Integration boundary proven

**Upstream**: None (orphaned files had no callers)
**Downstream**: None (orphaned files had no consumers)
**Contract**: N/A
