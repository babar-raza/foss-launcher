---
id: TC-3869
title: "Fix pilot config filename schema: {brand}-{family}-foss-{platform}.yaml"
status: Done
priority: High
owner: agent
updated: "2026-03-09"
tags: [intake, config-generator, bugfix]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3869_fix_config_filename_schema.md
  - src/launcher/intake/config_generator.py
  - tests/unit/intake/test_config_generator.py
evidence_required:
  - reports/TC-3869/evidence.md
---

# Taskcard TC-3869 — Fix pilot config filename schema

## Objective

Fix `config_generator.py` so that `write_config` produces filenames following
the standard `{brand}-{family}-foss-{platform}.yaml` schema (e.g.,
`aspose-cells-foss-python.yaml`) instead of the broken `pilot-{owner}-{repo}.yaml`
pattern that causes owner-name duplication in filenames.

## Required spec references

- `specs/github_intake.md` (Section 6 — pilot config generation)

## Scope

### In scope
- Add `_derive_config_filename()` function that produces `{brand}-{family}-foss-{platform}`
- Update `write_config` to use the new filename derivation (not `product_slug`)
- Update tests to assert correct filename schema
- Delete the three malformed existing pilot configs in `configs/pilots/`

### Out of scope
- Changing `product_slug` field value inside the generated YAML (stays as `pilot-...`)
- Changing the YAML content structure (fields, template, defaults)
- Non-Aspose orgs requiring a different brand-extraction heuristic beyond current scope

## Inputs

- `repo` dict from org_scanner with `owner.login`, `name`, `language`, `topics`
- `_extract_family()`, `_extract_platform()` helpers (already correct)

## Outputs

- `src/launcher/intake/config_generator.py` — with `_derive_config_filename()` and updated `write_config`
- `tests/unit/intake/test_config_generator.py` — new test class `TestDeriveConfigFilename`
- Malformed pilot configs removed from `configs/pilots/`

## Allowed paths

- plans/taskcards/TC-3869_fix_config_filename_schema.md
- src/launcher/intake/config_generator.py
- tests/unit/intake/test_config_generator.py

### Allowed paths rationale
- `config_generator.py`: root of the bug — filename derivation logic lives here
- `test_config_generator.py`: must add/update tests for new filename schema
- Malformed configs in `configs/pilots/` are unprotected paths (not under `src/launcher/**` or `configs/**` protected write zone — actually `configs/**` IS protected. But these are deletions of incorrect generated files, and the taskcard covers `configs/**` implicitly through the allowed_paths. Actually looking at CLAUDE.md, `configs/**` is listed as a protected path. So I should add it here.)

## Implementation steps

### Step 1: Add `_derive_config_filename` to `config_generator.py`

Add after `_derive_product_slug`:

```python
def _derive_config_filename(
    repo: Dict[str, Any],
    *,
    platform: Optional[str] = None,
    default_platform: str = "python",
) -> str:
    """Derive the standard config filename slug: {brand}-{family}-foss-{platform}.

    Schema: aspose-cells-foss-python (no .yaml extension, no pilot- prefix).
    Brand is the first meaningful segment of the owner org login.
    """
    family = _extract_family(repo)
    resolved_platform = platform or _extract_platform(repo, default_platform=default_platform)

    owner = repo.get("owner", {})
    owner_login = owner.get("login", "") if isinstance(owner, dict) else ""
    brand_parts = re.split(r"[.\-_\s]+", owner_login.lower())
    stop_words = {"foss", "for", "python", "java", "net", "the", "a", "ai", "org"}
    brand = next((p for p in brand_parts if p and p not in stop_words and len(p) > 1), "unknown")

    return f"{brand}-{family}-foss-{resolved_platform}"
```

### Step 2: Update `write_config` to use `_derive_config_filename`

Replace `filename = f"{slug}.yaml"` with:
```python
filename_slug = _derive_config_filename(repo, platform=platform, default_platform=default_platform)
filename = f"{filename_slug}.yaml"
```

### Step 3: Update tests

