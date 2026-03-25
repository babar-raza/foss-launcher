# TC-2378 Evidence: Content Sanitizer Robust Fence Parser

**Agent**: CONTENT_AGENT
**Date**: 2026-02-20
**Status**: Done

---

## Summary

Replaced 14 `in_fence = not in_fence` boolean toggle sites in
`src/launch/workers/_shared/content_sanitizer.py` with the new `_FenceState`
counter class. Added the Shared.1 Fence Parser Contract to
`specs/21_worker_contracts.md`. Added 7 tests to
`tests/unit/workers/test_content_sanitizer.py`.

---

## Acceptance Check Results

| Check | Result |
|-------|--------|
| `grep -c "in_fence = not in_fence" content_sanitizer.py` | **0** (all 14 replaced) |
| `_FenceState` class present in `content_sanitizer.py` | Yes |
| `specs/21_worker_contracts.md` contains "Shared.1 Fence Parser Contract" | Yes |
| TC-2354 work not duplicated | Confirmed — TC-2354 scope is metrics instrumentation only |

---

## Toggle Sites Fixed

All 14 `in_fence = not in_fence` toggle sites replaced with `fence = _FenceState()` +
`fence.process_line(line)` + `fence.in_fence`. Original line numbers (before patch),
function names:

| # | Original Line | Function |
|---|---------------|----------|
| 1 | 189 | `strip_source_annotations()` |
| 2 | 331 | `fence_bare_commands()` |
| 3 | 406 | `fence_orphan_lang_names()` |
| 4 | 501 | `fix_collapsed_markdown_tables()` |
| 5 | 564 | `strip_inline_seo_keywords()` |
| 6 | 616 | `fence_bare_code_lines()` |
| 7 | 1071 | `close_unclosed_fences()` |
| 8 | 1109 | `fix_nested_fences()` |
| 9 | 1461 | `fix_trailing_periods_in_code()` |
| 10 | 1795 | `fix_unicode_in_code_blocks()` |
| 11 | 1970 | `strip_llm_scaffolding()` |
| 12 | 2037 | `strip_boilerplate_sentences()` |
| 13 | 2348 | `trim_dangling_sentence_fragments()` |
| 14 | 2440 | `normalize_module_names()` |

---

## `_FenceState` Class Added

Location: `src/launch/workers/_shared/content_sanitizer.py`, after `_track()` helper,
before Phase 1 comment block.

```python
class _FenceState:
    """Counter-based fence depth tracker (replaces boolean toggle).

    Idempotent: depth clamps to 0 on unmatched closing fences.
    Spec: specs/21_worker_contracts.md § Shared.1 Fence Parser Contract.
    """

    def __init__(self) -> None:
        self.depth: int = 0

    def process_line(self, line: str) -> None:
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if self.depth == 0:
                self.depth = 1
            else:
                self.depth = max(0, self.depth - 1)

    @property
    def in_fence(self) -> bool:
        return self.depth > 0
```

---

## Spec Amendment

Added to `specs/21_worker_contracts.md` under the "Shared Module" section:

> **Shared.1 Fence Parser Contract (TC-2378, binding)**
> All sanitizer functions that track code-fence state MUST use an integer depth counter
> (not a boolean toggle). ... Idempotency contract: f(f(x)) == f(x).

---

## Test Results

### TC-2378 new tests (7 tests in `TestFenceState` class)

| Test | Result |
|------|--------|
| `test_fence_counter_increments_on_open` | PASS |
| `test_fence_counter_decrements_on_close` | PASS |
| `test_fence_counter_clamps_at_zero` | PASS |
| `test_fence_state_odd_fenced_content` | PASS |
| `test_fence_idempotency_close_unclosed_fences` | PASS |
| `test_fence_idempotency_strip_boilerplate_sentences` | PASS |
| `test_fence_idempotency_strip_source_annotations` | PASS |

### Full suite

```
4596 passed, 9 skipped, 1 warning in 122.10s
```

Pre-existing skipped count: 9 (unchanged — all env-gated integration tests).
Zero regressions.
