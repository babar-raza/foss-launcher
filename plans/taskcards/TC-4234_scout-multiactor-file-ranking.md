---
id: TC-4234
title: "Scout multi-factor file importance ranking (int 0-7, 4 additive factors)"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [scout, file-ranking, budget]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4234_scout-multiactor-file-ranking.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout.py
evidence_required:
  - reports/agents/B_implementation/TC-4234/evidence.md
---

# Taskcard TC-4234 — Scout multi-factor file importance ranking

## Objective

Replace binary 0/1 `_file_importance_rank()` with a multi-factor int 0-7 scorer
so non-standard important files (OVERVIEW.md, FEATURES.txt, root-level docs)
receive meaningful rank and are read before stubs and deeply-nested files.

## Required spec references

- `specs/worker_understand.md` (Section: Phase A — Scout)

## Scope

### In scope
- Refactor `_file_importance_rank()` return type from 0/1 to int 0-6 (keyword + root + ext)
- Add size-signal factor (+1) inline in sort lambda in `_read_repo_content()`
- New constants: `_STANDARD_DOC_EXTS`, `_STANDARD_SRC_EXTS`, `_SIZE_SIGNAL_MIN/MAX`
- 5 new tests

### Out of scope
- Changing sort key structure `(-rank, size_bytes)` — only rank value enriched
- TC-4236 `important_files_skipped` metric (separate TC depending on this one)

## Inputs

- `rel_path: str`, `category: FileCategory` — unchanged signature

## Outputs

- `int` in range 0-6 from `_file_importance_rank()` (size adds +1 at sort site, max total 7)

## Allowed paths

- plans/taskcards/TC-4234_scout-multiactor-file-ranking.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout.py

### Allowed paths rationale
Function lives in scout.py; tests in test_scout.py.

## Implementation steps

### Step 1: Add constants after `_SOURCE_IMPORTANCE_STEMS`

```python
_STANDARD_DOC_EXTS: frozenset[str] = frozenset({".md", ".rst", ".txt"})
_STANDARD_SRC_EXTS: frozenset[str] = frozenset({
    ".py", ".ts", ".js", ".java", ".cs", ".go", ".rb", ".rs",
    ".php", ".cpp", ".c", ".h", ".kt", ".swift",
})
_SIZE_SIGNAL_MIN: int = 200        # below = stub, no size bonus
_SIZE_SIGNAL_MAX: int = 50_000     # above = likely generated, no size bonus
```

### Step 2: Refactor `_file_importance_rank()` at scout.py:222

```python
def _file_importance_rank(rel_path: str, category: FileCategory) -> int:
    """Return priority rank for a file within its category (0-6 base; sort adds size bonus).

    Three additive factors:
    1. Stem keyword match (+3): known-important names via _DOC/_SOURCE_IMPORTANCE_STEMS
    2. Root-level file (+2): '/' not in rel_path
    3. Standard extension for category (+1): .md/.rst/.txt for doc; .py/.ts/... for source

    Size signal (+1) is applied at sort time in _read_repo_content() to avoid
    threading size through this function's signature.

    TC-4234: replaces binary 0/1 (TC-4102) with multi-factor int 0-6.
    """
    stem = Path(rel_path).stem.lower().replace("-", "").replace("_", "")
    score = 0

    # Factor 1: Stem keyword (+3)
    if category == FileCategory.doc:
        if any(s in stem for s in _DOC_IMPORTANCE_STEMS):
            score += 3
    elif category == FileCategory.source:
        if any(s in stem for s in _SOURCE_IMPORTANCE_STEMS):
            score += 3

    # Factor 2: Root-level file (+2)
    if '/' not in rel_path and '\\' not in rel_path:
        score += 2

    # Factor 3: Standard extension (+1)
    ext = Path(rel_path).suffix.lower()
    if category == FileCategory.doc and ext in _STANDARD_DOC_EXTS:
        score += 1
    elif category == FileCategory.source and ext in _STANDARD_SRC_EXTS:
        score += 1

    return score
```

### Step 3: Update sort lambda in `_read_repo_content()` (scout.py:334)

