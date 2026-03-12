---
id: TC-HO-08
title: "Richness profile injection + tier-aware evaluate calibration"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [generate, evaluate, richness_tier, calibration, wave4b]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-HO-08_richness-profile-calibration.md
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/evaluate/checks/density.py
  - src/launcher/workers/evaluate/checks/structure.py
  - tests/unit/workers/generate/test_tc_ho08_richness_profile.py
  - tests/unit/workers/test_density_tier_aware.py
  - tests/unit/workers/test_structure_tier_aware.py
  - reports/agents/wave4b/TC-HO-08/evidence.md
evidence_required:
  - reports/agents/wave4b/TC-HO-08/evidence.md
---

# Taskcard TC-HO-08 — Richness profile calibration (Parts A + B + C)

## Objective

Part A: Inject `richness_tier.reason` as a structured REPOSITORY PROFILE block in the section
prompt so the LLM understands evidence quality constraints.

Part B: Make `check_density()` tier-aware by replacing flat thresholds with a tier dict.

Part C: Make `check_structure()` tier-aware for heading-density threshold.

## Required spec references

- `specs/worker_generate.md` (Section: richness tier context)
- `specs/worker_evaluate.md` (Section: density and structure checks)

## Scope

### In scope
- Part A: `richness_tier` parameter + `_format_richness_profile()` helper in section_prompt.py
- Part B: `_TIER_DENSITY` dict + `richness_tier` param in density.py
- Part C: `_TIER_HEADING` dict + `richness_tier` param in structure.py
- Tests for all three parts

### Out of scope
- Changing evaluate worker.py call sites (checks accept optional param; default "A" preserves behaviour)
- Changing RichnessResult model

## Inputs

- `understand.richness_tier` — RichnessResult (tier, reason, code_evidence_sparse)
- Current density.py and structure.py check functions

## Outputs

- Modified `section_prompt.py` with richness profile injection
- Modified `density.py` with tier-aware thresholds
- Modified `structure.py` with tier-aware heading threshold
- Tests

## Allowed paths

- plans/taskcards/TC-HO-08_richness-profile-calibration.md
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/evaluate/checks/density.py
- src/launcher/workers/evaluate/checks/structure.py
- tests/unit/workers/generate/test_tc_ho08_richness_profile.py
- tests/unit/workers/test_density_tier_aware.py
- tests/unit/workers/test_structure_tier_aware.py
- reports/agents/wave4b/TC-HO-08/evidence.md

### Allowed paths rationale

Three source files + three test files + taskcard. No other files modified.

## Implementation steps

### Step 1 (Part A): Add `_format_richness_profile()` to section_prompt.py

Parses semicolon-separated reason string into bullet points. Output:
```
REPOSITORY PROFILE:
- Richness Tier: {tier}
- {parsed_reason_field_1}
- {parsed_reason_field_2}
```
For Tier C with code_evidence_sparse=True, append:
"Do not fabricate code examples. One real example or prose only."

### Step 2 (Part A): Add `richness_tier: Any | None = None` to build_section_prompt()

Extract tier str and code_evidence_sparse from the RichnessResult object.
Prepend REPOSITORY PROFILE block (after existing EVIDENCE CONSTRAINT prepend).

### Step 3 (Part A): Pass from worker.py

Extract `understand.richness_tier` in `_process_page` and pass down to `build_section_prompt()`.

### Step 4 (Part B): Update density.py

Add `_TIER_DENSITY` dict. Add `richness_tier: str = "A"` param to `check_density()`.
Look up thresholds from dict (default to "A" if unknown tier string).

### Step 5 (Part C): Update structure.py

Add `_TIER_HEADING` dict. Add `richness_tier: str = "A"` param to `check_structure()`.
Replace the hardcoded `word_count > 500 and h2_count < 2` check with tier-aware lookup.

### Step 6: Write tests

Part A: Tier C sparse → REPOSITORY PROFILE + sparse warning; Tier A → profile but no warning
Part B: Tier C 60-word section → no density finding; Tier A same → finding
Part C: Tier C 700-word 0-H2 page → no structure finding; Tier A same → finding

## Failure modes

### Failure mode 1: tier string not in _TIER_DENSITY/_TIER_HEADING

**Detection**: KeyError on dict lookup
**Resolution**: Use `.get(richness_tier, _TIER_DENSITY["A"])` fallback

### Failure mode 2: richness_tier param not forwarded through call stack in worker.py

**Detection**: TypeError (unexpected keyword argument)
**Resolution**: Add the param to `_generate_page()` signature and pass it to `build_section_prompt()`

### Failure mode 3: Existing structure tests fail — heading density check changes

**Detection**: `pytest tests/unit/workers/test_structure*.py` failures
**Resolution**: Default tier is "A" which preserves the existing threshold (500 words, 2 H2s)

## Task-specific review checklist

1. [ ] _format_richness_profile() handles semicolon-split reason correctly
2. [ ] Tier C sparse warning only appears when code_evidence_sparse=True
3. [ ] _TIER_DENSITY fallback to "A" thresholds for unknown tier
4. [ ] _TIER_HEADING fallback to "A" thresholds for unknown tier
5. [ ] Default richness_tier="A" in both check functions (backward compat)
6. [ ] Test: Tier C 60 words → no density finding
7. [ ] Test: Tier A 60 words → density finding
8. [ ] Test: Tier C 700 words 0 H2s → no structure finding
9. [ ] Test: Tier A 700 words 0 H2s → structure finding
10. [ ] Docstrings updated for new params
11. [ ] Spec confirmed — no drift

## Deliverables

1. Modified `section_prompt.py`
2. Modified `density.py`
3. Modified `structure.py`
4. Three test files
5. Evidence markdown

## Acceptance checks

1. [ ] All new tests pass
2. [ ] No regressions in `tests/unit/workers/` or `tests/unit/workers/generate/`
3. [ ] REPOSITORY PROFILE block appears in Tier C sparse prompt
4. [ ] Tier C density thresholds are lower (50/10 vs 100/20 for Tier A)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/agents/wave4b/TC-HO-08/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc_ho08_richness_profile.py tests/unit/workers/test_density_tier_aware.py tests/unit/workers/test_structure_tier_aware.py -v
```

**Expected results**:
- All tests pass

## Integration boundary proven

**Upstream**: `UnderstandingBundle.richness_tier` (RichnessResult) from Understand worker
**Downstream (Part A)**: LLM prompt with REPOSITORY PROFILE context
**Downstream (Parts B+C)**: Evaluate checks with tier-appropriate thresholds
**Contract**: RichnessResult.tier is "A", "B", or "C"; reason is semicolon-separated string
