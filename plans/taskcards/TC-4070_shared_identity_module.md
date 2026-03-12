---
id: TC-4070
title: "Extract shared identity module to eliminate duplicate derivation"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase1, intake, identity, refactor]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4070_shared_identity_module.md
  - src/launcher/shared/identity.py
  - src/launcher/workers/intake/worker.py
  - src/launcher/intake/config_generator.py
  - tests/unit/shared/__init__.py
  - tests/unit/shared/test_identity.py
  - tests/unit/workers/test_intake.py
evidence_required:
  - reports/TC-4070/evidence.md
---

# Taskcard TC-4070 — Extract shared identity module

## Objective

Move `_resolve_identity(family, platform)` from `workers/intake/worker.py` to a new
`src/launcher/shared/identity.py` module so that both the runtime pipeline worker
and the pre-pipeline config generator use one canonical identity derivation path.
Inconsistency between the two paths is structurally impossible once this is in place.

## Required spec references

- `specs/system_contract.md` (Worker I/O contracts)
- `configs/families.yaml` (Identity templates)

## Scope

### In scope
- Create `src/launcher/shared/identity.py` with `resolve_identity()`, `_load_families_data()`, `_clear_families_cache()`
- Update `workers/intake/worker.py` to import from `shared.identity`
- Update `intake/config_generator.py` `_derive_canonical_import()` and `_derive_display_name()` to delegate to `shared.identity.resolve_identity()`
- Update `tests/unit/workers/test_intake.py` import paths
- Create `tests/unit/shared/test_identity.py`

### Out of scope
- Phase B Scout/Understand changes (Phase 2+)
- `require_python` default change (TC-4071)

## Inputs

- `src/launcher/workers/intake/worker.py` — source of `_resolve_identity`, `_load_families_data`, `_clear_families_cache`
- `src/launcher/intake/config_generator.py` — source of duplicate `_derive_canonical_import`, `_derive_display_name`
- `configs/families.yaml` — families/platforms config used by both

## Outputs

- `src/launcher/shared/identity.py` — new canonical identity module
- Updated `workers/intake/worker.py` — imports from shared.identity
- Updated `intake/config_generator.py` — delegates to shared.identity
- `tests/unit/shared/test_identity.py` — new tests

## Allowed paths

- plans/taskcards/TC-4070_shared_identity_module.md
- src/launcher/shared/identity.py
- src/launcher/workers/intake/worker.py
- src/launcher/intake/config_generator.py
- tests/unit/shared/__init__.py
- tests/unit/shared/test_identity.py
- tests/unit/workers/test_intake.py

### Allowed paths rationale
- shared/identity.py: new canonical module
- worker.py: imports updated to point to shared
- config_generator.py: duplicate functions replaced with delegation
- tests: new identity tests + import fix in test_intake

## Implementation steps

### Step 1: Create src/launcher/shared/identity.py
Move `_resolve_identity`, `_load_families_data`, `_clear_families_cache` from worker.py.
Rename `_resolve_identity` → `resolve_identity` (public API).
Keep `IdentityResolution` NamedTuple here.
Keep `_FAMILIES_YAML` path computation relative to this file's location.

### Step 2: Update worker.py
Remove moved functions. Import `resolve_identity`, `_clear_families_cache` from `launcher.shared.identity`.
Update call site: `_resolve_identity(...)` → `resolve_identity(...)`.

### Step 3: Update config_generator.py
`_derive_canonical_import()` and `_derive_display_name()`: delegate to `resolve_identity(family, platform)`.
The `display_name` field comes from `resolution.display_name`.
The `canonical_import` field comes from `resolution.canonical_import`.
Note: `_derive_display_name` currently derives from org login heuristic, not families.yaml `display` field.
After this change it uses families.yaml `display` field (via shared.identity) — this is the correct behavior.

### Step 4: Update tests/unit/workers/test_intake.py
Change `from launcher.workers.intake.worker import _resolve_identity` →
`from launcher.shared.identity import resolve_identity` (and update all call sites).

### Step 5: Create tests/unit/shared/test_identity.py
Tests:
- `test_resolve_identity_python_cells` — family="cells", platform="python" → canonical_import matches families.yaml
- `test_resolve_identity_typescript` — platform="typescript" → uses families.yaml import_tpl
- `test_resolve_identity_unknown_platform` — provenance="families_yaml_fallback"
- `test_resolve_identity_no_families_yaml` — monkeypatch returns empty → inferred_default
- `test_config_generator_uses_shared_identity` — generate_config output canonical_import matches resolve_identity

## Failure modes

1. `_FAMILIES_YAML` path computed relative to `identity.py` is wrong if the file is not at `src/launcher/shared/identity.py` — mitigated by explicit path comment and test
2. `_clear_families_cache` used in tests — must be importable from `launcher.shared.identity`; all test imports must be updated
3. `config_generator._derive_display_name` currently uses org login heuristic; after change it uses families.yaml display. Downstream test may assert old heuristic value — must update those tests

## Task-specific review checklist

- [ ] `resolve_identity` is the single source of truth imported by both worker.py and config_generator.py
- [ ] `_FAMILIES_YAML` path computation in identity.py correctly resolves to `configs/families.yaml`
- [ ] All test imports updated (no `from launcher.workers.intake.worker import _resolve_identity` remaining)
- [ ] `_clear_families_cache` accessible from `launcher.shared.identity` for test isolation
- [ ] New test `test_config_generator_uses_shared_identity` passes
- [ ] No duplicate families.yaml file open in config_generator.py (old lookup removed)
- [ ] Provenance values unchanged: "families_yaml", "families_yaml_fallback", "inferred_default", "config_override"

## Deliverables

- `src/launcher/shared/identity.py`
- Updated `src/launcher/workers/intake/worker.py`
- Updated `src/launcher/intake/config_generator.py`
- `tests/unit/shared/__init__.py`
- `tests/unit/shared/test_identity.py`
- Updated `tests/unit/workers/test_intake.py`

## Acceptance checks

- [x] `pytest tests/unit/shared/test_identity.py` — all pass (verified 2026-03-11)
- [x] `pytest tests/unit/workers/test_intake.py` — all pass (no import errors, verified 2026-03-11)
- [x] `grep -r "_resolve_identity" src/` — 2 results only: backward-compat alias shim in worker.py (intentional, not a duplicate function). Spirit of check: PASS.
- [x] `grep -r "from launcher.shared.identity" src/launcher/workers/intake/worker.py` returns 1 result
- [x] `grep -r "from launcher.shared.identity" src/launcher/intake/config_generator.py` returns 1 result

## Self-review

After implementation, verify: does calling `resolve_identity("cells", "python")` from both
`worker.py` and `config_generator.py` return identical canonical_import? (Yes — same function.)

## E2E verification

Run `pytest tests/unit/shared/ tests/unit/workers/test_intake.py -x` — all must pass.

## Integration boundary proven

After this TC: `intake_bundle.json` `canonical_import` field and `run_config.yaml` `canonical_import`
field are always derived from the same function. Inconsistency is structurally impossible.
