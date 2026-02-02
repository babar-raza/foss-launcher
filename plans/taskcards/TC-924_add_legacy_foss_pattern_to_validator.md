---
id: TC-924
title: "Add legacy FOSS pattern to repo URL validator"
status: In-Progress
priority: Critical
owner: "SUPERVISOR"
updated: "2026-02-01"
tags: ["repo", "validator", "pilot", "blocker"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - src/launch/workers/_git/repo_url_validator.py
  - tests/unit/workers/_git/test_repo_url_validator.py
  - reports/agents/**/TC-924/**
evidence_required:
  - reports/agents/SUPERVISOR/TC-924/validator_fix.diff
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-924 — Add legacy FOSS pattern to repo URL validator

## Objective
Add support for legacy FOSS repository pattern `Aspose.{Family}-FOSS-for-{Platform}` to the repo URL validator to unblock pilot VFV runs.

## Problem Statement
VFV runs for both pilots fail with URL policy violations because their repository names use the legacy FOSS pattern:
- Pilot-1: `https://github.com/aspose-3d-foss/Aspose.3d-FOSS-for-Python`
- Pilot-2: `https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python`

Current validator supports only:
1. New pattern: `aspose-{family}-foss-{platform}` (all lowercase)
2. Legacy pattern: `Aspose.{Family}-for-{Platform}` (no FOSS)

But NOT the hybrid: `Aspose.{Family}-FOSS-for-{Platform}`

## Required spec references
- specs/36_repository_url_policy.md (URL validation policy)

## Scope

### In scope
- Add LEGACY_FOSS_REPO_PATTERN regex to match `Aspose.{Family}-FOSS-for-{Platform}`
- Update _validate_product_repo() to try legacy FOSS pattern after standard patterns
- Add test cases for both pilot URLs

### Out of scope
- Changing pilot repository URLs
- Modifying specs/36 (this is an implementation fix for existing spec coverage)

## Allowed paths
- plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- src/launch/workers/_git/repo_url_validator.py
- tests/unit/workers/_git/test_repo_url_validator.py
- reports/agents/**/TC-924/**

## Implementation
Quick fix - add pattern immediately after LEGACY_REPO_PATTERN definition (line ~86):

```python
# Legacy FOSS repository pattern (for existing pilot repos)
# https://github.com/{org}/Aspose.{Family}-FOSS-for-{Platform}
LEGACY_FOSS_REPO_PATTERN = re.compile(
    r"^https://github\.com/"
    r"(?P<org>[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)"
    r"/Aspose\.(?P<family>[a-zA-Z0-9]+)-FOSS-for-(?P<platform>[a-zA-Z0-9]+)"
    r"(?:\.git)?$",
    re.IGNORECASE
)
```

Then in _validate_product_repo(), add matching after legacy pattern (around line 360):

```python
if match:
    # ... existing legacy handling ...
    
# Try legacy FOSS pattern
match = LEGACY_FOSS_REPO_PATTERN.match(normalized_url)
if match:
    family = match.group("family").lower()
    platform = match.group("platform").lower()
    # ... validate family/platform, return ValidatedRepoUrl with is_legacy_pattern=True
```

## Success Criteria
- Both pilot URLs validate successfully
- validate_swarm_ready.py PASS
- pytest PASS (or same baseline)
