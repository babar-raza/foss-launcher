# Chat-Derived Plan: Scout/Intake Module A/A+ Grade Fixes

**Materialized**: 2026-03-12
**Source**: Orchestrator conversation — scout gap analysis + plan design
**Primary plan**: `C:\Users\prora\.claude\plans\bubbly-strolling-toast.md`
**Status**: In-Progress — executing via TC-4233..TC-4236

---

## Context

Scout (Phase 1 of the pipeline) was graded B+ after pilot analysis of
aspose-cells-foss and aspose-3d-foss runs. Four root-cause gaps prevent A/A+.
This plan delivers production-grade fixes, not patches.

---

## Goals

1. Replace blind `[:4000]` README truncation with section-aware extraction
2. Upgrade binary file importance ranking to multi-factor 0-7 scoring
3. Extend rich manifest metadata (description, deps, entrypoints) to all platforms
4. Add observability metric for important files skipped by budget manager

---

## Assumptions (verified)

- [VERIFIED] `readme_summary = repo_content[_key][:4000]` — scout.py:84
- [VERIFIED] `_file_importance_rank()` returns 0/1 — scout.py:222-235
- [VERIFIED] description/deps/entrypoints only populated for Python — scout.py:600 comment
- [VERIFIED] No `important_files_skipped` metric in RepoInfo — understanding.py:56-80
- [VERIFIED] TC-4230..TC-4232 IDs already used; new IDs are TC-4233..TC-4236
- [VERIFIED] `SharedFacts` already has description/dependencies/entrypoints fields — understanding.py:50-53

---

## Steps (repo-specific)

1. [TC-4233] `_extract_readme_summary(raw, max_chars=8000)` — section-aware, replaces `[:4000]`
2. [TC-4234] `_file_importance_rank()` returns int 0-7 with 4 additive factors
3. [TC-4235] Extend all manifest parsers to 7-tuple; add platform-priority ordering
4. [TC-4236] Add `important_files_skipped: int` to `RepoInfo`; ScoutWorker self-review warning

---

## Acceptance Criteria

- `readme_summary` for aspose-cells-foss contains content from after char 4000
- `_file_importance_rank("OVERVIEW.md", FileCategory.doc)` ≥ 3 (was 0)
- `SharedFacts.description` non-empty for a fake Node/Java/C# repo
- `repo_info.important_files_skipped` field present in scout_bundle.json
- All existing tests pass (PYTHONHASHSEED=0)
- New tests: ≥15 new test cases across the 4 TCs

---

## Evidence Commands

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_scout.py \
  tests/unit/workers/test_scout_budget_log_cap.py \
  tests/unit/workers/test_scout_facts.py \
  -v --tb=short

PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q --tb=short
```

---

## Risks + Rollback

- Risk: Extending manifest parsers breaks existing tests → rollback: revert scout.py to prior state
- Risk: README section extraction diverges from expected output → rollback: reduce max_chars back to 8000 (keep algorithm)
- Risk: RepoInfo schema change breaks serialized artifacts → mitigation: `default=0` on new field

---

## Open Questions

(none — all resolved during investigation)
