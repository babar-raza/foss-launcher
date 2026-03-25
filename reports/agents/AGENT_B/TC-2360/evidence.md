# Evidence: TC-2360 — W7 Phase 0 LLM Formatting Review and Fix

**Date**: 2026-02-19
**Agent**: orchestrator (Claude Sonnet 4.6)
**Status**: Done

## Files Created / Modified

| File | Action |
|------|--------|
| `specs/09_validation_gates.md` | Updated — Gate 17 documented |
| `specs/21_worker_contracts.md` | Updated — W7 Phase 0 documented |
| `src/launch/workers/w7_content_reviewer/prompts/format_fixer.txt` | Created |
| `src/launch/workers/w7_content_reviewer/fixes/llm_format_fix.py` | Created |
| `src/launch/workers/w7_content_reviewer/fixes/__init__.py` | Modified — export `run_llm_format_fix` |
| `src/launch/workers/w7_content_reviewer/worker.py` | Modified — Phase 0 wired in |
| `src/launch/workers/w7_content_reviewer/scoring.py` | Modified — `formatting_quality.*` → `content_quality` |
| `tests/unit/workers/test_llm_format_fix.py` | Created — 8 tests |
| `plans/taskcards/TC-2360_w7_phase_0_llm_formatting_fix.md` | Created |
| `plans/taskcards/INDEX.md` | Updated — TC-2360 registered |

## Test Results

```
tests/unit/workers/test_llm_format_fix.py  8 passed
Full suite (excluding pre-existing NUL issue): 4059 passed, 9 skipped, 0 failed
```

## Acceptance Criteria Verification

- [x] `run_llm_format_fix()` sends each draft to LLM with format_fixer prompt
- [x] LLM response `fixed_content` written to disk if non-null and differs from original
- [x] LLM response `defects` returned as issues in standard W7 format
- [x] Function returns `([], [])` without exception when llm_client is None
- [x] Phase 0 wired into worker.py before dimension check cycle
- [x] `formatting_quality.*` check names mapped to `content_quality` in scoring.py
- [x] All 8 unit tests pass
