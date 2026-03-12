---
id: TC-4252
title: "BUG: Replace llm_unbound claim_source with llm_fallback to fix Pydantic Literal crash"
status: Done
priority: Critical
owner: "Agent"
updated: "2026-03-12"
tags: [understand, claims, bugfix, validation, literal]
depends_on: [TC-4247]
allowed_paths:
  - plans/taskcards/TC-4252_understand-fix-llm-unbound-claim-source.md
  - src/launcher/workers/understand/extract/_entry.py
evidence_required:
  - reports/TC-4252/evidence.md
---

# Taskcard TC-4252 — BUG: Fix llm_unbound claim_source Pydantic crash

## Objective

TC-4247 introduced `claim_source="llm_unbound"` for LLM claims that fail fact
binding, but the `Claim` model's `claim_source` Literal only accepts
`['llm', 'deterministic', 'docstring', 'llm_fallback']`. This causes a
`pydantic_core.ValidationError` in `_validate_and_normalize_claims()`, crashing
the Understand worker. Fix: replace `"llm_unbound"` with `"llm_fallback"` — same
confidence (0.35), same U-2 filter behavior (dropped before checkpoint).

## Scope

### In scope
- Change `"llm_unbound"` → `"llm_fallback"` in `_entry.py` line 434
- No model change needed — `"llm_fallback"` is already in the Literal

### Out of scope
- Adding `"llm_unbound"` as a new Literal value (requires schema change — separate TC)
- Any other changes to fact binding logic

## Allowed paths

- plans/taskcards/TC-4252_understand-fix-llm-unbound-claim-source.md
- src/launcher/workers/understand/extract/_entry.py

## Implementation steps

### Step 1: Fix _entry.py line 434

Change:
```python
updated["claim_source"] = "llm_unbound"
```
To:
```python
updated["claim_source"] = "llm_fallback"  # TC-4252: llm_unbound not in Claim Literal; use llm_fallback (same confidence=0.35, dropped by U-2 filter)
```

## Failure modes

### Failure mode 1: Semantics lost — can't distinguish unbound from fallback

**Detection**: Log analysis can't differentiate TC-4247 downgraded claims from TC-4224 fallback claims.
**Resolution**: Both are dropped by U-2 filter. Observability is provided by the existing `fact_binding_validation` log (`unbound_downgraded=32`). Distinction preserved in logs, not in claim_source field.
**Gate**: `fact_binding_validation` log event

### Failure mode 2: Other uses of "llm_unbound" exist

**Detection**: grep for `llm_unbound` in src/
**Resolution**: Only one occurrence at line 434.
**Gate**: Verified below

### Failure mode 3: U-2 filter doesn't drop these claims (confidence=0.35)

**Detection**: Claims with confidence=0.35 appear in understand_checkpoint.json.
**Resolution**: U-2 filter runs after `_validate_and_normalize_claims`; claims with confidence<0.5 are dropped. Correct by design.
**Gate**: Pilot run checkpoint inspection

## Task-specific review checklist

1. [ ] Line 434 uses `"llm_fallback"` not `"llm_unbound"`
2. [ ] No other `"llm_unbound"` references remain in src/
3. [ ] Pilot run proceeds past Understand validation
4. [ ] fact_binding_validation log still fires (unbound_downgraded count still visible)
5. [ ] U-2 filter drops these claims (confidence=0.35 < 0.5)
6. [ ] Docstrings: comment added referencing TC-4252
7. [ ] Spec: no behavior change (observability preserved in logs)
8. [ ] Schema: no changes needed
9. [ ] `docs/README.md`: N/A
10. [ ] No new `docs/guides/` file added

## Deliverables

1. Fixed `_entry.py` line 434 (1-line change)

## Acceptance checks

1. [ ] `grep llm_unbound src/launcher/workers/understand/extract/_entry.py` returns empty
2. [ ] Pilot run proceeds past Understand worker
3. [ ] `fact_binding_validation` log event still shows `unbound_downgraded` count

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: pilot run past Understand PASS
- [ ] Evidence: pilot log

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-cells-foss-python.yaml 2>&1 | grep -E "understand|Worker"
```

## Integration boundary proven

**Upstream**: TC-4247 fact binding → sets claim_source for unbound LLM claims
**Downstream**: `_validate_and_normalize_claims` → creates `Claim` pydantic objects
**Contract**: `claim_source` must be one of the 4 allowed Literal values; `"llm_fallback"` is the correct substitute for `"llm_unbound"`
