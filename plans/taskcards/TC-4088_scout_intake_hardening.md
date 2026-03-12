---
id: TC-4088
title: "Scout/Intake hardening: README sanitization, clone cache integrity, families.yaml fail-loud, tomllib fallback warning"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase5, scout, intake, security, reliability]
depends_on: [TC-4087]
allowed_paths:
  - plans/taskcards/TC-4088_scout_intake_hardening.md
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/shared/identity.py
  - tests/unit/workers/test_scout.py
  - tests/unit/workers/test_clone.py
  - tests/unit/workers/test_intake.py
  - reports/TC-4088/evidence.md
evidence_required:
  - reports/TC-4088/evidence.md
---

# Taskcard TC-4088 — Scout/Intake: README sanitization, clone cache integrity, families.yaml fail-loud, tomllib fallback warning

## Objective

Fix four confirmed root-cause defects in the Scout and Intake phases that allow secrets to leak, silently corrupt cache hits, drop manifest data without warning, and hide configuration errors.

## Required spec references

- `specs/worker_understand.md` (Scout phase A contract)
- `specs/github_intake.md` (Intake contract)
- `configs/families.yaml` (identity derivation source)

## Scope

### In scope
- P1-A: Make `readme_summary` use the sanitized README from `_read_repo_content`, not a second unsanitized read
- P1-B: Add content integrity check to `clone_repo_cached()` before returning cached dir
- P1-C: Add WARNING log when `families.yaml` is missing or fails to parse
- P1-D: Upgrade `tomllib` fallback log from `debug` to `warning`; attempt regex for description/python_requires

### Out of scope
- P1-E (importance ranking stems) — already has size secondary sort; deferring stem expansion
- P1-F (require_language) — already implemented in classifier
- Clone retry logic — separate concern, not root-cause of current failures

## Inputs

- `src/launcher/workers/scout/scout.py` — `run_scout()`, `_read_readme()`, `_read_repo_content()`, `_parse_pyproject()`
- `src/launcher/workers/intake/clone.py` — `clone_repo_cached()`
- `src/launcher/shared/identity.py` — `_load_families_data()`

## Outputs

- Fixed `src/launcher/workers/scout/scout.py`
- Fixed `src/launcher/workers/intake/clone.py`
- Fixed `src/launcher/shared/identity.py`
- New/updated tests in `tests/unit/workers/test_scout.py`, `test_clone.py`
- `reports/TC-4088/evidence.md`

## Allowed paths

- plans/taskcards/TC-4088_scout_intake_hardening.md
- src/launcher/workers/scout/scout.py
- src/launcher/workers/intake/clone.py
- src/launcher/shared/identity.py
- tests/unit/workers/test_scout.py
- tests/unit/workers/test_clone.py
- tests/unit/workers/test_intake.py
- reports/TC-4088/evidence.md

### Allowed paths rationale
All fixes are in Scout, Clone, and Identity modules. Tests are in the corresponding test files.

## Implementation steps

### Step 1: Fix P1-A — README double-read sanitization

**File**: `src/launcher/workers/scout/scout.py`

**Root cause**: `run_scout()` calls `_read_readme(repo_dir)` at line 73 BEFORE calling `_read_repo_content()`. The `_read_readme()` function does a plain `read_text()` with no sanitization. The `readme_summary` in `RepoInfo` therefore contains the unsanitized README.

**Fix**:
1. Remove the call to `_read_readme()` at line 73.
2. After `_read_repo_content()` returns, extract the README key from `repo_content` dict:
   ```python
   # Extract sanitized README from repo_content (already sanitized by _read_repo_content)
   readme_summary = ""
   for readme_name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
       for key in repo_content:
           if key.lower() == readme_name.lower():
               readme_summary = repo_content[key][:4000]
               break
       if readme_summary:
           break
   ```
3. Pass `readme_summary` to `RepoInfo(readme_summary=readme_summary, ...)`.
4. Do NOT remove `_read_readme()` function itself (tests may use it directly), but annotate it with a deprecation note.

**Verification**: After fix, `repo_info.readme_summary` will always be a substring of the sanitized `repo_content[readme_key]`.

### Step 2: Fix P1-B — Clone cache content integrity check

**File**: `src/launcher/workers/intake/clone.py`

**Root cause**: At lines 160-165, when the cache SHA matches, the code immediately returns `(cache_dir, remote_sha, False)` without verifying `cache_dir` actually contains files.

**Fix**: After the cache hit log message and before the return statement, add:
```python
# Integrity check: ensure cache_dir is non-empty (not deleted/corrupted)
_cache_files = list(cache_dir.iterdir()) if cache_dir.exists() else []
if not _cache_files:
    logger.warning(
        "[Clone] Cache dir %s is empty or missing — forcing fresh clone for %s",
        cache_dir, repo_url,
    )
    shutil.rmtree(cache_dir, ignore_errors=True)
    # Fall through to re-clone below
else:
    _log_cache_age(cache_dir, repo_url)
    return cache_dir, remote_sha, False
```

Apply the same pattern to the fallback case (lines 167-181) where `remote_sha is None` and we use the existing cache. Also add a git sanity check if `.git` marker is accessible.

