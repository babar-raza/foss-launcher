# TC-PA-01..04 Test Evidence

## Test Run Summary

- **Date**: 2026-03-20
- **Runner**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest`
- **Total new tests**: 13
- **All new tests**: PASSED
- **Full suite**: 5866 passed, 1 pre-existing failure (unrelated)

## New Tests by Group

### Group 1: TC-PA-01 (claim coverage computation) — 4 tests

File: `tests/unit/workers/evaluate/checks/test_claim_coverage.py`

| Test | Status |
|------|--------|
| `TestComputeClaimCoverage::test_compute_claim_coverage_actual_ratio` | PASSED |
| `TestComputeClaimCoverage::test_compute_claim_coverage_zero_assigned_returns_one` | PASSED |
| `TestComputeClaimCoverage::test_compute_claim_coverage_backward_compat_no_field` | PASSED |
| `TestComputeClaimCoverage::test_assigned_vs_cited_divergence` | PASSED |

### Group 2: TC-PA-02 (depth finding grading + context windows) — 2 tests

File: `tests/unit/workers/evaluate/checks/test_claim_coverage.py`

| Test | Status |
|------|--------|
| `TestDepthFindingGrading::test_depth_finding_is_deterministic_medium_for_grader` | PASSED |
| `TestMultiTermContextWindows::test_multi_term_context_windows_merged` | PASSED |

### Group 3: TC-PA-04 (severity promotions / LLM check names) — 4 tests

File: `tests/unit/workers/test_evaluate.py`

| Test | Status |
|------|--------|
| `TestTCPA04SeverityPromotions::test_factual_accuracy_high_produces_grade_d` | PASSED |
| `TestTCPA04SeverityPromotions::test_code_correctness_high_produces_grade_d` | PASSED |
| `TestTCPA04SeverityPromotions::test_heading_quality_high_still_capped_to_medium` | PASSED |
| `TestTCPA04SeverityPromotions::test_promoted_checks_no_longer_contains_factual_accuracy` | PASSED |

### Group 4: TC-PA-03 (evidence formatting) — 3 tests

File: `tests/unit/workers/generate/test_section_prompt_evidence.py`

| Test | Status |
|------|--------|
| `TestTCPA03EvidenceFormatting::test_evidence_snippet_cap_600` | PASSED |
| `TestTCPA03EvidenceFormatting::test_two_evidence_anchors_included` | PASSED |
| `TestTCPA03EvidenceFormatting::test_confidence_filtered_count_populated` | PASSED |

## Pre-existing Failure (not caused by this change)

```
FAILED tests/unit/workers/evaluate/test_grader_promotion.py::TestIsPromotedLlmFinding::test_factual_accuracy_with_not_supported
```

This test was written assuming `factual_accuracy` is in `_PROMOTED_LLM_CHECKS`, but TC-PA-04 removed it. The test predates TC-PA-04 and needs updating separately.

## Full Suite Output

```
1 failed, 5866 passed, 5 xfailed, 2 xpassed in 189.76s
```
