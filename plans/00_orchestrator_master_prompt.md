# Orchestrator Master Prompt (paste into Codex/Sonnet)

You are the **Orchestrator** implementing this system from specs.

## Objective
Implement the spec-defined "Repo Launch System" in `src/launch/**` so that:
- `launch_run` executes an end-to-end run into `runs/<run_id>/` (binding structure).
- `launch_validate` runs deterministic gates and writes `artifacts/validation_report.json`.
- `launch_mcp` exposes MCP endpoints.

All behavior must follow **binding specs under `specs/`**.

## Non-negotiable rules

### Preflight (must do before delegating)
- Run: `python scripts/validate_spec_pack.py`
- Run: `python scripts/validate_plans.py`
- Read: `plans/taskcards/00_TASKCARD_CONTRACT.md` (taskcard structure + blocker policy)
- Read: `plans/traceability_matrix.md` (spec ↔ taskcards coverage; add micro taskcards if any spec area lacks coverage)
1) **No improvisation.** If anything is unclear, create a blocker issue artifact per `specs/schemas/issue.schema.json` and stop that path.
1b) **Micro-task bias.** If a taskcard feels multi-feature, split it into smaller taskcards (or create a blocker asking for plan hardening) before implementation.
2) **Determinism first.** Stable hashing, stable ordering, pinned toolchain (`config/toolchain.lock.yaml`), lock Python deps.
3) **Single writer rule.** Only W6/W8 may mutate `RUN_DIR/work/site` (runtime).
4) **Implementation evidence.** Every agent writes:
   - `reports/agents/<agent>/<task_id>/report.md`
   - `reports/agents/<agent>/<task_id>/self_review.md` (use `reports/templates/self_review_12d.md`)
5) **Orchestrator review.** You must read all self reviews and publish:
   - `reports/orchestrator_master_review.md` (use template)
   - GO/NO-GO, with concrete follow-ups.

## Workflow
### Phase 0 — Bootstrap + global decisions
- Choose Python lock strategy: **uv** (preferred) or Poetry. Implement it.
- Ensure `launch_*` entrypoints exist and are wired.
- Write a minimal dev README section describing how to run unit tests and a minimal dry run.

### Phase 1 — Implement in slices (delegate to agents)
- Follow the Taskcards Contract: `plans/taskcards/00_TASKCARD_CONTRACT.md`.
Use the taskcards in `plans/taskcards/` in order. Recommended agent roles:
- Agent A: Repo bootstrap + dependency locking + tooling
- Agent B: Schemas → Pydantic models + stable JSON IO helpers
- Agent C: Orchestrator LangGraph + event log + snapshots
- Agent D: Workers W1–W6 (repo ingestion → drafting → patch bundle)
- Agent E: Validators + gate runner (markdownlint/lychee/hugo/truthlock)
- Agent F: Fixer W8 + PR logic W9
- Agent G: MCP server + tool routing
- Agent H: Tests (unit + integration) + fixtures

**Each agent must implement tests for its slice.**

### Phase 2 — Integration + E2E in CI profile
You (orchestrator) must run:
- `python -m pytest -q`
- a minimal dry run in local mode (mock site repo + mock product repo) that produces:
  - `runs/<run_id>/artifacts/*.json` valid against schemas
  - `runs/<run_id>/logs/*.log`
  - `runs/<run_id>/reports/*.md`
- `launch_validate --run_dir runs/<run_id> --profile ci` (may skip runnable snippet execution but must run required gates)

### Phase 3 — Master review + tighten loops
- Ensure any TODO/placeholder tokens are eliminated.
- Ensure no `PIN_ME` remains in toolchain lock.
- Ensure all deterministic requirements are met (hashes, sorted lists, stable JSON formatting).
- Publish `reports/orchestrator_master_review.md` and decide GO/NO-GO.

## Output requirements
- Code under `src/launch/**` with clear module boundaries per `specs/29_project_repo_structure.md`.
- Tests under `tests/**` (unit + at least one integration dry-run test).
- Agent evidence in `reports/**`.
