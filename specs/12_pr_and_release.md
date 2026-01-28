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
## Rollback + Recovery Contract (Guarantee L - Binding)

All PR artifacts MUST include rollback metadata to enable safe rollback when launches fail in production.

### Required rollback fields

The `RUN_DIR/artifacts/pr.json` file MUST include:

- **`base_ref`**: The commit SHA of the site repo before changes (base of the PR branch)
- **`run_id`**: The run that produced this PR (links artifacts to telemetry/logs)
- **`rollback_steps`**: Array of shell commands to revert changes (e.g., `["git revert <sha>", "git push"]`)
- **`affected_paths`**: Array of all modified/created file paths (for blast radius assessment)

### Enforcement

- **Prod profile**: pr.json MUST exist and include all rollback fields. Validation MUST fail if missing.
- **CI profile**: pr.json SHOULD exist; validation warns if missing rollback fields.
- **Local profile**: pr.json optional.

### Schema

All pr.json artifacts MUST validate against `specs/schemas/pr.schema.json`.

### Rollback procedure template

```bash
# Rollback procedure (generated from pr.json rollback_steps)
git fetch origin
git checkout <base_ref>
git revert --no-commit <pr_merge_sha>
git commit -m "Rollback: revert launch run <run_id>"
git push origin main
```

## Telemetry commit association (non-negotiable)
After each commit is created via the commit service, the orchestrator MUST associate the returned commit SHA
with telemetry runs using the Local Telemetry API `associate-commit` endpoint (see `specs/16_local_telemetry_api.md`).

