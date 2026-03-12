# Healing Plan: TC-HAL Sprint Gaps
Date: 2026-03-11
Source: Phase 1 self-review — Hallucination Reduction Sprint

## Context
TC-HAL-01..TC-HAL-10 completed. 4121 tests pass. However, Phase 1 self-review identified:
- Missing file-read evidence for all implementation claims (operating from context summary only)
- GAP-1: `EvaluationReport` model missing `hallucination_rate: float` field
- GAP-2: No unit test asserting `hallucination_metrics` shape in `extraction_audit`
- GAP-3: `Snippet.source_type` Literal not extended with `"invalid_import"` — latent Pydantic runtime error

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| E-001 | Evidence verification: read all TC-HAL modified files | SR-01 |
| GAP-1 | `hallucination_rate` field missing from `EvaluationReport` | SR-02 |
| GAP-2 | `hallucination_metrics` shape not covered by unit test | SR-03 |
| GAP-3 | `Snippet.source_type` Literal missing `"invalid_import"` | SR-04 |

---

## SR-01: Evidence Verification

**Status**: Done
**Gap linkage**: E-001
**Role**: Senior engineer — verify existing implementations are correctly wired

### Scope
- Fix: None — read-only verification pass
- Allowed paths: none (read only)
- Forbidden paths: no code changes in this taskcard

### Acceptance checks
- [ ] `_contradiction_resolver.py` contains `method_ids`, `property_ids`, `enum_member_map`, Check 2b, Check 2c, Check 2d
- [ ] `_entry.py` contains `_filter_fallback_api_claims`, `property_name_set` in `_harvest_docstring_claims_raw`
- [ ] `_validation.py` contains `_CONFIDENCE_BY_SOURCE` and confidence assignment
- [ ] `section_prompt.py` contains `_CLAIM_CONFIDENCE_THRESHOLD` and filter
- [ ] `evaluate/worker.py` contains hallucination_rate check registration
- [ ] `understand/worker.py` contains `hallucination_metrics` audit block
- [ ] `models/claims.py` contains `confidence: float = 1.0` field

### Now (runbook)
```bash
grep -n "method_ids\|property_ids\|enum_member_map" src/launcher/workers/understand/extract/_contradiction_resolver.py | head -20
grep -n "_filter_fallback_api_claims\|property_name_set" src/launcher/workers/understand/extract/_entry.py | head -10
grep -n "_CONFIDENCE_BY_SOURCE\|confidence" src/launcher/workers/understand/extract/_validation.py | head -10
grep -n "_CLAIM_CONFIDENCE_THRESHOLD\|confidence" src/launcher/workers/generate/section_prompt.py | head -10
grep -n "hallucination_rate\|check_hallucination" src/launcher/workers/evaluate/worker.py | head -10
grep -n "hallucination_metrics" src/launcher/workers/understand/worker.py | head -10
grep -n "confidence" src/launcher/models/claims.py | head -10
```

---

## SR-02: Add `hallucination_rate` to `EvaluationReport`

**Status**: Done
**Gap linkage**: GAP-1
**Role**: Senior engineer — drop-in, production-ready field addition

### Scope
- Fix: Add `hallucination_rate: float = 0.0` to `EvaluationReport` in `models/evaluation.py`
- Allowed paths: `src/launcher/models/evaluation.py`
- Forbidden paths: do not change evaluate worker or check logic

### Acceptance checks
- [ ] `EvaluationReport` has `hallucination_rate: float = 0.0`
- [ ] Field is optional with default (backward-compatible)
- [ ] Existing model tests still pass
- [ ] `python -c "from launcher.models.evaluation import EvaluationReport; r = EvaluationReport(); print(r.hallucination_rate)"` prints `0.0`

### Deliverables
- `src/launcher/models/evaluation.py`: add field with default

### Hard rules
- Keep all existing public signatures intact
- `= 0.0` default — no breaking change to existing serialized reports
- No new dependencies

### Review dimensions: 5/5 means
- Correctness: field appears in model with correct type and default
- Wiring: `EvaluationReport` instantiation works without providing the field
- Tests: all evaluation model tests pass

### Now (runbook)
```bash
grep -n "class EvaluationReport\|hallucination" src/launcher/models/evaluation.py
# Add field after reading
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q -k "evaluat" --tb=short 2>&1 | tail -5
```

---

## SR-03: Unit test for `hallucination_metrics` audit shape

**Status**: Done
**Gap linkage**: GAP-2
**Role**: Senior engineer — add regression guard

### Scope
- Fix: Add `test_hallucination_metrics_shape` test
- Allowed paths: `tests/unit/workers/understand/`
- Forbidden paths: no changes to production code

### Acceptance checks
- [ ] Test asserts `hallucination_metrics` key present in audit dict
- [ ] Test asserts all sub-keys: `confidence_distribution`, `estimated_hallucination_rate`, `low_confidence_claim_count`, `llm_fallback_rate`, `total_claim_count`
- [ ] Test passes with `PYTHONHASHSEED=0`
- [ ] Test is deterministic (no LLM calls, no network)

### Deliverables
- New test function in existing test file OR new `test_hallucination_audit.py`

### Hard rules
- No network in tests
- No mocking of production modules — use real implementations with fixture data

### Now (runbook)
```bash
ls tests/unit/workers/understand/
grep -n "hallucination" tests/unit/workers/understand/*.py 2>/dev/null | head -20
```

---

## SR-04: Extend `Snippet.source_type` Literal

**Status**: Done
**Gap linkage**: GAP-3
**Role**: Senior engineer — extend Literal without breaking existing values

### Scope
- Fix: Add `"invalid_import"` to `Snippet.source_type` Literal in `models/claims.py`
- Allowed paths: `src/launcher/models/claims.py`
- Forbidden paths: no other files (snippets.py already uses the value)

### Acceptance checks
- [ ] `Snippet.source_type` Literal includes `"invalid_import"`
- [ ] `python -c "from launcher.models.claims import Snippet; s = Snippet(code='x', source_type='invalid_import'); print(s.source_type)"` exits 0
- [ ] All existing claims tests still pass
- [ ] Backward-compatible: `"extracted"`, `"generated"`, `"synthetic"` still valid

### Deliverables
- `src/launcher/models/claims.py`: extend Literal on `Snippet.source_type`

### Hard rules
- Do not change the default (still `"extracted"`)
- Keep the backward-compat comment about `"synthetic"`

### Now (runbook)
```bash
grep -n "source_type" src/launcher/models/claims.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ tests/unit/models/ -q --tb=short 2>&1 | tail -5
```
