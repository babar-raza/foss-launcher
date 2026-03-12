# BT-03: Add Observability to Backtick Wrapping

**Status**: Done
**Gap linkage**: BT-00 → BT-03
**Role**: Engineer
**Severity**: MEDIUM — impossible to debug backtick wrapping issues in production

## Problem

`_backtick_api_names()` in `section_validator.py` has zero logging. When backticks are applied (or not applied), there is no way to trace what happened without adding breakpoints. Other functions in the same file (`_strip_claim_comments`, `_strip_claim_citations`, `_validate_table_content`) all have debug/info logging.

## Scope

**In scope**: Add debug-level logging to `_backtick_api_names()`.
**Out of scope**: Structured logging migration, new log sinks.

## Fix

Add three log statements:

1. **Entry**: `logger.debug("Backtick pass: %d identifiers, %d chars content", len(api_identifiers), len(content))`
2. **Matches found**: `logger.debug("Backtick pass: %d matches, %d protected, %d wrapped", len(matches), skipped, wrapped)`
3. **No-op short circuit**: Already implicit from empty identifiers check, but add: `logger.debug("Backtick pass: skipped (no identifiers)")` when `api_identifiers` is empty/None

## Acceptance Checks

- [ ] Debug log emitted on entry with identifier count
- [ ] Debug log emitted with match/skip/wrap counts
- [ ] No logging at INFO or above during normal operation (debug only)
- [ ] Existing tests pass

## Deliverables

- Modified: `src/launcher/workers/generate/section_validator.py`

## Hard Rules

- DEBUG level only — no INFO/WARNING for normal backtick operations
- No new dependencies
- Match the existing logging style in the file (uses `logger.debug()` pattern)

## Review Dimensions

1. Log output is useful for debugging (shows counts, not raw content)
2. No sensitive content in logs (no full block content)
3. Consistent with other functions in the same file

## Now (Runbook)

1. Read `section_validator.py:_backtick_api_names()` (lines 313-363)
2. Add counter variables for skipped/wrapped matches
3. Add debug log at entry and after processing
4. Run full test suite
