# BT-06: AG-002 Retroactive Taskcard for Backtick Implementation

**Status**: Done
**Gap linkage**: BT-00 → BT-06
**Role**: Governance
**Severity**: LOW — governance violation, code already written and tested

## Problem

The backtick API name wrapping implementation modified 8 files under protected paths (`src/launcher/`, `specs/schemas/`) without a prior taskcard. This violates AG-002, the repository's #1 governance rule. The code is functional and tested (1904 tests pass), but the governance record is missing.

## Scope

**In scope**: Create a retroactive taskcard in `plans/taskcards/` documenting the work that was done.
**Out of scope**: Reverting the code, re-doing the work.

## Fix

Create `plans/taskcards/TC-XXXX_api_backtick_wrapping.md` from the template with:
- All 14 mandatory sections filled
- Status: `Done` (work is complete)
- Note in header: "Retroactive — created post-implementation to satisfy AG-002"
- `allowed_paths` listing all 8 modified files
- Acceptance checks marked as `[x]` with evidence

## Files Modified (for taskcard record)

1. `src/launcher/models/product.py` — added `api_identifiers` field
2. `specs/schemas/understanding_bundle.schema.json` — added `api_identifiers` property
3. `src/launcher/workers/understand/extract.py` — collect identifiers in `_extract_api_surface()`
4. `src/launcher/prompts/section_writer.txt` — backtick rule in prompt
5. `src/launcher/workers/generate/section_prompt.py` — backtick class names in format
6. `src/launcher/workers/generate/worker.py` — thread `api_ids` to validator
7. `src/launcher/workers/generate/section_validator.py` — `_backtick_api_names()` + signature extensions
8. `src/launcher/prompts/review_prompt.txt` — check #10

## Acceptance Checks

- [ ] Taskcard exists in `plans/taskcards/` with all 14 sections
- [ ] Status is `Done`
- [ ] Retroactive note is present
- [ ] All 8 modified files listed in `allowed_paths`

## Deliverables

- New: `plans/taskcards/TC-XXXX_api_backtick_wrapping.md`

## Hard Rules

- Use the official template from `plans/taskcards/TC-000_TEMPLATE.md`
- Do NOT modify any code — this is a governance-only task

## Now (Runbook)

1. Read `plans/taskcards/TC-000_TEMPLATE.md`
2. Copy to new taskcard file with appropriate TC number
3. Fill all 14 sections referencing the completed work
4. Set status to `Done`
