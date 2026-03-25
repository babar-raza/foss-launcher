# TC-2389 Evidence — JSON Contracts: JSON Schema per LLM call + worker I/O validation

**Agent**: ORCH_AGENT
**Date**: 2026-02-20
**Status**: Done

## Changes Made

### New File: `src/launch/workers/_shared/contracts.py`

Created the worker I/O contract validation module with:

- `PRODUCT_FACTS_SCHEMA` — JSON Schema for `product_facts.json` artifact (requires `product_name`, `claims`, `claim_groups`)
- `PAGE_PLAN_SCHEMA` — JSON Schema for `page_plan.json` artifact (requires `pages` array with `slug`, `page_role`, `output_path` per item)
- `SECTION_DRAFT_SCHEMA` — JSON Schema for section draft artifacts (requires `sections` array with `heading`, `level`, `body` per item)
- `DEFINED_SCHEMAS` — Registry mapping schema names to schema dicts
- `validate_artifact(data, schema_name) -> bool` — Validates a dict against a named schema; returns True for unknown schemas (backwards compat); returns False and logs error on validation failure; returns True (with warning) for non-jsonschema errors (don't block pipeline)

### Modified File: `src/launch/clients/llm_provider.py`

Added optional `output_schema: Optional[Dict[str, Any]] = None` parameter to `chat_completion()`.

When `output_schema` is provided, the schema is injected as a JSON instruction appended to the last user message before the API call. This instructs the LLM to return valid JSON matching the schema. The injection is non-destructive — it copies the messages list and does not mutate the caller's list.

### New File: `tests/unit/workers/test_contracts.py`

Created 8 unit tests covering:

1. `test_validate_artifact_product_facts_valid` — valid `product_facts` → True
2. `test_validate_artifact_product_facts_missing_field` — missing `claims` → False
3. `test_validate_artifact_page_plan_valid` — valid `page_plan` → True
4. `test_validate_artifact_unknown_schema` — unknown schema name → True (backwards compat)
5. `test_validate_artifact_section_draft_valid` — valid `section_draft` → True
6. `test_validate_artifact_section_draft_missing_body` — missing `body` → False
7. `test_defined_schemas_contains_all` — `DEFINED_SCHEMAS` has all 3 keys
8. `test_validate_artifact_empty_pages_array` — empty pages list → True

## Test Results

```
4681 passed, 9 skipped, 0 failed (1 warning)
```

All 8 new TC-2389 tests pass. Zero regressions across full suite (4681 > 4662 threshold).

## Acceptance Checks

- [x] `contracts.py` created with `DEFINED_SCHEMAS` + `validate_artifact()`
- [x] `validate_artifact()` returns True for unknown schemas (backwards compat)
- [x] `llm_provider.py` accepts optional `output_schema` param
- [x] Schema instruction injected into prompt when `output_schema` provided
- [x] All 8 tests pass; full suite has 0 regressions
