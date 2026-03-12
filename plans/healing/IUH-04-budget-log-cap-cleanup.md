---
id: IUH-04
title: "Cap budget_log at 500 entries and remove unused Counter import"
status: Done
priority: High
owner: Refactor Engineer
updated: "2026-03-11"
tags: [performance, robustness, scout, cleanup]
depends_on: []
allowed_paths:
  - src/launcher/workers/understand/scout.py
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_scout_budget_log_cap.py
  - plans/healing/IUH-04-budget-log-cap-cleanup.md
evidence_required:
  - reports/IUH-04/evidence.md
---

# Taskcard IUH-04 — Cap budget_log at 500 entries and remove unused Counter import

## Objective

`_read_repo_content()` appends one dict to `budget_log` for every skipped file. On a 10,000-file repo where budget is exhausted early, this produces up to 9,950 entries in memory and yields a multi-megabyte `scout_inventory.json` that is unreadable in practice. Cap the log at 500 entries with an overflow counter. Also remove the unused `from collections import Counter` import left in `worker.py`'s artifact write block.

## Required spec references

- `plans/reflective-finding-lark.md` — TC-B08: `scout_inventory.json` format (budget_log)
- `specs/worker_understand.md` — scout phase observability

## Scope

### In scope
- Add `_BUDGET_LOG_MAX = 500` constant to `scout.py`
- Guard every `budget_log.append(...)` call (4 call sites in the tier loop + README section)
- Track `budget_log_overflow_count` for skipped entries beyond the cap
- Expose `budget_log_overflow_count` in `scout_inventory.json`
- Remove `from collections import Counter` from `worker.py` artifact block

### Out of scope
- Changing the structure of existing `budget_log` entries
- Changing `scout_inventory.json` other than adding `budget_log_overflow_count`
- Any logic changes to budget allocation

## Inputs

- `src/launcher/workers/understand/scout.py` — `_read_repo_content()` with unbounded budget_log
- `src/launcher/workers/understand/worker.py` — artifact assembly with unused Counter import

## Outputs

- `src/launcher/workers/understand/scout.py` — budget_log capped at 500; overflow count tracked
- `src/launcher/workers/understand/worker.py` — Counter import removed; `budget_log_overflow_count` in artifact
- `tests/unit/workers/test_scout_budget_log_cap.py` — new test

## Allowed paths

- `src/launcher/workers/understand/scout.py`
- `src/launcher/workers/understand/worker.py`
- `tests/unit/workers/test_scout_budget_log_cap.py`
- `plans/healing/IUH-04-budget-log-cap-cleanup.md`

### Allowed paths rationale
Both `scout.py` (log generation) and `worker.py` (artifact assembly) need changes. A focused new test file proves the cap works without polluting existing scout tests.

## Implementation steps

### Step 1: Add constant and overflow counter to _read_repo_content()

In `scout.py`, add to `_read_repo_content()`:

```python
_BUDGET_LOG_MAX = 500  # module-level constant, before the function

def _read_repo_content(...) -> tuple[dict[str, str], int, int, list[dict]]:
    ...
    budget_log: list[dict] = []
    budget_log_overflow_count = 0  # counts entries beyond _BUDGET_LOG_MAX
    ...
```

### Step 2: Replace all budget_log.append() calls with guarded version

Define a helper inline at the top of `_read_repo_content()` (or use a simple inline pattern at each call site):

**Pattern to apply at every `budget_log.append(...)` call site**:
```python
# Before:
budget_log.append({
    "path": rel_path,
    "category": category.value,
    "size_bytes": entry.size_bytes,
    "reason": "budget_exceeded",
})

# After:
if len(budget_log) < _BUDGET_LOG_MAX:
    budget_log.append({
        "path": rel_path,
        "category": category.value,
        "size_bytes": entry.size_bytes,
        "reason": "budget_exceeded",
    })
else:
    budget_log_overflow_count += 1
```

Apply this pattern to ALL 5 call sites:
1. README truncation (`"reason": "per_file_cap"`)
2. Tier loop: `"reason": "budget_exceeded"`
3. Tier loop: `"reason": "doc_cap_reached"`
4. Tier loop: `"reason": "source_reserve"`
5. Tier loop: `"reason": "file_too_large_for_remaining_budget"`
6. Tier loop: `"reason": "per_file_cap"` (file truncated by sanitize_input)

