# RID-03: Retroactive Taskcard for AG-002 Compliance

## Status: Done

## Gap Linkage
- G-RID-04: AG-002 taskcard violation — code was written under `src/launcher/**` without a taskcard

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
Create a retroactive taskcard under `plans/taskcards/` documenting the run-ID
unification work that was already performed. This does NOT re-do the code — it
creates the governance artifact that should have existed before the code was written.

The taskcard must:
1. Follow the `TC-000_TEMPLATE.md` format with all 14 mandatory sections filled
2. Reference the files already modified: `src/launcher/util/run_id.py`, `src/launcher/orchestrator/run_loop.py`, `scripts/run_pilot.py`
3. Set status to `Done` with a note that this is a retroactive filing
4. Include acceptance checks that can be verified against the current codebase state
5. Flag the AG-002 violation in the self-review section

### Allowed paths
- `plans/taskcards/TC-XXXX_run_id_unification.md` (new file, pick next available TC number)

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `ls plans/taskcards/TC-*run_id*` returns exactly one file

### Tests
- N/A (governance artifact, no code)

### Config respected end-to-end
- Taskcard `allowed_paths` matches the 3 files that were modified
- Taskcard status is `Done`

## Deliverables
- One taskcard file under `plans/taskcards/` with all 14 mandatory sections

## Hard Rules
- Follow TC-000_TEMPLATE.md exactly
- No code changes
- Document the AG-002 violation honestly in self-review

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Thoroughness | All 14 sections filled, no TBD |
| Consistency | Matches template format exactly |
| Scope adherence | Single file under `plans/taskcards/` |
| Maintainability | Future engineers can trace the change back to this taskcard |
| Minimality | One file, no code |

## Now (Runbook)

```bash
# 1. Check next available TC number
ls plans/taskcards/TC-*.md | tail -5
# 2. Copy template
cp plans/taskcards/TC-000_TEMPLATE.md plans/taskcards/TC-XXXX_run_id_unification.md
# 3. Fill all 14 sections
# 4. Set status to Done with retroactive note
# 5. Verify
grep -c "##" plans/taskcards/TC-XXXX_run_id_unification.md  # should be ≥14
```
