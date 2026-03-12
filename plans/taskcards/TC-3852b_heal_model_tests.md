---
id: TC-3852b
title: "Heal Model / Classifier / Golden Loader Tests (H4.2)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, tests, golden]
depends_on: [TC-3829, TC-3831, TC-3833, TC-3838]
allowed_paths:
  - plans/taskcards/TC-3852b_heal_model_tests.md
  - tests/unit/test_heal_models.py
  - tests/unit/test_finding_classifier.py
  - tests/unit/test_golden_loader.py
  - reports/TC-3852b/evidence.md
evidence_required:
  - reports/TC-3852b/evidence.md
---

# Taskcard TC-3852b — Heal Model / Classifier / Golden Loader Tests (H4.2)

## Objective

Create three new test files covering: HealDecision/HealResult validation+serialization,
FindingClassifier buckets, and GoldenIndex load+query.

## Allowed paths

- plans/taskcards/TC-3852b_heal_model_tests.md
- tests/unit/test_heal_models.py
- tests/unit/test_finding_classifier.py
- tests/unit/test_golden_loader.py
- reports/TC-3852b/evidence.md

## Acceptance checks

1. [ ] All 3 test files pass in isolation
2. [ ] 0 failures in full suite

## Self-review

### Verification results
- [ ] Evidence file: `reports/TC-3852b/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_models.py tests/unit/test_finding_classifier.py tests/unit/test_golden_loader.py -v
```

## Integration boundary proven

**Upstream**: HealDecision/HealResult from models/evaluation.py (TC-3829)
**Downstream**: heal.py uses HealDecision schema; finding_classifier drives heal decisions
