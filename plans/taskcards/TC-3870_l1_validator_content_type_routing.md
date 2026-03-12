---
id: TC-3870
title: "Fix L1 validator to respect content_type — skip array check for non-json_array calls"
status: Done
priority: High
owner: "claude-agent"
updated: "2026-03-08"
tags: [llm, validation, review, sandwich, e2e]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3870_l1_validator_content_type_routing.md
  - src/launcher/shared/llm_response_validator.py
  - src/launcher/clients/llm_provider.py
  - tests/unit/shared/test_llm_response_validator.py
evidence_required:
  - reports/TC-3870/evidence.md
---

# Taskcard TC-3870 — Fix L1 validator to respect content_type

## Objective

`validate_llm_response` in `llm_response_validator.py` ignores the `content_type`
kwarg passed from `llm_provider.py` and always validates responses as a JSON array
with `type` keys. This is the correct schema for the generate worker but wrong for
review tasks, which return `{"grade": ..., "findings": [...]}` (a JSON object/dict).

Result: every single LLM review call fails L1 with `Expected JSON array, got dict`,
wastes 2 retry budget slots, and fills logs with false-positive errors. The actual
response is still returned (best-effort accept after MAX_L1_RETRIES), so quality
assessment still runs — but the wasted retries consume token budget and slow the
evaluate phase.

## Required spec references

- `src/launcher/clients/llm_provider.py` (L1 retry loop, line 439–442)
- `src/launcher/workers/evaluate/llm_review.py` (review response format)

## Scope

### In scope
- Add explicit `content_type` parameter to `validate_llm_response` (extracted from
  `**kwargs` for backward compatibility)
- When `content_type == "markdown"`: return valid immediately (no JSON parsing needed)
- When `content_type == "json_object"`: validate JSON parseability + result is dict
- When `content_type == "json_array"` (default): existing behavior unchanged
- Update `enhance_prompt_for_retry` docstring to note content_type awareness
- Add / update unit tests in `tests/unit/shared/test_llm_response_validator.py`

### Out of scope
- No changes to `llm_provider.py` (already passes correct content_type)
- No changes to `llm_review.py`
- No changes to generate worker (still passes json_array via `_l1_content_type`)

## Inputs

- `src/launcher/shared/llm_response_validator.py` — current implementation

## Outputs

- `src/launcher/shared/llm_response_validator.py` — updated with content_type routing
- `tests/unit/shared/test_llm_response_validator.py` — new tests

## Allowed paths

- `src/launcher/shared/llm_response_validator.py`
- `tests/unit/shared/test_llm_response_validator.py`

## Implementation steps

1. Extract `content_type` from `**kwargs` in `validate_llm_response`, defaulting to `"json_array"`.
2. If `content_type == "markdown"`: return `ValidationResult(is_valid=True)` immediately.
3. If `content_type == "json_object"`: run Layer 1 (JSON parseable) + check isinstance dict.
4. If `content_type == "json_array"` (or anything else): run existing 3-layer check.
5. Add tests for each content_type branch.

## Failure modes

1. `content_type` not passed → defaults to `"json_array"` → existing generate worker behavior unchanged
2. Unknown `content_type` value → falls through to `json_array` path → safe (strictest validation)
3. Review call returns malformed JSON → Layer 1 still catches it even for `json_object`

## Task-specific review checklist

- [ ] `validate_llm_response` extracts `content_type` from kwargs
- [ ] `content_type="markdown"` returns valid immediately (no parse)
- [ ] `content_type="json_object"` validates parseable dict
- [ ] `content_type="json_array"` (default) — existing 3-layer logic unchanged
- [ ] All existing tests pass (generate worker json_array path)
- [ ] New tests cover all three content_type branches
- [ ] Full test suite: 2938+ tests, 0 failures

## Deliverables

- Modified `src/launcher/shared/llm_response_validator.py`
- Modified `tests/unit/shared/test_llm_response_validator.py`

## Acceptance checks

- [x] Taskcard created with status In-Progress
- [x] `validate_llm_response` respects `content_type`
- [x] Review LLM calls no longer fail L1 with `Expected JSON array, got dict`
- [x] Generate worker json_array validation unchanged
- [x] Full suite passes (PYTHONHASHSEED=0) — 2954 tests, 0 failures

## Self-review

_To be filled after implementation._

## E2E verification

Run: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_llm_response_validator.py -v`
Expected: all tests pass including new content_type routing tests.

## Integration boundary proven

`validate_llm_response` is called only from `llm_provider.py` L1 retry loop.
No other callers. The `content_type` routing change is contained to this function.
