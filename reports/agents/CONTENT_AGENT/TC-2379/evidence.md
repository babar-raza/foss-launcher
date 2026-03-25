# TC-2379 Evidence: W5 Generator Context Builders for 13 Missing Roles

**Taskcard**: TC-2379
**Agent**: CONTENT_AGENT
**Date**: 2026-02-20
**Status**: Done

## Summary

Implemented 13 new `build_*_context()` functions in
`src/launch/workers/w5_section_writer/generators/content_generators.py`, plus a
`get_context_for_role()` dispatch function. All 16 roles now have dedicated
role-ranked context builders.

## Acceptance Check Results

### 1. Context builder count

```
grep -c "def build_.*_context" src/launch/workers/w5_section_writer/generators/content_generators.py
```

**Result: 16** (requirement: ≥ 16) ✓

### 2. Spec amendment

`specs/21_worker_contracts.md` — added "W5 Generator Context Builders (TC-2379, Binding)"
section (lines 1268–1313 of updated file) stating:

> Every `generate_*_content()` function MUST have a corresponding
> `build_*_context(page, product_facts, snippet_catalog) -> dict` function.

### 3. `get_context_for_role()` dispatch function

Exists at line 1065 of `content_generators.py`. Uses `_CONTEXT_BUILDERS` dict (line 1045)
with all 16 roles registered. Falls back to `build_tutorial_context` for unknown roles.

### 4. Tests

All 6 required tests added to `TestTC2379GeneratorContextBuilders` class:

- `test_all_generator_roles_have_context_builder` — verifies 16 `build_*_context` functions ✓
- `test_troubleshooting_context_prioritizes_error_claims` — error claims rank first ✓
- `test_toc_context_returns_empty` — empty claims, snippets, claim_context, snippet_text ✓
- `test_get_context_for_role_unknown_falls_back` — unknown role → tutorial context ✓
- `test_context_dict_has_required_keys` — 3 builders checked for required keys ✓
- `test_faq_context_no_snippets` — FAQ returns empty snippets list ✓

**Test run result: 6/6 passed (0.60s)**

### 5. Full suite regression check

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=no
```

**Result: 4602 passed, 9 skipped, 0 failures** (pre-existing 9 skipped env-gated tests unchanged)

### 6. TC-2340 scope conflict check

TC-2340 only modifies `src/launch/workers/w5_section_writer/worker.py` — no overlap with
`content_generators.py`. No conflicts.

## Files Modified

| File | Change |
|------|--------|
| `src/launch/workers/w5_section_writer/generators/content_generators.py` | Added 13 context builders + dispatch function + wired into 5 generators |
| `specs/21_worker_contracts.md` | Added W5 Generator Context Builders binding spec section |
| `tests/unit/workers/test_tc_440_section_writer.py` | Added `TestTC2379GeneratorContextBuilders` class with 6 tests |

## New Context Builders

| Function | Role | Claim Priority |
|----------|------|----------------|
| `build_comprehensive_guide_context` | comprehensive_guide | workflow → feature → api |
| `build_troubleshooting_context` | troubleshooting | error → limitation → format |
| `build_blog_context` | blog | feature → workflow |
| `build_feature_blog_context` | feature_blog | feature → workflow |
| `build_performance_context` | performance | limitation → feature |
| `build_faq_context` | faq | feature → api → format (no snippets) |
| `build_best_practices_context` | best_practices | workflow → limitation |
| `build_getting_started_context` | getting_started | workflow (install-first) → feature |
| `build_workflow_page_context` | workflow_page | workflow (source_section order) |
| `build_landing_context` | landing | feature (top 5 only) |
| `build_format_conversion_context` | format_conversion | format → api |
| `build_howto_article_context` | howto_article | workflow (source_section order) |
| `build_toc_context` | toc | (none — structural) |

## Generators Wired (Step 6)

| Generator | Wiring comment |
|-----------|----------------|
| `generate_workflow_page_content` | Uses `get_context_for_role("workflow_page", ...)` |
| `generate_landing_content` | Uses `get_context_for_role("landing", ...)` |
| `generate_api_reference_content` (TC-2332) | Uses `get_context_for_role("api_reference", ...)` |
| `generate_format_conversion_content` | Uses `get_context_for_role("format_conversion", ...)` |
| `generate_howto_article_content` | Uses `get_context_for_role("howto_article", ...)` |
| `generate_feature_blog_content` | Uses `get_context_for_role("feature_blog", ...)` |

Note: `generate_tutorial_content`, `generate_feature_showcase_content` already call their
builders directly (TC-2369) and were not changed.