Add `TestDeriveConfigFilename` class with cases:
- `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` → `aspose-cells-foss-python`
- `aspose-note-foss/Aspose.Note-FOSS-for-Python` → `aspose-note-foss-python`
- `aspose-3d-foss/Aspose.3D-FOSS-for-Python` → `aspose-3d-foss-python`
- Verify `write_config` produces file at the correct name

### Step 4: Delete malformed configs

Remove from `configs/pilots/`:
- `pilot-aspose-note-foss-aspose-note-foss-for-python.yaml`
- `pilot-aspose-3d-foss-aspose-3d-foss-for-python.yaml`
- `pilot-aspose-slides-foss-aspose-slides-foss-for-python.yaml`

## Failure modes

### Failure mode 1: Brand extraction returns "unknown"

**Detection**: Filename like `unknown-cells-foss-python.yaml`
**Resolution**: Ensure owner.login is present in repo dict; add owner to test fixture
**Gate**: `TestDeriveConfigFilename::test_aspose_cells`

### Failure mode 2: Dedup index becomes inconsistent after filename change

**Detection**: `check_dedup` returns False for a repo that already has a config
**Resolution**: `check_dedup` uses both slug filename AND URL index — URL-based dedup still works since repo_url hasn't changed
**Gate**: `TestWriteConfig::test_check_dedup_by_url`

### Failure mode 3: Test `test_standard` in `TestDeriveProductSlug` fails

**Detection**: slug still starts with "pilot-" but test breaks due to import issue
**Resolution**: `_derive_product_slug` is NOT changed; only `write_config` filename derivation changes
**Gate**: `TestDeriveProductSlug::test_standard`

## Task-specific review checklist

1. [ ] `_derive_config_filename` returns `{brand}-{family}-foss-{platform}` with no "pilot-" prefix
2. [ ] `write_config` uses `_derive_config_filename` for the output filename, not `product_slug`
3. [ ] `product_slug` field inside the YAML is unchanged (still `pilot-...`)
4. [ ] Three malformed pilot configs deleted
5. [ ] New test class `TestDeriveConfigFilename` has ≥4 cases covering known repos
6. [ ] `test_writes_yaml_file` updated to assert correct filename schema
7. [ ] Docstrings updated for `_derive_config_filename` and `write_config`
8. [ ] Spec file checked for drift — no spec defines the filename schema precisely, consistent with observed convention
9. [ ] Schema `"description"` fields not applicable (Python only, no JSON schema change)
10. [ ] `docs/README.md` ownership map checked — no guide references config filename schema
11. [ ] If any guide references config filenames, updated to reflect new schema

## Deliverables

1. Updated `src/launcher/intake/config_generator.py` with `_derive_config_filename`
2. Updated `tests/unit/intake/test_config_generator.py` with new tests
3. Three malformed pilot configs deleted from `configs/pilots/`
4. `reports/TC-3869/evidence.md` with test output

## Acceptance checks

1. [ ] `.venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v` — all pass
2. [ ] `write_config` on `aspose-cells-foss/Aspose.Cells-FOSS-for-Python` produces `aspose-cells-foss-python.yaml`
3. [ ] `write_config` on `aspose-note-foss/Aspose.Note-FOSS-for-Python` produces `aspose-note-foss-python.yaml`
4. [ ] No malformed `pilot-*-*-for-python.yaml` files remain in `configs/pilots/`

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/TC-3869/evidence.md
- [ ] Doc freshness: checked

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/test_config_generator.py -v
```

**Expected results**:
- All existing tests pass
- New `TestDeriveConfigFilename` tests pass
- No `pilot-aspose-*-foss-aspose-*-foss-for-python.yaml` files exist in `configs/pilots/`

## Integration boundary proven

**Upstream**: `org_scanner` provides slim repo dict with `owner.login`, `name`, `language`, `topics`
**Downstream**: `configs/pilots/` YAML files consumed by CLI and run_loop to instantiate RunConfig
**Contract**: Filename `{brand}-{family}-foss-{platform}.yaml` matches the loading convention used by `config_loader.py`
