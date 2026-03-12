# RID-13: Retroactive Taskcard for Run ID v3 (AG-002)

## Status: Done

## Gap Linkage
- G-RV3-05: AG-002 taskcard violation — `src/launcher/**` modified without taskcard (repeat offense from same module)

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Create a retroactive taskcard under `plans/taskcards/` documenting the run ID v3
change (timestamp + family + platform format). This is the second AG-002 violation
for this module — the first was tracked by RID-03 and resolved with TC-3805. This
taskcard must:

1. Follow `TC-000_TEMPLATE.md` with all 14 mandatory sections
2. Reference files modified: `src/launcher/util/run_id.py`, `src/launcher/orchestrator/run_loop.py`, `scripts/run_pilot.py`, `tests/unit/util/test_run_id.py`, `tests/unit/orchestrator/test_run_manifest.py`
3. Set status to `Done` with explicit note: "Retroactive — code was written before taskcard (AG-002 violation, repeat offense)"
4. Reference the previous taskcard TC-3805 as predecessor
5. Flag the repeat violation in the self-review section with a root-cause note: "Agent did not check CLAUDE.md governance rules before starting implementation"

### Allowed paths
- `plans/taskcards/TC-XXXX_run_id_v3_family_platform.md` (new file, pick next available TC number)

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `ls plans/taskcards/TC-*run_id_v3*` returns exactly one file
- `grep -c "##" plans/taskcards/TC-*run_id_v3*` returns ≥14 (all sections present)

### Tests
- N/A (governance artifact, no code)

### Config respected end-to-end
- Taskcard `allowed_paths` matches all 5 files that were modified
- Taskcard status is `Done`

## Deliverables
- One taskcard file under `plans/taskcards/` with all 14 mandatory sections

## Hard Rules
- Follow TC-000_TEMPLATE.md exactly
- No code changes
- Document the AG-002 violation honestly and identify root cause
- Reference predecessor TC-3805

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 14 sections filled, no TBD, root cause identified |
| Consistency | Matches template format exactly; references predecessor |
| Scope adherence | Single file under `plans/taskcards/` |
| Maintainability | Future engineers can trace the v3 change to this taskcard |
| Minimality | One file, no code |

## Now (Runbook)

```bash
# 1. Check next available TC number
ls plans/taskcards/TC-*.md | sort -t- -k2 -n | tail -5
# 2. Copy template
cp plans/taskcards/TC-000_TEMPLATE.md plans/taskcards/TC-XXXX_run_id_v3_family_platform.md
# 3. Fill all 14 sections
# 4. Set status to Done with retroactive note
# 5. Verify section count
grep -c "##" plans/taskcards/TC-XXXX_run_id_v3_family_platform.md
```
