---
id: TC-3865
title: "Complete readability thresholds per SEO-20 spec"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [readability, seo, evaluate, quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3865_readability_thresholds.md
  - src/launcher/workers/evaluate/checks/readability.py
  - tests/unit/workers/test_readability_check.py
evidence_required:
  - reports/TC-3865/evidence.md
---

# Taskcard TC-3865 — Complete readability thresholds per SEO-20 spec

## Objective

The current readability check only flags FK > 12.0 (severity: low). Plan SEO-20 specifies
three thresholds: FK < 6 (too simple for technical audience), FK > 16 (complex), and FK > 20
(severely complex, escalated to medium). This TC implements the missing thresholds so the
evaluate worker catches both extremes of readability failure.

## Required spec references

- Plan: `sparkling-discovering-walrus.md` (SEO-20 readability thresholds)

## Scope

### In scope
- Add FK < 6 → severity "low", message "too simple"
- Split FK > 12 into: FK > 20 → "medium", FK 12-20 → "low"
- Update both `check_readability` (dict-based) and `check_readability_from_markdown` (Finding-based)
- Update tests for the new thresholds

### Out of scope
- Changing reading time calculation
- Changing the syllable counting algorithm
- Adding readability to finding_classifier (separate TC-3867)

## Inputs

- `src/launcher/workers/evaluate/checks/readability.py`

## Outputs

- FK < 6 findings at severity "low"
- FK > 20 findings at severity "medium" (triggers B grade instead of A)
- FK 12-20 findings unchanged at severity "low"

## Allowed paths

- plans/taskcards/TC-3865_readability_thresholds.md
- src/launcher/workers/evaluate/checks/readability.py
- tests/unit/workers/test_readability_check.py

## Implementation steps

### Step 1: Update check_readability (dict-based) thresholds

Replace the single `if fk_grade > 12.0` block with:

```python
findings = []
if fk_grade > 20.0:
    findings.append({
        "check": "readability",
        "message": (
            f"Prose is severely complex (Flesch-Kincaid grade {fk_grade:.1f}, "
            "threshold: ≤20.0). Simplify sentences and vocabulary."
        ),
        "severity": "medium",
    })
elif fk_grade > 12.0:
    findings.append({
        "check": "readability",
        "message": (
            f"Prose may be too complex (Flesch-Kincaid grade {fk_grade:.1f}, "
            "threshold: ≤12.0). Consider shorter sentences and simpler vocabulary."
        ),
        "severity": "low",
    })
elif fk_grade < 6.0 and word_count >= 100:
    findings.append({
        "check": "readability",
        "message": (
            f"Prose may be too simple for a technical audience "
            f"(Flesch-Kincaid grade {fk_grade:.1f}, threshold: ≥6.0)."
        ),
        "severity": "low",
    })
return findings
```

### Step 2: Mirror in check_readability_from_markdown (Finding-based)

Same logic, producing Finding objects instead of dicts.

### Step 3: Update tests

Add to test_readability_check.py:
- `test_too_simple_flagged` — FK < 6 with ≥100 words → finding with message containing "too simple"
- `test_severely_complex_escalated` — FK > 20 → severity="medium"
- `test_moderately_complex_still_low` — FK between 12 and 20 → severity="low"
- `test_too_simple_short_page_no_finding` — FK < 6 but < 100 words → no finding (not enough data)

## Failure modes

### Failure mode 1: FK calculation returns 0 for very short pages
**Detection**: word_count < 100 guard should prevent false positives
**Resolution**: Keep the 100-word minimum guard — FK < 6 check must also require ≥100 words
**Gate**: test_too_simple_short_page_no_finding

### Failure mode 2: FK > 20 changes grade from A to B for otherwise-clean pages
**Detection**: Expected — this is the desired behavior per SEO-20 spec
**Resolution**: No resolution needed; medium severity → B grade is correct
**Gate**: test_severely_complex_escalated checks severity="medium"

### Failure mode 3: Existing tests fail due to threshold change
**Detection**: pytest shows test_too_simple failing differently
**Resolution**: Update test_too_simple to assert finding IS generated (not absent)
**Gate**: Run full test suite after change

## Task-specific review checklist

1. [ ] FK < 6 only fires when word_count >= 100
2. [ ] FK > 20 produces severity="medium" (not "low")
3. [ ] FK 12-20 still produces severity="low" (no regression)
4. [ ] FK <= 12 and FK >= 6 produces no finding (clean)
5. [ ] Both check_readability and check_readability_from_markdown updated consistently
6. [ ] test_too_simple now asserts a finding IS generated
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed
9. [ ] Schema description fields present
10. [ ] Checked docs/README.md ownership map
11. [ ] New docs/guides/ file added if needed

## Deliverables

1. `src/launcher/workers/evaluate/checks/readability.py` — updated thresholds
2. `tests/unit/workers/test_readability_check.py` — updated + new tests

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v` — all pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — count >= 2878
3. [ ] A severely complex page (FK > 20) gets Finding severity="medium"

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: readability thresholds PASS
- [ ] Evidence captured: reports/TC-3865/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_readability_check.py -v
```

## Integration boundary proven

**Upstream**: Evaluate worker calls check_readability_from_markdown on each page
**Downstream**: grade_page() assigns B for medium findings, A for low-only
**Contract**: Finding objects with check="readability", severity in ["low","medium"]
