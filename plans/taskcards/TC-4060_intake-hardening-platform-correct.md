---
id: TC-4060
title: "Intake Hardening — Platform-Correct Acquisition"
status: Done
priority: High
owner: "agent"
updated: "2026-03-11"
tags: [intake, platform, acquisition, hardening]
depends_on: [TC-4057, TC-4058]
allowed_paths:
  - plans/taskcards/TC-4060_intake-hardening-platform-correct.md
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/intake/config_generator.py
  - tests/unit/workers/test_intake.py
  - tests/unit/intake/test_config_generator.py
  - reports/TC-4060/evidence.md
evidence_required:
  - reports/TC-4060/evidence.md
---

# Taskcard TC-4060 — Intake Hardening: Platform-Correct Acquisition

## Objective

Remove Aspose/Python brand assumptions from the Intake worker and config generator,
strengthen the acquisition artifact with confidence + repo signals, and make clone
staleness visible. By the end, the acquisition phase is trustworthy for all platforms.

## Required spec references

- `specs/system_overview.md` (Section: Intake worker responsibilities)
- `specs/worker_understand.md` (Section: Intake→Understand contract)
- `configs/families.yaml` (Platform taxonomy — canonical import templates)

## Scope

### In scope
- `worker.py` code-level identity default (Aspose brand removal)
- `worker.py` Python-shaped canonical_import warning (extend to `families_yaml_fallback`)
- `worker.py` `intake_bundle.json` artifact enrichment (`acquisition_confidence`, `repo_signals`)
- `clone.py` timestamp recording + stale cache logging + `force_refresh` param
- `config_generator.py` `_derive_canonical_import` platform-awareness
- New tests for all above in `test_intake.py` and `test_config_generator.py`

### Out of scope
- `src/launcher/intake/org_scanner.py` — batch onboarding, not runtime path
- `src/launcher/intake/scheduler.py` — out of scope for this taskcard
- RunConfig schema changes — not required
- Understanding worker — covered by TC-4061

## Inputs

- `configs/families.yaml` — platform taxonomy with import templates
- `src/launcher/workers/intake/worker.py` — current identity resolution logic
- `src/launcher/workers/intake/clone.py` — current clone implementation
- `src/launcher/intake/config_generator.py` — batch config generator

## Outputs

- Updated `src/launcher/workers/intake/worker.py`
- Updated `src/launcher/workers/intake/clone.py`
- Updated `src/launcher/intake/config_generator.py`
- Updated `tests/unit/workers/test_intake.py`
- New `tests/unit/intake/test_config_generator.py`
- `reports/TC-4060/evidence.md`

## Allowed paths

- plans/taskcards/TC-4060_intake-hardening-platform-correct.md
- src/launcher/workers/intake/worker.py
- src/launcher/workers/intake/clone.py
- src/launcher/intake/config_generator.py
- tests/unit/workers/test_intake.py
- tests/unit/intake/test_config_generator.py
- reports/TC-4060/evidence.md

### Allowed paths rationale
- `worker.py`: identity defaults + artifact enrichment + warning extension
- `clone.py`: timestamp + stale logging + force_refresh
- `config_generator.py`: _derive_canonical_import platform-awareness
- `test_intake.py`: new tests for above
- `test_config_generator.py`: new file — config_generator unit tests
- `reports/TC-4060/evidence.md`: evidence artifact

## Implementation steps

### Step 1: Fix code-level display_name default in worker.py

Replace line ~204:
```python
display_name = f"Aspose.{family.capitalize()} FOSS for {platform.capitalize()}"
```
With:
```python
display_name = f"{family.capitalize()} for {platform.capitalize()}"
```
Rationale: The code-level default fires when `families.yaml` has no entry. Embedding "Aspose"
in that default is brand-specific and wrong for any non-Aspose product.

### Step 2: Extend Python-shaped canonical_import warning

Current warning at worker.py:61-71 only fires when `provenance["canonical_import"] == "inferred_default"`.
Extend to also fire when provenance is `"families_yaml_fallback"` — both cases mean the import
was not properly derived from the platform entry.

### Step 3: Add acquisition_confidence field to artifact

In `_resolve_identity`, compute `acquisition_confidence` from provenance:
- `"high"` — all 3 fields have `"families_yaml"` provenance
- `"medium"` — any field has `"families_yaml_fallback"` provenance
- `"low"` — any field has `"inferred_default"` provenance

Write it into the artifact dict in `worker.py`.

### Step 4: Add repo_signals to artifact

After clone, perform a quick file scan in worker.py:
```python
repo_signals = _build_repo_signals(repo_dir)
```
Where `_build_repo_signals` checks:
- `readme_present`: bool — any README.md/README.rst/README exists at root
- `is_empty_clone`: bool — no files at all in repo_dir
- `files_estimated`: int — count of top-level files (non-recursive, cap at 100 to stay fast)

Write `repo_signals` dict into the artifact.

### Step 5: Write .clone_timestamp in clone.py

After writing `.clone_sha`, write `.clone_timestamp`:
```python
from datetime import datetime, timezone
ts_marker = cache_dir / ".clone_timestamp"
ts_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
```

### Step 6: Log cache age on hit path

When returning a cache hit, read `.clone_timestamp` if it exists and compute days since clone:
```python
age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).days
if age_days > 7:
    logger.warning("[Clone] Cache for %s is %d days old — consider force_refresh=True", repo_url, age_days)
else:
    logger.info("[Clone] Cache hit age=%d days for %s", age_days, repo_url)
```

### Step 7: Add force_refresh to clone_repo_cached

Add `force_refresh: bool = False` parameter. When True, bypass SHA equality check and proceed
to re-clone regardless of cache state:
```python
if force_refresh and cache_dir.exists():
    shutil.rmtree(cache_dir, ignore_errors=True)
    # then proceed to fresh clone
```

