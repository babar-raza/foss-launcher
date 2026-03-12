---
id: TC-3870
title: "Config generator schema alignment + check_dedup Tier 1 fix"
status: Done
priority: High
owner: agent
updated: "2026-03-09"
tags: [intake, config-generator, bugfix, schema]
depends_on: [TC-3869]
allowed_paths:
  - plans/taskcards/TC-3870_config_generator_schema_alignment.md
  - src/launcher/intake/config_generator.py
  - tests/unit/intake/test_config_generator.py
  - configs/pilots/aspose-3d-foss-python.yaml
  - configs/pilots/aspose-slides-foss-python.yaml
evidence_required:
  - reports/TC-3870/evidence.md
---

# Taskcard TC-3870 — Config generator schema alignment + check_dedup Tier 1 fix

## Objective

Fix two bugs in `config_generator.py`:
1. `check_dedup` Tier 1 uses `_derive_product_slug` (old `pilot-...` format) instead of
   `_derive_config_filename`, so it never finds existing configs by filename.
2. System-generated configs are missing `display_name`, `canonical_import`, and `golden`
   (needed by the pipeline) and include junk fields RunConfig ignores (`github_ref`,
   `product_slug`, `budgets`, `telemetry`).

## Required spec references

- `specs/github_intake.md` (Section 6 — pilot config generation)

## Scope

### In scope
- Fix `check_dedup` Tier 1 to use `_derive_config_filename`
- Add `_derive_display_name()` helper
- Add `_derive_canonical_import()` helper
- Update `_DEFAULT_TEMPLATE`: add `display_name`, `canonical_import`, `golden`; remove
  `github_ref`, `product_slug`, `budgets`, `telemetry`
- Update `generate_config()` to populate new fields
- Update tests to cover new helpers and Tier 1 dedup
- Delete and regenerate `aspose-3d-foss-python.yaml` and `aspose-slides-foss-python.yaml`

### Out of scope
- `aspose-cells-foss-python.yaml` and `aspose-note-foss-python.yaml` are manually crafted
  and must NOT be overwritten
- `product_name` auto-derivation from GitHub description (already working, kept as-is)
- Non-Aspose orgs / non-Python platforms (same derivation pattern applies generically)

## Inputs

- `configs/pilots/aspose-cells-foss-python.yaml` — reference schema for what generated
  configs must match
- GitHub repo metadata dicts (owner.login, name, language, topics)

## Outputs

- Fixed `src/launcher/intake/config_generator.py`
- Updated `tests/unit/intake/test_config_generator.py`
- Regenerated `configs/pilots/aspose-3d-foss-python.yaml` (complete schema)
- Regenerated `configs/pilots/aspose-slides-foss-python.yaml` (complete schema)

## Allowed paths

- plans/taskcards/TC-3870_config_generator_schema_alignment.md
- src/launcher/intake/config_generator.py
- tests/unit/intake/test_config_generator.py
- configs/pilots/aspose-3d-foss-python.yaml
- configs/pilots/aspose-slides-foss-python.yaml

### Allowed paths rationale

All paths are directly involved in the fix. The two pilot configs are regenerated to
replace the incomplete system-generated versions.

## Implementation steps

### Step 1: Fix check_dedup Tier 1
Replace `_derive_product_slug` with `_derive_config_filename` in Tier 1 check.

### Step 2: Add _derive_display_name and _derive_canonical_import helpers
`_FAMILY_DISPLAY_MAP` for acronyms (3D, OCR, etc.), `capitalize()` fallback.
`canonical_import` pattern: `{brand}_{family}_foss`.

### Step 3: Update _DEFAULT_TEMPLATE
Remove: `github_ref`, `product_slug`, `budgets`, `telemetry`.
Add: `display_name`, `canonical_import`, `golden`.

### Step 4: Update generate_config()
Populate `display_name` and `canonical_import` from new helpers.
Remove `github_ref` assignment.

### Step 5: Update tests, delete broken configs, regenerate

## Failure modes

### Failure mode 1: canonical_import validation fails for non-Python configs
**Detection**: `ConfigError` during `validate` CLI on a Java config
**Resolution**: `_validate_canonical_import` only runs for Python platform — non-Python
configs are unaffected; canonical_import still populated but not validated
**Gate**: `test_derive_canonical_import_non_python`

### Failure mode 2: check_dedup Tier 1 now needs platform to derive filename
**Detection**: `_derive_config_filename` called with no platform arg — defaults to
`python` which may be wrong for TypeScript repos
**Resolution**: `check_dedup` has no platform arg; `_derive_config_filename` auto-detects
from repo metadata (same as when writing) — same result for same repo
**Gate**: `TestCheckDedupTier1::test_dedup_tier1_by_new_filename`

### Failure mode 3: _DEFAULT_TEMPLATE deep_copy_dict breaks on golden dict
**Detection**: Test `test_template_deep_copy_isolates_telemetry` equivalent for golden
**Resolution**: `_deep_copy_dict` handles nested dicts recursively — golden dict is safe
**Gate**: `TestDefaultTemplateV2Fields::test_has_golden`

## Task-specific review checklist

1. [ ] `check_dedup` Tier 1 uses `_derive_config_filename` not `_derive_product_slug`
2. [ ] `_derive_display_name` returns `Aspose.3D` (not `Aspose.3d`) for 3d family
3. [ ] `_derive_canonical_import` returns `aspose_cells_foss` for cells/python
4. [ ] `_DEFAULT_TEMPLATE` has no `github_ref`, `product_slug`, `budgets`, `telemetry`
5. [ ] `_DEFAULT_TEMPLATE` has `display_name`, `canonical_import`, `golden`
6. [ ] `generate_config()` populates `display_name` and `canonical_import`
7. [ ] Docstrings on all new helper functions
8. [ ] Tests cover Tier 1 dedup with new filename format
9. [ ] Manual configs (`cells`, `note`) NOT overwritten (verified after regeneration)
10. [ ] `validate` CLI passes on all 4 pilot configs
11. [ ] No spec drift — no spec defines exact generator field list

## Deliverables

1. Updated `src/launcher/intake/config_generator.py`
2. Updated `tests/unit/intake/test_config_generator.py`
3. Regenerated `configs/pilots/aspose-3d-foss-python.yaml`
4. Regenerated `configs/pilots/aspose-slides-foss-python.yaml`

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v`
2. [ ] All 4 pilot configs have `display_name`, `canonical_import`, `golden.enabled=true`
3. [ ] `validate` CLI passes on all 4 configs
4. [ ] `aspose-cells-foss-python.yaml` content unchanged (manual values preserved)
5. [ ] No `pilot-` prefixed yaml files in `configs/pilots/`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3870/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v
.venv/Scripts/python.exe -m launcher.cli.main validate configs/pilots/aspose-3d-foss-python.yaml
.venv/Scripts/python.exe -m launcher.cli.main validate configs/pilots/aspose-slides-foss-python.yaml
```

## Integration boundary proven

**Upstream**: `org_scanner` → slim repo dicts
**Downstream**: `configs/pilots/*.yaml` → `RunConfig` model via `validate`/`run` CLI
**Contract**: Generated YAML must parse into valid `RunConfig` with non-empty
`display_name`, `canonical_import`, and `golden.enabled=True`
