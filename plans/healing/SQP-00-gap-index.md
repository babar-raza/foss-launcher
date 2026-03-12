# Healing Plan: squishy-purring-stardust Self-Review Gaps

**Source**: Self-review of TC-4030, TC-4031, TC-4032 implementation
**Date**: 2026-03-11
**Plan file**: `C:\Users\prora\.claude\plans\squishy-purring-stardust.md`

---

## Context

Three taskcards were implemented against the understand-worker extraction pipeline:
- **TC-4032**: `_build_embedding_index()` OSError handling
- **TC-4030**: Eliminate duplicate `pyproject.toml` parsing via `SharedFacts` enrichment
- **TC-4031**: Go struct/param/enum + C++ tree-sitter extraction depth

Post-implementation self-review identified 6 gaps: 3 code correctness bugs, 1 missing test coverage block,
1 observability gap, and 1 maintainability debt item. All are captured below.

---

## Gap Table

| Gap ID   | Severity | Description                                                               | Taskcard(s)        | File(s) affected |
|----------|----------|---------------------------------------------------------------------------|--------------------|------------------|
| SQP-G01  | Critical | `worker.py` second `extract_install_recipe` call missing `shared_facts`   | SQP-H1             | `worker.py`      |
| SQP-G02  | High     | Poetry "python" dep key not filtered in `_parse_pyproject()` .keys() path | SQP-H2             | `scout.py`       |
| SQP-G03  | Medium   | `specs.index()` O(N²) + fragile break logic in `_add_go_iota_enums()`    | SQP-H3             | `ts_analyzer.py` |
| SQP-G04  | High     | Zero new tests for TC-4032 OSError, TC-4030 SharedFacts, TC-4031 Go/C++  | SQP-H4             | test files        |
| SQP-G05  | Medium   | No log output when SharedFacts enriched; Go/C++ extraction silent         | SQP-H5             | `scout.py`, `ts_analyzer.py` |
| SQP-G06  | Low      | `_extract_class()` ~230 lines; Go/C++ blocks inline; stale docstrings    | SQP-H6             | `ts_analyzer.py` |

---

## Healing Files

| File                                    | Taskcards       |
|-----------------------------------------|-----------------|
| `plans/healing/SQP-01-code-bugs.md`     | SQP-H1, SQP-H2, SQP-H3 |
| `plans/healing/SQP-02-test-coverage.md` | SQP-H4          |
| `plans/healing/SQP-03-observability-and-refactor.md` | SQP-H5, SQP-H6 |

---

## Priority Order

1. **SQP-H1** — Critical correctness: the stated 4→2 disk-read reduction is actually 4→3 in production
2. **SQP-H2** — Data quality: Poetry repos emit "python" as a dependency in `SharedFacts.dependencies`
3. **SQP-H4** — Zero test coverage for all three new code paths is unacceptable before merging
4. **SQP-H3** — Correctness + performance in Go iota enum detection
5. **SQP-H5** — Observability: silent extraction paths are undebuggable in production
6. **SQP-H6** — Maintainability: `_extract_class()` has grown to 230 lines; safe to defer after others
