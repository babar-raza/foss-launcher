# AQ-08 — Taskcard Governance: Evidence Files + Acceptance Checks

**Status**: Not Started
**Gap linkage**: GAP-13 (evidence files not written, taskcard acceptance checks not ticked)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

AG-002 requires taskcards to be marked Done only when ALL acceptance checks are `[x]`, evidence files exist, and tests pass. Both TC-3816 and TC-3817:
- Have `evidence_required` fields pointing to `reports/TC-3816/evidence.md` and `reports/TC-3817/evidence.md`
- Neither evidence file was created
- Acceptance check items in both taskcards remain as `[ ]`
- TC-3817 was set to `In-Progress` without explicit user approval

This taskcard closes the governance loop.

## Scope

### Fix

1. Write evidence files for both TC-3816 and TC-3817 with test results and change summaries
2. Tick acceptance checks in both taskcard frontmatter
3. Set both taskcards to `Done` status

### Allowed paths
- `plans/taskcards/TC-3816_adaptive_understand.md`
- `plans/taskcards/TC-3817_generate_planner_quality.md`
- `reports/TC-3816/evidence.md`
- `reports/TC-3817/evidence.md`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: Evidence files exist at expected paths
- **Tests**: N/A (no code changes)
- **Config respected end-to-end**: Taskcard status = Done, all `[ ]` → `[x]`
- **No mock data in production paths**: Evidence reflects actual test run results

## Deliverables

1. `reports/TC-3816/evidence.md` — test counts, file list, change summary
2. `reports/TC-3817/evidence.md` — test counts, file list, change summary
3. Updated `TC-3816_adaptive_understand.md` — status: Done, acceptance checks ticked
4. Updated `TC-3817_generate_planner_quality.md` — status: Done, acceptance checks ticked

## Hard rules

- Evidence must reflect actual current test suite results (run `pytest` and capture count)
- Acceptance checks must be honestly assessed — only tick what is truly done
- Note any acceptance checks that depend on healing taskcards (AQ-01 through AQ-07) and leave those unticked with a note

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Thoroughness | Every acceptance check item has a clear pass/fail/pending status |
| Consistency | Evidence file format matches any existing evidence files in `reports/` |
| Scope adherence | Only touches taskcard/evidence files, no code changes |

## Now (runbook)

```bash
# 1. Run test suite to get current counts
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short 2>&1 | tail -5

# 2. Create reports/TC-3816/ and reports/TC-3817/ directories
mkdir -p reports/TC-3816 reports/TC-3817

# 3. Write evidence files with actual results

# 4. Update taskcard frontmatter: status → Done

# 5. Tick acceptance checks that are met; note healing deps for others
```
