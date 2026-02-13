---
id: TC-1501
title: "Enrich AST Extraction with Docstrings, Signatures, Inheritance"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "code-analyzer", "ast", "docstrings", "signatures"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1501_ast_enrichment.md
  - src/launch/workers/w2_facts_builder/code_analyzer.py
  - tests/unit/workers/test_w2_code_analyzer.py
evidence_required:
  - "reports/agents/agent_b/TC-1501/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1501 — Enrich AST Extraction with Docstrings, Signatures, Inheritance

## Objective
Change `analyze_python_file()` to extract enriched class metadata (docstrings, base classes, method signatures, return types) as dicts instead of bare strings, enabling downstream consumers to generate meaningful documentation content.

## Problem Statement
`code_analyzer.py` extracted only bare class/function names as strings. This meant `_build_offline_understanding()` could only produce stubs like "ClassName class" and `_generate_offline_api_claims()` produced generic templates.

## Scope

### In scope
- Enrich `analyze_python_file()` output: classes as dicts with name, docstring, bases, module, methods, method_details
- New helpers: `_format_base()`, `_extract_signature()`, `_extract_return_annotation()`
- Update `analyze_repository_code()` aggregation for dict dedup
- 7 new tests for enriched output
- Update existing tests for new dict format

### Out of scope
- JS/C# analyzers (no AST library available, still return strings)
- Changing the functions list format (remains flat strings)

## Acceptance criteria
1. Python classes are returned as dicts with name, docstring, bases, module, methods, method_details
2. All existing tests pass (backward compat via isinstance guards)
3. 7 new tests pass
4. Functions list remains flat strings for backward compat
