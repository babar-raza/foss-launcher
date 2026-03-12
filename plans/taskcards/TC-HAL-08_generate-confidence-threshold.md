---
id: TC-HAL-08
title: "Generate phase: filter low-confidence claims from section prompts"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "generate", "confidence"]
depends_on: ["TC-HAL-06"]
allowed_paths:
  - plans/taskcards/TC-HAL-08_generate-confidence-threshold.md
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/generate/test_section_prompt.py
evidence_required:
  - reports/TC-HAL-08/evidence.md
---

# Taskcard TC-HAL-08 — Generate phase: filter low-confidence claims from section prompts

## Objective
When building LLM prompts for section generation, filter out claims with `confidence < 0.5`. This prevents `llm_fallback` claims (confidence=0.35) and other low-evidence claims from being injected into the generation prompt, which is where they cause the LLM to write hallucinated API calls.

## Required spec references
- `specs/worker_generate.md` (Section: Section prompt construction)

## Scope
### In scope
- In `section_prompt.py`, when building the claims block for a section, filter to `confidence >= 0.5`
- Log filtered count per section at DEBUG level
- Constant `_CLAIM_CONFIDENCE_THRESHOLD = 0.5` in the module

### Out of scope
- Changing claim assignment in the planner (claims are pre-assigned)
- Removing claims from the UnderstandingBundle (they remain for provenance)

## Inputs
- `src/launcher/workers/generate/section_prompt.py` — claims block construction

## Outputs
- Updated `section_prompt.py` with confidence threshold filter
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-08_generate-confidence-threshold.md
- src/launcher/workers/generate/section_prompt.py
- tests/unit/workers/generate/test_section_prompt.py

### Allowed paths rationale
Only section_prompt.py needs the filter. Tests in existing generate test file.

## Implementation steps

### Step 1: Add confidence threshold constant
At the top of `section_prompt.py` with other constants:
```python
# TC-HAL-08: Claims below this confidence are excluded from generation prompts
_CLAIM_CONFIDENCE_THRESHOLD: float = 0.5
```

### Step 2: Filter claims before building claims block
Find the location in `section_prompt.py` where `section.claim_ids` are resolved to claim objects and formatted for the prompt. Add filtering:

```python
# TC-HAL-08: Filter low-confidence claims from generation prompt
if hasattr(claim_obj, 'confidence'):
    high_confidence_claims = [c for c in resolved_claims if c.confidence >= _CLAIM_CONFIDENCE_THRESHOLD]
    filtered_count = len(resolved_claims) - len(high_confidence_claims)
    if filtered_count:
        logger.debug(
            "section_prompt: filtered %d low-confidence claims (confidence < %.1f) for section %s",
            filtered_count, _CLAIM_CONFIDENCE_THRESHOLD, section.section_id,
        )
    resolved_claims = high_confidence_claims
```

The exact insertion point depends on how section_prompt.py processes claims. Find the function that formats claims for the prompt (likely a function like `_format_claims_block` or similar) and add the filter at the top of that function.

### Step 3: Unit tests
Add to `tests/unit/workers/generate/test_section_prompt.py`:
- `test_low_confidence_claims_filtered` — provide mix of high (0.75) and low (0.35) confidence claims → only high-confidence claims appear in prompt output
- `test_all_high_confidence_claims_included` — all claims confidence=1.0 → all included
- `test_no_confidence_field_legacy_compat` — claim objects without confidence field (legacy) → all included (backward compat with default 1.0)
- `test_threshold_boundary` — claim with confidence=0.5 exactly → included (>= threshold)
- `test_claim_confidence_0499_excluded` — claim with confidence=0.499 → excluded

## Failure modes

### Failure mode 1: All claims filtered (empty claims block)
**Detection**: All claims for a section have confidence < 0.5 → claims block is empty → LLM generates generic content
**Resolution**: This is acceptable — better than generating hallucinated content. The "EVIDENCE ABSENT" path in section_prompt.py handles empty evidence gracefully.
**Gate**: Verify section_prompt handles empty claims list without crash

### Failure mode 2: Legacy claim objects without confidence field
**Detection**: Older UnderstandingBundle loaded from checkpoint has no confidence field → AttributeError
**Resolution**: Use `getattr(c, 'confidence', 1.0)` for safe access with default 1.0. Or check `hasattr(claim_obj, 'confidence')`.
**Gate**: Unit test with claim object missing confidence field → passes (treated as 1.0)

### Failure mode 3: Threshold too aggressive in production
**Detection**: A+B rate drops after this change because too many valid claims are filtered
**Resolution**: Tune threshold. Starting at 0.5 preserves: docstring (1.0), llm (0.75), deterministic (0.5). Drops only: llm_fallback (0.35).
**Gate**: Run pilot and compare grade distribution before/after

## Task-specific review checklist
1. [ ] `_CLAIM_CONFIDENCE_THRESHOLD = 0.5` defined as module constant (not magic number)
2. [ ] Filter uses `>=` (not `>`) so threshold=0.5 claims are included
3. [ ] Backward compat: claims without confidence field treated as 1.0
4. [ ] DEBUG log when claims are filtered (not WARNING — expected behavior)
5. [ ] Unit test: low-confidence claim absent from prompt
6. [ ] Unit test: high-confidence claim present in prompt
7. [ ] No regressions in full generate test suite

## Deliverables
1. Updated `src/launcher/workers/generate/section_prompt.py`
2. Unit tests
3. `reports/TC-HAL-08/evidence.md`

## Acceptance checks
1. [ ] `test_low_confidence_claims_filtered` PASS
2. [ ] `test_all_high_confidence_claims_included` PASS
3. [ ] `test_no_confidence_field_legacy_compat` PASS
4. [ ] Full generate test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -q
```

## Integration boundary proven
**Upstream**: `Claim.confidence` populated by TC-HAL-06
**Downstream**: LLM generation prompt contains only high-confidence claims
**Contract**: `Claim.confidence: float >= 0.5` to pass filter
