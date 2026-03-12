# From Chat: TC-4237 — Generate Retry Prepend Type Reminder (2026-03-12)

## Context

TC-4228 (G-2) is Done: coercion in `_validate_block` (section_validator.py:313-334) and the base CRITICAL note in section_writer.txt:76 are already implemented. Despite these, LLMs still omit the `type` field on retry calls because neither retry path (section quality check nor enforce_block_spec Pass 2) explicitly includes the `type` requirement in its retry prepend/addition. The targeted fix is to add the type reminder to the retry prepend — NOT to further strengthen the base prompt.

Scope exclusions (user-confirmed out of scope):
- Advisor confidence thresholds / circuit breaker routing — separate concern
- `max_re_runs` configuration — content quality issue, not a bug

## Goals

Reduce `L1_VALIDATOR_FAIL` events by ensuring every retry instruction explicitly reminds the LLM to include a `type` field on every block.

## Assumptions

| Assumption | Status |
|---|---|
| TC-4228 coercion is merged and working | VERIFIED (section_validator.py:313-334) |
| Base prompt already has CRITICAL note | VERIFIED (section_writer.txt:76) |
| Neither retry path currently mentions type | VERIFIED (worker.py:1100-1128, 1517-1542 — no type mention) |
| Prepend cap of 300 chars is too small after adding violations | VERIFIED by character count (~247 chars already) |

## Steps

1. **Change 1** (`worker.py` ~line 1128): Add type-field reminder to `_retry_additions` (section quality check retry)
2. **Change 2** (`worker.py` ~line 1533): Add type-field violation to `violations` list in `enforce_block_spec` Pass 2
3. **Change 2b** (`worker.py` ~line 1542): Raise `prepend[:300]` cap to `prepend[:500]`
4. Run tests: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q`
5. Update TC-4237 to Done; create evidence

## Acceptance criteria

- [ ] Tests pass (generate worker unit tests + test_generate.py)
- [ ] `_retry_additions` always includes type-field reminder when quality check retry fires
- [ ] `enforce_block_spec` Pass 2 violations list always includes type-field reminder
- [ ] Prepend cap raised from 300 → 500 chars

## Risks + rollback

- Risk: Longer prepend increases token usage slightly. Mitigation: negligible (one line ~100 chars).
- Rollback: Revert the three-line change in worker.py; all tests should return to prior state.

## Evidence commands

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ tests/unit/workers/test_generate.py -x -q
```

## Open questions

(empty)