### Step 3: Return overflow count from _read_repo_content()

Change the return to a 5-tuple:
```python
return content, total_redactions, files_truncated, budget_log, budget_log_overflow_count
```

Update the return type annotation:
```python
) -> tuple[dict[str, str], int, int, list[dict], int]:
```

### Step 4: Update run_scout() to unpack 5-tuple

In `run_scout()`:
```python
# Before:
repo_content, sanitize_redactions, sanitize_truncated, budget_log = _read_repo_content(...)

# After:
repo_content, sanitize_redactions, sanitize_truncated, budget_log, budget_log_overflow = _read_repo_content(...)
```

Update the return to pass `budget_log_overflow` through:
```python
return repo_info, repo_content, budget_log, budget_log_overflow
```

Update `run_scout()` return type annotation:
```python
) -> tuple[RepoInfo, dict[str, str], list[dict], int]:
```

### Step 5: Update worker.py to unpack 4-tuple from run_scout() and expose overflow

```python
# Before:
repo_info, repo_content, scout_budget_log = await run_scout(repo_dir)

# After:
repo_info, repo_content, scout_budget_log, scout_budget_log_overflow = await run_scout(repo_dir)
```

In the `scout_inventory.json` build, add the overflow field:
```python
scout_inventory = {
    "files_enumerated": len(repo_info.file_tree),
    "files_read": repo_info.content_files_read,
    "content_used_bytes": repo_info.content_budget_used,
    "by_category": cat_counts,
    "budget_log": scout_budget_log,
    "budget_log_overflow_count": scout_budget_log_overflow,
    "truncated_files": [
        e for e in scout_budget_log if e.get("reason") == "per_file_cap"
    ],
}
```

Also remove unused import:
```python
# Remove this line entirely:
from collections import Counter
```

### Step 6: Write test

Create `tests/unit/workers/test_scout_budget_log_cap.py`:

```python
"""Tests that budget_log is capped at 500 entries — IUH-04."""
from __future__ import annotations
from pathlib import Path
from launcher.models.understanding import FileCategory, FileEntry
from launcher.workers.understand.scout import _read_repo_content


def _make_file_index(repo_dir: Path, count: int, category: FileCategory = FileCategory.doc) -> dict:
    """Create a file_index with `count` files of 1KB each, all as docs."""
    index = {}
    for i in range(count):
        fname = f"doc_{i:04d}.md"
        p = repo_dir / fname
        p.write_text("# Doc\n" * 10, encoding="utf-8")
        index[fname] = FileEntry(category=category, size_bytes=p.stat().st_size, language="")
    return index


class TestBudgetLogCap:
    def test_budget_log_capped_at_500(self, tmp_path):
        """budget_log must not exceed 500 entries even with 1000 skipped files."""
        # Create 600 tiny doc files; budget exhausts early
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count = _read_repo_content(
            tmp_path, index, budget_bytes=5_000  # tiny budget forces many skips
        )

        assert len(budget_log) <= 500, (
            f"budget_log has {len(budget_log)} entries, expected ≤ 500"
        )
        assert overflow_count >= 0, "overflow_count must be non-negative"
        total = len(budget_log) + overflow_count
        # Not all 600 files will be skipped (some will be read before budget hits)
        # but the sum must be consistent
        assert total <= 600

    def test_budget_log_overflow_count_nonzero_when_capped(self, tmp_path):
        """When more than 500 files are skipped, overflow_count must be > 0."""
        # 600 files, tiny budget to force many skips
        index = _make_file_index(tmp_path, count=600, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count = _read_repo_content(
            tmp_path, index, budget_bytes=500  # very tiny budget
        )

        if len(budget_log) == 500:
            assert overflow_count > 0, (
                "When budget_log is at cap, overflow_count must be > 0"
            )

    def test_small_repo_no_overflow(self, tmp_path):
        """For a small repo with few skips, overflow_count should be 0."""
        index = _make_file_index(tmp_path, count=5, category=FileCategory.doc)

        _, _, _, budget_log, overflow_count = _read_repo_content(
            tmp_path, index, budget_bytes=_DEFAULT_BUDGET
        )

        assert overflow_count == 0
        assert len(budget_log) <= 5  # at most 5 truncation entries


# Import the constant to use in test
from launcher.workers.understand.scout import _DEFAULT_BUDGET_BYTES as _DEFAULT_BUDGET
```

