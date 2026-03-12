---
id: TC-HYBRID-01
title: "Split canonical_import: add runtime_import for Python code generation + limitation claim kind"
status: Done
priority: Critical
owner: "Agent-B"
updated: "2026-03-10"
tags: [evidence-model, phase-0, canonical-import, python, critical]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HYBRID-01_runtime-import-split.md
  - configs/families.yaml
  - src/launcher/models/product.py
  - src/launcher/models/intake.py
  - src/launcher/models/run_config.py
  - src/launcher/models/claims.py
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/evaluate/checks/code.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/generate/fallback.py
  - src/launcher/io/run_config.py
  - specs/schemas/run_config.schema.json
  - configs/pilots/aspose-3d-foss-python.yaml
  - configs/pilots/aspose-cells-foss-python.yaml
  - configs/pilots/aspose-note-foss-python.yaml
  - configs/pilots/aspose-slides-foss-python.yaml
  - tests/unit/workers/test_intake.py
  - tests/unit/workers/test_code_check.py
  - tests/unit/test_run_config_validation.py
  - reports/agents/B/TC-HYBRID-01/plan.md
  - reports/agents/B/TC-HYBRID-01/changes.md
  - reports/agents/B/TC-HYBRID-01/evidence.md
  - reports/agents/B/TC-HYBRID-01/self_review.md
  - reports/agents/B/TC-HYBRID-01/commands.sh
  - reports/TC-HYBRID-01/evidence.md
evidence_required:
  - reports/TC-HYBRID-01/evidence.md
---

# Taskcard TC-HYBRID-01 — Split canonical_import: add runtime_import for Python code generation + limitation claim kind

## Objective

