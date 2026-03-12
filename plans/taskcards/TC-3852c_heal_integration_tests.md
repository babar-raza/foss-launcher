---
id: TC-3852c
title: "Heal Integration Tests (H4.3)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, integration, tests]
depends_on: [TC-3851, TC-3852a, TC-3852b]
allowed_paths:
  - plans/taskcards/TC-3852c_heal_integration_tests.md
  - tests/integration/test_heal_integration.py
  - reports/TC-3852c/evidence.md
evidence_required:
  - reports/TC-3852c/evidence.md
---

# Taskcard TC-3852c — Heal Integration Tests (H4.3)

## Objective

Create `tests/integration/test_heal_integration.py` covering the heal loop
end-to-end: dry-run, 1-step heal, budget exhaustion, LLM unavailable fallback,
quarantine persistence, and regression rollback.

## Allowed paths

- plans/taskcards/TC-3852c_heal_integration_tests.md
- tests/integration/test_heal_integration.py
- reports/TC-3852c/evidence.md

## Acceptance checks

1. [ ] All integration tests pass in isolation
2. [ ] `heal_plan.json` written in dry-run mode
3. [ ] LLM unavailable → stop_reason == "llm_unavailable"
4. [ ] 0 failures in full suite

## Self-review

### Verification results
- [ ] Evidence file: `reports/TC-3852c/evidence.md`

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_integration.py -v
```

## Integration boundary proven

**Upstream**: EvaluationReport written by evaluate worker
**Downstream**: heal_plan.json consumed by CI/monitoring
**Contract**: HealResult.stop_reason in ("dry_run", "llm_unavailable", "budget_exceeded", "max_steps")
