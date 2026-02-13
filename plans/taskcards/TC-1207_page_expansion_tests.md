---
id: TC-1207
title: "Page Expansion — Comprehensive Test Suite"
status: Draft
priority: High
owner: "Agent C (Testing & Verification)"
updated: "2026-02-11"
tags: ["tests", "page-expansion", "phase-4"]
depends_on: ["TC-1202", "TC-1203", "TC-1204", "TC-1206"]
allowed_paths:
  - plans/taskcards/TC-1207_page_expansion_tests.md
  - tests/unit/workers/test_page_expansion_integration.py
  - tests/unit/workers/test_page_expansion_determinism.py
  - tests/unit/workers/test_page_expansion_config.py
evidence_required:
  - reports/agents/AGENT_C/TC-1207/evidence.md
  - reports/agents/AGENT_C/TC-1207/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1207 — Page Expansion — Comprehensive Test Suite

## Objective
Create a comprehensive integration and cross-cutting test suite that validates the full page expansion pipeline end-to-end: W2 format extraction → W4 policy sources + sub-pages → W5 generators. This complements the per-taskcard unit tests (TC-1202/1203/1204/1206) with integration tests, config permutation tests, and determinism verification.

## Required spec references
- specs/08_content_distribution_strategy.md (policy source contracts)
- specs/06_page_planning.md (sub-page model, URL rules)
- specs/schemas/page_plan.schema.json (schema for validation)
- specs/schemas/run_config.schema.json (page_expansion config schema)
- All TC-120x taskcards (for understanding what was implemented)

## Scope

### In scope
1. **Integration tests** — Full W2→W4→W5 pipeline for page expansion
2. **Config permutation tests** — Verify all `page_expansion` config keys work correctly
3. **Determinism tests** — Run pipeline twice with same input, verify identical output
4. **Edge case tests** — Empty repos, repos with no formats, repos with 100+ classes
5. **Quota boundary tests** — Verify max_pages enforcement with expanded policies
6. **Schema validation tests** — Verify all generated page plans validate against schema
7. **Backward compatibility tests** — Verify old configs (without page_expansion) still work

### Out of scope
- Per-function unit tests (covered in TC-1202/1203/1204/1206)
- E2E pilot verification (TC-1208)
- Template validation (TC-1205 handles this)

## Inputs
- All implemented code from TC-1202, TC-1203, TC-1204, TC-1206
- Mock product_facts with rich data (format_capabilities, examples, workflows, api_surface_summary, claim_groups)
- Mock snippet_catalog
- Various run_config permutations

## Outputs
- tests/unit/workers/test_page_expansion_integration.py (NEW — ~300 lines)
- tests/unit/workers/test_page_expansion_determinism.py (NEW — ~100 lines)
- tests/unit/workers/test_page_expansion_config.py (NEW — ~200 lines)

## Allowed paths
- plans/taskcards/TC-1207_page_expansion_tests.md
- tests/unit/workers/test_page_expansion_integration.py
- tests/unit/workers/test_page_expansion_determinism.py
- tests/unit/workers/test_page_expansion_config.py

### Allowed paths rationale
Tests only. No code modifications. These tests import from existing modules — reading/importing is always allowed per taskcard contract.

## Implementation steps

### Step 1: Read implemented code to understand actual interfaces
Before writing tests, read the actual implementations from TC-1202/1203/1204/1206 to understand:
- Function signatures
- Return types
- Expected data structures

**Resilience note**: The implementations may differ from what the taskcards specified. Write tests against the ACTUAL code, not the taskcard specs. If interfaces have changed, adapt the tests accordingly.

### Step 2: Create shared test fixtures
Build comprehensive mock data that all test files can use:

