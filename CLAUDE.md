# foss-launcher — Agent Instructions

## Mandatory: Taskcard-First Workflow

Before making ANY code changes (edits, new files, refactors, bug fixes, features),
you MUST create or identify a taskcard:

1. Check if a relevant taskcard exists: search `plans/taskcards/` for the topic
2. If one exists and is In-Progress: reference it and proceed
3. If none exists: create one FIRST using `python scripts/create_taskcard.py`
   - Follow the contract at `plans/taskcards/00_TASKCARD_CONTRACT.md`
   - Template: `plans/_templates/taskcard.md` (manual) or use the script (interactive)
   - All 14 required frontmatter fields must be present
   - All 14 mandatory body sections must be filled
   - Run `python tools/validate_taskcards.py` to confirm validity
4. Only after a valid taskcard exists with status `In-Progress`: proceed with implementation

This applies to ALL changes — even "small" fixes. No exceptions unless the user
explicitly says "skip the taskcard."

## Why This Matters

- Taskcards are the traceability backbone of this project
- Every code change must be traceable to a taskcard (specs/30_ai_agent_governance.md)
- CI/CD will block PRs without proper taskcard coverage
- The pre-commit hook checks that staged source files are covered by an In-Progress taskcard
- 400+ existing taskcards set the precedent — all changes follow this pattern

## Taskcard Quick Reference

- Contract: `plans/taskcards/00_TASKCARD_CONTRACT.md`
- Template: `plans/_templates/taskcard.md`
- Creator: `python scripts/create_taskcard.py`
- Validator: `python tools/validate_taskcards.py`
- Coverage checker: `python tools/check_taskcard_coverage.py`
- Governance spec: `specs/30_ai_agent_governance.md`

## Allowed Paths per Taskcard

Each taskcard defines `allowed_paths` in its frontmatter. Only modify files
within those paths when working on that taskcard. Shared libraries have
single-owner restrictions:
- `src/launch/io/**` — only TC-200
- `src/launch/util/**` — only TC-200
- `src/launch/models/**` — only TC-250
- `src/launch/clients/**` — only TC-500

## Other Governance Rules

See `.claude_code_rules` for additional rules (AG-001 through AG-009):
- Branch creation requires approval (AG-001)
- Destructive operations blocked (AG-005)
- Protected files require approval (AG-008)
- Dependency installation requires approval (AG-009)
