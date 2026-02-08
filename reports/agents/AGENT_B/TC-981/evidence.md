# TC-981 Evidence: Fix W4 Template Claims and Product-Specific Tokens

## Summary
TC-981 fixed three interconnected issues in the W4 IAPlanner:
1. RC-2: Template pages getting empty required_claim_ids
2. RC-3: Hardcoded 3D-specific class names in generate_content_tokens()
3. RC-5: Title leading space when product_name is empty

## Files Modified

### src/launch/workers/w4_ia_planner/worker.py
- **Line 32**: Added module-level import re
- **Lines 681-684**: Fixed RC-5 title leading space with .strip() and family-based fallback
- **Lines 1360-1450**: NEW helper _extract_symbols_from_claims(product_facts, family)
- **Line 1458**: Added product_facts parameter to generate_content_tokens()
- **Lines 1612-1618**: Replaced hardcoded Scene/Entity/Node with product_facts-derived values
- **Line 1690**: Added product_facts parameter to fill_template_placeholders()
- **Lines 1753-1775**: NEW claim assignment logic for template pages using claim_groups
- **Line 1750**: Pass product_facts to generate_content_tokens() call
- **Line 1951**: Pass product_facts to fill_template_placeholders() in execute_ia_planner()

### tests/unit/workers/test_w4_docs_token_generation.py
- Updated imports to include _extract_symbols_from_claims and fill_template_placeholders
- Added TestExtractSymbolsFromClaims (8 tests)
- Added TestGenerateContentTokensWithProductFacts (6 tests)
- Added TestFillTemplatePlaceholdersClaimAssignment (4 tests)
- Added TestTitleLeadingSpaceFix (3 tests)

## Test Results

### TC-981 Tests: 35 passed
### TC-980 Tests: 33 passed
### Total: 68 passed, 0 failed

## Acceptance Criteria Verification

1. __BODY_KEY_SYMBOLS__ does NOT contain Scene for Note: PASS (NoteDocument, NotePage)
2. __BODY_POPULAR_CLASSES__ is product-specific: PASS (Scene, Entity, Property, Transform for 3D)
3. Template pages have >0 required_claim_ids: PASS
4. Title has no leading space: PASS
5. All tests pass: PASS (68/68)

## Determinism
- Symbol extraction uses frequency-based ranking with alphabetical tie-breaking
- All claim ID lists are sorted() before assignment
- No randomness, no set iteration without sorting
