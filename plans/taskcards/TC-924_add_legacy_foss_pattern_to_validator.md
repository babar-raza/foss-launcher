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

- `plans/taskcards/TC-924_add_legacy_foss_pattern_to_validator.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `src/launch/workers/_git/repo_url_validator.py`
- `tests/unit/workers/_git/test_repo_url_validator.py`
- `reports/agents/**/TC-924/**`## Implementation
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

## Inputs
- Current repo_url_validator.py with two patterns (new lowercase, legacy Aspose.Family-for-Platform)
- Pilot repo URLs: `https://github.com/aspose-3d-foss/Aspose.3d-FOSS-for-Python` and `https://github.com/aspose-note-foss/Aspose.Note-FOSS-for-Python`
- VFV error logs showing URL policy violations

## Outputs
- Updated src/launch/workers/_git/repo_url_validator.py with LEGACY_FOSS_REPO_PATTERN
- Unit tests in tests/unit/workers/_git/test_repo_url_validator.py covering both pilot URLs
- VFV reports showing preflight PASS (no URL validation errors)

## Implementation steps
1. Add LEGACY_FOSS_REPO_PATTERN regex constant after line 86 in repo_url_validator.py
2. Update _validate_product_repo() to try legacy FOSS pattern after existing patterns
3. Add two test cases: test_legacy_foss_pattern_3d() and test_legacy_foss_pattern_note()
4. Run pytest to verify new tests pass
5. Run validate_swarm_ready.py to verify gates pass

## Deliverables
- src/launch/workers/_git/repo_url_validator.py (LEGACY_FOSS_REPO_PATTERN added)
- tests/unit/workers/_git/test_repo_url_validator.py (2 new test cases)
- VFV report showing both pilots' URLs validated

## Acceptance checks
1. Both pilot URLs validate successfully (no ValueError)
2. Unit tests pass: pytest tests/unit/workers/_git/test_repo_url_validator.py
3. VFV preflight PASS for both pilots
4. validate_swarm_ready.py PASS (or same baseline)

## Success Criteria
- Both pilot URLs validate successfully
- validate_swarm_ready.py PASS
- pytest PASS (or same baseline)

## E2E verification
Run full pilot VFV with both runs:
```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output report.json
```

Expected artifacts:
- VFV preflight PASS (no URL validation errors)
- Both pilots' GitHub repo URLs validated successfully
- Run 1 and Run 2 proceed past W1 (Repo Scout)

## Integration boundary proven
**Upstream:** VFV harness calls validate_github_url() before attempting git clone in W1.
**Downstream:** W1 Repo Scout receives validated GitHub URL and proceeds with shallow clone.
**Contract:** validate_github_url() returns ValidatedRepoUrl with is_legacy_pattern=True for both pilot URLs, allowing W1 to proceed.

## Task-specific review checklist
1. [ ] LEGACY_FOSS_REPO_PATTERN regex correctly matches Aspose.{Family}-FOSS-for-{Platform} format
2. [ ] Regex uses case-insensitive matching (re.IGNORECASE flag)
3. [ ] Both pilot URLs validate successfully: Aspose.3d-FOSS-for-Python and Aspose.Note-FOSS-for-Python
4. [ ] Pattern positioned correctly in code (after LEGACY_REPO_PATTERN definition around line 86)
5. [ ] _validate_product_repo() tries legacy FOSS pattern after existing patterns (additive, no breaking changes)
6. [ ] Unit tests include test_legacy_foss_pattern_3d() for first pilot URL
7. [ ] Unit tests include test_legacy_foss_pattern_note() for second pilot URL
8. [ ] ValidatedRepoUrl returns is_legacy_pattern=True for matched URLs
9. [ ] Existing validation patterns (new lowercase, legacy Aspose.Family-for-Platform) remain unchanged
10. [ ] validate_swarm_ready shows no new gate failures after change

## Failure modes

### Failure mode 1: Regex fails to match pilot URLs due to case sensitivity
**Detection:** VFV preflight fails with ValueError: "URL does not match any allowed patterns" despite URLs being in correct format
**Resolution:** Verify LEGACY_FOSS_REPO_PATTERN includes re.IGNORECASE flag; test regex against both pilot URLs manually using regex101.com or Python REPL; ensure family name matching handles mixed case (3d vs 3D)
**Spec/Gate:** specs/36_repository_url_policy.md (URL validation rules)

### Failure mode 2: Validator rejects URLs due to pattern order
**Detection:** VFV preflight passes for one pilot but fails for another; error mentions "already matched by earlier pattern with wrong extraction"
**Resolution:** Verify pattern matching order in _validate_product_repo() - legacy FOSS must be tried after new lowercase and legacy patterns; ensure pattern groups (?P<family>, ?P<platform>) extract correctly
**Spec/Gate:** Gate A1 (URL policy validation)

### Failure mode 3: Unit tests pass but VFV still fails
**Detection:** pytest test_repo_url_validator.py shows 2/2 PASS, but VFV preflight errors with "URL validation failed"
**Resolution:** Check that test URLs exactly match pilot configs; verify test is calling validate_github_url() not just pattern matching; ensure ValidatedRepoUrl object construction includes all required fields (org, family, platform, is_legacy_pattern)
**Spec/Gate:** VFV preflight contract (scripts/run_pilot_vfv.py URL validation step)

## Deliverables
- Code:
  - src/launch/workers/_git/repo_url_validator.py (LEGACY_FOSS_REPO_PATTERN added)
  - tests/unit/workers/_git/test_repo_url_validator.py (2 new test cases)
- Reports (required):
  - reports/agents/SUPERVISOR/TC-924/validator_fix.diff

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
