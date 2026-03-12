---
id: TC-4236
title: "Scout important-file coverage guarantee (observability metric + self-review)"
status: Done
priority: Normal
owner: "agent-B"
updated: "2026-03-12"
tags: [scout, observability, coverage, self-review]
depends_on: [TC-4234]
allowed_paths:
  - plans/taskcards/TC-4236_scout-coverage-guarantee.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/scout/worker.py
  - tests/unit/workers/test_scout.py
  - tests/unit/workers/test_scout_budget_log_cap.py
evidence_required:
  - reports/agents/B_implementation/TC-4236/evidence.md
---

# Taskcard TC-4236 — Scout important-file coverage guarantee

## Objective

Add `important_files_skipped: int` to `RepoInfo` (understanding.py) and count how
many high-rank (≥ 4 total, combining TC-4234 rank + size bonus) files were skipped
by the budget manager. Add a medium-severity ScoutWorker self-review warning when
count > 0. Provides operator observability without changing budget semantics.

## Required spec references

- `specs/worker_understand.md` (Section: Phase A — Scout: self-review criteria)

## Scope

### In scope
- Add `important_files_skipped: int = 0` to `RepoInfo` in `understanding.py`
- Count high-rank skips in `_read_repo_content()` for reasons budget_exceeded + file_too_large
- Return count from `_read_repo_content()` (7-tuple return, was 6-tuple)
- Pass count through `run_scout()` to `RepoInfo` constructor
- Add medium self-review finding in `ScoutWorker.self_review()`
- 2 new tests

