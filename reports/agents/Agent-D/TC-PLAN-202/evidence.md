# TC-PLAN-202 Evidence: Evidence-Gated Generation with Numeric evidence_score

## Date: 2026-03-14
## Owner: Agent-D
## Status: Done

## Changes Made

### 1. `src/launcher/models/plan.py`
- Added `evidence_score: float = Field(default=1.0, ...)` to `PlannedPage` model
- Positioned before existing `evidence_sufficient` field for logical grouping
- Default 1.0 ensures backward compatibility with existing pages

### 2. `src/launcher/workers/planner/plan.py`
- Added `_EVIDENCE_THRESHOLDS` dict with role-specific thresholds (11 roles)
- Added `_DEFAULT_THRESHOLD = 0.15` for unknown roles
- Added `_compute_evidence_score(page, api_surface, claims)` function:
  - Reference pages: scored by typed_methods docstring coverage in class_briefs
  - Content pages: scored by high-confidence claim ratio
  - Low-bar pages: scored by existence of any evidence
  - All scores blended with snippet validity factor (0.7 * base + 0.3 * snippet_factor)
- Called `_compute_evidence_score()` after `_assign_claims()` in `run_plan()`
- Uses `model_copy(update={...})` for frozen PlannedPage

### 3. `src/launcher/workers/generate/worker.py`
- Added threshold check at start of `_generate_page()`
- Pages with `evidence_score < threshold` get `render_minimal_stub()` instead of LLM generation
- Emits `page_evidence_below_threshold` event with score details
- Returns early with stub PageIR (0 LLM calls, 1 fallback count)

### 4. `src/launcher/workers/generate/fallback.py`
- Added `render_minimal_stub(page_plan, product, class_briefs=None)` function
- Produces honest minimal page acknowledging limited documentation
- Lists available methods/properties from class_briefs when available
- Includes import example

### 5. Tests (9 new tests)

**`tests/unit/workers/test_planner_topic_starvation.py`** (5 tests):
- `test_evidence_score_reference_page_with_docstrings`: score > 0.5 PASS
- `test_evidence_score_reference_page_empty_docstrings`: score < 0.2 PASS
- `test_evidence_score_content_page_with_claims`: score > 0.2 PASS
- `test_evidence_score_content_page_no_claims`: score ~ 0.15 PASS
- `test_evidence_score_default_backward_compatible`: default 1.0 PASS

**`tests/unit/workers/test_generate.py`** (4 tests):
- `test_evidence_threshold_gates_generation`: below-threshold page gets stub PASS
- `test_evidence_score_backward_compatible`: default 1.0 passes all thresholds PASS
- `test_evidence_score_above_threshold_not_stubbed`: above-threshold not stubbed PASS
- `test_render_minimal_stub_with_class_briefs`: stub lists methods PASS

## Test Results

```
Full suite: 4502 passed, 3 failed (pre-existing), 65 skipped
TC-PLAN-202 tests: 9 passed, 0 failed
```

Pre-existing failures (not introduced by this taskcard):
- `TestBacktickApiNames::test_longest_first_matching`
- `TestSectionIdMapping::test_section_skip_reuses_cached_section`
- `TestSectionIdMapping::test_section_skipped_event_emitted`

## Acceptance Checks

1. [x] evidence_score computed for all planned pages (in run_plan after _assign_claims)
2. [x] Reference pages with zero docstrings get score < 0.2 (test_evidence_score_reference_page_empty_docstrings)
3. [x] Reference pages with full docstrings get score > 0.5 (test_evidence_score_reference_page_with_docstrings)
4. [x] Below-threshold pages produce minimal stubs (test_evidence_threshold_gates_generation)
5. [x] Full test suite: 4502 passed, 0 new failures
6. [x] New tests: 9 (exceeds minimum of 6)

## Backward Compatibility

- `evidence_score` defaults to 1.0, which passes all thresholds
- Existing `evidence_sufficient` boolean is untouched and still functions
- Existing `_apply_evidence_gate()` logic unchanged
- No schema changes required (Pydantic model field with default)
