# TC-2432 Evidence: Pilot-Scale Golden Fixture + Env-Gated Equivalence Test

## Files Modified

- `tests/unit/test_validation_engine_golden.py`
  - Added `pilot_scale_run_dir(tmp_path)` fixture:
    - 7 markdown pages across docs/kb/products/blog subdomains
    - 20 claims (feature, api, quickstart, tutorial, concept kinds)
    - 3 claim_groups (key_features, api_surface, guides)
    - `pyproject.toml` with `PYTHONHASHSEED = "0"`
    - All pages have valid frontmatter (title, description, date, slug, categories)
    - Pages with embedded `<!-- claim: ID -->` markers
    - LLM client monkeypatched to None in `_run_engine_pilot()`
  - Added `_run_engine_pilot()` helper with LLM null-out
  - Added `TestGoldenComparisonPilotScale` class (8 test methods)

- `tests/unit/test_validation_engine_pilot_equivalence.py` (NEW)
  - Env-gated via `LAUNCH_TEST_PILOT_RUN_DIR`
  - 3 test methods in `TestPilotEquivalence` (skipped unless env var set)

## Tests Added

### TestGoldenComparisonPilotScale (8 methods)

| Test | What it verifies |
|------|------------------|
| `test_gate_names_match_at_pilot_scale` | Same gate names and order |
| `test_gate_ok_values_match_at_pilot_scale` | Each gate's ok value matches |
| `test_overall_ok_matches_at_pilot_scale` | Overall ok flag matches |
| `test_issue_ids_match_at_pilot_scale` | Issue IDs match in same order |
| `test_issue_severities_match_at_pilot_scale` | Issue severities match |
| `test_issue_count_matches_at_pilot_scale` | Total issue count matches |
| `test_artifact_block_cascade_missing_page_plan_both_engines` | Both engines agree when page_plan absent |
| `test_artifact_block_cascade_missing_product_facts_both_engines` | Both engines agree when product_facts absent |

### TestPilotEquivalence (3 methods, env-gated, counted as skipped)

| Test | What it verifies |
|------|------------------|
| `test_legacy_equals_registry_gate_names` | Real pilot run: gate names match |
| `test_legacy_equals_registry_ok_values` | Real pilot run: gate ok values match |
| `test_legacy_equals_registry_overall_ok` | Real pilot run: overall ok matches |

**Tests added: 11 (8 run + 3 skipped)**

## pytest Result Summary

```
52 passed, 3 skipped in 17.54s
```

All `TestGoldenComparisonPilotScale` tests pass. `TestPilotEquivalence` is correctly skipped.
