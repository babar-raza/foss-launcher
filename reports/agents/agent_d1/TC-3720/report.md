# TC-3720 Evidence Report: LLM-Enhanced Claim Extraction in W2 Facts Builder

Agent: agent_d1
Taskcard: TC-3720
Date: 2026-03-04

## Files Changed

| File | Status | Lines |
|------|--------|-------|
| `src/launch/workers/w2_facts_builder/llm_extractor.py` | CREATED | 519 |
| `src/launch/workers/w2_facts_builder/worker.py` | MODIFIED | +89 lines |
| `specs/schemas/run_config.schema.json` | MODIFIED | +32 lines |
| `tests/unit/workers/w2_facts_builder/__init__.py` | CREATED | 0 |
| `tests/unit/workers/w2_facts_builder/test_tc3720_llm_extraction.py` | CREATED | 495 |

## Commands Run

```
# Check test baseline
PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/ --collect-only 2>&1 | grep collected
# → 8625 tests collected

# Run new TC-3720 tests
PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/unit/workers/w2_facts_builder/test_tc3720_llm_extraction.py -v --tb=short

# Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/ --tb=short

# Verify pre-existing failures on main (without changes)
git stash
PYTHONHASHSEED=0 .venv/Scripts/python -m pytest tests/unit/io/test_atomic_taskcard.py ... --tb=line
git stash pop
```

## TC-3720 Test Results (21 passed)

```
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-8.4.2, pluggy-1.6.0
collected 21 items

tests\unit\workers\w2_facts_builder\test_tc3720_llm_extraction.py ...... [ 28%]
...............                                                          [100%]

======================== 21 passed, 1 warning in 1.10s ========================
```

## Tests Implemented (15 required + 6 additional helper tests)

1. `TestLlmExtractReturnsClaims::test_llm_extract_returns_raw_claims`
2. `TestSourceFileMissingRejected::test_source_file_missing_rejected`
3. `TestLowConfidenceNoSourceRejected::test_low_confidence_no_source_rejected`
4. `TestHighConfidenceNoSourceKept::test_high_confidence_no_source_kept`
5. `TestCountCapEnforced::test_count_cap_enforced`
6. `TestMaxPerKindEnforced::test_max_per_kind_enforced`
7. `TestRequireSourceCitationRejectsUnanchored::test_require_source_citation_true_rejects_unanchored`
8. `TestFabricatedMetricGuard::test_fabricated_metric_guard`
9. `TestFabricatedMetricGuard::test_is_fabricated_metric_detects_patterns` (extra)
10. `TestExtractionBundleWithinBudget::test_extraction_bundle_within_budget`
11. `TestFallbackToRegexOnLlmFailure::test_fallback_to_regex_on_llm_failure`
12. `TestLlmJsonParseErrorRetried::test_llm_json_parse_error_retried`
13. `TestDuplicateClaimsNotDeduplicated::test_duplicate_claims_not_deduplicated_in_extractor`
14. `TestChangelogLast3VersionsOnly::test_changelog_last_3_versions_only`
15. `TestChangelogLast3VersionsOnly::test_extract_changelog_last_3_versions_helper` (extra)
16. `TestVerifyClaimSourceExistingFile::test_verify_claim_source_existing_file`
17. `TestVerifyClaimSourceExistingFile::test_verify_claim_source_no_source_file` (extra)
18. `TestVerifyClaimSourceExistingFile::test_verify_claim_source_empty_source_file` (extra)
19. `TestVerifyClaimSourceMissingFile::test_verify_claim_source_missing_file`
20. `TestVerifyClaimSourceMissingFile::test_verify_claim_source_subdir_file` (extra)
21. `TestVerifyClaimSourceMissingFile::test_verify_claim_source_subdir_file_missing` (extra)

## Full Suite Results

```
12 failed (pre-existing), 8617 passed, 13 skipped, 3 xfailed
Total collected: 8646 (was 8625, +21 new tests)
```

Pre-existing failures verified on main branch BEFORE changes:
- tests/unit/io/test_atomic_taskcard.py (2 tests)
- tests/unit/orchestrator/test_run_loop_taskcard.py (1 test)
- tests/unit/test_validation_engine_golden.py (1 test)
- tests/unit/util/test_taskcard_loader.py (5 tests)
- tests/unit/workers/w9/test_gate_fixtures.py (4 tests)

No new failures introduced.

## Implementation Summary

### `src/launch/workers/w2_facts_builder/llm_extractor.py` (CREATED)

- `build_extraction_bundle(repo_dir)`: Builds text bundle from README + module docstrings + CHANGELOG (last 3 versions) + up to 5 example files. Budget: 32,000 chars.
- `llm_extract_claims(repo_dir, run_config)`: Primary LLM extraction. Uses `_llm_client` injected into run_config dict by worker.py. temperature=0. Post-LLM guards: source_file existence, low-confidence+no-source rejection, fabricated metric rejection, max_per_kind cap, count_cap.
- `_parse_llm_claims_json(raw_content, client, messages)`: JSON parse with retry on failure.
- `_verify_claim_source(claim, repo_dir)`: Checks source_file exists on disk.
- `_is_fabricated_metric(text)`: Reuses same regex pattern as worker.py _FABRICATED_METRIC_RE.
- `_extract_changelog_last_n_versions(content, n)`: Extracts last n version sections from CHANGELOG.

### `src/launch/workers/w2_facts_builder/worker.py` (MODIFIED)

- Added import: `from .llm_extractor import llm_extract_claims, build_extraction_bundle`
- Added `_merge_claims(llm_claims, regex_claims)` helper: LLM claims primary, regex claims appended if not exact-match duplicates.
- Wired TC-3720 LLM primary path in `execute_facts_builder()` Step 1: if `w2_synthesis.enabled=True` and LLM client available, run `llm_extract_claims()`. On RuntimeError, log warning and fall back to regex-only path. After regex extraction, merge with `_merge_claims()`.

### `specs/schemas/run_config.schema.json` (MODIFIED)

- Added `w2_synthesis` property with: `enabled` (bool, default true), `count_cap` (int|null, default null), `quality_threshold` (number, default 0.5), `max_per_kind` (int, default 10), `require_source_citation` (bool, default true).
