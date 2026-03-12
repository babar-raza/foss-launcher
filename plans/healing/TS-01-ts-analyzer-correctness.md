# TS-01 — ts_analyzer.py Correctness + Cleanup

## Context

Four issues in `ts_analyzer.py` introduced or left behind by the HC healing
sprint. Three are correctness bugs (thread safety, regex anchoring, dead state);
one is code quality (duplicated replacer branches).

## Status: Done

## Gap linkage

| Gap ID | Description |
|--------|-------------|
| G-01 | `_ensure_ts()` TOCTOU race on `_ts_available` global |
| G-03 | Go import regex unanchored — matches inside string literals |
| G-04 | `_language_cache` dict never used — dead state |
| G-08 | `normalize_imports._replacer` 7 identical branches |

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. **G-01**: Wrap `_ensure_ts()` in double-checked locking using `_parser_lock`.
   The global `_ts_available` is currently read/written without any lock, yet
   `_get_parser()` calls it before acquiring its own lock. Two threads could both
   enter the `import tree_sitter` path simultaneously.

   ```python
   def _ensure_ts() -> bool:
       global _ts_available
       if _ts_available is not None:
           return _ts_available
       with _parser_lock:
           if _ts_available is not None:
               return _ts_available
           try:
               import tree_sitter
               _ts_available = True
           except ImportError:
               logger.warning("tree_sitter_not_installed")
               _ts_available = False
       return _ts_available
   ```

2. **G-03**: Anchor Go import regex to require `import` keyword or line-start
   whitespace before the quote, while still matching both `import "..."` and
   indented `"..."` inside import blocks:

   ```python
   "go": re.compile(r'(?:^import\s+|^\s+)"(github\.com/aspose/\w+)"', re.MULTILINE),
   ```

3. **G-04**: Delete the unused `_language_cache` dict (line 82).

4. **G-08**: Collapse the 7 identical `_replacer` branches into one:

   ```python
   def _replacer(m: re.Match) -> str:
       original = m.group(0)
       old_pkg = m.group(1)
       return original.replace(old_pkg, canonical_import)
   ```

### Allowed paths

- `src/launcher/shared/ts_analyzer.py`
- `tests/unit/shared/test_ts_healing.py` (update existing tests if needed)

### Forbidden

Any other file or path.

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_analyzer.py tests/unit/shared/test_ts_healing.py -v` — 0 failures
- **Tests**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x` — full suite 0 failures
- **Thread safety**: Existing `TestThreadSafety.test_concurrent_parser_access` still passes
- **Go regex**: Add test: `normalize_imports('var s = "github.com/aspose/cells"', "go", "x")` does NOT rewrite inside string literal
- **Dead code**: `grep _language_cache src/launcher/shared/ts_analyzer.py` returns 0 matches
- **Replacer**: Only one `return original.replace(...)` line in `_replacer`
- No mock data in production paths

## Deliverables

- Full file replacement for `ts_analyzer.py` (all 4 fixes applied)
- Updated/new test in `test_ts_healing.py` for Go regex anchoring
- No TODOs, no stubs

## Hard rules

- Keep public signatures unchanged (`analyze_file`, `validate_snippet`, `extract_doc_comments`, `extract_imports_from_code`, `extract_exports_from_code`, `normalize_imports`)
- No network in offline tests
- Deterministic runs (PYTHONHASHSEED=0)
- No new deps
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 means |
|-----------|-----------|
| Thoroughness | All 4 fixes applied, no partially-fixed items |
| Consistency | All regex patterns anchored consistently; all lock paths use same `_parser_lock` |
| Production grading | Thread-safety claim now provably correct; no race window |
| Correctness | Go regex test proves no false-positive on string content |
| Testability | Each fix has at least one dedicated test assertion |
| Robustness | `_ensure_ts` + `_get_parser` are both fully thread-safe |
| Performance | Double-checked locking avoids lock on hot path after initialization |
| Minimality | Only the 4 targeted fixes; no unrelated changes |
| Observability | Existing structlog logging retained |

## Now (runbook)

```bash
# 1. Apply G-01: _ensure_ts double-checked locking
#    Edit ts_analyzer.py lines 38-48: wrap in _parser_lock

# 2. Apply G-03: anchor Go regex
#    Edit ts_analyzer.py line 428: change pattern

# 3. Apply G-04: delete _language_cache
#    Edit ts_analyzer.py line 82: remove the line

# 4. Apply G-08: collapse _replacer branches
#    Edit ts_analyzer.py lines 441-460: single return

# 5. Add Go regex anchoring test
#    Edit test_ts_healing.py: add test_go_normalize_no_false_positive_in_string

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_analyzer.py tests/unit/shared/test_ts_healing.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x

# 7. Verify dead code removal
grep _language_cache src/launcher/shared/ts_analyzer.py
# Expected: 0 matches
```
