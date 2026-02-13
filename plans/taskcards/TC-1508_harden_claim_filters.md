---
id: TC-1508
title: "Harden Claim Quality Filters"
status: In-Progress
priority: High
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "extract-claims", "code-filter", "quality", "license-exclusion"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1508_harden_claim_filters.md
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - tests/unit/workers/test_tc_411_extract_claims.py
evidence_required:
  - "reports/agents/agent_b/TC-1508/evidence.md"
spec_ref: "specs/21_worker_contracts.md"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1508 — Harden Claim Quality Filters

## Objective
Reduce raw code leakage from 38% to <5% by strengthening `_is_code_like`, fixing `_is_noun_phrase_claim`, and excluding LICENSE files.

## Acceptance criteria
1. `_is_code_like("from enum import Enum class Interpolation(Enum):")` returns True
2. `_is_code_like("class Quaternion:")` returns True
3. `_is_code_like("def detect(self, stream):")` returns True
4. `_is_code_like("Scene supports OBJ format loading")` returns False
5. LICENSE file extraction returns empty list
6. All existing tests pass
