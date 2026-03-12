---
id: GR-07
title: "Verify pre-existing test_moderately_complex_is_medium failure is truly pre-existing"
status: Open
priority: Low
owner: agent
updated: "2026-03-09"
tags: [golden, regression, readability, verification]
depends_on: []
allowed_paths:
  - plans/healing/GR-07-readability-failure-verification.md
  - reports/GR-07/evidence.md
evidence_required:
  - reports/GR-07/evidence.md
---

# GR-07 — Verify pre-existing readability failure

## Objective

TC-3876b evidence.md claimed `test_moderately_complex_is_medium` was a
"pre-existing failure not caused by TC-3876b". This was stated without git
verification. Verify using `git bisect` or `git log --oneline` whether the
failure existed before TC-3876a/b changes, and document the finding.

## Gap source

TC-3876b self-review: the claim was made based on the test's docstring mentioning
"TC-3878 recalibrated thresholds" but that alone does not prove the failure
pre-dates TC-3876a/b changes. An unjustified claim of pre-existence is a
governance gap.

## Required spec references

- `reports/TC-3876b/evidence.md` (claim: "pre-existing failure")

## Scope

### In scope
- Run `git log` to identify commit(s) that introduced TC-3876a/b changes
- Check `tests/unit/workers/test_readability_check.py` blame for
  `test_moderately_complex_is_medium`
- Run the test against the commit BEFORE TC-3876a to confirm pre-existence
- Update `reports/TC-3876b/evidence.md` with verified status

### Out of scope
- Fixing the readability check (that is TC-3878)
- Any src/ changes

## Inputs

- `git log` output
- `tests/unit/workers/test_readability_check.py`
- `src/launcher/workers/evaluate/checks/readability.py`

## Outputs

- `reports/GR-07/evidence.md` (verification result)
- `reports/TC-3876b/evidence.md` (updated with verified status if needed)

## Allowed paths

- plans/healing/GR-07-readability-failure-verification.md
- reports/GR-07/evidence.md
- reports/TC-3876b/evidence.md

### Allowed paths rationale

Investigation and documentation only. Updating evidence files is in scope.

## Implementation steps

### Step 1: Find the commit that introduced TC-3876a/b

```bash
git log --oneline | head -20
```

Identify the hash for the commit before TC-3876a changes to `golden_loader.py`.

### Step 2: Check when the test was introduced

```bash
git log --follow -p tests/unit/workers/test_readability_check.py 2>/dev/null | \
  grep -A5 "test_moderately_complex_is_medium" | head -30
```

This shows which commit introduced the test and what FK threshold it asserts.

### Step 3: Run the test on current HEAD

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  "tests/unit/workers/test_readability_check.py::test_moderately_complex_is_medium" \
  -v 2>&1
```

Record: PASS or FAIL, with exact error if FAIL.

### Step 4: Check what FK threshold the test uses vs what readability.py implements

```bash
grep -n "moderately_complex\|FK\|fk\|18\|16" tests/unit/workers/test_readability_check.py
grep -n "FK\|fk\|medium\|threshold\|18\|16" src/launcher/workers/evaluate/checks/readability.py
```

If the test asserts FK > 18 → medium but readability.py uses FK > 16 → medium,
the test was written for a future implementation.

### Step 5: Update evidence

If pre-existing: update `reports/TC-3876b/evidence.md` to add:
```
## Pre-existing failure (verified)

test_moderately_complex_is_medium was introduced in commit [HASH] before TC-3876a.
The test asserts FK > 18 → medium; readability.py currently uses FK > 16 → medium.
Confirmed by `git log --follow` showing the test pre-dates TC-3876a/b changes.
```

If NOT pre-existing (TC-3876a/b introduced it): escalate as a bug and create
a separate healing TC to fix the regression.

## Failure modes

### Failure mode 1: git log shows test was introduced IN TC-3876a/b

**Detection**: `git log --follow` shows test added in the TC-3876a commit
**Resolution**: This is a regression introduced by TC-3876a/b. Create a new
healing TC to fix. Update `reports/TC-3876b/evidence.md` to remove the
"pre-existing" claim. Notify user.
**Gate**: `git blame` shows commit hash vs TC-3876a hash

### Failure mode 2: Only one commit in git history (orphan branch)

**Detection**: `git log --oneline` shows only one commit ("chore: initialize foss-launcher v2")
**Resolution**: Cannot do git bisect on orphan branch with single commit.
Use `git blame` to check line introduction. If only one commit, record:
"Cannot verify — orphan branch with single commit. Claim unverifiable by git history."
Update `reports/TC-3876b/evidence.md` accordingly.
**Gate**: git log output has ≥2 commits for bisect; if not, document limitation

### Failure mode 3: Test passes (no failure)

**Detection**: `pytest test_moderately_complex_is_medium -v` returns PASS
**Resolution**: Self-review finding was incorrect. Remove the pre-existing failure
claim from evidence. No bug exists.
**Gate**: Pytest output says PASSED

## Task-specific review checklist

1. [ ] `git log --oneline` output captured in evidence
2. [ ] `git blame` or `git log --follow` output for the test captured
3. [ ] Readability.py threshold (FK > X → medium) documented
4. [ ] Test assertion (FK > Y → medium) documented
5. [ ] Conclusion: pre-existing (verified) / pre-existing (unverifiable) / regression
6. [ ] `reports/TC-3876b/evidence.md` updated with verified status
7. [ ] Spec file: not applicable (investigation only)
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `reports/GR-07/evidence.md` (git log output + verification conclusion)
2. `reports/TC-3876b/evidence.md` (updated if needed)

## Acceptance checks

1. [ ] Evidence report contains git log output
2. [ ] Evidence report states verified conclusion (pre-existing / regression / unverifiable)
3. [ ] `reports/TC-3876b/evidence.md` reflects the verified status

## Self-review

### Verification results
- [ ] git log captured
- [ ] Conclusion reached
- [ ] Evidence captured: reports/GR-07/evidence.md

## E2E verification

```bash
git log --oneline | head -5
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  "tests/unit/workers/test_readability_check.py::test_moderately_complex_is_medium" -v
```

**Expected results**:
- git log shows commit history
- Test result (PASS or FAIL) documented in evidence

## Integration boundary proven

**Upstream**: git history (authoritative source of truth for commit order)
**Downstream**: TC-3878 (readability threshold fix) — needs to know if failure is a pre-existing gap or a regression
**Contract**: Pre-existence claim is either verified by git or explicitly marked unverifiable