### Out of scope
- Changing reading order or budget semantics (TC-4234's richer ranking handles that organically)
- Adding a BLOCKING gate on `important_files_skipped > 0`

## Inputs

- Budget loop in `_read_repo_content()` with rank from TC-4234's `_file_importance_rank()`

## Outputs

- `repo_info.important_files_skipped` in scout_bundle.json
- Medium self-review finding when count > 0

## Allowed paths

- plans/taskcards/TC-4236_scout-coverage-guarantee.md
- src/launcher/models/understanding.py
- src/launcher/workers/scout/scout.py
- src/launcher/workers/scout/worker.py
- tests/unit/workers/test_scout.py
- tests/unit/workers/test_scout_budget_log_cap.py

### Allowed paths rationale
Model in understanding.py; Scout logic in scout.py; worker self-review in worker.py.

## Implementation steps

### Step 1: Add `important_files_skipped` to `RepoInfo` in understanding.py

After `skipped_paths` field at line 76:
```python
important_files_skipped: int = Field(
    default=0,
    description=(
        "TC-4236: Count of files with importance rank >= 4 (TC-4234 base + size bonus) "
        "that were skipped due to budget exhaustion. Non-zero indicates quality loss; "
        "ScoutWorker self-review emits a medium warning."
    ),
)
```

### Step 2: Track skips in `_read_repo_content()`

Change return signature to 7-tuple (append `important_skipped: int`).
In the budget-skip branches (`budget_exceeded` and `file_too_large_for_remaining_budget`):

```python
# After computing rank for the file:
effective_rank = (
    _file_importance_rank(rel_path, category)
    + (1 if _SIZE_SIGNAL_MIN <= entry.size_bytes <= _SIZE_SIGNAL_MAX else 0)
)
if effective_rank >= 4:
    important_skipped += 1
```

Initialize `important_skipped = 0` at top of function.
Add to return tuple at end.

### Step 3: Update `run_scout()` to unpack 7-tuple and pass to `RepoInfo`

```python
repo_content, sanitize_redactions, sanitize_truncated, budget_log, \
    budget_log_overflow, dropped_by_category, important_skipped = \
    _read_repo_content(repo_dir, file_index)
```

```python
repo_info = RepoInfo(
    ...
    important_files_skipped=important_skipped,
)
```

### Step 4: Add self-review check in `ScoutWorker.self_review()` (worker.py)

Append after existing checks:
```python
if output.repo_info.important_files_skipped > 0:
    findings.append(SelfReviewFinding(
        severity="medium",
        message=(
            f"Scout budget skipped {output.repo_info.important_files_skipped} "
            f"high-rank file(s) (rank≥4). Check repo_info.skipped_paths."
        ),
        field="important_files_skipped",
    ))
```

### Step 5: Add 2 tests

`test_scout.py` — `test_self_review_warns_on_important_files_skipped`:
- Create a constrained budget that forces budget_exceeded on a root-level .md file
- Verify ScoutWorker.self_review() returns a medium SelfReviewFinding

`test_scout_budget_log_cap.py` — `test_important_files_skipped_metric`:
- Build file_index with 1 root-level important file that exceeds budget
- Call `_read_repo_content()` with tiny budget
- Verify last element of returned tuple > 0

## Failure modes

### Failure mode 1: All callers of `_read_repo_content()` break on 7th return value

**Detection**: `ValueError: too many values to unpack` in run_scout() and tests
**Resolution**: Update ALL callers — run_scout() + test_scout_budget_log_cap.py's `_read_repo_content` calls
**Gate**: `test_budget_log_never_exceeds_500` must pass

### Failure mode 2: `SelfReviewFinding` import missing in worker.py

**Detection**: `ImportError` on `SelfReviewFinding`
**Resolution**: Confirm import at top of worker.py; add if missing
**Gate**: `test_scout_self_review_passes_on_good_repo` must pass

### Failure mode 3: Old scout_bundle.json fails validation with new field

**Detection**: `ValidationError` loading artifact without `important_files_skipped`
**Resolution**: Field has `default=0` — Pydantic uses default for absent fields
**Gate**: `test_scout_bundle_round_trips` must pass

## Task-specific review checklist

1. [ ] `important_files_skipped` field in `RepoInfo` with description including TC-4236 tag
2. [ ] `_read_repo_content()` returns 7-tuple; ALL callers updated
3. [ ] Both skip reasons counted (budget_exceeded + file_too_large_for_remaining_budget)
4. [ ] Self-review severity is "medium" (not "high")
5. [ ] Self-review check does NOT fire for good repos (important_files_skipped == 0)
6. [ ] 2 new tests pass
7. [ ] Existing `TestScoutSelfReview` tests pass
8. [ ] `test_scout_bundle_round_trips` passes (default=0)
9. [ ] Schema field description present
10. [ ] `docs/README.md` ownership map checked
11. [ ] No new docs guides needed

## Deliverables

1. Updated `src/launcher/models/understanding.py`
2. Updated `src/launcher/workers/scout/scout.py` (7-tuple + counting)
3. Updated `src/launcher/workers/scout/worker.py` (self-review)
4. Updated `tests/unit/workers/test_scout.py`
5. Updated `tests/unit/workers/test_scout_budget_log_cap.py`
6. `reports/agents/B_implementation/TC-4236/evidence.md`

## Acceptance checks

1. [x] `important_files_skipped` field in `RepoInfo` with `default=0`
2. [x] ScoutWorker.self_review() emits medium finding when count > 0
3. [x] ScoutWorker.self_review() does NOT fire when count == 0
4. [x] Both new tests pass
5. [x] All existing scout + budget tests pass

## Self-review

### Verification results
- [x] Tests: 6/6 TC-4236 tests PASS; 4208 full suite PASS
- [x] Evidence: reports/agents/B_implementation/TC-4236/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py \
  tests/unit/workers/test_scout_budget_log_cap.py \
  -v --tb=short
```

## Integration boundary proven

**Upstream**: `_read_repo_content()` budget loop with TC-4234 rank values
**Downstream**: `ScoutBundle.repo_info.important_files_skipped` in scout_bundle.json
**Contract**: `int` with `default=0` — backward-compatible with old artifacts
