---
id: TC-1410
title: "W2 LLM-Powered Code Understanding"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "code-understanding", "llm", "facts-builder", "code-analysis"]
depends_on: ["TC-1041", "TC-1042"]
allowed_paths:
  - plans/taskcards/TC-1410_w2_llm_code_understanding.md
  - src/launch/workers/w2_facts_builder/code_understanding.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_code_understanding.py
  - reports/agents/agent_b/TC-1410/evidence.md
  - reports/agents/agent_b/TC-1410/self_review.md
evidence_required:
  - "reports/agents/agent_b/TC-1410/evidence.md"
  - "reports/agents/agent_b/TC-1410/self_review.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1410 — W2 LLM-Powered Code Understanding

## Objective
Build a structured code understanding artifact (`code_understanding.json`) that sends key source files to an LLM for deep analysis of class profiles, core concepts, usage workflows, and API relationships. This enables W5 SectionWriter to generate richer, grounded content with real code examples instead of pseudocode.

## Problem Statement
Code analysis was limited to shallow AST parsing — class/function names only. This led to generic templated claims like "provides the Document class for document operations" and pseudocode in generated content. W5 had no deep understanding of the codebase when generating documentation.

## Required spec references
- specs/03_product_facts_and_evidence.md (LLM Code Understanding TC-1410 section)
- specs/21_worker_contracts.md (W2 FactsBuilder contract, code_understanding.json output)
- specs/07_code_analysis_and_enrichment.md (Code analysis requirements)

## Scope

### In scope
- New module: `src/launch/workers/w2_facts_builder/code_understanding.py`
- LLM-powered path: identify public API files, send to LLM, parse structured JSON response
- Offline fallback: generate minimal profiles from AST data (docstrings, class/method names)
- Integration into W2 worker as Step 0.75 (after code analysis, before claim extraction)
- Write `code_understanding.json` artifact to `RUN_DIR/artifacts/`
- 18 unit tests covering offline fallback, LLM path, error handling, file identification, truncation
- All test fixtures use generic library examples (product-agnostic)

### Out of scope
- Modifying code_analyzer.py (AST parsing already complete)
- W5 SectionWriter integration (separate task)
- Changing LLM provider or model selection

## Allowed paths
- `plans/taskcards/TC-1410_w2_llm_code_understanding.md`
- `src/launch/workers/w2_facts_builder/code_understanding.py`
- `src/launch/workers/w2_facts_builder/worker.py`
- `tests/unit/workers/test_code_understanding.py`
- `reports/agents/agent_b/TC-1410/evidence.md`
- `reports/agents/agent_b/TC-1410/self_review.md`

## Acceptance criteria
1. `code_understanding.json` is produced for both LLM and offline paths
2. Schema includes: schema_version, product_name, product_summary, core_concepts, class_profiles, usage_workflows, api_relationships, metadata
3. LLM failure gracefully falls back to offline AST profiles
4. All 18 unit tests pass
5. W2 worker writes artifact after code analysis step
6. No product-specific hardcoded logic — works for any FOSS library