### Step 7: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_budget_log_cap.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

## Failure modes

### Failure mode 1: Other callers of run_scout() expect 3-tuple, not 4-tuple

**Detection**: `ValueError: not enough values to unpack` or `too many values to unpack`.
**Resolution**: `grep -rn "run_scout" src/ tests/` to find all callers. Update each to unpack 4-tuple. For tests that mock `run_scout`, update the mock return value to a 4-tuple.
**Gate**: G-04 — no regression

### Failure mode 2: Tests mock _read_repo_content and expect 3-tuple return

**Detection**: Tests that patch `_read_repo_content` returning a 3-tuple will fail with `not enough values to unpack`.
**Resolution**: `grep -rn "_read_repo_content" tests/` and update mock return values to 5-tuple `(content, 0, 0, [], 0)`.
**Gate**: G-04 — test suite clean after signature change

### Failure mode 3: FileEntry import path wrong in test

**Detection**: `ImportError` in `test_scout_budget_log_cap.py`.
**Resolution**: Check `from launcher.models.understanding import FileEntry, FileCategory` — confirm the import path matches the actual module.
**Gate**: Test correctness

## Task-specific review checklist

1. [ ] `len(budget_log) <= 500` in all code paths in `_read_repo_content()`
2. [ ] `budget_log_overflow_count` increments when cap is reached
3. [ ] `scout_inventory.json` includes `budget_log_overflow_count` field
4. [ ] `from collections import Counter` removed from `worker.py`
5. [ ] `run_scout()` return type updated to 4-tuple
6. [ ] All callers of `run_scout()` updated (worker.py + any tests)
7. [ ] `test_budget_log_capped_at_500` PASS
8. [ ] Full unit suite: no regressions

## Deliverables

1. `src/launcher/workers/understand/scout.py` — budget_log capped; overflow count returned
2. `src/launcher/workers/understand/worker.py` — Counter removed; overflow in artifact
3. `tests/unit/workers/test_scout_budget_log_cap.py` — 3 new tests
4. `reports/IUH-04/evidence.md` — test output + confirmation Counter removed

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_budget_log_cap.py -v` — all PASS
2. [ ] `grep "from collections import Counter" src/launcher/workers/understand/worker.py` — 0 matches
3. [ ] `grep "budget_log_overflow" src/launcher/workers/understand/worker.py` — ≥1 match
4. [ ] Full unit suite: no new failures

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: Counter import absent PASS
- [ ] Evidence captured: `reports/IUH-04/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
grep -c "from collections import Counter" src/launcher/workers/understand/worker.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_budget_log_cap.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

**Expected results**:
- Counter import: 0 matches
- New tests: all PASS
- Full suite: no regressions

## Integration boundary proven

**Upstream**: `_read_repo_content()` returns bounded `budget_log` (max 500 entries) + `overflow_count`
**Downstream**: `scout_inventory.json` is a readable artifact (≤ a few KB for normal repos); `budget_log_overflow_count > 0` warns operator that log was capped
**Contract**: `len(budget_log) ≤ 500` always; `budget_log_overflow_count ≥ 0` always; sum is consistent

---

## Review dimensions (what 5/5 means for this taskcard)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Performance | `budget_log` never exceeds 500 entries in memory; `scout_inventory.json` stays under 50KB on large repos |
| Correctness | Overflow count is the exact count of entries NOT in the log; `len(log) + overflow == total_skipped` |
| Minimality | Only the append call sites change; no logic changes to budget allocation |
| Observability | `budget_log_overflow_count` in artifact immediately tells operator the log was truncated |
| Robustness | Small repos (0 skipped files) produce `overflow_count=0` with no behavior change |

## Now (runbook)

```bash
# 1. Count current budget_log.append() call sites
grep -n "budget_log.append" src/launcher/workers/understand/scout.py

# 2. Add _BUDGET_LOG_MAX constant and overflow counter — use Edit tool

# 3. Guard each append site — use Edit tool for each

# 4. Update return tuple + type annotation — use Edit tool

# 5. Update run_scout() unpacking and return — use Edit tool

# 6. Update worker.py unpacking + remove Counter + add overflow to artifact — use Edit tool

# 7. Write test file — use Write tool

# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout_budget_log_cap.py -v

# 9. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```
