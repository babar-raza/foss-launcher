# Orchestrator Protocol Execution Plan — Scout/Understand Assessment

## Context

The user requested autonomous execution of the repo plan with chat-first plan resolution, evidence for every claim, mandatory self-review, and final pilot verification.
The disk plan `C:\Users\prora\.claude\plans\refactored-watching-kahn.md` remains relevant for pilot-first sequencing, but one of its remediation steps is stale in the current worktree and must be re-validated before any protected-path edits.

## Goals

- Resolve the current mission into a repo-internal primary plan and preserve prior plan history.
- Run a fresh `aspose-3d-foss-python` pilot to obtain post-redesign evidence.
- Compare the new pilot against the two most recent prior runs before declaring any outcome.
- Apply only still-needed root-cause fixes, with taskcards, tests, docs, and evidence.
- Finish with passing self-reviews or explicit hardening tickets backed by evidence.

## Assumptions

- UNVERIFIED: `.venv/Scripts/python.exe` and the configured LLM endpoint are runnable in this workspace.
- VERIFIED: `C:\Users\prora\.claude\plans\refactored-watching-kahn.md` is accessible and relevant to Scout/Understand.
- VERIFIED: The confidence-override issue called out in the disk plan is stale here because `TC-4252` already changed `llm_unbound` to `llm_fallback`.
- UNVERIFIED: The current dirty worktree is intentional and compatible with a fresh pilot run.

## Steps

1. Materialize plan sources.
   Verify the user protocol and disk plan, then update `reports/PLAN_SOURCES.md`, `reports/PLAN_INDEX.md`, and `TASK_BACKLOG.md` without overwriting prior session history.
2. Validate stale-vs-active remediation items.
   Re-check the disk plan against current code and taskcards so only still-needed work survives into execution.
3. Run the full 3D Python pilot.
   Execute `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml` and capture the resulting run directory, `events.ndjson`, evaluate report, and representative generated pages.
4. Perform AG-018 regression review.
   Compare A+B rate, D+F rate, and CRITICAL counts against the two most recent prior runs recorded in `phase_store` and/or prior run artifacts.
5. Diagnose active root causes from pilot evidence.
   Confirm whether the remaining blocker is still format-matrix sparsity, thin claim volume, or a newer defect class introduced after the redesign waves.
6. If the pilot still fails, create or activate taskcards before protected-path edits.
   Scope each root-cause fix narrowly, implement it, add a regression test, update any touched specs/docs, and record evidence under the agent workspaces.
7. Re-run validation and pilot checks until PASS or a documented blocker.
   Any task self-review dimension below 4/5 routes back to the same owner via a hardening ticket.
8. Publish session status.
   Update `reports/STATUS.md`, `reports/CHANGELOG.md`, agent evidence, and `phase_store/trend.md` with the final state of the session.

## Acceptance criteria

- `reports/PLAN_SOURCES.md` and `reports/PLAN_INDEX.md` contain this session and name a single primary plan source.
- `TASK_BACKLOG.md` contains a live TODO and no prior session content is deleted.
- A fresh 3D Python pilot is executed, or a blocking failure is captured with logs and exact command output references.
- A regression table compares the new pilot to the two most recent prior runs for A+B, D+F, and CRITICAL counts.
- Any protected-path fix is taskcard-authorized, regression-tested, and accompanied by docs/spec updates when behavior changes.
- Every active agent workspace has `plan.md`, `changes.md`, `evidence.md`, `self_review.md`, and `commands.sh`.
- Open questions are empty by session end; unresolved items become concrete investigation or hardening steps.

## Risks + rollback

- Risk: the dirty worktree may already contain partial changes affecting pilot output.
  Rollback: do not revert unrelated files; treat the current tree as the baseline and document that baseline in evidence.
- Risk: pilot execution may fail due to missing credentials or network access.
  Rollback: capture the failing command, environment prerequisite, and blocker in `reports/STATUS.md` and the agent evidence files.
- Risk: the disk plan may recommend fixes that are already superseded.
  Rollback: prefer repo evidence over plan prose and record stale plan items explicitly.

## Evidence commands

```powershell
git status --short
rg -n "llm_unbound|llm_fallback|_CONFIDENCE_BY_SOURCE|fact_binding_validated|low_confidence_claims_dropped" src tests phase_store reports
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```

## Open questions

None. Investigation for any pilot-discovered unknowns is explicitly covered by Steps 5-7.
