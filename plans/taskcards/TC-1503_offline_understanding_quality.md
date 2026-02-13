---
id: TC-1503
title: "Improve Offline Code Understanding Quality"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "code-understanding", "offline", "docstrings", "workflows"]
depends_on: ["TC-1501"]
allowed_paths:
  - plans/taskcards/TC-1503_offline_understanding_quality.md
  - src/launch/workers/w2_facts_builder/code_understanding.py
  - tests/unit/workers/test_code_understanding.py
evidence_required:
  - "reports/agents/agent_b/TC-1503/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1503 — Improve Offline Code Understanding Quality

## Objective
Rewrite `_build_offline_understanding()` to leverage enriched AST data from TC-1501, producing meaningful class purposes from docstrings, real method signatures, base class relationships, code examples, and usage workflows instead of generic stubs.

## Problem Statement
The offline code understanding path produced stubs like "ClassName class" for all 96 classes in the 3D pilot. This was because `code_analyzer.py` only returned bare class name strings. With TC-1501's enriched dict output, the offline path can now generate meaningful content.

## Scope

### In scope
- Use docstrings for class purpose (fallback chain: docstring → bases → methods → "ClassName class")
- Use method_details for key_methods (real signatures, docstrings as purpose)
- Build relationships from base classes
- Generate typical_usage code examples from class + method names
- Build api_relationships dict from bases
- Infer "Basic Usage" workflow from load/save/open/close method patterns
- 6 new tests in TestEnrichedOfflineUnderstanding class

### Out of scope
- LLM code understanding path (already works when LLM available)
- Changes to code_understanding.json schema
- Feature profiles module changes

## Acceptance criteria
1. Class profiles have real purpose text from docstrings (not "ClassName class")
2. Key methods include signatures from method_details
3. Relationships populated from base classes
4. typical_usage generates code examples with class + method names
5. api_relationships built from inheritance data
6. "Basic Usage" workflow generated when load/save patterns detected
7. All 6 new tests pass
8. All existing tests pass (backward compat with string-format classes)
