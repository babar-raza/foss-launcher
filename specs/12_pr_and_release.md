# PR and Release Manager

## Goal
Open a clean PR that is easy for humans to review, with evidence and checklists.

## Non-negotiable
All commits and PR actions against aspose.org MUST go through the centralized GitHub commit service.
Direct git commits from the orchestrator are forbidden in production mode.

See 17_github_commit_service.md.

## Branching
- Create a deterministic branch name:
  - launch/<product_slug>/<github_ref_short>/<run_id_short>

## Commits
- Use atomic commits via the commit service:
  1) artifacts and plan (optional to include in repo if allowed)
  2) content drafts applied
  3) fixes from validation
- Commit messages and bodies MUST be generated from configurable templates in run_config.

## PR description must include
- Summary of what was launched
- Page inventory by section with links
- Evidence summary (top claim citations)
- Validation checklist results
- Links to run artifacts (or attached)

## Acceptance
- PR opens successfully (via commit service)
- PR body contains validation_report summary and diff highlights
## Telemetry commit association (non-negotiable)
After each commit is created via the commit service, the orchestrator MUST associate the returned commit SHA
with telemetry runs using the Local Telemetry API `associate-commit` endpoint (see `specs/16_local_telemetry_api.md`).

