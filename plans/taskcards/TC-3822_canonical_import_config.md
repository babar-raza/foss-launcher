---
id: TC-3822
title: "Fix canonical_import in pilot configs + startup validation"
status: In-Progress
priority: Critical
owner: agent
updated: "2026-03-07"
tags: [phase-7a, engineering-fix, config, canonical-import]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3822_canonical_import_config.md
  - configs/pilots/aspose-cells-foss-python.yaml
  - configs/pilots/aspose-note-foss-python.yaml
  - src/launcher/io/run_config.py
  - tests/test_run_config.py
evidence_required:
  - reports/TC-3822/evidence.md
---

# Taskcard TC-3822 --- Fix canonical_import in pilot configs + startup validation

## Objective

Fix a config bug where pilot configs set `canonical_import` to the PyPI package name (`aspose.cells`) instead of the Python import name (`aspose_cells_foss`). This causes the import normalizer to no-op and the LLM to generate wrong imports. Add startup validation to prevent this class of bug from recurring.

## Required spec references

- `configs/families.yaml` (Section: platforms.python.import_tpl -- defines correct import format)
- `specs/system_overview.md` (Section: Config loading -- runtime validation)

## Scope

### In scope
- Correct `canonical_import` in both pilot config files
- Add startup validation that checks canonical_import format against families.yaml import_tpl
- Tests for the validation logic

### Out of scope
- Inline code body reference replacement (`aspose.cells.Workbook()`) -- deferred, requires AST-aware parsing
- Import statement normalization code changes -- already works correctly with correct config
- Changes to `_normalize_imports()` in section_validator.py

## Inputs

- `configs/pilots/*.yaml` -- pilot config files with `canonical_import` field
- `configs/families.yaml` -- family/platform taxonomy with `import_tpl` pattern

## Outputs

- Corrected pilot configs with proper Python import names
- Startup validation that catches config/taxonomy mismatches

## Allowed paths

- plans/taskcards/TC-3822_canonical_import_config.md
- configs/pilots/aspose-cells-foss-python.yaml
- configs/pilots/aspose-note-foss-python.yaml
- src/launcher/io/run_config.py
- tests/test_run_config.py

### Allowed paths rationale
- configs/pilots/*.yaml: Fix the incorrect canonical_import values
- run_config.py: Add validation logic during config loading
- tests/: Unit tests for validation

## Implementation steps

### Step 1: Fix pilot config values

Change `canonical_import` in both pilot configs:

`configs/pilots/aspose-cells-foss-python.yaml`:
```yaml
canonical_import: "aspose_cells_foss"  # was: "aspose.cells"
```

`configs/pilots/aspose-note-foss-python.yaml`:
```yaml
canonical_import: "aspose_note_foss"  # was: "aspose.note"
```

### Step 2: Add startup validation in run_config.py

Add a validation function that checks canonical_import format:
- If platform is "python", canonical_import should match `aspose_{family}_foss` pattern (no dots, underscored)
- If canonical_import contains dots and platform is python, warn or error
- Load families.yaml to derive expected import and compare

### Step 3: Write tests

- Test that validation catches `canonical_import: "aspose.cells"` for platform=python
- Test that validation accepts `canonical_import: "aspose_cells_foss"` for platform=python
- Test that validation catches mismatch between canonical_import and families.yaml import_tpl

## Failure modes

### Failure mode 1: Existing pilot runs cached with old canonical_import

**Detection**: Re-running a pilot after config change produces different output than cached artifacts
**Resolution**: Old artifacts used wrong imports anyway. Cache invalidation is correct behavior. Bump ENGINE_VERSION if needed.
**Gate**: code check (import validation)

### Failure mode 2: families.yaml not found during validation

**Detection**: FileNotFoundError when loading families.yaml
**Resolution**: Make validation optional (warn, don't crash) if families.yaml is missing. Config-only runs (no taxonomy) should still work.
**Gate**: startup validation

### Failure mode 3: Non-Python platforms have dotted imports legitimately

**Detection**: Validation incorrectly flags `com.aspose.cells` for Java platform
**Resolution**: Only validate Python platform imports (underscored format). Java/dotnet/node have their own patterns defined in families.yaml import_tpl.
**Gate**: startup validation

## Task-specific review checklist

1. [ ] Both pilot configs updated with correct canonical_import
2. [ ] Validation checks canonical_import against families.yaml import_tpl
3. [ ] Validation only strict for Python platform (dotted imports valid for Java/dotnet)
4. [ ] Validation is non-fatal (warning) if families.yaml is missing
5. [ ] Tests cover correct and incorrect canonical_import values
6. [ ] No changes to section_validator.py -- code already works with correct config

## Deliverables

1. Modified `configs/pilots/aspose-cells-foss-python.yaml`
2. Modified `configs/pilots/aspose-note-foss-python.yaml`
3. Modified `src/launcher/io/run_config.py`
4. New/updated tests in `tests/`

## Acceptance checks

1. [ ] `canonical_import` in aspose-cells pilot is `aspose_cells_foss`
2. [ ] `canonical_import` in aspose-note pilot is `aspose_note_foss`
3. [ ] Startup validation catches dotted Python imports
4. [ ] Startup validation accepts underscored Python imports
5. [ ] All existing tests pass with PYTHONHASHSEED=0

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: config loading PASS
- [ ] Evidence captured: reports/TC-3822/

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -v -k "run_config or canonical"
```

**Expected results**:
- Config validation catches wrong import format
- All existing tests pass

## Integration boundary proven

**Upstream**: families.yaml defines import_tpl pattern per platform
**Downstream**: section_validator `_normalize_imports()` uses canonical_import to rewrite; LLM receives it in prompt
**Contract**: canonical_import matches `platforms[platform].import_tpl.format(family=family)` from families.yaml
