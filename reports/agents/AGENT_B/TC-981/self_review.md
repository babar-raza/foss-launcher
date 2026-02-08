# TC-981 Self-Review

## 12D Checklist

1. **Determinism**: Symbol extraction uses frequency + alphabetical tie-break. Claim IDs sorted. PASS
2. **Dependencies**: No new external dependencies. Only added import re (stdlib). PASS
3. **Documentation**: TC-981 taskcard, evidence.md, self_review.md. PASS
4. **Data preservation**: Token values derived from actual product claims. Fallback chain preserves backward compat. PASS
5. **Deliberate design**: Fallback: product_facts -> family-based naming -> generic. PASS
6. **Detection**: Gate 11 catches malformed tokens; tests verify non-empty claim_ids. PASS
7. **Diagnostics**: Logger messages for token generation preserved. PASS
8. **Defensive coding**: product_facts=None fallback at every level. PASS
9. **Direct testing**: 21 new unit tests covering all changes. PASS
10. **Deployment safety**: Backward compatible (Optional parameter with default=None). PASS
11. **Delta tracking**: Modified generate_content_tokens, fill_template_placeholders, execute_ia_planner. PASS
12. **Downstream impact**: W5 receives product-specific tokens and non-empty claim_ids. PASS

## Task-specific Review Checklist

1. [x] generate_content_tokens() accepts product_facts parameter
2. [x] No hardcoded Scene, Entity, Node, Mesh in token values
3. [x] Note pilot tokens produce Note-specific class names (NoteDocument, NotePage)
4. [x] fill_template_placeholders() assigns non-empty required_claim_ids
5. [x] Title has no leading space
6. [x] execute_ia_planner() passes product_facts to both functions
7. [x] All tests pass (68/68)
8. [x] Backward compatible (product_facts=None works)

## Verification Results
- Tests: PASS (35 token + 33 content distribution)
- Note pilot tokens: Note-specific (NoteDocument, NotePage)
- 3D pilot tokens: 3D-specific (Scene, Entity, Property, Transform)

## Pre-existing Test Failures (not introduced by TC-981)
- test_tc_903_vfv: assertion mismatch (pre-existing)
- test_validate_windows_reserved_names: nul file in repo (pre-existing)
- test_plan_pages_minimal_tier: expects <=2 docs pages, stale from TC-972 (pre-existing)
- test_tc_902 fill_template tests: use fake template paths (pre-existing)
