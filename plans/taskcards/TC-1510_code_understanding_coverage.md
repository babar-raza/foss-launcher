---
id: TC-1510
title: "Expand Code Understanding Class Coverage"
status: Draft
priority: High
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "code-understanding", "llm", "class-profiles", "file-selection"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1510_code_understanding_coverage.md
  - src/launch/workers/w2_facts_builder/code_understanding.py
  - tests/unit/workers/test_code_understanding.py
evidence_required:
  - "reports/agents/agent_b/TC-1510/evidence.md"
spec_ref: "specs/21_worker_contracts.md"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1510 — Expand Code Understanding Class Coverage

## Objective
Increase class profile coverage from 10/96 (10%) to 30+/96 (30%+).

## Acceptance criteria
1. MAX_FILES_TO_LLM >= 20
2. Scene.py, Node.py, Mesh.py ranked above FBX parser files
3. Prompt includes AST details for top classes not in source files
4. metadata.product_name is non-empty
5. 3D pilot produces 20+ class profiles