```python
@pytest.fixture
def rich_product_facts():
    """Product facts with all page expansion evidence."""
    return {
        "claims": [...],  # 20+ claims across multiple kinds
        "claim_groups": {
            "key_features": ["c1", "c2", "c3", "c4", "c5"],
            "install_steps": ["c6", "c7"],
            "limitations": ["c8", "c9"],
            "compatibility_notes": ["c10"],
            "workflow_claims": ["c11", "c12", "c13"],
        },
        "format_capabilities": {
            "read_formats": ["FBX", "OBJ", "STL"],
            "write_formats": ["FBX", "GLTF", "GLB", "OBJ"],
            "confirmed_pairs": [["FBX", "GLTF"], ["FBX", "GLB"], ["OBJ", "GLTF"]],
        },
        "examples": [
            {"name": "basic-load", "claim_ids": ["c1"], "snippet_ids": ["s1"]},
            {"name": "advanced-render", "claim_ids": ["c2", "c3"], "snippet_ids": ["s2", "s3"]},
            {"name": "no-evidence", "claim_ids": [], "snippet_ids": []},
        ],
        "workflows": [
            {"name": "Model Loading", "steps": [{"desc": "Load"}, {"desc": "Transform"}]},
            {"name": "Rendering", "steps": [{"desc": "Setup"}, {"desc": "Render"}, {"desc": "Save"}]},
        ],
        "api_surface_summary": {
            "classes": [
                {"name": "Scene", "module": "aspose.threed", "methods": ["load", "save"]},
                {"name": "Mesh", "module": "aspose.threed.entities", "methods": ["create"]},
                {"name": "Material", "module": "aspose.threed.entities", "methods": ["set_color"]},
                {"name": "Camera", "module": "aspose.threed.entities", "methods": ["look_at"]},
                {"name": "Light", "module": "aspose.threed.entities", "methods": ["set_intensity"]},
            ],
        },
    }

@pytest.fixture
def rich_snippet_catalog():
    """Snippet catalog with evidence for all page types."""
    return {
        "snippets": [
            {"id": "s1", "tags": ["fbx", "load"], "content": "..."},
            {"id": "s2", "tags": ["gltf", "render"], "content": "..."},
            {"id": "s3", "tags": ["mesh", "create"], "content": "..."},
        ]
    }

@pytest.fixture
def full_page_expansion_config():
    """Run config with all page expansion features enabled."""
    return {
        "page_expansion": {
            "enabled_policies": [],  # All enabled
            "format_pairs_override": {"add": [["FBX", "USD"]], "remove": []},
            "reference_granularity": "namespace",
            "max_feature_sub_pages": 4,
            "combination_top_n": 5,
        }
    }
```

### Step 3: Write integration tests (`test_page_expansion_integration.py`)

1. **test_full_pipeline_generates_format_pair_pages** — W2 extracts formats → W4 generates per_format_pair pages → verify page count and slugs
2. **test_full_pipeline_generates_example_pages** — Examples with evidence → pages generated; examples without evidence → skipped
3. **test_full_pipeline_generates_tutorial_pages** — Workflows → tutorial pages
4. **test_full_pipeline_generates_namespace_ref_pages** — API classes grouped by module → namespace reference pages
5. **test_full_pipeline_generates_deep_dive_pages** — Top 5 features → pairwise deep dive pages
6. **test_full_pipeline_generates_theme_pages** — claim_groups with 3+ → theme overview pages
7. **test_full_pipeline_generates_faq_topic_pages** — Claims grouped by kind → FAQ topic pages
8. **test_sub_pages_generated_for_eligible_features** — Feature pages with enough evidence → sub-pages
9. **test_sub_pages_not_generated_for_thin_features** — Feature pages with 1 claim → no sub-pages
10. **test_all_generated_pages_have_content** — W5 produces non-empty content for every W4-planned page
11. **test_page_plan_validates_against_schema** — All page plan entries pass JSON schema validation
12. **test_cross_links_populated_for_new_pages** — Format conversion pages link to related conversions

### Step 4: Write determinism tests (`test_page_expansion_determinism.py`)

