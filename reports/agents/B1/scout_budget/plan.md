# Agent B1 — Scout Budget Plan

## Taskcards Implemented

### TC-4262: LLM doc window 32KB → 128KB
- File: `src/launcher/workers/understand/extract/_llm.py`
- Change: `_MAX_SOURCE_CHARS = 32_000` → `_MAX_SOURCE_CHARS = 128_000`
- Test: add `TestLLMDocWindowConstant.test_max_source_chars_128k` in `tests/unit/workers/test_understand.py`

### TC-4263: Scout budget 1MB → 5MB + per-file cap differentiation
- File: `src/launcher/workers/scout/scout.py`
- Sub-change 1: `_DEFAULT_BUDGET_BYTES = 1_000_000` → `_DEFAULT_BUDGET_BYTES = 5_000_000`
- Sub-change 2: Add `_PER_FILE_MAX_CHARS` dict with doc=500_000 and source=300_000
- Sub-change 3: Update two `sanitize_input` call sites to use per-category caps
- Tests: add `TestScoutBudgetConstants` (3 tests) in `tests/unit/workers/test_scout.py`

### TC-4264: Meta-doc subdirectory keyword filtering
- File: `src/launcher/workers/scout/scout.py`
- Inspection finding: the `"/" not in lower and` root-level guard was NOT present in the
  current codebase. The code already correctly applies keyword filtering at all path depths.
  No source change required.
- Tests: add `TestMetaDocSubdirFiltering` (4 tests) in `tests/unit/workers/test_scout.py`
  to lock in the correct behavior.
