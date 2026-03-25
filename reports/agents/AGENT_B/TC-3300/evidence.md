# TC-3300 Evidence — W4 Deterministic page_uid + Explainability Artifact

## Summary

Added deterministic `page_uid` to every planned page in page_plan.json. The uid uses non-slug discriminators (template_path, object_name, topic title, workflow_tag) with slug as fallback, making incremental preservation stable across slug changes.

## Phase 1: Initial Implementation (33 tests)

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py -v
# 33 passed

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_1760_incremental.py -v
# 32 passed (backward compat verified)

.venv/Scripts/python.exe -m pytest tests/ --tb=no
# 7522 passed, 13 skipped, 0 failed
```

## Phase 2: Healing SRs (SR-01 through SR-04, +16 tests)

**SR-01**: Triple collision fix + uniqueness guard
- `_assign_page_uids()` → `while uid in seen` loop with counter + safety valve (100 iter max)
- Uniqueness assertion after assignment: raises ValueError on duplicates
- 3 tests: triple collision, five-way collision, collision suffix format
- 2 tests: idempotency (no collisions), idempotency (with collisions)

**SR-02**: Platform/locale uid stability + template path portability
- Hash input: `section|role|discriminator|locale|platform` (locale before platform per user directive)
- Template path fallback: filename-only when `/specs/templates/` not found
- 3 tests: platform differentiation, baseline match, locale-platform ordering
- 2 tests: filename fallback, /specs/templates/ still works

**SR-03**: Rationale schema + claim selection summary
- `claim_selection_summary` added to `_build_page_plan_rationale()`: total_claims_assigned + pages_by_claim_kind
- `specs/schemas/page_plan_rationale.schema.json` created (additionalProperties: false)
- 3 tests: claim_kind counting, empty kind, multiple kinds
- 1 test: schema structure validation

**SR-04**: Observability + integration test
- `EVENT_ARTIFACT_WRITTEN` emitted after rationale write with artifact/path/total_pages
- `logger.debug` for preservation_match_uid and preservation_match_slug_fallback
- 2 tests: uid match logging, slug fallback logging (via @patch mock_logger)

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w4_page_uid.py -v
# 49 passed (33 original + 16 new)

.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_1760_incremental.py -v
# 32 passed (backward compat verified)

.venv/Scripts/python.exe -m pytest tests/ --tb=no
# 7588 passed, 13 skipped, 0 failed
```

## Deliverables

- [x] `compute_page_uid()` — deterministic page identity from non-slug metadata
- [x] `_assign_page_uids()` — while-loop collision resolution (triple+ safe) + uniqueness guard
- [x] `selection_source` field — set on all 5 construction paths
- [x] `_apply_page_preservation()` — uid-primary matching with slug fallback + match logging
- [x] `preservation_metadata` — populated with previous_page_uid, claim_overlap_score, should_preserve
- [x] `page_plan_rationale.json` — source distribution, claim_selection_summary, quota context, per-page metadata
- [x] `page_plan_rationale.schema.json` — new schema file
- [x] Schema updated — page_uid, selection_source, source, claim_kind, previous_page_uid
- [x] EVENT_ARTIFACT_WRITTEN emitted for rationale artifact
- [x] 49 tests — all passing
- [x] No regressions — 7588 passed, 0 failed

## Files Changed

| File | Change |
|------|--------|
| `src/launch/workers/w4_ia_planner/worker.py` | SR-01: while-loop collision + uniqueness guard; SR-02: locale+platform hash + template path filename fallback; SR-03: claim_selection_summary; SR-04: rationale event + preservation logging |
| `specs/schemas/page_plan_rationale.schema.json` | NEW: rationale artifact schema |
| `tests/unit/workers/test_w4_page_uid.py` | +16 tests (7 classes added: TestTripleCollision, TestAssignPageUidsIdempotency, TestPlatformLocaleUid, TestTemplatePathPortability, TestClaimSelectionSummary, TestRationaleSchemaValidation, TestPreservationLogging) |
| `plans/healing/11_tc3300_page_uid_healing.md` | All 4 SRs marked Done |
| `plans/taskcards/TC-3300.md` | allowed_paths updated (+rationale schema, +healing) |
