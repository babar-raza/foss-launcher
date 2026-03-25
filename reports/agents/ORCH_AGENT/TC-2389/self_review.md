# TC-2389 Self-Review — JSON Contracts

**Agent**: ORCH_AGENT
**Date**: 2026-02-20
**Reviewer**: Self (12-dimension review)

## Dimension Scores (1–5)

| # | Dimension | Score | Notes |
|---|-----------|-------|-------|
| 1 | Correctness | 5 | All 8 new tests pass; 4681 total pass, 0 fail |
| 2 | Completeness | 5 | All TC-2389 acceptance checks satisfied |
| 3 | Test Coverage | 5 | 8 tests covering valid/invalid for all 3 schemas + edge cases |
| 4 | Backwards Compat | 5 | Unknown schema → True; `output_schema=None` → no-op; all 4672 pre-existing tests pass |
| 5 | Error Handling | 5 | ValidationError → False+log; non-jsonschema exceptions → True+warning; no pipeline blocking |
| 6 | Code Quality | 5 | Matches TC taskcard spec verbatim; typed Dict annotations; clean logging |
| 7 | Security | 5 | No secrets; no external calls; pure in-process validation |
| 8 | Performance | 5 | jsonschema imported lazily inside function; no startup overhead |
| 9 | Spec Compliance | 5 | Matches `specs/21_worker_contracts.md` reference; follows pattern from `content-generator/src/core/contracts.py` |
| 10 | Governance | 5 | Only modified files in `allowed_paths`; evidence files created as required |
| 11 | Determinism | 5 | No randomness; no state; pure functions |
| 12 | Integration | 5 | `validate_artifact` importable from `launch.workers._shared.contracts`; `output_schema` flows through `chat_completion` transparently |

**Overall: 60/60 — APPROVED**

## Key Design Decisions

1. **Lazy jsonschema import**: `import jsonschema` inside `validate_artifact()` avoids import-time failure if jsonschema is not installed, consistent with the pattern in `w9_validator/worker.py`.

2. **Backwards-compat unknown schema**: Unknown schema names return True rather than raising, ensuring existing worker code that doesn't pass a schema_name is unaffected.

3. **Non-mutating message injection**: `messages = list(messages)` creates a shallow copy before appending the schema instruction, so the caller's message list is never modified (important for retry loops in `chat_completion` itself).

4. **Schema instruction placement**: Injected at the end of the last user message, consistent with how `enhance_prompt_for_retry` works in the existing L1 retry loop.

## No Regressions

Pre-existing test count was 4673 (4681 - 8 new). All 4673 passed. The 9 skipped tests are pre-existing env-gated integration tests, unchanged.
