---
id: TC-4216
title: "Readable cache folder naming + org allowlist enforcement"
status: Done
priority: Normal
owner: "orchestrator"
updated: "2026-03-12"
tags: [intake, clone, cache, security]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4216_readable-cache-names.md
  - src/launcher/workers/intake/clone.py
  - src/launcher/workers/intake/worker.py
  - tests/unit/workers/test_clone.py
  - tools/migrate_cache_to_readable_names.py
  - reports/agents/B/TC-4216/evidence.md
evidence_required:
  - reports/agents/B/TC-4216/evidence.md
---

# Taskcard TC-4216 — Readable cache folder naming + org allowlist enforcement

## Objective

Replace the SHA-256-based clone cache folder naming (e.g. `71874a68ac78/`) with a human-readable
scheme (`{brand}_{family}_{platform}`, e.g. `aspose_cells_python`) and enforce that only repositories
from allowed Aspose-FOSS organizations (defined in `intake_config.yaml`) can be cloned.

## Required spec references

- `specs/system_contract.md` (Section: Intake worker contract — repo acquisition)
- `configs/intake_config.yaml` (Source of truth for allowed organizations)

## Scope

### In scope
- `clone.py`: new `_normalize_slug`, `_extract_brand_from_url` helpers; new `_get_cache_dir` signature; `.clone_url` marker; `allowed_org_prefixes` param
- `worker.py`: pass `family`, `platform`, `allowed_org_prefixes` to `clone_repo_cached()`
- `test_clone.py`: update all existing tests; add 8 new test cases
- `tools/migrate_cache_to_readable_names.py`: migration script (unprotected path)

### Out of scope
- Changes to `intake_config.yaml` schema (org names already encode the allowlist)
- Changes to `org_scanner.py` or `repo_classifier.py` (already FOSS-only by config)
- Changes to `run_config.py` models (no new fields needed)
- Actual deletion of hash folders (migration script only — human executes)

## Inputs

- `src/launcher/workers/intake/clone.py` (current SHA-256 implementation)
- `src/launcher/workers/intake/worker.py` (current clone call site)
- `configs/intake_config.yaml` (25 aspose-*-foss org names)
- `src/launcher/intake/config_loader.py` (provides `load_intake_config()`)

## Outputs

- Updated `clone.py` with readable slug naming and allowlist enforcement
- Updated `worker.py` passing family/platform/allowlist to clone
- Updated `test_clone.py` with all tests passing
- `tools/migrate_cache_to_readable_names.py` migration script

## Allowed paths

- plans/taskcards/TC-4216_readable-cache-names.md
- src/launcher/workers/intake/clone.py
- src/launcher/workers/intake/worker.py
- tests/unit/workers/test_clone.py
- tools/migrate_cache_to_readable_names.py
- reports/agents/B/TC-4216/evidence.md

### Allowed paths rationale

- `clone.py`: primary change — hash naming → readable slug + allowlist
- `worker.py`: caller update — passes family/platform to clone
- `test_clone.py`: test coverage for new API
- `tools/migrate_cache_to_readable_names.py`: unprotected path; migration helper

## Implementation steps

### Step 1: Add helpers to clone.py

Add at module level (after imports):
- `_SLUG_STOP_WORDS = frozenset({"foss", "for", "the", "a", "ai", "org", "net"})`
- `_CLONE_URL_MARKER = ".clone_url"`
- `_normalize_slug(s: str) -> str` — lowercase + non-alnum → `_`, strip underscores
- `_extract_brand_from_url(repo_url: str) -> str` — parse GitHub org, filter stop words, return first segment

### Step 2: Replace _get_cache_dir in clone.py

Old: `_get_cache_dir(repo_url: str, work_dir: Path) -> Path`
New: `_get_cache_dir(brand: str, family: str, platform: str, work_dir: Path) -> Path`

Slug = `{_normalize_slug(brand)}_{_normalize_slug(family)}_{_normalize_slug(platform)}`
Cache root unchanged: `work_dir.parent.parent / ".clone_cache"`
Remove `hashlib` import.

### Step 3: Add .clone_url marker + collision detection in clone_repo_cached

After writing `.clone_sha` marker, also write `.clone_url` with the repo_url.
Before returning on cache hit: check `.clone_url` marker; if URL mismatches → raise RuntimeError.

### Step 4: Update clone_repo_cached signature

```python
def clone_repo_cached(
    repo_url: str,
    *,
    family: str,
    platform: str,
    brand: str | None = None,
    work_dir: Path | None = None,
    force_refresh: bool = False,
    allowed_org_prefixes: list[str] | None = None,
) -> tuple[Path, str, bool]:
```

At top of body: allowlist check if `allowed_org_prefixes` is not None.
Derive `_brand = brand or _extract_brand_from_url(repo_url)`.
Pass `_brand, family, platform, work_dir` to `_get_cache_dir`.

### Step 5: Update IntakeWorker.run() in worker.py

Add module-level helper (with lru_cache):
```python
@functools.lru_cache(maxsize=1)
def _load_allowed_org_prefixes() -> tuple[str, ...]:
    ...load from intake_config.yaml, return tuple of https://github.com/{org}/ prefixes...
```

Update clone call to pass `family=config.family`, `platform=config.platform`,
`allowed_org_prefixes=_load_allowed_org_prefixes() or None`.

### Step 6: Update test_clone.py

