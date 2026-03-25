# TC-3640 Agent B Implementation Plan

## Mission

Add two new validation functions to `tools/validate_taskcards.py` that enforce
`## Root cause` and `## Approaches considered` sections on Draft/In-Progress taskcards.

## What was already present

Before any changes, `tools/validate_taskcards.py` already contained:

- `extract_section(body, heading)` at lines 191-195 (functionally equivalent to the
  specified `_extract_section()` helper)
- `validate_root_cause_section(taskcard_path, body, status)` at lines 198-217
- `validate_approaches_considered_section(taskcard_path, body, status)` at lines 220-239
- Both functions wired into `validate_taskcard_file()` at lines 714-721

The implementation was already complete. No code additions to `validate_taskcards.py`
were needed.

## What required fixing

The TC-3640 taskcard's `## Allowed paths` body section (lines 117-132) used
backtick-wrapped paths (e.g., `` `tools/validate_taskcards.py` ``) while the
frontmatter used plain paths (e.g., `tools/validate_taskcards.py`).

The `extract_body_allowed_paths()` function does not strip backtick wrapping, so
the comparison failed with a mismatch. The fix was to remove the backtick wrapping
from the TC-3640 taskcard body `## Allowed paths` section, making it consistent
with the frontmatter.

## Steps taken

1. Read `tools/validate_taskcards.py` — confirmed all three functions and wiring
   already present (lines 191-239, 714-721)
2. Ran `validate_taskcard_file()` on TC-3640 — found body/frontmatter path mismatch
   due to backtick wrapping in body
3. Fixed TC-3640 `## Allowed paths` body section: removed backtick wrapping from all 16
   path entries
4. Re-ran validation — TC-3640 now passes; TC-3633 (Done) still fails on pre-existing
   issues unrelated to the new functions (backward compat confirmed)
5. Created evidence files
