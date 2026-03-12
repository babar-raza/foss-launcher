# Healing Plan — TC-4237 Self-Review Gap SR-01

## Context

TC-4237 added type-field reminders to both retry paths in `worker.py`. All 654 existing tests pass, but **no test verifies that the new reminder strings are actually present in the retry prompts**. The 654 tests were passing before the changes too — meaning they don't cover the new lines.

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| SR-01 | `enforce_block_spec` Pass 2 retry_prompt must contain type-field reminder — no test exists | SR-TC4237-01 |
| SR-02 | Quality check retry (`_retry_additions`) must contain type-field reminder — no direct test | SR-TC4237-01 |

---

## Taskcard SR-TC4237-01

**Status**: Done
**Gap linkage**: SR-01, SR-02
**Role**: Senior engineer — drop-in tests, production-ready.

### Scope

**Fix**: Add targeted unit tests that verify:
1. `enforce_block_spec` Pass 2 retry_prompt contains type-field reminder (`enforce_block_spec` from `worker.py`)
2. Quality-check retry (`_generate_section` path) contains type-field reminder — tested via source inspection since `_generate_section` is a complex async private function

**Allowed paths**:
- `tests/unit/workers/generate/test_tc4237_retry_type_reminder.py` (new file)
- `plans/healing/SR-TC4237-01_add-retry-type-reminder-tests.md` (this file)

**Forbidden paths**:
- `src/launcher/**` (implementation already done — no changes)
- `tests/unit/workers/test_enforcement.py` (don't modify existing tests)

### Acceptance checks

- [ ] New test file `tests/unit/workers/generate/test_tc4237_retry_type_reminder.py` exists
- [ ] `test_enforce_block_spec_pass2_retry_prompt_contains_type_reminder` passes — captures `_call_llm` call, asserts `"type" field` in retry_prompt prepend
- [ ] `test_enforce_block_spec_pass2_type_reminder_always_present_even_without_other_violations` passes — spec fails only on min_words (no block type violations), but type reminder still present
- [ ] `test_quality_retry_additions_always_contain_type_reminder` passes — uses `inspect.getsource` to assert the TC-4237 reminder string is present in `_generate_section` source as a guard test
- [ ] All new tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc4237_retry_type_reminder.py -v`
- [ ] Full suite still passes: 654+ tests

### Deliverables

1. `tests/unit/workers/generate/test_tc4237_retry_type_reminder.py` — 3 tests, all passing

### Hard rules

- No network calls in tests
- No new dependencies
- Use existing `AsyncMock` / `patch` pattern from `test_enforcement.py`
- Keep public signatures unchanged

### Review dimensions

- Correctness 5/5: tests fail if reminder is removed from worker.py
- Thoroughness 5/5: both retry paths covered (enforce_block_spec + source guard)
- Robustness 5/5: tests are deterministic (PYTHONHASHSEED=0, no LLM calls)

### Now (runbook)

```bash
# 1. Create test file (see implementation below)
# 2. Run new tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_tc4237_retry_type_reminder.py -v
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q
```