### Step 8: Fix config_generator._derive_canonical_import

Current: always returns `{brand}_{family}_foss` (Python pip-name convention)
Fix: attempt to load families.yaml and use `import_tpl` for the detected platform:
```python
def _derive_canonical_import(repo: dict, families_yaml_path: Path | None = None) -> str:
    platform = _extract_platform(repo)
    family = _extract_family(repo)
    # Try families.yaml first
    if families_yaml_path and families_yaml_path.exists():
        data = yaml.safe_load(families_yaml_path.read_text())
        platform_info = data.get("platforms", {}).get(platform, {})
        if platform_info:
            tpl = platform_info.get("import_tpl", "")
            if tpl:
                return tpl.format(family=family, Family=family.capitalize())
    # Fallback: platform-neutral (no _foss suffix assumption)
    brand = ... # existing logic
    if platform == "python":
        return f"{brand}_{family}_foss"
    return f"{brand}_{family}"
```

## Failure modes

### Failure mode 1: families.yaml not found at runtime (wrong CWD)

**Detection**: `_resolve_identity` returns `inferred_default` provenance for all fields even when
families.yaml clearly exists. Verify: check `_FAMILIES_YAML.exists()` manually.
**Resolution**: `_FAMILIES_YAML` uses `Path("configs/families.yaml")` — CWD-relative. If CWD is not
repo root at runtime, path fails. Fix: use `Path(__file__).resolve().parents[N] / "configs/families.yaml"`.
**Gate**: Intake self-review `acquisition_confidence` will be `"low"` when this fails.

### Failure mode 2: repo_dir stat fails on empty clone

**Detection**: `_build_repo_signals` raises OSError when repo_dir is not readable.
**Resolution**: Wrap in try/except; return `{"readme_present": False, "is_empty_clone": True, "files_estimated": 0}` on error.
**Gate**: Intake self-review checks `repo_dir` exists and is non-empty; will catch truly broken clones.

### Failure mode 3: config_generator families.yaml lookup fails

**Detection**: `_derive_canonical_import` falls back to Python-default even for non-Python repos.
**Resolution**: families_yaml_path defaults to `Path("configs/families.yaml")` relative to CWD.
If that fails, the Python-default fallback is still better than crashing. Log at WARNING.
**Gate**: New test `test_derive_canonical_import_typescript` will catch regression.

### Failure mode 4: .clone_timestamp read fails on stale marker

**Detection**: `datetime.fromisoformat(ts)` raises ValueError on malformed timestamp.
**Resolution**: Wrap in try/except; skip age logging silently (non-critical).
**Gate**: `test_stale_cache_logged` verifies the happy path; ValueError branch covered by negative test.

## Task-specific review checklist

1. [x] `display_name` default no longer contains "Aspose" string for unknown products
2. [x] Warning fires on BOTH `inferred_default` AND `families_yaml_fallback` provenance
3. [x] `intake_bundle.json` contains `acquisition_confidence` with one of: high/medium/low
4. [x] `intake_bundle.json` contains `repo_signals` with readme_present, is_empty_clone, files_estimated
5. [x] `.clone_timestamp` written alongside `.clone_sha` after fresh clone
6. [x] Cache age logged on hit path (INFO when fresh, WARNING when >7 days)
7. [x] `force_refresh=True` bypasses cache even on SHA match
8. [x] TypeScript repo gets non-Python canonical_import from config_generator
9. [x] All new tests pass under `PYTHONHASHSEED=0`
10. [x] No existing test broken
11. [x] Docstrings updated for all new/changed public functions
12. [x] Spec file confirmed — no spec drift from this change
13. [x] Schema `"description"` fields present for all new model fields (N/A — no new model fields)
14. [x] Checked docs/README.md ownership map — no trigger event applies

## Deliverables

1. `src/launcher/workers/intake/worker.py` — updated identity defaults + artifact + warnings
2. `src/launcher/workers/intake/clone.py` — timestamp + stale logging + force_refresh
3. `src/launcher/intake/config_generator.py` — platform-aware canonical_import
4. `tests/unit/workers/test_intake.py` — 6 new tests
5. `tests/unit/intake/test_config_generator.py` — new file with 3 tests
6. `reports/TC-4060/evidence.md` — test output + artifact inspection

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v` — all pass
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/intake/ -v` — all pass
3. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 3711 pass, pre-existing TestDeployIntegration failures excluded (asyncio isolation, predates TC-4060)
4. [x] `intake_bundle.json` artifact shape verified in evidence.md
5. [x] TypeScript fixture: `_derive_canonical_import` returns no `_foss` suffix for non-Python
6. [x] Empty fixture: `is_empty_clone: true` in `_build_repo_signals` (test: `test_empty_dir_signals`)

## Self-review

### Verification results
- [x] Tests: 143/143 PASS (targeted) + 3711 PASS (regression suite)
- [x] Validation: self_review structure verified — all helpers return correct shapes
- [x] Evidence captured: reports/TC-4060/evidence.md
- [x] Doc freshness: confirmed no spec drift

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py tests/unit/intake/ -v --tb=short
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

**Expected results**:
- All test_intake.py tests pass (existing + 6 new)
- All test_config_generator.py tests pass (3 new)
- Full suite: no regressions

## Integration boundary proven

**Upstream**: `RunConfig` (family, platform, repo_url, launch_tier from pilot config)
**Downstream**: `IntakeBundle` → `UnderstandWorker` receives platform-correct identity
**Contract**: `IntakeBundle.canonical_import` is platform-correct; `IntakeBundle.repo_dir` points to non-empty clone
