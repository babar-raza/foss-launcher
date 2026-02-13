---
id: TC-1411
title: "W2 Structured Feature Profiles"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "feature-profiles", "claims", "facts-builder", "clustering"]
depends_on: ["TC-1410"]
allowed_paths:
  - plans/taskcards/TC-1411_w2_structured_feature_profiles.md
  - src/launch/workers/w2_facts_builder/feature_profiles.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_feature_profiles.py
  - reports/agents/agent_b/TC-1411/evidence.md
  - reports/agents/agent_b/TC-1411/self_review.md
evidence_required:
  - "reports/agents/agent_b/TC-1411/evidence.md"
  - "reports/agents/agent_b/TC-1411/self_review.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1411 — W2 Structured Feature Profiles

## Objective
Build structured feature profiles that group related claims into coherent feature descriptions with capabilities, limitations, code examples, and audience level. Feature profiles provide in-depth structured information beyond individual sentence claims.

## Problem Statement
Claims are individual sentences with no semantic grouping. The `claim_groups` structure is just lists of claim_ids sorted by kind. There is no way to represent grouped, structured information like "Feature X supports A, B, C with these tradeoffs" or "Here's everything about data export: supported formats, limitations, examples."

## Required spec references
- specs/03_product_facts_and_evidence.md (Structured Feature Profiles TC-1411 section)
- specs/21_worker_contracts.md (W2 FactsBuilder contract, feature_profiles output)

## Scope

### In scope
- New module: `src/launch/workers/w2_facts_builder/feature_profiles.py`
- Generic keyword-based claim clustering (product-agnostic topics: installation, getting_started, import_export, data_processing, api_reference, configuration, error_handling, performance, security, integration)
- Heuristic profile assembly: capabilities/limitations splitting, audience inference, code example integration from code_understanding
- Optional LLM enrichment for polished summaries and details
- Integration into `assemble_product_facts()` in W2 worker
- 19 unit tests with generic library examples
- Feature profiles stored in `product_facts.json` under `feature_profiles` key

### Out of scope
- Product-specific keyword lists (keywords are generic software library topics)
- W5 SectionWriter consumption of feature_profiles (separate task)
- Modifying claim extraction or deduplication logic

## Allowed paths
- `plans/taskcards/TC-1411_w2_structured_feature_profiles.md`
- `src/launch/workers/w2_facts_builder/feature_profiles.py`
- `src/launch/workers/w2_facts_builder/worker.py`
- `tests/unit/workers/test_feature_profiles.py`
- `reports/agents/agent_b/TC-1411/evidence.md`
- `reports/agents/agent_b/TC-1411/self_review.md`

## Acceptance criteria
1. `feature_profiles` array is present in `product_facts.json`
2. Each profile has: feature_id, name, summary, detail, related_claims, capabilities, limitations, code_example, api_classes, audience, tags
3. Keyword clustering is product-agnostic — works for any FOSS library
4. LLM enrichment failure falls back to heuristic profiles
5. All 19 unit tests pass
6. Feature IDs are deterministic (derived from topic name with `fp_` prefix)
