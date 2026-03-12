---
id: TC-HAL-06
title: "Add confidence field to Claim model"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-11"
tags: ["hallucination", "models", "understand"]
depends_on: ["TC-HAL-01", "TC-HAL-04"]
allowed_paths:
  - plans/taskcards/TC-HAL-06_claim-confidence-field.md
  - src/launcher/models/claims.py
  - src/launcher/workers/understand/extract/_validation.py
  - specs/schemas/understanding_bundle.schema.json
  - tests/unit/models/test_claims.py
evidence_required:
  - reports/TC-HAL-06/evidence.md
---

# Taskcard TC-HAL-06 — Add confidence field to Claim model

## Objective
Add a numeric `confidence: float = 1.0` field to the `Claim` model. Assign confidence values by claim source: `docstring`→1.0, `llm`→0.75, `llm_fallback`→0.35, `deterministic`→0.5. Claims downgraded by the contradiction resolver → 0.0. This enables downstream phases (Generate, Evaluate) to filter by evidence strength.

## Required spec references
- `specs/claims_evidence.md` (Section: Claim schema)
- `specs/schemas/understanding_bundle.schema.json`

## Scope
### In scope
- Add `confidence: float = 1.0` to `Claim` model in `claims.py`
- Assign confidence by claim_source in `_validate_and_normalize_claims()` in `_validation.py`
- Set `confidence = 0.0` on claims downgraded by contradiction resolver (visibility=internal from resolver)
- Update `understanding_bundle.schema.json` to add `confidence` property to claim objects
- Add `confidence_distribution` bucket counts to extraction_audit output

### Out of scope
- Changing claim_source values
- Downstream filtering (TC-HAL-08 handles Generate; TC-HAL-09 handles Evaluate)

## Inputs
- `src/launcher/models/claims.py` — Claim model
- `src/launcher/workers/understand/extract/_validation.py` — normalization pipeline
- `specs/schemas/understanding_bundle.schema.json` — schema for claim objects

## Outputs
- Updated `claims.py` with `confidence` field
- Updated `_validation.py` with confidence assignment
- Updated `understanding_bundle.schema.json` with `confidence` in claims array items
- Unit tests

## Allowed paths
- plans/taskcards/TC-HAL-06_claim-confidence-field.md
- src/launcher/models/claims.py
- src/launcher/workers/understand/extract/_validation.py
- specs/schemas/understanding_bundle.schema.json
- tests/unit/models/test_claims.py

### Allowed paths rationale
Model change requires updating claims.py and schema. Validation pipeline assigns the value. Tests verify assignment logic.

## Implementation steps

### Step 1: Add confidence field to Claim model
In `src/launcher/models/claims.py:19–28`, add after `tier_relevance`:
```python
confidence: float = 1.0  # Evidence strength: docstring=1.0, llm=0.75, llm_fallback=0.35, deterministic=0.5
```

### Step 2: Assign confidence in _validate_and_normalize_claims()
In `src/launcher/workers/understand/extract/_validation.py`, in the normalization loop after claim_id generation, add:
```python
# Assign confidence by claim source (TC-HAL-06)
_CONFIDENCE_BY_SOURCE: dict[str, float] = {
    "docstring": 1.0,
    "llm": 0.75,
    "deterministic": 0.5,
    "llm_fallback": 0.35,
}
_confidence_val = _CONFIDENCE_BY_SOURCE.get(claim.get("claim_source", "llm"), 0.75)
```
Then when building the Claim object, pass `confidence=_confidence_val`.

If working with Claim objects (already normalized): in the normalization loop, update each claim's confidence:
```python
claim = claim.model_copy(update={"confidence": _CONFIDENCE_BY_SOURCE.get(claim.claim_source, 0.75)})
```

