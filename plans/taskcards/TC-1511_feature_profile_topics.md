---
id: TC-1511
title: "Fix Feature Profile Topic Assignment"
status: Draft
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "feature-profiles", "keyword-matching", "topic-assignment"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1511_feature_profile_topics.md
  - src/launch/workers/w2_facts_builder/feature_profiles.py
  - tests/unit/workers/test_feature_profiles.py
evidence_required:
  - "reports/agents/agent_b/TC-1511/evidence.md"
spec_ref: "specs/21_worker_contracts.md"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1511 — Fix Feature Profile Topic Assignment

## Objective
Eliminate misclassified feature profiles by raising keyword threshold and adding ambiguous keyword handling.

## Acceptance criteria
1. "FbxElement contains key tokens" NOT in security profile
2. "STL file extension header" NOT in integration profile
3. "authenticate with token credentials" IS in security profile
4. Profiles with <3 claims are dropped
