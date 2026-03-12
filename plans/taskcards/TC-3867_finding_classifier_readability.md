---
id: TC-3867
title: "Register readability check in finding_classifier"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [heal, finding-classifier, readability, quality]
depends_on: [TC-3865]
allowed_paths:
  - plans/taskcards/TC-3867_finding_classifier_readability.md
  - src/launcher/workers/evaluate/finding_classifier.py
  - tests/unit/test_finding_classifier.py
evidence_required:
  - reports/TC-3867/evidence.md
---

# Taskcard TC-3867 — Register readability check in finding_classifier

## Objective

`finding_classifier.py` uses "unknown" as the fallback for unrecognized check names, which
maps to "engineering_only" in `classify_finding()`. The `readability` check name is absent
from all buckets, so heal can never propose LLM fixes for readability findings. This TC
registers "readability" as LLM_FIXABLE since the LLM can rewrite prose for complexity.

## Required spec references

- Plan: `quirky-mapping-mccarthy.md` (H2 — finding classification for heal)

## Scope

### In scope
- Add "readability" to LLM_FIXABLE_CHECKS frozenset
- Verify "structure" (block_spec findings) is already in LLM_FIXABLE_CHECKS (it is — confirm)
- Add tests for readability classification

### Out of scope
- Adding new classification buckets
- Modifying the MIXED sub-classifier logic
- Changing how "unknown" maps (it stays as engineering_only)

## Inputs

- `src/launcher/workers/evaluate/finding_classifier.py`

## Outputs

- `classify_check("readability")` returns "llm_fixable"
- `classify_finding(Finding(check="readability"))` returns "llm_fixable"
- `is_healable("readability")` returns True

## Allowed paths

- plans/taskcards/TC-3867_finding_classifier_readability.md
- src/launcher/workers/evaluate/finding_classifier.py
- tests/unit/test_finding_classifier.py

### Allowed paths rationale
- Taskcard file itself — always required.
- `finding_classifier.py` — the only file modified: add "readability" to LLM_FIXABLE_CHECKS.
- `test_finding_classifier.py` — unit tests verifying the new classification.

## Implementation steps

### Step 1: Add "readability" to LLM_FIXABLE_CHECKS

In finding_classifier.py, add to the LLM_FIXABLE_CHECKS frozenset:
```python
LLM_FIXABLE_CHECKS: frozenset[str] = frozenset({
    "density",
    "repetition",
    "product_names",
    "artifacts",
    "structure",
    "semantic_structure",
    "code",
    "readability",   # LLM can rewrite prose for complexity/simplicity
})
```

### Step 2: Verify "structure" is already present

Confirm "structure" is in LLM_FIXABLE_CHECKS (it is, per exploration). No change needed.

### Step 3: Add tests

In test_finding_classifier.py add:
- `test_readability_is_llm_fixable` — classify_check("readability") == "llm_fixable"
- `test_readability_is_healable` — is_healable("readability") is True
- `test_readability_finding_classify` — classify_finding(Finding(check="readability", message="complex")) == "llm_fixable"

## Failure modes

### Failure mode 1: readability added to wrong bucket
**Detection**: test_readability_is_llm_fixable fails
**Resolution**: Verify set membership in LLM_FIXABLE_CHECKS
**Gate**: Direct assertion in test

### Failure mode 2: Existing tests for "unknown" behavior break
**Detection**: test suite count drops
**Resolution**: "unknown" default is unchanged; only adding a known entry
**Gate**: Full test suite run after change

### Failure mode 3: Heal sends readability findings to LLM with insufficient context
**Detection**: Heal diagnostician prompt doesn't include readability details
**Resolution**: Heal prompt building is separate; classification is a prerequisite
**Gate**: Unit test only; heal integration is out of scope here

## Task-specific review checklist

1. [x] "readability" added to LLM_FIXABLE_CHECKS (not MIXED or DATA_FIXABLE)
2. [x] "structure" confirmed already in LLM_FIXABLE_CHECKS
3. [x] 3 new tests added and passing (5 added in TestReadabilityClassification, 45/45 PASS)
4. [x] No existing tests broken (45/45 PASS)
5. [x] is_healable("readability") returns True (test_readability_is_healable PASS)
6. [x] classify_finding with readability Finding returns "llm_fixable" (test_readability_finding_classify PASS)
7. [x] Docstrings updated for all new/changed public functions (no new public functions; inline comment added at line 47)
8. [x] Spec file updated if worker behavior changed (specs/worker_evaluate.md has no finding_classifier ref; no spec drift)
9. [x] Schema description fields present (no JSON schema properties introduced)
10. [x] Checked docs/README.md ownership map (no trigger event; finding_classifier not listed)
11. [x] New docs/guides/ file added if needed (not needed — internal classification change)

## Deliverables

1. `src/launcher/workers/evaluate/finding_classifier.py` — readability added
2. `tests/unit/test_finding_classifier.py` — 3 new tests

## Acceptance checks

1. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_finding_classifier.py -v` — 45/45 PASS
2. [x] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no` — 2936 passed (>= 2878)
3. [x] classify_check("readability") == "llm_fixable" — confirmed by AC1

## Self-review

### Verification results
- [x] Tests: 45/45 PASS (tests/unit/test_finding_classifier.py)
- [x] Validation: classify_check("readability") == "llm_fixable" PASS
- [x] Evidence captured: reports/TC-3867/evidence.md
- [x] Doc freshness: N/A — single-commit orphan branch; script requires committed history. No src/launcher/** changes in this TC; no doc trigger events apply. Clean by inspection.

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_finding_classifier.py -v
```

**Expected results**:
- All `TestReadabilityClassification` tests PASS (5 tests)
- All pre-existing `TestClassifyCheck`, `TestClassifyFinding`, `TestIsHealable` tests PASS
- Total test count >= prior baseline (no regressions)

## Integration boundary proven

**Upstream**: evaluate worker produces findings with check="readability"
**Downstream**: heal.py uses is_healable() / classify_finding() to route findings to LLM
**Contract**: classify_check("readability") == "llm_fixable"
