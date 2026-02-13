---
id: TC-1502
title: "Improve Claim Extraction Quality and Coverage"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "extract-claims", "filters", "bullet-extraction", "readme-sections"]
depends_on: ["TC-1501"]
allowed_paths:
  - plans/taskcards/TC-1502_claim_extraction_quality.md
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - tests/unit/workers/test_tc_411_extract_claims.py
evidence_required:
  - "reports/agents/agent_b/TC-1502/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1502 — Improve Claim Extraction Quality and Coverage

## Objective
Relax overly aggressive claim filters, add bullet-point and structured README section extraction, and raise the offline API claims cap to increase claim volume and quality for downstream documentation generation.

## Problem Statement
The 3D pilot produced only 46 claims for 18 planned pages. Root causes:
- `MIN_CLAIM_WORDS=4` rejected valid 3-word claims
- `_is_code_like` threshold of 2 produced false positives on prose with minor code references
- No extraction of bullet points from README/docs
- No structured extraction of Installation/Getting Started/Usage sections from README
- Offline API claims capped at 30 with generic templates
- Verb list in `_is_prose_like` too narrow, missing common documentation verbs

## Scope

### In scope
- Relax thresholds: MAX_CLAIM_TEXT_LENGTH_EXTRACT 300→500, MIN_CLAIM_WORDS 4→3
- Raise _is_code_like threshold: 2→3 pattern matches required
- Expand verb list in _is_prose_like with 20 additional verbs
- New _is_noun_phrase_claim() function for feature noun acceptance
- Bullet point extraction (second pass in extract_candidate_statements_from_text)
- Structured README section extraction (extract_structured_sections_from_readme)
- Raise offline API claims cap: 30→50
- Update 8 existing tests for new thresholds

### Out of scope
- LLM-based claim classification (separate TC-1402)
- Claim deduplication changes
- Evidence mapping changes

## Acceptance criteria
1. MIN_CLAIM_WORDS is 3, MAX_CLAIM_TEXT_LENGTH_EXTRACT is 500
2. _is_code_like requires >= 3 pattern matches (not 2)
3. Bullet points from markdown lists are extracted as candidate statements
4. README sections (Installation, Getting Started, Usage, Features, Requirements) produce structured claims
5. Offline API claims cap is 50
6. All existing tests pass (updated for new thresholds)
7. Noun-phrase claims like "CSV and JSON format support" are accepted