```python
tier_files.sort(
    key=lambda x: (
        -(
            _file_importance_rank(x[0], category)
            + (1 if _SIZE_SIGNAL_MIN <= x[1].size_bytes <= _SIZE_SIGNAL_MAX else 0)
        ),
        x[1].size_bytes,
    )
)
```

### Step 4: Add 5 unit tests to TestFileImportanceRankSubstring

```python
def test_root_level_adds_2pts(self):
    # OVERVIEW.md at root: no keyword (0), root (+2), ext (+1) = 3
    assert _file_importance_rank("OVERVIEW.md", FileCategory.doc) == 3

def test_nested_nonkeyword_doc_is_low(self):
    # subdir/notes.log: no keyword, nested, non-standard ext = 0
    assert _file_importance_rank("subdir/notes.log", FileCategory.doc) == 0

def test_keyword_nested_doc(self):
    # docs/api_reference.md: keyword (+3), nested (0), .md (+1) = 4
    assert _file_importance_rank("docs/api_reference.md", FileCategory.doc) == 4

def test_root_keyword_doc_is_high(self):
    # README.md: keyword (+3), root (+2), .md (+1) = 6
    assert _file_importance_rank("README.md", FileCategory.doc) == 6

def test_source_root_init_py(self):
    # __init__.py at root: keyword "init" (+3), root (+2), .py (+1) = 6
    assert _file_importance_rank("__init__.py", FileCategory.source) == 6
```

## Failure modes

### Failure mode 1: Existing tests expect rank == 1

**Detection**: `AssertionError` in old `TestFileImportanceRankSubstring` tests
**Resolution**: Old tests used `== 1`; update to `>= 1` if needed, or verify they're flexible
**Gate**: All existing `TestFileImportanceRankSubstring` tests pass

### Failure mode 2: Sort stability broken

**Detection**: Non-deterministic ordering in budget tests
**Resolution**: Python sort is stable; secondary key `size_bytes` provides tiebreaker
**Gate**: `test_budget_log_never_exceeds_500` still passes

### Failure mode 3: Windows path separator in `rel_path`

**Detection**: `'/' not in rel_path` true even for nested Windows paths
**Resolution**: scout.py already normalizes to forward slash at `_walk_file_tree()` line 164
**Gate**: `test_root_level_adds_2pts` on actual walk output

## Task-specific review checklist

1. [ ] `_file_importance_rank()` docstring updated with 3 factors listed
2. [ ] Constants `_STANDARD_DOC_EXTS`, `_STANDARD_SRC_EXTS`, `_SIZE_SIGNAL_MIN/MAX` defined
3. [ ] Sort lambda in `_read_repo_content()` includes size-signal bonus
4. [ ] All 5 new tests pass
5. [ ] Existing `TestFileImportanceRankSubstring` tests still pass
6. [ ] `test_scout_budget_log_cap.py` all tests pass
7. [ ] Docstrings updated
8. [ ] Spec confirmed — no drift
9. [ ] Schema unchanged
10. [ ] `docs/README.md` ownership map checked
11. [ ] No new docs guides needed

## Deliverables

1. Updated `src/launcher/workers/scout/scout.py`
2. Updated `tests/unit/workers/test_scout.py`
3. `reports/agents/B_implementation/TC-4234/evidence.md`

## Acceptance checks

1. [x] `_file_importance_rank("OVERVIEW.md", FileCategory.doc)` returns 3
2. [x] `_file_importance_rank("subdir/notes.log", FileCategory.doc)` returns 0
3. [x] `_file_importance_rank("README.md", FileCategory.doc)` returns 6
4. [x] 5 new tests pass
5. [x] All existing scout tests pass

## Self-review

### Verification results
- [x] Tests: 4208/4208 PASS (full suite); 26/26 understand/test_scout.py PASS
- [x] Evidence: reports/agents/B_implementation/TC-4234/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py -k "rank or Rank" \
  tests/unit/workers/test_scout_budget_log_cap.py \
  -v --tb=short
```

## Integration boundary proven

**Upstream**: `file_index` from `_walk_file_tree()`
**Downstream**: Sort order in `_read_repo_content()` → reading priority
**Contract**: Higher int rank → read earlier in budget loop
