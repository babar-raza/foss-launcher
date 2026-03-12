---
id: TC-4073
title: "Add force_rescan parameter to org_scanner scan_org and scan_orgs"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [phase1, intake, org-scanner]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4073_force_rescan_org_scanner.md
  - src/launcher/intake/org_scanner.py
  - tests/unit/intake/test_org_scanner.py
evidence_required:
  - reports/TC-4073/evidence.md
---

# Taskcard TC-4073 — Add force_rescan to org_scanner

## Objective

Add `force_rescan: bool = False` to `scan_org()` and `scan_orgs()`. When `True`, repos
already in `seen_repos` are NOT skipped — they are processed even if previously seen.
This is required for a living system where previously-ineligible or previously-classified
repos may need re-evaluation.

## Implementation steps

### Step 1: Update scan_org()
Add `force_rescan: bool = False` parameter.
Change the `seen_repos` skip logic:
```python
if not force_rescan and full_name in seen_repos:
    logger.debug("Skipping already-seen repo: %s", full_name)
    continue
```
(Previously: `if full_name in seen_repos: ...`)

### Step 2: Update scan_orgs() if it exists
Find and update `scan_orgs()` to pass `force_rescan` through to `scan_org()`.

### Step 3: Add test
`tests/unit/intake/test_org_scanner.py`:
- `test_force_rescan_processes_seen_repos`: Mock HTTP, pre-populate `seen_repos` with a repo full_name. Call `scan_org(..., seen_repos=seen_repos, force_rescan=True)`. Verify the repo IS included in results.
- `test_default_skips_seen_repos`: Without `force_rescan`, seen repo is skipped (existing behavior).

## Failure modes

1. `scan_orgs()` may not exist or may have different parameter passing — adapt accordingly
2. When `force_rescan=True` AND `seen_repos` is used for deduplication post-scan, re-scanned repos may appear twice — caller responsibility to manage `seen_repos` properly

## Task-specific review checklist

- [ ] `scan_org(..., force_rescan=True)` processes repos already in `seen_repos`
- [ ] `scan_org(..., force_rescan=False)` (default) skips repos in `seen_repos` (unchanged behavior)
- [ ] `scan_orgs()` passes `force_rescan` through to `scan_org()`
- [ ] Test `test_force_rescan_processes_seen_repos` passes
- [ ] No breaking change to existing call sites (default is False)

## Deliverables

- Updated `src/launcher/intake/org_scanner.py`
- Updated `tests/unit/intake/test_org_scanner.py`

## Acceptance checks

- [x] `pytest tests/unit/intake/test_org_scanner.py -v` all pass (23 passed, verified 2026-03-11)
- [x] `force_rescan=False` (default) is backward-compatible (verified: param default=False at line 95)

## E2E verification

`pytest tests/unit/intake/ -x`

## Integration boundary proven

A CLI command with `--force-rescan` can call `scan_org(..., force_rescan=True)` and every
repo in the org is re-processed regardless of prior scan state.
