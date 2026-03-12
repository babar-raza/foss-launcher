---
id: TC-4102
title: "Doc importance rank: substring matching for compound stem names"
status: Done
priority: Low
owner: Agent-B
updated: "2026-03-11"
tags: [scout, file-prioritization]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4102_stem_substring_matching.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout.py
  - reports/agents/B/TC-4102/evidence.md
evidence_required:
  - reports/agents/B/TC-4102/evidence.md
---

# Taskcard TC-4102 — Doc importance rank: substring matching for compound stem names

## Objective

`_file_importance_rank()` in `scout.py` uses `stem in _DOC_IMPORTANCE_STEMS` (exact set membership). Files like `api_reference.md` normalize to stem `apireference` which does NOT match `"reference"` exactly. This fix changes the match from exact set membership to substring containment so that compound names like `api_reference`, `getting-started`, and `quickstart` all resolve to rank 1.

## Required spec references

- `specs/worker_understand.md` (Section: Scout file budget allocation — importance ranking)
- `specs/system_overview.md` (Section: Scout phase output contracts)

## Scope

### In scope
- Change `_file_importance_rank()` logic in `src/launcher/workers/scout/scout.py` from exact match to substring containment
- Same change applied to `_SOURCE_IMPORTANCE_STEMS` branch in the same function
- Unit tests in `tests/unit/workers/test_scout.py` verifying compound stem names rank 1

### Out of scope
- Changing the `_DOC_IMPORTANCE_STEMS` or `_SOURCE_IMPORTANCE_STEMS` sets themselves
- Changing budget allocation logic that consumes importance ranks
- Modifying any other function in `scout.py`

## Inputs

- `src/launcher/workers/scout/scout.py` — `_file_importance_rank()` and importance stem sets
- `tests/unit/workers/test_scout.py` — existing test suite to extend

## Outputs

- Updated `scout.py` with substring-containment importance matching
- New unit tests in `test_scout.py`
- `reports/agents/B/TC-4102/evidence.md`

## Allowed paths

- plans/taskcards/TC-4102_stem_substring_matching.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout.py
- reports/agents/B/TC-4102/evidence.md

### Allowed paths rationale

- `scout.py` contains the `_file_importance_rank()` function to be changed
- `test_scout.py` is the existing scout test module for the regression tests
- `evidence.md` captures the pytest run output

## Implementation steps

### Step 1: Read _file_importance_rank() and the importance stem sets

Read `scout.py` — locate `_file_importance_rank()`, `_DOC_IMPORTANCE_STEMS`, and `_SOURCE_IMPORTANCE_STEMS`. Note the current exact-match logic and how the normalized stem is computed (lowercased, hyphens/underscores stripped).

### Step 2: Change exact match to substring containment for doc stems

Replace:
```python
return 1 if stem in _DOC_IMPORTANCE_STEMS else 0
```
With:
```python
return 1 if any(s in stem for s in _DOC_IMPORTANCE_STEMS) else 0
```

Apply the same change to the `_SOURCE_IMPORTANCE_STEMS` branch.

### Step 3: Write unit tests

In `tests/unit/workers/test_scout.py`, add tests verifying:
- `api_reference.md` → rank 1 (normalized stem `apireference` contains `"reference"`)
- `GETTING-STARTED.md` → rank 1 (normalized stem `gettingstarted` contains `"getting"` or `"start"`)
- `quickstart.rst` → rank 1 (normalized stem `quickstart` contains `"quick"` or `"start"`)
- `random_file.py` → rank 0 (no importance stem is a substring)
- `setup.py` → rank 1 via `_SOURCE_IMPORTANCE_STEMS` if `"setup"` is a source stem (verify or skip based on actual set)

## Failure modes

### Failure mode 1: Short stem false positives (e.g., "api" in "capital")

**Detection**: A file named `capital.md` normalizes to `capital` which contains `"api"` as substring — would incorrectly rank 1.
**Resolution**: Review `_DOC_IMPORTANCE_STEMS` — confirm no stem is fewer than 3 characters. "api" (3 chars) is the shortest and matching inside "capital" is an acceptable tradeoff since API docs are genuinely high importance. The list is bounded and explicit. Document the accepted false-positive rate in the function docstring.
**Gate**: `specs/worker_understand.md` — budget allocation; over-inclusion has lower cost than under-inclusion.

### Failure mode 2: `_SOURCE_IMPORTANCE_STEMS` over-matching source files

**Detection**: Common utility files (e.g., a file containing `"test"` in the stem) rank as importance 1 unexpectedly.
**Resolution**: Check that no source stem would cause broad over-matching. `"__init__"` normalizes to `"init"` — already handled by earlier fixes. The change is safe as long as stems are at least 4 characters and domain-specific.
**Gate**: Scout budget allocation — importance rank 1 files get higher token budget; false positives waste budget but do not cause failures.

### Failure mode 3: Empty stem after normalization

**Detection**: A file named `-.md` normalizes to empty string `""` — `any(s in "" for s in stems)` returns False correctly.
**Resolution**: No special handling needed — `any(s in "" ...)` for any non-empty `s` is always False. Empty stems naturally rank 0.
**Gate**: `specs/worker_understand.md` — degenerate filenames must not crash the scout.

## Task-specific review checklist

1. [ ] Both `_DOC_IMPORTANCE_STEMS` and `_SOURCE_IMPORTANCE_STEMS` branches use substring containment
2. [ ] The normalization step (lowercase, strip hyphens/underscores) is applied BEFORE the substring check
3. [ ] Unit test: `api_reference.md` → rank 1
4. [ ] Unit test: `GETTING-STARTED.md` → rank 1
5. [ ] Unit test: `random_file.py` → rank 0
6. [ ] No stems shorter than 3 characters exist in either set (verified by inspection)
7. [ ] Docstring for `_file_importance_rank()` updated to document substring matching behavior
8. [ ] Spec file `specs/worker_understand.md` reviewed — no spec drift introduced
9. [ ] Schema `"description"` fields present for any new/changed properties (N/A — no schema change)
10. [ ] Checked `docs/README.md` ownership map — scout internals change does not require guide update
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated (N/A for this TC)

## Deliverables

1. Updated `src/launcher/workers/scout/scout.py` with substring-containment importance ranking
2. New unit tests in `tests/unit/workers/test_scout.py`
3. `reports/agents/B/TC-4102/evidence.md` with pytest output showing 0 failures

## Acceptance checks

- [ ] Unit test: compound names (`api_reference`, `getting-started`, `quickstart`) rank 1
- [ ] Unit test: completely unrelated names rank 0
- [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py -v` — 0 failures
- [ ] No regressions in existing `test_scout.py` tests

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: substring importance matching PASS
- [ ] Evidence captured: `reports/agents/B/TC-4102/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_scout.py -v
```

**Expected results**:
- All pre-existing `test_scout.py` tests PASS
- New substring-match tests PASS: compound names → rank 1, unrelated → rank 0

## Integration boundary proven

**Upstream**: `_file_importance_rank()` receives a normalized filename stem from the scout file-walk
**Downstream**: Importance ranks feed into Scout's budget allocator — rank-1 files receive higher token budgets
**Contract**: `_file_importance_rank()` returns int (0 or 1) for any valid filename string — unchanged by this fix; behavior extended to compound stems
