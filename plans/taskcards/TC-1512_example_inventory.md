---
id: TC-1512
title: "Populate Example Inventory from Code"
status: Draft
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "example-inventory", "readme", "code-understanding"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1512_example_inventory.md
  - src/launch/workers/w2_facts_builder/worker.py
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - tests/unit/workers/test_tc_410_facts_builder.py
evidence_required:
  - "reports/agents/agent_b/TC-1512/evidence.md"
spec_ref: "specs/21_worker_contracts.md"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1512 — Populate Example Inventory from Code

## Objective
Populate the empty `example_inventory` by harvesting code examples from README and code_understanding.json.

## Acceptance criteria
1. README Quick Start code block appears in example_inventory
2. Code understanding class typical_usage appears in example_inventory
3. When W1 provides examples, no duplicates
4. 3D pilot produces 5+ example_inventory entries
