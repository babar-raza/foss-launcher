---
id: TC-1507
title: "Handle LLM Response Truncation in Code Understanding"
status: Done
priority: Normal
owner: "agent_b"
updated: "2026-02-13"
tags: ["w2", "llm", "truncation", "code-understanding", "json-repair"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1507_llm_truncation_handling.md
  - src/launch/clients/llm_provider.py
  - src/launch/workers/w2_facts_builder/code_understanding.py
  - tests/unit/workers/test_code_understanding.py
evidence_required:
  - "reports/agents/agent_b/TC-1507/evidence.md"
spec_ref: "7a2e753d308154582e85aea06a0cf85e2c91a5f2"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1507 — Handle LLM Response Truncation in Code Understanding

## Objective
Fix the silent LLM-to-offline fallback in `build_code_understanding()` caused by response truncation at `max_tokens=4096`. Expose `finish_reason` from the LLM provider, raise token limits, limit classes sent to LLM, and attempt JSON repair on truncated responses.

## Problem Statement
The LLM was called successfully (HTTP 200, 37s). But `max_tokens=4096` is too small for 96 classes. Response truncated (`finish_reason: "length"`) → malformed JSON → `json.loads()` fails → caught by `except Exception` → silent fallback to offline. No truncation-specific warning exists. `finish_reason` is not returned in `chat_completion()` result dict — only stored in telemetry.

## Scope

### In scope
- Part A: Expose `finish_reason` in `chat_completion()` return dict (llm_provider.py)
- Part B: New constants `CODE_UNDERSTANDING_MAX_TOKENS=16384`, `MAX_CLASSES_TO_LLM=30`
- Part C: Limit classes sent to LLM prompt — sort by method count, send top 30 detailed
- Part D: Check `finish_reason` after LLM call, log truncation warning, attempt JSON repair
- New helper `_attempt_json_repair()` for closing unmatched brackets/braces
- 5 new tests

### Out of scope
- Retry logic (retry with fewer classes on truncation)
- Changing LLM model or endpoint configuration
- Modifying other LLM call sites (only code_understanding)

## Acceptance criteria
1. `chat_completion()` return dict includes `finish_reason` field
2. `CODE_UNDERSTANDING_MAX_TOKENS >= 16384`
3. Repos with 50+ classes send only top 30 to LLM prompt (by method count)
4. `finish_reason="length"` logs explicit truncation warning
5. Truncated JSON with missing closing brackets is repaired when possible
6. All 5 new tests pass
7. All existing tests pass unchanged