1. **test_format_pair_determinism** — Two runs with identical input → identical format pair pages (order, slugs, content)
2. **test_sub_page_determinism** — Two runs → identical sub-page output
3. **test_full_expansion_determinism** — Two complete runs → byte-identical page_plan.json
4. **test_combination_pair_ordering** — Verify alphabetical pair ordering is stable

### Step 5: Write config permutation tests (`test_page_expansion_config.py`)

1. **test_all_policies_enabled_by_default** — Empty `enabled_policies` → all sources active
2. **test_selective_policy_enable** — `enabled_policies: ["per_format_pair", "per_example"]` → only those two active
3. **test_format_pairs_override_add** — Override adds FBX→USD pair
4. **test_format_pairs_override_remove** — Override removes FBX→GLTF pair
5. **test_max_feature_sub_pages_zero** — Disables all sub-pages
6. **test_max_feature_sub_pages_two** — Only overview + quickstart generated
7. **test_combination_top_n_three** — Only 3 features paired (3 pairs max)
8. **test_no_page_expansion_config** — Old run_config without `page_expansion` → all defaults apply, backward compatible
9. **test_quota_enforcement** — max_pages=5 with evidence for 20 pages → only 5 selected by quality score
10. **test_empty_product_facts** — No claims, no formats, no examples → 0 expansion pages, no errors

### Step 6: Run full test suite
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_page_expansion_*.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x  # full regression
```

## Failure modes

### Failure mode 1: Test fixtures diverge from actual data model
**Detection:** Tests fail with KeyError or AttributeError because fixture data doesn't match actual product_facts structure.
**Resolution:** Before writing fixtures, read actual pilot product_facts.json to understand real structure. Adapt fixtures to match.
**Spec/Gate:** Testing best practices

### Failure mode 2: Determinism tests fail due to dict ordering
**Detection:** Two runs produce different ordering in page_plan.json despite identical input.
**Resolution:** Ensure all tests use `PYTHONHASHSEED=0`. Verify all sorting in W4 uses deterministic keys (not dict iteration order).
**Spec/Gate:** specs/34 Guarantee E (determinism)

### Failure mode 3: Integration tests import functions that were renamed/moved
**Detection:** ImportError when running tests because function names changed during implementation.
**Resolution:** Read actual source files before writing imports. Use `from ... import ...` with actual function names.
**Spec/Gate:** Testing resilience principle

## Task-specific review checklist
1. [ ] 12+ integration tests covering all 7 policy sources + sub-pages
2. [ ] 4+ determinism tests with PYTHONHASHSEED=0
3. [ ] 10+ config permutation tests covering all page_expansion keys
4. [ ] Shared fixtures provide rich mock data
5. [ ] Edge cases tested (empty data, zero config, quota boundary)
6. [ ] Backward compatibility tested (no page_expansion config)
7. [ ] Schema validation tested (all page plans valid)
8. [ ] All tests pass with PYTHONHASHSEED=0
9. [ ] No flaky tests (no timing dependencies, no network calls)
10. [ ] Test names are descriptive and follow project convention

## Deliverables
- tests/unit/workers/test_page_expansion_integration.py (NEW — ~300 lines)
- tests/unit/workers/test_page_expansion_determinism.py (NEW — ~100 lines)
- tests/unit/workers/test_page_expansion_config.py (NEW — ~200 lines)
- reports/agents/AGENT_C/TC-1207/evidence.md
- reports/agents/AGENT_C/TC-1207/self_review.md

## Acceptance checks
1. [ ] All 26+ tests pass
2. [ ] Full regression suite passes
3. [ ] PYTHONHASHSEED=0 determinism verified
4. [ ] No flaky tests
5. [ ] Backward compatibility confirmed

## Preconditions / dependencies
- TC-1202, TC-1203, TC-1204, TC-1206 all completed (code to test exists)

## Self-review
[To be completed by Agent C after implementation]
