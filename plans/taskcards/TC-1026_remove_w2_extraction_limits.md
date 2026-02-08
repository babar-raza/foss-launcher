---
id: TC-1026
title: "Remove All W2 Extraction Limits"
status: Complete
priority: P1
owner: agent-e
updated: "2026-02-07"
tags: ["w2", "extraction", "limits", "healing"]
depends_on: [TC-1020]
allowed_paths:
  - src/launch/workers/w2_facts_builder/extract_claims.py
  - src/launch/workers/w2_facts_builder/worker.py
  - tests/unit/workers/test_tc_411_extract_claims.py
  - tests/unit/workers/test_tc_410_facts_builder.py
  - plans/taskcards/TC-1026_*
  - reports/agents/agent_e/TC-1026/**
evidence_required:
  - reports/agents/agent_e/TC-1026/evidence.md
  - reports/agents/agent_e/TC-1026/self_review.md
spec_ref: "46d7ac2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1026 --- Remove All W2 Extraction Limits

## Objective

Remove the 10-example cap, 4-word minimum, keyword filter, and LLM processing cap in W2.
Per the updated specs (TC-1020), W2 MUST process ALL documents without count limits
and MUST NOT apply minimum word-count or keyword-presence filters.

## Problem Statement

W2 FactsBuilder currently applies four artificial limits that reduce claim extraction coverage:

1. **4-word minimum filter** (`extract_claims.py` line 370): `len(sentence.split()) >= 4` discards short but valid claims.
2. **Keyword marker gate** (`extract_claims.py` lines 372-377): Sentences without specific keywords are silently dropped, even if they contain valid claims.
3. **10-document LLM cap** (`extract_claims.py` line 419): `doc_files[:10]` limits LLM extraction to first 10 docs.
4. **10-example cap** (`worker.py` line 314): `example_files[:10]` limits example inventory to 10 entries.

## Changes

### extract_claims.py
- Remove the 4-word minimum: change `>= 4` to `>= 1`
- Convert keyword marker filter from a gate to a scoring boost (keyword presence adds `keyword_boost: true` metadata but does NOT skip the candidate)
- Remove `[:10]` slice on `doc_files` in `extract_claims_with_llm`
- Add `claims_extracted_count` to logger telemetry

### worker.py
- Remove `[:10]` slice on `example_files` in `assemble_product_facts`
- Add `examples_processed_count` to logger telemetry

### Tests
- Update assertion thresholds expecting old behavior
- Add test verifying single-word sentences are candidates
- Add test verifying no document caps are applied

## Acceptance Criteria

1. No `[:10]` slicing on doc_files or example_files
2. No minimum word count gate (>= 1 word is fine)
3. Keyword presence is a boost, not a gate
4. All existing tests pass
5. New tests verify the removal of limits

## Verification

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```
