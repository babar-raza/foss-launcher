---
id: GR-03
title: "Clarify installation.md KNOWN_FAILURES: golden file defect vs gate miscalibration"
status: Open
priority: Low
owner: agent
updated: "2026-03-09"
tags: [golden, regression, documentation, safety-check]
depends_on: []
allowed_paths:
  - plans/healing/GR-03-installation-known-failure-comment.md
  - tests/golden/test_checks_regression.py
evidence_required:
  - reports/GR-03/evidence.md
---

# GR-03 — Clarify installation.md KNOWN_FAILURES classification

## Objective

The `installation.md` KNOWN_FAILURE comment currently suggests the safety check
is miscalibrated ("installation pages need safety exemption for download URLs").
The root cause is actually a golden file defect: `releases.aspose.com` is a
commercial domain link that should not appear in a FOSS documentation page.
Fix the comment to correctly classify this as a **golden file defect** and
recommend fixing the golden file, not the safety gate.

## Gap source

TC-3876b self-review: the KNOWN_FAILURES comment for `installation.md` frames
`releases.aspose.com` as a legitimate URL that the gate should exempt. However
the veto oracle principle says: if a gate fires on a grade-A page → either the
gate is wrong OR the golden file is wrong. In this case the golden file is wrong
(commercial link in FOSS doc), and the safety gate is correct.

## Required spec references

- `plans/purrfect-beaming-crown.md` (Guiding constraint: golden pages veto wrong
  thresholds — but golden pages themselves must also be correct)

## Scope

### In scope
- Update the KNOWN_FAILURES comment for `installation.md` in the regression test
- Update `_KNOWN_FAILURES_HIGH_CRITICAL` dict value for `installation.md`
- Add a comment pointing toward fixing the golden file (not the gate)

### Out of scope
- Fixing the golden file itself (requires a separate golden-maintenance TC)
- Modifying the safety check
- Removing the xfail — keep it in place until the golden file is fixed

## Inputs

- `tests/golden/test_checks_regression.py` (current KNOWN_FAILURES comment and dict)
- `golden/installation.md` (the offending URL — read to confirm)

## Outputs

- `tests/golden/test_checks_regression.py` (comment updated)
- `reports/GR-03/evidence.md`

## Allowed paths

- plans/healing/GR-03-installation-known-failure-comment.md
- tests/golden/test_checks_regression.py

### Allowed paths rationale

Comment-only change to the regression test. No code logic changes.

## Implementation steps

### Step 1: Read current comment in test file

Locate the `installation.md` block in `_KNOWN_FAILURES_HIGH_CRITICAL` and the
detailed comment above it. Current text (approximately):

```python
#   installation.md (grade=A, role=installation):
#     [HIGH] safety — Commercial domain link: https://releases.aspose.com
#     Root cause: safety check flags aspose.com links as commercial.
#     Installation pages legitimately reference download sources.
#     Fix needed: exempt installation/license pages from commercial-link rule,
#     OR update golden file to use aspose.net release URL.
#     → Fixed by: future TC (safety role exemption for installation pages)
```

And the dict value:
```python
"installation.md": (
    "safety fires on commercial link (releases.aspose.com) — "
    "installation pages need safety exemption for download URLs"
),
```

### Step 2: Replace with corrected classification

Replace the detailed comment with:
```python
#   installation.md (grade=A, role=installation):
#     [HIGH] safety — Commercial domain link: https://releases.aspose.com
#     Root cause: GOLDEN FILE DEFECT — the golden page contains a commercial
#     domain link (releases.aspose.com) which legitimately triggers the safety
#     check. FOSS documentation should not link to commercial release servers.
#     The safety gate is CORRECT. The golden file needs to be updated to use
#     a FOSS-compatible download URL or remove the commercial link.
#     Classification: golden file defect, NOT gate miscalibration
#     → Fix: update golden/installation.md to remove commercial URL (separate TC)
```

Replace the dict value with:
```python
"installation.md": (
    "GOLDEN FILE DEFECT: safety fires on commercial link (releases.aspose.com). "
    "Gate is correct — golden file must be updated to remove commercial URL. "
    "xfail retained until golden/installation.md is fixed."
),
```

### Step 3: Create evidence report

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1
```

Confirm: `installation.md` still xfails (now with corrected reason string).

## Failure modes

### Failure mode 1: xfail reason string change affects pytest output matching

**Detection**: `pytest -v` output shows new xfail reason
**Resolution**: Verify xfail is still correctly classified — the test still xfails,
just with an improved reason message
**Gate**: `pytest tests/golden/ -m golden -v` shows `XFAIL` for installation.md

### Failure mode 2: Comment removed or lost in edit

**Detection**: `grep "GOLDEN FILE DEFECT" tests/golden/test_checks_regression.py`
returns no results
**Resolution**: Re-add the comment per Step 2
**Gate**: grep check above

### Failure mode 3: Misidentification — golden file does NOT contain commercial URL

**Detection**: `grep "releases.aspose.com" golden/installation.md` returns no results
**Resolution**: The safety check finding itself names the URL — verify directly.
If URL is absent, remove the xfail entirely (the check was wrong in TC-3876b).
**Gate**: URL present → keep xfail with updated comment; URL absent → remove xfail

## Task-specific review checklist

1. [ ] `installation.md` KNOWN_FAILURES comment says "GOLDEN FILE DEFECT" not "miscalibration"
2. [ ] Comment recommends fixing golden file, not exempting the safety gate
3. [ ] xfail still in place for `installation.md` (gate still fires)
4. [ ] `_KNOWN_FAILURES_HIGH_CRITICAL` dict value updated to match new classification
5. [ ] `golden/installation.md` checked for presence of `releases.aspose.com`
6. [ ] All other KNOWN_FAILURES comments unchanged
7. [ ] Spec file: no worker behavior change
8. [ ] Schema: not applicable
9. [ ] Checked `docs/README.md` — no trigger events apply
10. [ ] No new `docs/guides/` file added

## Deliverables

1. `tests/golden/test_checks_regression.py` (comment updated to GOLDEN FILE DEFECT)
2. `reports/GR-03/evidence.md`

## Acceptance checks

1. [ ] `grep "GOLDEN FILE DEFECT" tests/golden/test_checks_regression.py` returns match
2. [ ] `pytest tests/golden/ -m golden -v` shows `installation.md` as `XFAIL` (not FAILED)
3. [ ] No test result changes from before

## Self-review

### Verification results
- [ ] grep confirms GOLDEN FILE DEFECT text present
- [ ] Pytest output shows xfail unchanged
- [ ] Evidence captured: reports/GR-03/evidence.md

## E2E verification

```bash
grep "GOLDEN FILE DEFECT" tests/golden/test_checks_regression.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/golden/ -m golden -v 2>&1 | grep "installation"
```

**Expected results**:
- `grep` returns the corrected comment
- `pytest` shows `XFAIL test_no_high_critical_on_grade_a[installation.md]`

## Integration boundary proven

**Upstream**: safety check (commercial domain detection — correct behaviour)
**Downstream**: TC for golden file maintenance (updates golden/installation.md)
**Contract**: xfail is a temporary hold; removing xfail requires fixing golden file first