- Update `TestGetCacheDir` — new signature `(brand, family, platform, work_dir)`, verify slug
- Update `TestCloneRepoCached` — add `family="cells"`, `platform="python"` to all calls
- Update `TestCacheIntegrityCheck` — same
- Add `TestNormalizeSlug` — 4 cases (basic, hyphen, "3d", empty)
- Add `TestExtractBrandFromUrl` — 3 cases (aspose-cells-foss, aspose-3d-foss, bad URL)
- Add `TestOrgAllowlist` — allowed URL passes, blocked URL raises ValueError
- Add `TestCloneUrlMarker` — marker written on fresh clone, collision raises RuntimeError
- Add `TestReadableSlugNames` — verify folder name is `aspose_cells_python`

### Step 7: Write tools/migrate_cache_to_readable_names.py

Script that:
1. Scans `runs/.clone_cache/` for all folders
2. Identifies hash folders (12-char hex) vs readable names
3. For each hash folder: runs `git remote get-url origin` to get URL
4. Derives new readable name using `_extract_brand_from_url` + `_normalize_slug`
5. With `--dry-run`: prints mapping without changes
6. Without `--dry-run`: prompts for confirmation, renames FOSS folders, reports non-FOSS

## Failure modes

### Failure mode 1: Collision — two URLs map to same slug

**Detection**: RuntimeError "[Clone] Cache collision: slug ... was cloned from X but now requested for Y"
**Resolution**: Investigate why two different repo URLs produce the same brand/family/platform. Check if one is commercial (should be excluded by allowlist). Fix org config or add brand suffix.
**Gate**: `allowed_org_prefixes` check prevents non-FOSS URLs from reaching clone; collision can only occur with two FOSS repos for same family/platform.

### Failure mode 2: Allowlist blocks a legitimate repo

**Detection**: ValueError "[Clone] repo_url ... is not in the allowed org list"
**Resolution**: Add the org name to `configs/intake_config.yaml` organizations list. `_load_allowed_org_prefixes()` is lru_cached — restart pipeline to pick up new config.
**Gate**: `allowed_org_prefixes` parameter; `None` disables check (test mode).

### Failure mode 3: Brand extraction returns "unknown" for unexpected org name

**Detection**: Cache folder named `unknown_{family}_{platform}` appears.
**Resolution**: Verify repo URL org follows `{brand}-{family}-foss` pattern. Update `_SLUG_STOP_WORDS` if a new stop word causes the brand segment to be filtered.
**Gate**: Unit test `TestExtractBrandFromUrl` catches regressions.

### Failure mode 4: Migration script renames a folder that is currently in use by another run

**Detection**: `git rev-parse HEAD` fails in renamed folder (path changed while another process holds it).
**Resolution**: Stop all pipeline runs before executing migration. The script uses `--dry-run` by default.
**Gate**: Migration script prompts for confirmation before making changes.

## Task-specific review checklist

1. [ ] `_get_cache_dir("aspose", "cells", "python", tmp)` returns path ending in `aspose_cells_python`
2. [ ] `_normalize_slug("aspose-3D")` returns `"aspose_3d"`
3. [ ] `_extract_brand_from_url("https://github.com/aspose-cells-foss/repo")` returns `"aspose"`
4. [ ] `clone_repo_cached(url, family="x", platform="y", allowed_org_prefixes=["https://github.com/other/"])` raises `ValueError`
5. [ ] `.clone_url` marker written after fresh clone
6. [ ] Collision (mismatched `.clone_url`) raises `RuntimeError` before returning cache hit
7. [ ] Docstrings updated for all changed public functions in clone.py
8. [ ] Spec file: no worker behavior change requiring spec update (clone is acquisition infra)
9. [ ] Schema `"description"` fields: no schema changes made
10. [ ] `docs/README.md` checked — no trigger event applies (intake infra change)
11. [ ] `test_intake.py` still passes after worker.py change

## Deliverables

1. Updated `src/launcher/workers/intake/clone.py`
2. Updated `src/launcher/workers/intake/worker.py`
3. Updated `tests/unit/workers/test_clone.py`
4. New `tools/migrate_cache_to_readable_names.py`
5. Evidence bundle at `reports/agents/B/TC-4216/evidence.md`

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_clone.py -v` — 45/45 PASS (was 14 before; 31 new tests)
2. [x] `pytest tests/unit/workers/test_intake.py -v` — 81/81 PASS, no regression
3. [x] `pytest -x -q` — 4121 passed, 1 skipped, 3 xfailed, 0 failures
4. [x] Cache folder `runs/.clone_cache/aspose_cells_python/` confirmed after `fl run --stop-after intake` (2026-03-12)
5. [x] Cloning a non-allowed URL raises `ValueError` (covered by TestOrgAllowlist)

## Self-review

### Verification results
- [x] Tests: 45/45 test_clone.py PASS | 81/81 test_intake.py PASS | 4121/4121 full suite PASS
- [x] Evidence captured: reports/agents/B/TC-4216/evidence.md
- [x] Doc freshness: no spec drift (clone is acquisition infra; no worker contract change)
- [x] Self-review score: 12x 5/5, 1x 4/5 (observability) — APPROVED 2026-03-12

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_clone.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_intake.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q 2>&1 | tail -5
python tools/migrate_cache_to_readable_names.py --dry-run
```

**Expected results**:
- All test_clone.py tests PASS (≥ 22 tests including 8 new)
- All test_intake.py tests PASS
- Full suite: 0 failures
- Migration dry-run prints 8 folders with rename/delete decisions

## Integration boundary proven

**Upstream**: `RunConfig.repo_url` + `RunConfig.family` + `RunConfig.platform` provided by pipeline orchestrator
**Downstream**: `IntakeBundle.repo_dir` (readable path) consumed by Scout and Understand workers
**Contract**: `clone_repo_cached()` returns `(Path, str, bool)` — contract unchanged; only cache location differs
