---
id: TC-3902
title: "Use existing clone cache when ls-remote fails (network error resilience)"
status: In-Progress
priority: High
owner: agent
updated: "2026-03-09"
tags: [intake, clone, resilience]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3902_clone_cache_network_fallback.md
  - src/launcher/workers/intake/clone.py
evidence_required: []
---

# Taskcard TC-3902 — Use existing clone cache when ls-remote fails

## Objective

When `git ls-remote` fails (exit code 128 — network error, GitHub rate limit, etc.),
`clone_repo_cached` deletes the existing cached clone and tries to re-clone — which
also fails, crashing the intake worker. Fix: if `ls-remote` fails but a valid
cached clone exists, use it rather than deleting it.

## Required spec references

- `src/launcher/workers/intake/clone.py`

## Scope

### In scope
- Add a fallback path in `clone_repo_cached`: when `remote_sha == ""` and cache
  exists with a marker, return the cached clone

### Out of scope
- Changing `check_remote_sha` behavior
- Any other worker changes

## Inputs

- `src/launcher/workers/intake/clone.py` — `clone_repo_cached` function

## Outputs

- Updated `clone.py` with network-failure fallback

## Allowed paths

- plans/taskcards/TC-3902_clone_cache_network_fallback.md
- src/launcher/workers/intake/clone.py

## Implementation steps

### Step 1: Add fallback before the cache deletion block

After the remote SHA cache-hit check, add:
```python
# If remote check failed but cache exists with marker, use it
if not remote_sha and cache_dir.exists() and marker.exists():
    cached_sha = marker.read_text(encoding="utf-8").strip()
    logger.warning("[Clone] ls-remote unavailable; using existing cache for %s (SHA=%s)", repo_url, cached_sha[:8])
    return cache_dir, cached_sha, False
```

This runs before the `if cache_dir.exists(): shutil.rmtree(...)` block, so the
cache is preserved when the network is unavailable.

## Failure modes

### Failure mode 1: Stale cache used with outdated content
**Detection**: Run uses old repo content (SHA marker differs from actual remote HEAD)
**Resolution**: This is acceptable — network unavailability means we cannot check; stale > no content
**Gate**: Run output will still show old SHA

### Failure mode 2: Cache dir exists but marker is missing
**Detection**: `marker.exists()` is False — code falls through to existing deletion logic
**Resolution**: Correct behavior — if no SHA marker, cache is incomplete; re-clone attempted
**Gate**: Normal flow

### Failure mode 3: Regression on normal network path
**Detection**: Cache hits or misses behave differently when network works
**Resolution**: The new block only fires when `remote_sha == ""` (ls-remote failed); normal path unchanged
**Gate**: Existing tests

## Task-specific review checklist

1. [x] New fallback block placed BEFORE the `shutil.rmtree` block
2. [x] Condition requires `not remote_sha AND cache_dir.exists() AND marker.exists()`
3. [x] Logs a WARNING (not INFO) — user should know cache freshness is unverified
4. [x] Returns `(cache_dir, cached_sha, False)` — `is_fresh_clone=False` (no re-clone)
5. [x] No change to the normal network-available path
6. [x] No new imports required

## Deliverables

1. Updated `src/launcher/workers/intake/clone.py`

## Acceptance checks

1. [ ] `git ls-remote` failure no longer deletes existing cache
2. [ ] note-python run completes past intake using existing cached clone
3. [ ] Tests pass

## Self-review

### Verification results
- [ ] Tests pass
- [ ] note-python intake succeeds on network failure

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -k "clone" -x -q
```

## Integration boundary proven

**Upstream**: `git ls-remote` — may fail due to network/rate-limit
**Downstream**: Intake worker uses `repo_dir` from clone for understand phase
**Contract**: When network unavailable, existing cache takes precedence over re-clone