Add a `runtime_import` field to `ProductIdentity` (and downstream models) that holds the
**Python runtime module path** (e.g. `aspose.threed`, `aspose.cells`), separate from the
existing `canonical_import` which holds the pip package name (`aspose_3d_foss`).
This eliminates the root cause of all Python code example failures: `import aspose_3d_foss`
is an invalid Python import (it's a pip name, not a module). Also add `limitation` as a
valid claim kind to enable limitation claim extraction in Phase 1.

## Required spec references

- `specs/system_overview.md` (Rule 5: Sandwich Model — evidence-first before LLM)
- `specs/worker_understand.md` (Section: ProductIdentity, canonical_import)
- `specs/worker_generate.md` (Section: code generation, import normalization)
- `specs/worker_evaluate.md` (Section: Check 3 — code validation)
- `specs/product_model.md` (Section: ProductIdentity fields)

## Scope

### In scope
- Add `runtime_import: str = ""` to `ProductIdentity`, `IntakeBundle`, `RunConfig`
- Add `runtime_import_tpl` + `runtime_import_overrides` to `families.yaml` Python platform
- Populate `runtime_import` in intake worker `_resolve_identity()` and pilot config override
- Update `check_code()` to validate Python imports against `runtime_import` (if set)
- Update `_normalize_imports()` in `section_validator.py` to use `runtime_import` for Python
- Update `generate/worker.py` code example generation to use `runtime_import`
- Update `generate/section_prompt.py` to inject `runtime_import` as the Python import
- Update `io/run_config.py` `_validate_canonical_import()` to check `runtime_import` format
- Update `specs/schemas/run_config.schema.json` to add `runtime_import` property
- Add `runtime_import` to all Python pilot configs
- Add `"limitation"` to valid claim kinds in `models/claims.py`
- Add/update tests for the above changes

### Out of scope
- Renaming or removing `canonical_import` (keep for backwards compat and TypeScript/Java/.NET)
- Changing TypeScript canonical_import (`@aspose/3d-foss`) — it is already correct
- Phase 1 API surface extraction (TC-HYBRID-02, TC-HYBRID-03)
- InstallRecipe / LimitationEntry models (TC-HYBRID-04)

## Inputs

- `configs/families.yaml` — current Python `import_tpl: "aspose_{family}_foss"`
- `src/launcher/models/product.py` — `ProductIdentity` with `canonical_import: str`
- `configs/pilots/*.yaml` — current `canonical_import: aspose_3d_foss` values

## Outputs

- `ProductIdentity.runtime_import` populated with `aspose.threed` for 3d, `aspose.cells` for cells, etc.
- Python code generation uses `runtime_import` not `canonical_import`
- Python import validation checks `runtime_import` not `canonical_import`
- All Python pilot configs have explicit `runtime_import:` field
- `Claim.kind = "limitation"` accepted without validation error

## Allowed paths

- plans/taskcards/TC-HYBRID-01_runtime-import-split.md
- configs/families.yaml
- src/launcher/models/product.py
- src/launcher/models/intake.py
- src/launcher/models/run_config.py
- src/launcher/models/claims.py
- src/launcher/workers/intake/worker.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/evaluate/checks/code.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/fallback.py
- src/launcher/io/run_config.py
- specs/schemas/run_config.schema.json
- configs/pilots/aspose-3d-foss-python.yaml
- configs/pilots/aspose-cells-foss-python.yaml
- configs/pilots/aspose-note-foss-python.yaml
- configs/pilots/aspose-slides-foss-python.yaml
- tests/unit/workers/test_intake.py
- tests/unit/workers/test_code_check.py
- tests/unit/test_run_config_validation.py
- reports/agents/B/TC-HYBRID-01/
- reports/TC-HYBRID-01/

### Allowed paths rationale
- `configs/families.yaml` — add `runtime_import_tpl` and `runtime_import_overrides`
- `src/launcher/models/product.py` — add `runtime_import` field to `ProductIdentity`
- `src/launcher/models/intake.py` — propagate `runtime_import` to `IntakeBundle`
- `src/launcher/models/run_config.py` — add `runtime_import` to `RunConfig`
- `src/launcher/models/claims.py` — add `"limitation"` kind
- `src/launcher/workers/intake/worker.py` — populate `runtime_import` in `_resolve_identity()`
- `src/launcher/workers/understand/worker.py` — pass `runtime_import` to `ProductIdentity`
- `src/launcher/workers/evaluate/checks/code.py` — use `runtime_import` for Python validation
- `src/launcher/workers/evaluate/worker.py` — pass `runtime_import` to `check_code()`
- `src/launcher/workers/generate/section_prompt.py` — inject `runtime_import` in prompts
- `src/launcher/workers/generate/section_validator.py` — use `runtime_import` in normalization
- `src/launcher/workers/generate/worker.py` — use `runtime_import` in code example injection
- `src/launcher/workers/generate/fallback.py` — use `runtime_import` for Python fallback
- `src/launcher/io/run_config.py` — add `runtime_import` validation
- `specs/schemas/run_config.schema.json` — add `runtime_import` property
- Pilot configs — add explicit `runtime_import:` field
- Tests — verify new behavior

## Implementation steps

### Step 1: Update families.yaml (Python runtime_import template)

Add `runtime_import_tpl` and `runtime_import_overrides` to Python platform section.
General rule: `aspose.{family}` (works for cells, note, slides, words, pdf, etc.)
Exception: `3d` → `aspose.threed` (Python identifiers can't start with digits).

```yaml
platforms:
  python:
    import_tpl: "aspose_{family}_foss"
    install_cmd: "pip install aspose-{family}-foss"
    lang_tag: "python"
    runtime_import_tpl: "aspose.{family}"
    runtime_import_overrides:
      3d: "aspose.threed"
```

### Step 2: Add `runtime_import: str = ""` to ProductIdentity (product.py)

Add after `canonical_import`:
```python
runtime_import: str = ""
"""Python runtime module import path (e.g. 'aspose.threed').

Separate from ``canonical_import`` which holds the pip package name
(``aspose_3d_foss``). Only populated for Python platform. Used for
code generation and import validation.
"""
```

### Step 3: Add `runtime_import: str = ""` to IntakeBundle (intake.py)

Add as optional field alongside `canonical_import`.

### Step 4: Add `runtime_import: str = ""` to RunConfig (run_config.py model)

Add as optional field in `RunConfig` pydantic model.

### Step 5: Update `_resolve_identity()` in intake/worker.py

After resolving `canonical_import`, also resolve `runtime_import`:
```python
runtime_import = ""
if platform_info:
    runtime_import_tpl = platform_info.get("runtime_import_tpl", "")
    runtime_import_overrides = platform_info.get("runtime_import_overrides", {})
    if runtime_import_tpl:
        derived = runtime_import_overrides.get(family.lower())
        if derived is None:
            derived = runtime_import_tpl.format(family=family.lower())
        runtime_import = derived
```

Override with config value if provided:
```python
if config.runtime_import:
    runtime_import = config.runtime_import
```

Pass `runtime_import` to `IntakeBundle`.

### Step 6: Update `run_config.schema.json`

Add `runtime_import` property:
```json
"runtime_import": {
  "type": "string",
  "description": "Python runtime module import path (e.g. 'aspose.threed'). Separate from pip package name."
}
```

### Step 7: Update `io/run_config.py` `_validate_canonical_import()`

Add validation for `runtime_import` when present for Python:
- Must contain a dot (e.g. `aspose.threed` has a dot; `aspose_3d_foss` does not)
- Log warning if runtime_import is empty for Python platform (not an error, just advisory)

### Step 8: Update `evaluate/checks/code.py` `check_code()`

Add `runtime_import: str = ""` parameter. For Python import validation:
- If `runtime_import` is set: validate Python imports contain `runtime_import` (or split by ".")
- If not set: fall back to existing `canonical_import` check
- Keep existing logic intact as fallback

### Step 9: Update `evaluate/worker.py`

Pass `context.config.runtime_import` (or `getattr(context.config, "runtime_import", "")`)
to `check_code()` where it calls the code check.

### Step 10: Update `generate/section_validator.py` `_normalize_imports()`

In `_normalize_imports()` and the prose-fix function:
- Accept `runtime_import` parameter
- For Python: use `runtime_import` as the canonical if set (else fall back to `canonical_import`)

### Step 11: Update `generate/worker.py`

In `_fix_prose_canonical_imports()` and `_fix_import_only_blocks()`:
- Use `product.runtime_import or product.canonical_import` for Python

### Step 12: Update `generate/section_prompt.py` `build_prompt()`

In the prompt context injection, add:
```python
# Use runtime_import for Python code (not pip name)
code_import = product.runtime_import or product.canonical_import
```
Update any prompt text that says "use `{canonical_import}`" to use `code_import` for Python.

### Step 13: Update `generate/fallback.py`

Use `product.runtime_import or product.canonical_import` for Python in fallback rendering.

### Step 14: Add `"limitation"` to claim kinds in `models/claims.py`

Find the claim kind Literal or Enum definition and add `"limitation"` as a valid kind.

### Step 15: Update Python pilot configs

Add `runtime_import:` field to each Python pilot config:
- `aspose-3d-foss-python.yaml`: `runtime_import: aspose.threed`
- `aspose-cells-foss-python.yaml`: `runtime_import: aspose.cells`
- `aspose-note-foss-python.yaml`: `runtime_import: aspose.note`
- `aspose-slides-foss-python.yaml`: `runtime_import: aspose.slides`

### Step 16: Update understand/worker.py

Pass `runtime_import` from `intake.runtime_import` to `ProductIdentity`.

### Step 17: Write/update tests

- `test_intake.py`: verify `_resolve_identity()` populates `runtime_import` correctly for 3d (→`aspose.threed`) and cells (→`aspose.cells`)
- `test_code_check.py`: verify `check_code()` with `runtime_import="aspose.threed"` → `import aspose.threed` PASSES, `import aspose_3d_foss` FAILS
- `test_run_config_validation.py`: verify `runtime_import` accepted by schema

## Failure modes

### Failure mode 1: `3d` family gets `aspose.3d` not `aspose.threed`

**Detection**: `test_intake.py` test for `_resolve_identity("3d", "python")` asserts `runtime_import == "aspose.threed"` — FAILS
**Resolution**: Check `runtime_import_overrides` in families.yaml — ensure `3d: "aspose.threed"` is present and `_resolve_identity` reads it
**Gate**: Step 5 logic

### Failure mode 2: Existing tests fail due to `canonical_import` behavior change

**Detection**: `pytest tests/` shows failures in test_code_check, test_section_validator, test_generate
**Resolution**: Ensure fallback chain: `runtime_import or canonical_import`. New field is additive. Don't break existing `canonical_import` paths.
**Gate**: All existing tests must still pass

### Failure mode 3: TypeScript canonical_import broken by runtime_import logic

**Detection**: `test_ts_analyzer.py` or TypeScript pilot tests fail
**Resolution**: `runtime_import` defaults to `""`. Code that uses `runtime_import or canonical_import` will use `canonical_import` for TypeScript. Only Python pilot configs add `runtime_import`.
**Gate**: TypeScript pilot tests green

### Failure mode 4: Pilot config schema validation fails for `runtime_import`

**Detection**: `load_and_validate_run_config()` raises `ConfigError` on updated pilot configs
**Resolution**: Add `runtime_import` to `run_config.schema.json`. Schema uses `additionalProperties: true` so new field is allowed even without explicit entry, but explicit is better.
**Gate**: Step 6 (schema update)

## Task-specific review checklist

1. [ ] `ProductIdentity.runtime_import` populated for all Python pilot profiles (aspose.3d → aspose.threed, aspose.cells → aspose.cells, etc.)
2. [ ] `check_code()` uses `runtime_import` when set; correctly identifies `aspose_3d_foss` as wrong import for Python
3. [ ] `_normalize_imports()` in section_validator.py uses `runtime_import` (not pip name) for Python normalization
4. [ ] `generate/worker.py` fallback code block uses `runtime_import` for Python examples
5. [ ] `generate/section_prompt.py` injects `runtime_import` as the import to use in Python code sections
6. [ ] TypeScript canonical_import (`@aspose/3d-foss`) is unchanged — only Python is affected
7. [ ] `"limitation"` claim kind accepted without validation error
8. [ ] All existing 3118+ tests pass (no regressions)
9. [ ] New test verifies `aspose.threed` passes import check, `aspose_3d_foss` fails
10. [ ] Docstrings updated for `ProductIdentity.runtime_import` explaining the pip vs runtime distinction
11. [ ] Schema description field present for `runtime_import` in run_config.schema.json
12. [ ] Checked `docs/README.md` ownership map — intake/generate/evaluate workers all touched; no guide changes required (no new user-facing behavior)

## Deliverables

1. `src/launcher/models/product.py` — `runtime_import` field on `ProductIdentity`
2. `configs/families.yaml` — `runtime_import_tpl` + `runtime_import_overrides` for Python
3. All Python pilot configs updated with `runtime_import:` field
4. `src/launcher/workers/intake/worker.py` — `_resolve_identity()` populates `runtime_import`
5. `evaluate/checks/code.py` — uses `runtime_import` for Python validation
6. `generate/worker.py`, `section_validator.py`, `section_prompt.py` — use `runtime_import`
7. `src/launcher/models/claims.py` — `"limitation"` kind added
8. Evidence at `reports/TC-HYBRID-01/evidence.md`

## Acceptance checks

1. [ ] `python -c "from launcher.models.product import ProductIdentity; p = ProductIdentity(family='3d', platform='python', display_name='x', canonical_import='aspose_3d_foss', repo_url='https://github.com/x/x', runtime_import='aspose.threed'); assert p.runtime_import == 'aspose.threed'"` — PASS
2. [ ] `pytest tests/unit/workers/test_intake.py -k runtime_import -v` — all new tests PASS
3. [ ] `pytest tests/unit/workers/test_code_check.py -v` — all tests PASS
4. [ ] `pytest tests/ -x -q` — 0 failures
5. [ ] Python pilot config has `runtime_import: aspose.threed` (for 3d) and `runtime_import: aspose.cells` (for cells)
6. [ ] `"limitation"` accepted as Claim kind without validation error

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: check_code import gate PASS with aspose.threed, FAIL with aspose_3d_foss
- [ ] Evidence captured: reports/TC-HYBRID-01/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
# Run all tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# Verify ProductIdentity runtime_import field
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
from launcher.models.product import ProductIdentity
p = ProductIdentity(family='3d', platform='python', display_name='x',
    canonical_import='aspose_3d_foss', repo_url='https://github.com/x', runtime_import='aspose.threed')
assert p.runtime_import == 'aspose.threed', f'Expected aspose.threed, got {p.runtime_import}'
print('PASS: runtime_import field works')
"

# Verify limitation claim kind accepted
PYTHONHASHSEED=0 .venv/Scripts/python.exe -c "
from launcher.models.claims import Claim
c = Claim(claim_id='CLM-1', text='FBX export has known parser bugs', kind='limitation', evidence=[])
print(f'PASS: limitation kind accepted: {c.kind}')
"

# Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/workers/test_code_check.py tests/unit/test_run_config_validation.py -v
```

**Expected results**:
- All tests PASS (no regressions)
- `runtime_import == "aspose.threed"` for 3d Python pilot
- `limitation` claim kind validates without error
- `check_code` rejects `aspose_3d_foss` as import when `runtime_import="aspose.threed"`

## Integration boundary proven

**Upstream**: `RunConfig` (pilot config) → `IntakeBundle.runtime_import`
**Downstream**: `ProductIdentity.runtime_import` → `check_code()` → `_normalize_imports()` → generation prompts
**Contract**: `runtime_import` is the Python module import path (dot-notation); `canonical_import` remains the pip package name (underscore-notation). Either can be empty; code falls back gracefully.
