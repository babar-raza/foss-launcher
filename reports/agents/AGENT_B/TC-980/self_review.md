# TC-980 Self-Review: Fix W4 claim_group Field Mismatch

## 12D Checklist

1. **Determinism:** All claim ID lists use `sorted()` for deterministic ordering. No dict iteration order dependency. PASS.
2. **Dependencies:** No new dependencies added. PASS.
3. **Documentation:** TC-980 taskcard documents the fix. Evidence file created. PASS.
4. **Data preservation:** No data loss. Claims existed in product_facts, just were not being resolved. PASS.
5. **Deliberate design:** Uses `claim_groups` dict (the authoritative grouping source) instead of non-existent per-claim `claim_group` field. PASS.
6. **Detection:** Gate 14 will report claim counts per page. 0 claims = regression indicator. PASS.
7. **Diagnostics:** W4 logger already logs planned pages and their claim counts. PASS.
8. **Defensive coding:** `isinstance(claim_groups, dict)` guard handles legacy list format. Empty dict/list defaults on all `.get()` calls. PASS.
9. **Direct testing:** 11 new unit tests + 22 updated existing tests. All 33 pass. PASS.
10. **Deployment safety:** Change only affects claim selection logic within `plan_pages_for_section()`. PASS.
11. **Delta tracking:** Modified exactly 2 files within allowed paths. PASS.
12. **Downstream impact:** W5 will receive non-empty `required_claim_ids` enabling claim marker injection. PASS.

## Task-Specific Review Checklist

1. [x] `claim_groups_dict` variable declared early (line 670) and used consistently
2. [x] Products section gets `key_features + install_steps` claims (sorted, capped at 10)
3. [x] Reference section gets `key_features` claims (sorted, capped at 5)
4. [x] KB section resolves full claim objects from `claim_groups_dict` IDs via set lookup
5. [x] KB FAQ page has non-empty `required_claim_ids` (install_steps + limitations, sorted, capped at 5)
6. [x] No `claim_group` string lookup on individual claims remains in products/reference/kb sections
7. [x] Tests updated and passing (33/33)
8. [x] Deterministic ordering preserved (sorted claim IDs everywhere)

## Acceptance Checks

1. [x] Products overview page has >0 `required_claim_ids` — verified by `test_products_overview_has_claim_ids`
2. [x] Reference api-overview page has >0 `required_claim_ids` — verified by `test_reference_api_overview_has_claim_ids`
3. [x] KB FAQ page has >0 `required_claim_ids` — verified by `test_kb_faq_has_claim_ids`
4. [x] All tests pass (pytest exit code 0) — 33 passed
5. [x] No per-claim `claim_group` field access remains in products/reference/kb sections of `plan_pages_for_section()`

## Remaining Per-Claim claim_group Usage (Out of Scope)

Two lines in the docs section still use `c.get("claim_group", "")`:
- Line 744: docs getting-started — has fallback to `claims[:3]` at line 754
- Line 776: docs developer-guide — has fallback to `claims[:len(workflows)]` at lines 780-781

These are noted but out of TC-980 scope. They produce degraded but non-empty results due to their fallback logic.

## Verification Results
- [x] Tests: 33/33 PASS
- [ ] Pilot 3D: Requires pilot re-run (not in TC-980 scope)
- [ ] Pilot Note: Requires pilot re-run (not in TC-980 scope)
