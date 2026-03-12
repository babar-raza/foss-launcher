# AQ-07 — Integration Test: class_briefs End-to-End Flow

**Status**: Not Started
**Gap linkage**: GAP-12 (no integration test proving class_briefs flows from extract → checkpoint → generate)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

`class_briefs` is a new field that flows through 5 layers:
1. `_extract_api_surface()` populates `ApiSurface.class_briefs`
2. `run_extract()` returns it in the ApiSurface
3. Understand worker serializes it to `understand_checkpoint.json`
4. Generate worker deserializes from checkpoint, passes to `_generate_page()`
5. `build_section_prompt()` formats it via `_format_api_surface()`

There is no integration test proving this chain works end-to-end. A serialization bug (e.g., `ClassBrief` not JSON-serializable, or `class_briefs` dropped during checkpoint roundtrip) would only surface in a full pilot run.

## Scope

### Fix

Add an integration test that creates a mock repo, runs `_extract_api_surface()`, serializes the result to JSON, deserializes it back, and verifies `class_briefs` survived the roundtrip with methods/properties/docstrings intact.

### Allowed paths
- `tests/integration/test_class_briefs_flow.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_class_briefs_flow.py -v --tb=short` — all pass
- **Tests**: Roundtrip: ApiSurface → JSON → ApiSurface → verify class_briefs[0].methods == original
- **Tests**: Verify `_format_api_surface()` produces non-empty output from deserialized briefs
- **No mock data in production paths**: Uses real pydantic serialization/deserialization

## Deliverables

1. New `tests/integration/test_class_briefs_flow.py` with:
   - `test_class_briefs_json_roundtrip` — serialize ApiSurface to JSON, deserialize, compare
   - `test_class_briefs_prompt_formatting` — deserialized briefs produce valid prompt output
   - `test_class_briefs_from_real_python_file` — create tmp .py file, run extract, verify briefs populated

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (seed/stable ordering) where needed
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Testability | The full data flow is proven by a single test file |
| Robustness | Catches serialization bugs before pilot runs |
| Integration | Tests the contract between understand and generate workers |
| Minimality | One test file, 3 test functions, no production code changes |

## Now (runbook)

```bash
# 1. Create tests/integration/test_class_briefs_flow.py

# 2. Write test_class_briefs_json_roundtrip:
#    api = ApiSurface(public_classes=["Doc"], class_briefs=[ClassBrief(...)], ...)
#    json_str = api.model_dump_json()
#    restored = ApiSurface.model_validate_json(json_str)
#    assert restored.class_briefs[0].methods == ["load", "save"]

# 3. Write test_class_briefs_prompt_formatting:
#    from section_prompt import _format_api_surface
#    result = _format_api_surface(["Doc"], class_briefs=[ClassBrief(...)])
#    assert "load" in result

# 4. Write test_class_briefs_from_real_python_file (with tmp_path)

# 5. Run
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_class_briefs_flow.py -v --tb=short
```