### Step 3: Fix P1-C — families.yaml fail-loud

**File**: `src/launcher/shared/identity.py`

**Root cause**: `_load_families_data()` at line 47 silently returns `{}` when families.yaml doesn't exist, and at line 52 uses `logger.warning()` only on parse failure. Missing file is silently swallowed.

**Fix**:
```python
if not _FAMILIES_YAML.exists():
    logger.warning(
        "[Identity] families.yaml not found at %s — identity derivation will use code defaults. "
        "All canonical_import/display_name values will be inferred, not authoritative.",
        _FAMILIES_YAML,
    )
    _families_cache = {}
    return _families_cache
```
This makes the missing-file case visible in logs without breaking the pipeline (it's a WARNING, not an ERROR — the fallback is still valid for development environments).

### Step 4: Fix P1-D — tomllib fallback upgrade to WARNING

**File**: `src/launcher/workers/scout/scout.py`, `_parse_pyproject()`

**Root cause**: Line 625 uses `logger.debug()` for the tomllib parse failure. Operators don't see it.

**Fix**:
1. Change `logger.debug(...)` to `logger.warning(...)` with a message that names the file and the exception.
2. In the fallback return, attempt `_toml_value()` extraction for description too (it's a simple regex):
   ```python
   except Exception as exc:
       logger.warning(
           "[Scout] pyproject.toml tomllib parse failed for %s (%s) — "
           "falling back to regex; description/python_requires/dependencies/entrypoints will be empty",
           path, exc,
       )
       try:
           content = path.read_text(encoding="utf-8", errors="replace")
       except Exception:
           return "", "", "", "", "", [], []
       return (
           _toml_value(content, "name"),
           _toml_value(content, "version"),
           _toml_value(content, "license"),
           _toml_value(content, "description"),  # attempt regex extraction
           "",  # python_requires — not regex-extractable reliably
           [],  # dependencies
           [],  # entrypoints
       )
   ```

## Failure modes

### Failure mode 1: README not found in repo_content

**Detection**: `readme_summary` is `""` even though README.md exists on disk.
**Resolution**: Check `_read_repo_content()` — README should always be read first (lines 262-299). If budget_log shows README was skipped, it means budget was 0 (extremely unlikely). Add assertion in test.
**Gate**: Scout self-review check: empty readme_summary for repos with README.

### Failure mode 2: Cache integrity check breaks valid cache

**Detection**: Test with a valid non-empty cache shows unexpected re-clone.
**Resolution**: The check uses `cache_dir.iterdir()` — any file (including .clone_sha) satisfies non-empty. Only truly empty or non-existent dirs trigger re-clone. This is correct behavior.
**Gate**: Test `test_clone_cache_hit_reuses_valid_cache` must still pass.

### Failure mode 3: tomllib fallback misses regex-extractable fields

**Detection**: After fix, test with a malformed TOML that has a valid `[project] description = "..."` line; assert description is extracted.
**Resolution**: `_toml_value(content, "description")` uses the same regex as name/version; should work if TOML line format is simple.
**Gate**: Unit test for malformed TOML fallback.

## Task-specific review checklist

1. [ ] `repo_info.readme_summary` never contains unsanitized content (assert via test with planted secret)
2. [ ] Clone cache returns fresh clone on empty cache dir (test explicitly)
3. [ ] Clone cache reuse still works for valid non-empty cache (regression test passes)
4. [ ] families.yaml missing logs `WARNING` (assert in test)
5. [ ] tomllib parse failure logs `WARNING` (assert in test; was previously `debug` — invisible)
6. [ ] No existing test regressions from these changes
7. [ ] Docstrings updated for changed public functions
8. [ ] Spec file confirmed: no spec drift (changes tighten existing behavior)
9. [ ] Schema description fields: N/A (no schema changes)
10. [ ] docs/README.md ownership map: N/A (no new public APIs)
11. [ ] If new docs/guides/ file added: N/A

## Deliverables

1. Fixed `src/launcher/workers/scout/scout.py`
2. Fixed `src/launcher/workers/intake/clone.py`
3. Fixed `src/launcher/shared/identity.py`
4. New/updated tests covering each fix
5. `reports/TC-4088/evidence.md` with test output

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass
2. [ ] `repo_info.readme_summary` in test does not contain planted secret (P1-A)
3. [ ] Empty cache dir triggers re-clone in test (P1-B)
4. [ ] Missing families.yaml emits WARNING in test (P1-C)
5. [ ] Malformed pyproject.toml emits WARNING in test (P1-D)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: scout self-review PASS
- [ ] Evidence captured: reports/TC-4088/evidence.md
- [ ] Doc freshness: run `python scripts/check_doc_freshness.py --uncommitted`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py tests/unit/workers/test_clone.py tests/unit/workers/test_intake.py -v
```

**Expected results**:
- All existing tests pass
- New tests for P1-A/B/C/D pass
- No secrets in readme_summary
- Cache integrity test passes

## Integration boundary proven

**Upstream**: RunConfig / repo URL → Intake
**Downstream**: Scout produces `RepoInfo` → Understand worker
**Contract**: `RepoInfo.readme_summary` is always sanitized content (≤4000 chars); `clone_repo_cached` returns a non-empty directory
