# P7A-05 — Taskcard Governance: Update Allowed Paths and Acceptance Checks

## Status: Not Started

## Gap Linkage: G-06, G-07

Two governance issues from the Phase 7a implementation:

1. **G-06**: Taskcards TC-3821, TC-3822, TC-3823 have `allowed_paths` that don't include
   all files that were actually modified (test files `tests/unit/workers/test_evaluate.py`,
   `tests/unit/workers/test_generate.py`, `tests/unit/test_ir_renderer.py` are missing).
2. **G-07**: Taskcard acceptance checks are all unchecked (`[ ]`). The implementation is
   done but the taskcards were never updated to reflect completion status.

## Role

Senior engineer. Taskcard housekeeping.

## Scope

### Fix

**TC-3821** (`plans/taskcards/TC-3821_claim_leakage_code_blocks.md`):
- Add to `allowed_paths`:
  - `tests/unit/workers/test_evaluate.py`
  - `tests/unit/workers/test_generate.py`
  - `tests/unit/test_ir_renderer.py`
- Check all acceptance checks that are verified:
  - `[x]` Code block containing `[CLM-12345]` stripped by section_validator
  - `[x]` Code block containing `[CLM-12345]` stripped by ir_renderer
  - `[x]` Frontmatter with unknown page_role produces high-severity finding
  - `[x]` Frontmatter with valid page_role produces no role-related findings
  - `[x]` Frontmatter with no page_role produces high-severity finding
  - `[x]` All existing tests pass with PYTHONHASHSEED=0
- Update status: `In-Progress` → `Done`
- Update self-review: `Tests: 2159/2159 PASS`

**TC-3822** (`plans/taskcards/TC-3822_canonical_import_config.md`):
- Check acceptance checks:
  - `[x]` canonical_import in aspose-cells pilot is `aspose_cells_foss`
  - `[x]` canonical_import in aspose-note pilot is `aspose_note_foss`
  - `[ ]` Startup validation catches dotted Python imports (pending P7A-02 strengthening)
  - `[ ]` Startup validation accepts underscored Python imports (pending P7A-01 tests)
  - `[x]` All existing tests pass with PYTHONHASHSEED=0
- Keep status: `In-Progress` (validation not yet fully tested)

**TC-3823** (`plans/taskcards/TC-3823_planner_role_validation.md`):
- Check acceptance checks:
  - `[ ]` Planner self-review produces finding for fake_role (pending P7A-01 tests)
  - `[ ]` Planner self-review passes for all 17 roles (pending P7A-01 tests)
  - `[x]` All existing tests pass with PYTHONHASHSEED=0
- Keep status: `In-Progress` (tests not yet written)

### Allowed paths

- `plans/taskcards/TC-3821_claim_leakage_code_blocks.md`
- `plans/taskcards/TC-3822_canonical_import_config.md`
- `plans/taskcards/TC-3823_planner_role_validation.md`

### Forbidden

Any path not listed above.

## Acceptance Checks

- All three taskcards have accurate `allowed_paths` reflecting actual file modifications
- Acceptance checks match actual verification state (checked = verified, unchecked = pending)
- Status reflects reality (Done only if all checks pass)

## Deliverables

- Updated `plans/taskcards/TC-3821_claim_leakage_code_blocks.md`
- Updated `plans/taskcards/TC-3822_canonical_import_config.md`
- Updated `plans/taskcards/TC-3823_planner_role_validation.md`

## Hard Rules

- Only update governance metadata (allowed_paths, status, acceptance checks)
- Do not change scope, implementation steps, or failure modes
- Check marks must reflect actual verification, not aspirational state

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Consistency | Taskcards accurately reflect implementation reality |
| Scope adherence | Only governance updates, no content changes |
| Correctness | Every `[x]` is verifiable by running a test or reading the code |

## Now (Runbook)

```bash
# 1. Edit TC-3821: add test paths to allowed_paths, check acceptance, set Done
# 2. Edit TC-3822: check verified acceptance items, keep In-Progress
# 3. Edit TC-3823: check verified acceptance items, keep In-Progress
# 4. Review: ensure no [x] is marked without evidence
```