### Step 3: Set confidence=0.0 for contradiction-downgraded claims
In `_entry.py`, after `resolve_contradictions()` runs (B.4b), scan claims and set confidence=0.0 for any claim with `visibility="internal"` that came from the resolver:
```python
# TC-HAL-06: Set confidence=0.0 for resolver-downgraded claims
for i, claim in enumerate(claims):
    if claim.visibility == "internal" and claim.confidence > 0.0:
        claims[i] = claim.model_copy(update={"confidence": 0.0})
```
Note: visibility=internal claims will be filtered by _validate_and_normalize_claims anyway, but setting confidence=0.0 before filtering ensures the confidence distribution metric is accurate.

Actually, since resolver-downgraded claims become visibility=internal and are then filtered by _validate_and_normalize_claims, they won't appear in the final claims list. The confidence=0.0 concept applies to claims that PASS the resolver but are still low-confidence. So confidence assignment by claim_source is sufficient here.

### Step 4: Update understanding_bundle.schema.json
In the claims array item schema, add:
```json
"confidence": {
  "type": "number",
  "minimum": 0.0,
  "maximum": 1.0,
  "description": "Evidence strength: 1.0=docstring, 0.75=llm, 0.5=deterministic, 0.35=llm_fallback"
}
```

### Step 5: Add unit tests
Add to `tests/unit/models/test_claims.py` (or create it):
- `test_claim_confidence_default` — Claim created without confidence → defaults to 1.0
- `test_confidence_assigned_by_source_docstring` — claim_source="docstring" → confidence=1.0
- `test_confidence_assigned_by_source_llm_fallback` — claim_source="llm_fallback" → confidence=0.35
- `test_confidence_range_valid` — confidence must be 0.0–1.0 range (schema validation)

## Failure modes

### Failure mode 1: Existing tests hardcode Claim construction without confidence
**Detection**: Tests fail with unexpected keyword argument or field mismatch
**Resolution**: `confidence: float = 1.0` has a default value → backward compatible. Existing tests that construct Claim() without confidence get 1.0 automatically.
**Gate**: Full test suite must pass with 0 regressions

### Failure mode 2: Schema validation rejects existing bundles without confidence field
**Detection**: Loading old extraction_audit.json/understanding_bundle.json fails schema validation
**Resolution**: Add `confidence` as non-required field in schema. Existing bundles without it are still valid.
**Gate**: Schema validation test with a bundle that has no confidence field → should pass

### Failure mode 3: claim_source value not in _CONFIDENCE_BY_SOURCE
**Detection**: New claim_source values added in future → get default 0.75 (reasonable fallback)
**Resolution**: Use `.get(claim.claim_source, 0.75)` as fallback. Log unknown sources.
**Gate**: Unit test with unknown claim_source → gets 0.75

## Task-specific review checklist
1. [ ] `confidence: float = 1.0` has default value (backward compatible)
2. [ ] All 4 claim_source values have explicit confidence mappings
3. [ ] Schema updated with `confidence` as optional (non-required) property
4. [ ] Unit test: each claim_source → correct confidence value
5. [ ] Unit test: confidence field missing in legacy data → default 1.0
6. [ ] No regressions in full test suite
7. [ ] `_CONFIDENCE_BY_SOURCE` dict is module-level constant (not recreated per call)

## Deliverables
1. Updated `src/launcher/models/claims.py`
2. Updated `src/launcher/workers/understand/extract/_validation.py`
3. Updated `specs/schemas/understanding_bundle.schema.json`
4. Unit tests
5. `reports/TC-HAL-06/evidence.md`

## Acceptance checks
1. [ ] `test_claim_confidence_default` PASS
2. [ ] `test_confidence_assigned_by_source_docstring` PASS
3. [ ] `test_confidence_assigned_by_source_llm_fallback` PASS
4. [ ] Full test suite 0 regressions

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/models/ -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -q
```

## Integration boundary proven
**Upstream**: `_validate_and_normalize_claims()` assigns confidence
**Downstream**: `section_prompt.py` filters by confidence (TC-HAL-08); `hallucination_rate.py` reads confidence (TC-HAL-09)
**Contract**: `Claim.confidence: float` in range [0.0, 1.0]
