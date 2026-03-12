# Hallucination Reduction Sprint — Chat-Materialized Plan

**Created**: 2026-03-11T23:00:00
**Source**: zippy-pondering-plum.md (ExitPlanMode approved)
**Mission**: Reduce hallucination to ≤5% across claims and generated content

---

## Context

Current run (260311_164147_3d_python_3f6f) shows:
- 412/435 claims (94.7%) from `llm_fallback` (LLM call failed; deterministic fallback ran)
- 20 factual_accuracy=HIGH findings all tracing to hallucinated API surface
- Hallucinated items: Node.create_child_node(), parent_nodes(), FbxElement, FbxScope, entity.visible, Mesh.create_box(), FileFormat.OBJ, Scene.properties(), root_node() as callable

---

## Goals

1. Fix contradiction resolver to catch property-as-method hallucinations
2. Fix contradiction resolver to catch lowercase API identifier hallucinations
3. Fix contradiction resolver to verify enum member names
4. Detect LLM failure and apply strict filtering to fallback claims
5. Fix docstring harvesting to not append () to properties
6. Add confidence field to Claim model for downstream filtering
7. Validate snippet import paths against api_surface.import_allowlist
8. Filter low-confidence claims from Generate prompts
9. Add hallucination_rate deterministic check in Evaluate
10. Add hallucination metrics to extraction_audit.json

---

## Assumptions

- [ ] UNVERIFIED: LLM call failure rate is consistent (not one-time network issue)
- [x] VERIFIED: contradiction resolver uses flat api_ids set (code confirmed)
- [x] VERIFIED: Check 2 only matches PascalCase/backtick (code confirmed at line 104-109)
- [x] VERIFIED: api_identifiers includes both methods and properties (_api_surface.py lines 280-287)
- [x] VERIFIED: _harvest_docstring_claims_raw appends () to all typed_methods (_entry.py line 439)
- [x] VERIFIED: No confidence field on Claim model (claims.py confirmed)

---

## Steps (numbered)

### Phase 1 — Contradiction Resolver Hardening (no schema changes)

1. **TC-HAL-01**: In `_contradiction_resolver.py`, build `method_ids` (from `cls.methods`) and `property_ids` (from `cls.properties`) separate sets. Add Check 2b: scan claim text for `identifier()` patterns; if identifier is only in `property_ids`, downgrade to internal.

2. **TC-HAL-02**: In `_contradiction_resolver.py`, for `kind == "api"` claims, extract dot-notation identifiers `\b\w+\.([a-z_]\w+)\(?`. If identifier not in `api_ids` (case-insensitive), downgrade to internal.

3. **TC-HAL-03**: In `_contradiction_resolver.py`, build `enum_member_map` from `api_surface.enums`. Add Check 2c: scan for `ClassName.MEMBER` patterns; if class is known enum and member not in enum_member_map, downgrade to internal.

### Phase 2 — Claim Source Quality (no schema changes)

4. **TC-HAL-04**: In `_llm.py`, emit warning event on fallback. In `_entry.py`, compute `fallback_rate`; if > 0.6, drop `llm_fallback` claims with `kind == "api"` where identifier not in `api_surface.api_identifiers`. Add `llm_fallback_rate` to audit.

5. **TC-HAL-05**: In `_entry.py:_harvest_docstring_claims_raw`, build `property_names` set from `brief.typed_properties`. When rendering `typed_methods` entry: if `ms.name` in `property_names`, render without `()`. Also add per-property claims for properties with docstrings > 20 chars.

### Phase 3 — Model Change + Downstream (requires schema change)

6. **TC-HAL-06**: Add `confidence: float = 1.0` to `Claim` in `claims.py`. In `_validation.py`, assign confidence by claim_source: docstring→1.0, llm→0.75, llm_fallback→0.35, deterministic→0.5. Claims downgraded by resolver → 0.0. Update `understanding_bundle.schema.json` to add `confidence` to claim object. Add `confidence_distribution` to `extraction_audit.json`.

7. **TC-HAL-07**: In `_snippets.py`, after extraction, validate each snippet's import lines against `api_surface.import_allowlist`. Flag invalid-import snippets; filter before passing downstream.

8. **TC-HAL-08**: In `section_prompt.py`, when building claims block, filter to `confidence >= 0.5` only. Log filtered count per section.

9. **TC-HAL-09**: New file `checks/hallucination_rate.py`. Compute `low_confidence_claims / total_claims` per page. CRITICAL if rate > 0.05. Register in `evaluate/worker.py`. Add `hallucination_rate` to `EvaluationReport`.

### Phase 4 — Measurement

10. **TC-HAL-10**: In `understand/worker.py`, add `hallucination_metrics` block to `extraction_audit.json` with: `llm_fallback_rate`, `unverified_api_claims_dropped`, `confidence_distribution`, `method_property_contradictions`, `enum_member_contradictions`, `lowercase_api_contradictions`, `invalid_import_snippets`, `estimated_hallucination_rate`.

---

## Acceptance Criteria

| Criterion | Target |
|-----------|--------|
| extraction_audit.hallucination_metrics present | Yes |
| estimated_hallucination_rate | < 0.05 |
| Claims with confidence < 0.5 in Generate prompts | 0 |
| factual_accuracy=HIGH findings | 0 |
| parent_nodes/excluded/root_node as callable methods in output | 0 |
| FbxElement/FbxScope in output | 0 |
| All tests pass (PYTHONHASHSEED=0) | Yes |

---

## Risks + Rollback

- Risk 1: Confidence threshold drops valid claims → reduce threshold to 0.3 if too many valid api claims drop
- Risk 2: Strict fallback filter drops too many llm_fallback claims → tune rate threshold from 0.6 to 0.8 if needed
- Risk 3: Property/method split breaks classes where same identifier is both (unlikely but possible) → add both-side check
- Rollback: All changes are additive (new fields, stricter filters). Rollback by reverting confidence threshold to 0.0 (pass-all) and removing strict fallback filter.

---

## Evidence Commands

```bash
# Run targeted tests after each phase
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -x

# Verify contradiction resolver catches property-as-method
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -k "contradiction" -v

# Verify extraction_audit has hallucination_metrics
cat runs/*/extraction_audit.json | python -c "import json,sys; d=json.load(sys.stdin); assert 'hallucination_metrics' in d"

# Full test suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short

# Verify no property-as-method in generated content
grep -r "parent_nodes()" publish/ | wc -l  # should be 0
grep -r "root_node()" publish/ | wc -l     # should be 0
```

---

## Open Questions

(must be empty by end of sprint)
