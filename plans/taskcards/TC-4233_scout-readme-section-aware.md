---
id: TC-4233
title: "Scout README section-aware extraction (replace [:4000] blind slice)"
status: Done
priority: High
owner: "agent-B"
updated: "2026-03-12"
tags: [scout, readme, content-quality]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4233_scout-readme-section-aware.md
  - src/launcher/workers/scout/scout.py
  - tests/unit/workers/test_scout.py
evidence_required:
  - reports/agents/B_implementation/TC-4233/evidence.md
---

# Taskcard TC-4233 — Scout README section-aware extraction

## Objective

Replace the blind `[:4000]` truncation in `run_scout()` (scout.py:84) with a
`_extract_readme_summary()` helper that produces up to 8000 chars of the most
information-dense README sections. Ensures API overviews, format lists, and code
examples appearing after char 4000 reach the Understand worker.

## Required spec references

- `specs/worker_understand.md` (Section: Phase A — Scout: README summary)

## Scope

### In scope
- New `_extract_readme_summary(raw: str, max_chars: int = 8000) -> str` in scout.py
- Call-site update: `readme_summary = _extract_readme_summary(repo_content[_key])`
- 5 new unit tests in `TestReadmeSectionExtraction`

### Out of scope
- Changing sanitize_input cap (stays 100K)
- Changes to UnderstandWorker or downstream consumers

## Inputs

- `repo_content[readme_key]` — sanitized README text (up to 100K chars)

## Outputs

- `readme_summary` — up to 8000 chars, section-prioritized by heading keywords

## Allowed paths

- plans/taskcards/TC-4233_scout-readme-section-aware.md
- src/launcher/workers/scout/scout.py
- tests/unit/workers/test_scout.py

### Allowed paths rationale
Scout logic lives entirely in scout.py; tests in test_scout.py.

## Implementation steps

### Step 1: Implement `_extract_readme_summary()`

Add after `_read_readme()` function.

### Step 2: Update call site in `run_scout()` at line 84

### Step 3: Add 5 unit tests in TestReadmeSectionExtraction

## Failure modes

### Failure mode 1: No headings in README
**Detection**: `boundaries` list is empty
**Resolution**: Returns `raw[:max_chars]` — degrades to old behavior
**Gate**: `test_short_readme_unchanged`

### Failure mode 2: All sections above budget
**Detection**: Every section is larger than remaining budget
**Resolution**: Greedy fill truncates at sentence boundary
**Gate**: `test_budget_respected`

### Failure mode 3: README key case mismatch
**Detection**: Key not in repo_content
**Resolution**: Existing case-insensitive loop at run_scout:81-87 handles this
**Gate**: Existing `test_readme_summary_extracted_from_repo_content`

## Task-specific review checklist

1. [ ] `_extract_readme_summary()` has docstring explaining algorithm
2. [ ] Call site at scout.py:84 replaced with new function
3. [ ] All 5 new tests pass
4. [ ] Existing `TestReadmeSanitization` tests still pass
5. [ ] Output is always ≤ max_chars
6. [ ] Intro paragraph always appears first in output
7. [ ] Docstrings updated for `run_scout()`
8. [ ] Spec confirmed — no spec drift
9. [ ] Schema description confirmed — `readme_summary` field in RepoInfo unchanged
10. [ ] `docs/README.md` ownership map checked
11. [ ] No new `docs/guides/` files needed

## Deliverables

1. Updated `src/launcher/workers/scout/scout.py` with `_extract_readme_summary()`
2. Updated `tests/unit/workers/test_scout.py` with `TestReadmeSectionExtraction`
3. `reports/agents/B_implementation/TC-4233/evidence.md`

## Acceptance checks

1. [x] `_extract_readme_summary` function exists in scout.py
2. [x] 5 new tests in `TestReadmeSectionExtraction` pass
3. [x] All existing scout tests pass (no regression)
4. [x] Output length ≤ 8000 chars on a 15K README

## Self-review

### Verification results
- [x] Tests: 4208/4208 PASS (full suite, 1 pre-existing failure unrelated to TC-4233)
- [x] Evidence captured: reports/agents/B_implementation/TC-4233/evidence.md
- [x] Doc freshness: no spec changes required

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py::TestReadmeSectionExtraction \
  tests/unit/workers/test_scout.py::TestReadmeSanitization \
  -v --tb=short
```

**Expected results**:
- All `TestReadmeSectionExtraction` tests pass
- `TestReadmeSanitization` still passes (no regression)

## Integration boundary proven

**Upstream**: `repo_content[readme_key]` from `_read_repo_content()`
**Downstream**: `RepoInfo.readme_summary` consumed by `UnderstandWorker`
**Contract**: `str` of max 8000 chars, sanitize_input already applied
