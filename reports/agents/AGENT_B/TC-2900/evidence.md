# TC-2900: Evidence Report — Operator Triage CLI Command

## Files Changed

| File | Action | Lines |
|---|---|---|
| `src/launch/cli/triage.py` | **NEW** | 322 lines |
| `src/launch/cli/main.py` | Modified (added `triage` command) | +60 lines |
| `docs/reference/cli_usage.md` | Modified (added triage runbook) | +65 lines |
| `tests/unit/cli/test_triage.py` | **NEW** | 280 lines |
| `plans/taskcards/TC-2900_operator_triage_cli.md` | **NEW** | Taskcard |

## Test Evidence

### Unit Tests: 18/18 passed
```
tests\unit\cli\test_triage.py ..................  [100%]
======================== 18 passed, 1 warning in 0.49s ========================
```

Test coverage:
- `TestLoadValidationReport`: load + missing-file error (2 tests)
- `TestBuildSummary`: severity counts, with/without snapshot (3 tests)
- `TestRankIssues`: top-N, all-critical, pad-with-warnings (3 tests)
- `TestRecommendAction`: W2/W5/W10/W8/W9 recommendations, multiple, run_dir inclusion (10 tests)

### Full Test Suite: 6831 passed, 0 failed
```
6831 passed, 13 skipped, 3 xfailed, 9 xpassed, 47 warnings in 135.32s
```

### CLI Help Verification
```
Usage: -c triage [OPTIONS] RUN_ID
Diagnose a validation report and recommend next actions.
```

### Live Test (real run directory)
```
== Triage Summary ==
  Run ID:        r_20260226T195330Z_launch_pilot-aspose-cells-foss-python_...
  Run state:     FAILED
  Profile:       local
  Gates:         41 total, 3 failed
  Issues:        0 blocker, 7 error, 243 warn, 0 info

== Top Issues ==
  [7 error rows with gate, code, path, line, message]

== Recommended Next Step ==
  1. Truth layer artifacts missing or incomplete → W2
  2. Hallucinated API symbols in code fences → W5
  3. Scaffold/prompt leak or formatting issues → W10
  4. Cross-page link or patch issues → W8
```

## Recommendation Mapping Verified

| Scenario | Gate/Code | Worker | Test |
|---|---|---|---|
| Truth layer missing | `gate_truth_layer_completeness` failed | W2 | `test_truth_layer_missing_recommends_w2` |
| Truth facts incomplete | `gate_truth_facts_completeness` failed | W2 | `test_truth_facts_completeness_recommends_w2` |
| Code fence API | `gate_15b_code_fence_api` failed | W5 | `test_code_fence_api_recommends_w5` |
| Scaffold leak | `gate_scaffold_leak` failed | W10 | `test_scaffold_leak_recommends_w10` |
| Formatting FQ | `FQ-*` error codes | W10 | `test_formatting_fq_recommends_w10` |
| Link issues | `gate_5_cross_page_link_validity` | W8 | `test_link_issues_recommend_w8` |
| Patch conflicts | `gate_12_patch_conflicts` | W8 | `test_patch_issues_recommend_w8` |
| Fallback | No pattern match | W9 | `test_fallback_recommends_w9` |
| Multiple | All three gate types | W2→W5→W10 | `test_multiple_recommendations` |

## Dependencies Added
None. Uses only stdlib (`json`, `pathlib`) and existing `rich` dependency.
