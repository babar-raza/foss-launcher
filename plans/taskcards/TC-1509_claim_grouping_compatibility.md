---
id: TC-1509
title: "Fix Claim Grouping and Add Compatibility Routing"
status: Draft
priority: High
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "claim-groups", "compatibility", "platforms", "routing"]
depends_on: ["TC-1508"]
allowed_paths:
  - plans/taskcards/TC-1509_claim_grouping_compatibility.md
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_tc_411_extract_claims.py
  - tests/unit/workers/test_tc_410_facts_builder.py
evidence_required:
  - "reports/agents/agent_b/TC-1509/evidence.md"
spec_ref: "specs/21_worker_contracts.md"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1509 — Fix Claim Grouping and Add Compatibility Routing

## Objective
Fix claim group contamination, populate `compatibility_notes` and `supported_platforms`.

## Acceptance criteria
1. Claims with kind `key_feature` normalized to `feature` and routed to key_features
2. "Python 3.7+" classified as compatibility claim
3. `## Python Version Support` recognized as compatibility section
4. `compatibility_notes` populated with version claims
5. `supported_platforms` non-empty for 3D pilot
