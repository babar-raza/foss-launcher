---
id: TC-1506
title: "Fix Feature Profile Code Example Lookup"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "feature-profiles", "code-examples", "api-classes", "bridge"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1506_feature_profile_code_examples.md
  - src/launch/workers/w2_facts_builder/feature_profiles.py
  - tests/unit/workers/test_feature_profiles.py
evidence_required:
  - "reports/agents/agent_b/TC-1506/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1506 — Fix Feature Profile Code Example Lookup

## Objective
Bridge the semantic gap between feature profile topic names (e.g., "api_reference", "import_export") and code_understanding class names (e.g., "Scene", "Mesh") so that `code_example` and `api_classes` are populated in feature profiles.

## Problem Statement
In `build_feature_profiles_heuristic()`, the `code_examples` dict is keyed by lowercased class/workflow names (e.g., "a3dobject", "basic_usage"). But profiles look up by topic name (e.g., "api_reference", "import_export") at line 179. Keys never match → all 9 profiles have empty `code_example` and empty `api_classes`.

## Scope

### In scope
- New helper `_extract_class_names_from_claims()`: CamelCase regex extraction from claim texts
- New helper `_find_code_example_for_topic()`: Bridge topic → class names → code_examples lookup
- Modify profile loop to use bridge when direct topic lookup returns empty
- 5 new tests

### Out of scope
- Modifying code_understanding.py output format
- Changing FEATURE_KEYWORDS clustering logic
- LLM-based topic-to-class mapping

## Acceptance criteria
1. Feature profiles with class names in their claims get populated `code_example`
2. Feature profiles with class names in their claims get populated `api_classes`
3. Direct topic name match is still preferred over bridge (backward compat)
4. `code_understanding=None` still works (empty code_example, no crash)
5. All 5 new tests pass
6. All existing tests pass unchanged
