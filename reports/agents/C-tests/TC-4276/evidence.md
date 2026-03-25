# TC-4276 Evidence — Downstream Regression Test Coverage

**Date**: 2026-03-14
**Agent**: Agent-C (Claude Sonnet 4.6)
**Taskcard**: TC-4276

---

## Tests Already Present (Added by B1)

B1 added 14 tests across two new classes in `tests/unit/workers/test_evaluate.py`:

### `TestApiVerificationPlatformAware` (TC-4271, 9 tests)
- `test_typescript_blocks_scanned_for_unknown_class` — TS blocks ARE scanned for unknown classes
- `test_python_blocks_skipped_for_typescript_product` — Python blocks NOT scanned for TS product
- `test_typescript_stdlib_classes_not_flagged` — Array, Promise, Map not flagged for TS
- `test_typescript_stdlib_methods_not_flagged` — filter, map, then, catch not flagged
- `test_ts_tag_scanned_same_as_typescript_tag` — short 'ts' tag treated same as 'typescript'
- `test_python_product_behavior_unchanged` — known Python class not false-positive flagged
- `test_python_product_default_platform` — default platform='python' preserved
- `test_unknown_ts_class_flagged_but_known_is_not` — known TS class passes; unknown TS class fails

### `TestCodeCheckPlatformAware` (TC-4275, 6 tests)
- `test_python_syntax_error_is_flagged` — Python syntax error caught
- `test_typescript_block_no_python_ast_error` — TS optional chaining/nullish coalescing skipped
- `test_ts_tagged_block_no_python_ast_error` — 'ts' tag also skips Python AST
- `test_python_valid_code_no_findings` — valid Python passes cleanly
- `test_javascript_block_no_python_ast_error` — JS blocks skip Python AST
- `test_py_tagged_block_validated_as_python` — 'py' tag triggers Python AST validation

---

## Gaps Identified

After reading both test files, the following critical contract tests were **absent**:

### TC-4272 (GenerationContext) — MISSING from test_generate.py
- No tests for `GenerationContext` model serialization/round-trip
- No tests for `PlanBundle.generation_context` optional field (None default)
- No tests for `PlanBundle` + `GenerationContext` JSON round-trip

### TC-4273 (ContentManifest.richness_tier + claims) — MISSING from test_evaluate.py
- No tests for `ContentManifest.richness_tier` default value ('B')
- No tests for `ContentManifest.claims` field default (empty list)
- No tests for richness_tier round-trip through JSON
- No integration test confirming Evaluate uses richness_tier from manifest

### TC-4274 (EvaluationReport.content_manifest_pages) — MISSING from test_evaluate.py
- No tests for `GeneratedPageRef` model round-trip
- No tests for `EvaluationReport.content_manifest_pages` field (default empty list)
- No integration test confirming Evaluate populates content_manifest_pages

---

## Tests Added

### `tests/unit/workers/test_generate.py` — `TestGenerationContextContract` (7 new tests)

| Test | What it verifies |
|------|-----------------|
| `test_generation_context_round_trip` | GenerationContext with all fields serializes and deserializes cleanly |
| `test_generation_context_defaults` | All fields default to safe empty values |
| `test_plan_bundle_accepts_generation_context` | PlanBundle carries GenerationContext when set |
| `test_plan_bundle_generation_context_defaults_none` | PlanBundle.generation_context defaults to None (backward compat) |
| `test_plan_bundle_with_generation_context_round_trip` | PlanBundle+GenerationContext survives JSON round-trip |
| `test_plan_bundle_none_generation_context_round_trip` | PlanBundle with generation_context=None survives round-trip |
| `test_generation_context_richness_tiers` | All valid tier values (A/B/C) accepted |

### `tests/unit/workers/test_evaluate.py` — `TestContentManifestRichnessTierClaims` (8 new tests)

| Test | What it verifies |
|------|-----------------|
| `test_default_richness_tier_is_b` | Default richness_tier is 'B' |
| `test_richness_tier_field_set_and_retrieved` | A/B/C values accepted |
| `test_richness_tier_round_trip` | Survives JSON serialization |
| `test_claims_field_defaults_empty` | claims defaults to [] |
| `test_claims_field_accepts_serialized_dicts` | List of Claim dicts accepted |
| `test_claims_field_round_trip` | claims survives JSON round-trip |
| `test_evaluate_uses_manifest_richness_tier` | EvaluateWorker reads richness_tier from manifest (no checkpoint needed) |
| `test_evaluate_uses_manifest_claims_for_hal09` | EvaluateWorker reads claims from manifest (no checkpoint needed) |

### `tests/unit/workers/test_evaluate.py` — `TestEvaluationReportContentManifestPages` (7 new tests)

| Test | What it verifies |
|------|-----------------|
| `test_generated_page_ref_round_trip` | GeneratedPageRef serializes and deserializes cleanly |
| `test_generated_page_ref_optional_fields_default` | ir_path and content_path default to "" |
| `test_generated_page_ref_with_all_fields` | All fields accepted correctly |
| `test_evaluation_report_content_manifest_pages_defaults_empty` | EvaluationReport.content_manifest_pages defaults to [] |
| `test_evaluation_report_accepts_content_manifest_pages` | EvaluationReport carries refs when set |
| `test_evaluation_report_content_manifest_pages_round_trip` | Survives JSON round-trip |
| `test_evaluate_worker_populates_content_manifest_pages` | EvaluateWorker populates content_manifest_pages in output report |

**Total new tests added by Agent-C: 22**

---

## Final Test Output

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
4369 passed, 65 skipped, 3 xfailed, 2 xpassed in 99.53s (0:01:39)
```

Baseline was 4347. Delta: +22 tests (all from Agent-C).
B1 added 32 tests total (14 in TestApiVerificationPlatformAware + TestCodeCheckPlatformAware + other pre-existing work). Agent-C added 22 for TC-4272/4273/4274.

---

## Self-Review Scores (12 dimensions)

| Dimension | Score | Notes |
|-----------|-------|-------|
| Correctness | 5/5 | All 22 tests pass; verified against actual model structures |
| Completeness | 5/5 | All 3 missing TCs covered (4272/4273/4274); 4271/4275 already covered |
| Test Quality | 5/5 | Model unit tests + integration tests; both round-trip and functional behavior |
| Naming | 5/5 | Follows existing snake_case conventions; descriptive names |
| Docstrings | 5/5 | Every test has a clear docstring explaining what is verified |
| Backward compat | 5/5 | Explicitly tests None defaults and empty defaults for backward compat |
| No source edits | 5/5 | Zero source files touched; tests only |
| Isolation | 5/5 | No LLM calls; no external dependencies |
| Coverage depth | 4/5 | Model round-trips + integration; full Generate worker fallback path not tested (requires LLM mock) |
| AG-002 compliance | 5/5 | Taskcard In-Progress; writes only to allowed_paths |
| Evidence captured | 5/5 | This file |
| Regression safety | 5/5 | Tests will catch field removal, type changes, worker behavioral regressions |

**Overall: 59/60 — all dimensions ≥4/5.**
