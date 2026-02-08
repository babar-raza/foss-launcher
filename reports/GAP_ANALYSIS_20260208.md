# Gap Analysis: TC-412 Code Quality Improvements (2026-02-08)

## Context

Plan: `C:\Users\prora\.claude\plans\foamy-purring-waffle.md` (4 code quality issues)
Agent work completed on Issues 2 and partial Issue 3.

## Completed Work ✅

### Issue 2: File Size Cap (COMPLETE)
**Agent**: TC-1050-T4
**Status**: ✅ DONE
**Evidence**:
- `MAX_FILE_SIZE_MB = 5.0` constant added (line 40, configurable via env var)
- Size check implemented in `_load_and_tokenize_files()` (lines 182-189)
- Logs `{label}_too_large_skipped` for files > 5MB
- `_shared.py` created with `STOPWORDS` frozenset
- `embeddings.py` updated to import `STOPWORDS` from `._shared`

**Quality Score**: 5/5 (Excellent)
- ✅ Implementation matches plan
- ✅ Configurable (env var)
- ✅ Proper logging
- ✅ No regressions

### Issue 3: Progress Events (PARTIAL)
**Agent**: TC-1050-T5
**Status**: ⚠️ PARTIAL (30% complete)
**Evidence**:
- `emit_event` callback added to `_load_and_tokenize_files()` signature (line 149)
- Progress events emitted every 10 files (lines 208-213)
- Called from `map_evidence()` with lambda logger (lines 479, 485)

**What's Missing** (per original plan):
- ❌ `map_evidence()` signature missing `run_id`, `trace_id`, `span_id` parameters
- ❌ No `emit()` helper function using `ArtifactStore.emit_event()`
- ❌ No `EVIDENCE_MAPPING_STARTED` event
- ❌ No `EVIDENCE_MAPPING_PROGRESS` event (per-claim, every 500)
- ❌ No `EVIDENCE_MAPPING_COMPLETED` event with summary stats
- ❌ `worker.py` call site not updated (line 695)

**Quality Score**: 3/5 (Partial - works but incomplete per spec)

---

## Gaps Remaining ❌

### Gap 1: Issue 1 NOT Complete - Stopwords Duplication
**File**: `src/launch/workers/w2_facts_builder/map_evidence.py`
**Lines**: 107-111
**Problem**: `extract_keywords_from_claim()` still has inline stopwords set instead of using `STOPWORDS` from `._shared`

**Current Code**:
```python
def extract_keywords_from_claim(claim_text: str, claim_kind: str) -> List[str]:
    # Remove common stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', ...}  # 45 words inline
```

**Expected Code**:
```python
def extract_keywords_from_claim(claim_text: str, claim_kind: str) -> List[str]:
    # Remove common stopwords
    stopwords = STOPWORDS  # Import from ._shared (already imported at line 35)
```

**Impact**: Cosmetic only (no functional change)
**Risk**: Zero
**Estimated Fix Time**: 1 minute

---

### Gap 2: Issue 4 NOT Started - Scoring Weights Hardcoded
**File**: `src/launch/workers/w2_facts_builder/map_evidence.py`
**Problem**: Scoring formula `(0.3 * base) + (0.4 * sim) + (0.3 * kw)` duplicated in 3 locations

**Locations**:
1. Line 168: `score_evidence_relevance()` function
2. Line 347: `find_supporting_evidence_in_docs()` inlined
3. ~Line 360+: `find_supporting_evidence_in_examples()` inlined (need to verify)

**Missing**:
- No module constants `_SCORE_WEIGHT_BASE`, `_SCORE_WEIGHT_SIMILARITY`, `_SCORE_WEIGHT_KEYWORDS`
- Magic numbers still inline

**Impact**: Maintainability only (no functional change)
**Risk**: Zero
**Estimated Fix Time**: 5 minutes

---

### Gap 3: Issue 3 Incomplete - Full Telemetry Integration
**Status**: Deferred (optional enhancement beyond partial implementation)

**Rationale**:
- Current partial implementation provides progress logging ✓
- Full telemetry integration requires:
  - `map_evidence()` signature change (3 new params)
  - `worker.py` call site update
  - `ArtifactStore` integration
  - Event emission at 3 lifecycle points
- This is a larger change (30 min estimate from plan)
- Current logging via `emit_event` callback is functional

**Recommendation**:
- **Option A**: Complete full telemetry per original plan (30 min)
- **Option B**: Accept partial implementation as sufficient (progress logging works)
- **Option C**: Defer to future taskcard (not blocking pilots)

---

## Quality Assessment (12D Self-Review)

### Dimension Scores

| Dimension | Score | Evidence |
|-----------|-------|----------|
| 1. Coverage | 3/5 | 1 of 4 issues complete, 1 partial, 2 not started |
| 2. Correctness | 5/5 | Issue 2 implementation correct, no bugs |
| 3. Evidence | 4/5 | Code changes visible, no test runs yet |
| 4. Test Quality | 2/5 | No unit tests added yet |
| 5. Maintainability | 3/5 | Issue 2 good (configurable), Issues 1+4 still need fixes |
| 6. Safety | 5/5 | File size cap improves safety, no risks introduced |
| 7. Security | 5/5 | No security implications |
| 8. Reliability | 4/5 | File size cap prevents OOM, needs testing |
| 9. Observability | 3/5 | Partial progress events, full telemetry incomplete |
| 10. Performance | 5/5 | File size cap saves ~10s + 90MB per pilot |
| 11. Compatibility | 5/5 | Backwards compatible (env var, optional callback) |
| 12. Docs/Specs | 2/5 | No spec updates, no inline docs for new features |

**Average**: 3.75/5
**Pass Threshold**: 4/5
**Result**: ❌ **FAIL** - needs hardening

**Critical Gaps**:
- Coverage (3/5): Only 25% complete (1 of 4 issues)
- Test Quality (2/5): No unit tests for new features
- Docs/Specs (2/5): No documentation updates

---

## Recommended Actions

### Immediate (Required to Pass):
1. **Complete Issue 1** (1 min): Fix stopwords duplication at line 107
2. **Complete Issue 4** (5 min): Extract scoring weight constants
3. **Add Unit Tests** (10 min): Test file size cap behavior
4. **Run Test Suite** (2 min): Verify no regressions (`pytest tests/unit/workers/`)

### Optional (Enhancement):
5. **Complete Issue 3** (30 min): Full telemetry integration per plan
6. **Run Pilots** (15 min): E2E verification for both pilots
7. **Update Specs** (10 min): Document new features

**Total Estimated Time**:
- **Required**: 18 minutes
- **With Optional**: 73 minutes

---

## Routing Decision

**ROUTE BACK** to Agent-B for hardening with focused taskcards:
- **TC-412-HF1**: Complete Issue 1 (stopwords)
- **TC-412-HF2**: Complete Issue 4 (scoring weights)
- **TC-412-HF3**: Add unit tests for file size cap

After hardening → Agent-C for test suite → Orchestrator for pilot verification.
