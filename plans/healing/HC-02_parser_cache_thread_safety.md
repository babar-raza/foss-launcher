---
id: HC-02
title: "Thread safety: add lock to _parser_cache in ts_analyzer"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-07"
tags: [healing, thread-safety, tree-sitter]
depends_on: [TC-3790]
allowed_paths:
  - plans/healing/HC-02_parser_cache_thread_safety.md
  - src/launcher/shared/ts_analyzer.py
  - tests/unit/shared/test_ts_thread_safety.py
evidence_required:
  - reports/healing/HC-02/evidence.md
---

# Taskcard HC-02 — Thread Safety for Parser Cache

## Objective

The `_parser_cache` global dict in `ts_analyzer.py` is accessed from multiple
threads via `ThreadPoolExecutor` in the understand worker. Add a `threading.Lock`
to prevent race conditions during concurrent parser initialization.

## Required spec references

- `specs/worker_understand.md` (Section: concurrent file analysis)

## Scope

### In scope
- Add `threading.Lock` around `_parser_cache` reads/writes in `_get_parser()`
- Add concurrent access test proving no crashes under threading

### Out of scope
- Changing the caching strategy (e.g., per-thread parsers)
- Performance optimization of parser creation

## Inputs

- `_parser_cache` dict and `_get_parser()` function in ts_analyzer.py

## Outputs

- Thread-safe `_get_parser()` with lock
- Concurrent access test

## Allowed paths

- plans/healing/HC-02_parser_cache_thread_safety.md
- src/launcher/shared/ts_analyzer.py
- tests/unit/shared/test_ts_thread_safety.py

### Allowed paths rationale
- ts_analyzer.py: add lock to `_get_parser()`
- test file: concurrent access test

## Implementation steps

### Step 1: Add lock to module globals

```python
import threading
_parser_lock = threading.Lock()
```

### Step 2: Guard `_get_parser()` with lock

```python
def _get_parser(language: str):
    resolved = _resolve_lang_name(language)
    with _parser_lock:
        if resolved in _parser_cache:
            return _parser_cache[resolved]
        # ... create parser ...
        _parser_cache[resolved] = parser
        return parser
```

### Step 3: Add concurrent access test

Use `concurrent.futures.ThreadPoolExecutor` with 8 threads all requesting
parsers for different languages simultaneously. Assert no exceptions.

## Failure modes

### Failure mode 1: Lock contention degrades performance
**Detection**: Parse times increase >2x under concurrent load
**Resolution**: Use a per-language lock instead of global lock (unlikely needed)
**Gate**: Performance test shows <10% overhead

### Failure mode 2: Deadlock
**Detection**: Test hangs
**Resolution**: Ensure lock is never held during parser usage, only during cache check/store
**Gate**: Test completes within timeout

### Failure mode 3: Parser objects not thread-safe themselves
**Detection**: Segfault or corruption during concurrent parsing
**Resolution**: Create per-thread parser instances instead of sharing
**Gate**: Concurrent parse test passes

## Task-specific review checklist

1. [ ] `threading.Lock` added to module scope
2. [ ] `_get_parser()` uses lock for cache read and write
3. [ ] Lock scope is minimal (only cache access, not parsing)
4. [ ] Concurrent test with 8+ threads passes
5. [ ] No deadlock possible (no nested locks)
6. [ ] Existing single-threaded tests still pass

## Deliverables

1. Updated `src/launcher/shared/ts_analyzer.py`
2. New `tests/unit/shared/test_ts_thread_safety.py`
3. Evidence at `reports/healing/HC-02/evidence.md`

## Acceptance checks

1. [ ] `_parser_lock` exists in ts_analyzer.py
2. [ ] `_get_parser()` acquires lock before cache access
3. [ ] Concurrent test: 8 threads, 0 exceptions
4. [ ] Full suite: 0 failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/healing/HC-02/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/shared/test_ts_thread_safety.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x
```

**Expected results**:
- Concurrent test passes with 0 exceptions
- No performance regression in existing tests

## Integration boundary proven

**Upstream**: ThreadPoolExecutor in understand worker calls `analyze_file_safe()`
**Downstream**: All TreeSitterAnalyzer consumers get thread-safe parser access
**Contract**: `_get_parser()` returns a valid parser for any supported language, safe under concurrency
