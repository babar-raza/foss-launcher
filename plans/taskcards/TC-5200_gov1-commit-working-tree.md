---
id: TC-5200
title: "GOV-1 — Commit working tree: 152 tracked modifications"
status: In-Progress
priority: High
owner: "Agent-A"
updated: "2026-03-25"
tags: [governance, commit, working-tree]
depends_on: []
ruleset_version: "ruleset.v1"
spec_ref: "34fbaac80f616fc82076006bb47d3f13d9e261f7"
templates_version: "templates.v1"
allowed_paths:
  - plans/taskcards/TC-5200_gov1-commit-working-tree.md
  - src/launcher/models/claims.py
  - src/launcher/models/content.py
  - src/launcher/models/evaluation.py
  - src/launcher/models/plan.py
  - src/launcher/models/run_config.py
  - src/launcher/models/understanding.py
  - src/launcher/models/fact_manifest.py
  - src/launcher/workers/understand/adapters/_base.py
  - src/launcher/workers/understand/adapters/_cpp.py
  - src/launcher/workers/understand/adapters/_dotnet.py
  - src/launcher/workers/understand/adapters/_java.py
  - src/launcher/workers/understand/adapters/_python.py
  - src/launcher/workers/understand/extract/__init__.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/extract/_linking.py
  - src/launcher/workers/understand/extract/_llm.py
  - src/launcher/workers/understand/extract/_snippets.py
  - src/launcher/workers/understand/extract/_validation.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/checks/api_verification.py
  - src/launcher/workers/evaluate/checks/artifacts.py
  - src/launcher/workers/evaluate/checks/claim_coverage.py
  - src/launcher/workers/evaluate/checks/hallucination_rate.py
  - src/launcher/workers/evaluate/checks/product_names.py
  - src/launcher/workers/evaluate/checks/structure.py
  - src/launcher/workers/evaluate/go_criteria.py
  - src/launcher/workers/evaluate/grader.py
  - src/launcher/workers/evaluate/worker.py
  - src/launcher/workers/generate/_identifier_repair.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/generate/section_validator.py
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/planner/plan.py
  - src/launcher/workers/planner/worker.py
  - src/launcher/workers/scout/scout.py
  - src/launcher/workers/scout/worker.py
  - src/launcher/workers/intake/clone.py
  - src/launcher/workers/intake/worker.py
  - src/launcher/workers/intake/acquisition.py
  - src/launcher/workers/publish/_git_publisher.py
  - src/launcher/workers/publish/worker.py
  - src/launcher/orchestrator/graph_builder.py
  - src/launcher/orchestrator/pipeline_advisor.py
  - src/launcher/orchestrator/run_loop.py
  - src/launcher/orchestrator/worker_contract.py
  - src/launcher/cli/deploy.py
  - src/launcher/cli/intake.py
  - src/launcher/shared/golden_loader.py
  - src/launcher/shared/identity.py
  - src/launcher/shared/ir_renderer.py
  - src/launcher/shared/linker.py
  - src/launcher/shared/metrics_calculator.py
  - src/launcher/shared/ts_analyzer.py
  - src/launcher/shared/forbidden_patterns.py
  - src/launcher/prompts/section_writer.txt
  - src/launcher/deploy/phase_promoter.py
  - src/launcher/deploy/snapshot_manifest.py
  - src/launcher/intake/config_generator.py
  - src/launcher/phase1/acquisition.py
  - configs/families.yaml
  - configs/pipeline.yaml
  - configs/pilots/aspose-cells-foss-python.yaml
  - configs/pilots/aspose-3d-foss-python.yaml
  - configs/pilots/aspose-3d-foss-typescript.yaml
  - configs/pilots/aspose-note-foss-python.yaml
  - configs/pilots/aspose-slides-foss-python.yaml
  - tests/unit/deploy/test_phase_promoter.py
  - tests/unit/deploy/test_snapshot_manifest.py
  - tests/unit/intake/test_intake_cli.py
  - tests/unit/intake/test_scheduler.py
  - tests/unit/test_pipeline_e2e.py
  - tests/unit/workers/generate/test_code_validation.py
  - tests/unit/workers/generate/test_identifier_repair.py
  - tests/unit/workers/intake/test_clone.py
  - tests/unit/workers/test_clone.py
  - tests/unit/workers/test_evaluate.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/test_intake.py
  - tests/unit/workers/test_planner_claim_cap.py
  - tests/unit/workers/test_scout_budget_log_cap.py
  - tests/unit/workers/test_scout_facts.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/understand/test_dotnet_adapter.py
  - tests/unit/workers/understand/test_extract.py
  - tests/unit/workers/understand/test_python_hardening.py
  - agents.md
  - .claude/settings.local.json
  - reports/PLAN_SOURCES.md
  - reports/PLAN_INDEX.md
  - reports/TASK_BACKLOG.md
  - reports/agents/agent-a/gov-1/plan.md
  - reports/agents/agent-a/gov-1/evidence.md
  - reports/agents/agent-a/gov-1/self_review.md
  - plans/from_chat/20260325_000000_from_chat_unified-quality-fix.md
  - plans/taskcards/TC-5200_gov1-commit-working-tree.md
  - scripts/check_tc_evidence.py
evidence_required:
  - reports/TC-5200/evidence.md
---

# Taskcard TC-5200 — GOV-1: Commit working tree: 152 tracked modifications

## Objective

Commit the 152 uncommitted tracked modifications (` M` in git status) into logical batches to create a clear audit trail. This restores the working tree to a clean state so future changes are attributable and the commit history remains meaningful.

## Required spec references

- `CLAUDE.md` (Section: AG-002 Taskcard-First Workflow — governs protected path writes)
- `.claude_code_rules` (Section: AG-001..AG-020 — governance rules)
- `agents.md` (Section: 1. Before Writing Any Code — pre-write safety checklist)

## Scope

### In scope
- Stage and commit all files shown as ` M` (tracked, modified) in `git status --short`
- Group into logical batches: models, understand, evaluate, generate, planner, orchestrator/cli/shared, scout/intake/publish, tests, config/schema/deploy, root-level
- Update `reports/TASK_BACKLOG.md` to reflect GOV-1 In-Progress
- Update `reports/PLAN_SOURCES.md` with 2026-03-25 section
- Create `plans/from_chat/20260325_000000_from_chat_unified-quality-fix.md`
- Add `__pycache__` cleanup guidance to `agents.md` (GOV-2)
- Create `scripts/check_tc_evidence.py` (GOV-3)
- Create agent workspace directories and evidence/self-review files

### Out of scope
- Untracked files (`??` in git status) — these belong to separate taskcards
- Amending prior commits
- Pushing to remote
- Any code changes (this is a pure governance/commit task)

## Inputs

- `git status --short` output showing 152 ` M` tracked modifications
- All modified tracked files in `src/launcher/**`, `configs/**`, `tests/**`, `deploy/**`, `specs/**`, `agents.md`, `.claude/settings.local.json`

## Outputs

- 10 git commits grouping modifications into logical batches
- `reports/agents/agent-a/gov-1/evidence.md` — evidence bundle
- `reports/agents/agent-a/gov-1/self_review.md` — self-review
- `reports/agents/agent-a/gov-1/plan.md` — plan summary
- `scripts/check_tc_evidence.py` — evidence gap checker
- Updated `agents.md` with `__pycache__` cleanup section

## Allowed paths

- plans/taskcards/TC-5200_gov1-commit-working-tree.md
- src/launcher/models/claims.py
- src/launcher/models/content.py
- src/launcher/models/evaluation.py
- src/launcher/models/plan.py
- src/launcher/models/run_config.py
- src/launcher/models/understanding.py
- src/launcher/models/fact_manifest.py
- src/launcher/workers/understand/adapters/_base.py
- src/launcher/workers/understand/adapters/_cpp.py
- src/launcher/workers/understand/adapters/_dotnet.py
- src/launcher/workers/understand/adapters/_java.py
- src/launcher/workers/understand/adapters/_python.py
- src/launcher/workers/understand/extract/__init__.py
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/extract/_linking.py
- src/launcher/workers/understand/extract/_llm.py
- src/launcher/workers/understand/extract/_snippets.py
- src/launcher/workers/understand/extract/_validation.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/checks/api_verification.py
- src/launcher/workers/evaluate/checks/artifacts.py
- src/launcher/workers/evaluate/checks/claim_coverage.py
- src/launcher/workers/evaluate/checks/hallucination_rate.py
- src/launcher/workers/evaluate/checks/product_names.py
- src/launcher/workers/evaluate/checks/structure.py
- src/launcher/workers/evaluate/go_criteria.py
- src/launcher/workers/evaluate/grader.py
- src/launcher/workers/evaluate/worker.py
- src/launcher/workers/generate/_identifier_repair.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/section_validator.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/planner/plan.py
- src/launcher/workers/planner/worker.py
- src/launcher/workers/scout/scout.py
- src/launcher/workers/scout/worker.py
- src/launcher/workers/intake/clone.py
- src/launcher/workers/intake/worker.py
- src/launcher/workers/intake/acquisition.py
- src/launcher/workers/publish/_git_publisher.py
- src/launcher/workers/publish/worker.py
- src/launcher/orchestrator/graph_builder.py
- src/launcher/orchestrator/pipeline_advisor.py
- src/launcher/orchestrator/run_loop.py
- src/launcher/orchestrator/worker_contract.py
- src/launcher/cli/deploy.py
- src/launcher/cli/intake.py
- src/launcher/shared/golden_loader.py
- src/launcher/shared/identity.py
- src/launcher/shared/ir_renderer.py
- src/launcher/shared/linker.py
- src/launcher/shared/metrics_calculator.py
- src/launcher/shared/ts_analyzer.py
- src/launcher/shared/forbidden_patterns.py
- src/launcher/prompts/section_writer.txt
- src/launcher/deploy/phase_promoter.py
- src/launcher/deploy/snapshot_manifest.py
- src/launcher/intake/config_generator.py
- src/launcher/phase1/acquisition.py
- configs/families.yaml
- configs/pipeline.yaml
- configs/pilots/aspose-cells-foss-python.yaml
- configs/pilots/aspose-3d-foss-python.yaml
- configs/pilots/aspose-3d-foss-typescript.yaml
- configs/pilots/aspose-note-foss-python.yaml
- configs/pilots/aspose-slides-foss-python.yaml
- tests/unit/deploy/test_phase_promoter.py
- tests/unit/deploy/test_snapshot_manifest.py
- tests/unit/intake/test_intake_cli.py
- tests/unit/intake/test_scheduler.py
- tests/unit/test_pipeline_e2e.py
- tests/unit/workers/generate/test_code_validation.py
- tests/unit/workers/generate/test_identifier_repair.py
- tests/unit/workers/intake/test_clone.py
- tests/unit/workers/test_clone.py
- tests/unit/workers/test_evaluate.py
- tests/unit/workers/test_generate.py
- tests/unit/workers/test_intake.py
- tests/unit/workers/test_planner_claim_cap.py
- tests/unit/workers/test_scout_budget_log_cap.py
- tests/unit/workers/test_scout_facts.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/understand/test_dotnet_adapter.py
- tests/unit/workers/understand/test_extract.py
- tests/unit/workers/understand/test_python_hardening.py
- agents.md
- .claude/settings.local.json
- reports/PLAN_SOURCES.md
- reports/PLAN_INDEX.md
- reports/TASK_BACKLOG.md
- reports/agents/agent-a/gov-1/plan.md
- reports/agents/agent-a/gov-1/evidence.md
- reports/agents/agent-a/gov-1/self_review.md
- plans/from_chat/20260325_000000_from_chat_unified-quality-fix.md
- plans/taskcards/TC-5200_gov1-commit-working-tree.md
- scripts/check_tc_evidence.py

### Allowed paths rationale
Each path corresponds to a tracked file modified in sessions 13–20 that required committing, or a governance artifact created by this task (reports/, plans/, scripts/check_tc_evidence.py). No write was made to any unrelated path.

## Implementation steps

### Step 1: Verify modified file list

```bash
git status --short | grep "^ M"
```

Confirm count is ~152 files.

### Step 2: Batch A — Models

```bash
git add src/launcher/models/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: models"
```

### Step 3: Batch B — Understand worker

```bash
git add src/launcher/workers/understand/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: understand worker"
```

### Step 4: Batch C — Evaluate worker

```bash
git add src/launcher/workers/evaluate/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: evaluate worker"
```

### Step 5: Batch D — Generate worker + prompts

```bash
git add src/launcher/workers/generate/ src/launcher/prompts/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: generate worker and prompts"
```

### Step 6: Batch E — Planner

```bash
git add src/launcher/workers/planner/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: planner worker"
```

### Step 7: Batch F — Orchestrator + CLI + Shared

```bash
git add src/launcher/orchestrator/ src/launcher/cli/ src/launcher/shared/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: orchestrator, cli, shared"
```

### Step 8: Batch G — Scout + Intake + Publish workers

```bash
git add src/launcher/workers/scout/ src/launcher/workers/intake/ src/launcher/workers/publish/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: scout, intake, publish workers"
```

### Step 9: Batch H — Tests

```bash
git add tests/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: tests"
```

### Step 10: Batch I — Config / Schema / Deploy / Snapshots / Intake / Phase store

```bash
git add configs/ specs/ deploy/ snapshots/ intake/ phase_store/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: configs, specs, deploy, snapshots, intake, phase_store"
```

### Step 11: Batch J — Root-level files

```bash
git add agents.md .claude/ && git commit -m "chore(gov): TC-5200 GOV-1 — commit working tree: agents.md and .claude config"
```

### Step 12: Verify clean state

```bash
git status --short | grep "^ M"
```

Expected: empty output (no remaining tracked modifications).

### Step 13: Run test suite

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=line 2>&1 | tail -10
```

## Failure modes

### Failure mode 1: Merge conflict during stage/commit

**Detection**: `git add` or `git commit` exits with non-zero code; error message mentions conflict markers.
**Resolution**: Run `git status` to identify conflicted files. For each, resolve manually or reset to HEAD using `git checkout HEAD -- <file>`. Retry the batch.
**Gate**: All commits must succeed before proceeding to next batch.

### Failure mode 2: Test suite failures after commits

**Detection**: `pytest` exits with non-zero; output shows `FAILED` lines.
**Resolution**: Identify the failing test. If the failure is pre-existing (present before this session), document it in evidence.md. If caused by this commit, revert the offending batch with `git revert`.
**Gate**: PYTHONHASHSEED=0 pytest tests/unit/ must pass (allowing pre-existing failures already documented).

### Failure mode 3: Missing files in batch (batch has no eligible files)

**Detection**: `git add <path>` succeeds but `git commit` says "nothing to commit".
**Resolution**: Skip that batch. Document in evidence.md that the path had no modified tracked files.
**Gate**: N/A — empty batch is not an error.

### Failure mode 4: Untracked files accidentally staged

**Detection**: `git status` after `git add` shows `A` (new file) entries unexpectedly.
**Resolution**: `git reset HEAD <file>` to unstage untracked files. Commit only the ` M` files.
**Gate**: Commits must contain only previously-tracked files (` M` → `M`).

## Task-specific review checklist

1. [x] All ` M` tracked files committed (git status shows no ` M` after all batches)
2. [x] Commits use TC-5200 GOV-1 prefix in messages
3. [x] Logical batching by component (models, workers, tests, config)
4. [x] No untracked (`??`) files accidentally staged
5. [x] Test suite passes after commits (0 new failures)
6. [x] evidence.md created at reports/agents/agent-a/gov-1/evidence.md
7. [x] Docstrings not applicable (governance-only task, no production code changes)
8. [x] Spec file drift not applicable (no worker behavior changed)
9. [x] Schema descriptions not applicable (no schema changes)
10. [x] docs/README.md ownership map: not applicable (no guide changes)
11. [x] No new docs/guides/ files added

## Deliverables

1. 10 git commits at `main` HEAD covering all 152 tracked modifications
2. `reports/agents/agent-a/gov-1/evidence.md` — commit log and test output
3. `reports/agents/agent-a/gov-1/self_review.md` — 12-dimension self-review
4. `scripts/check_tc_evidence.py` — evidence gap detection script
5. Updated `agents.md` with `__pycache__` cleanup section (GOV-2)

## Acceptance checks

1. [ ] `git status --short | grep "^ M"` returns empty
2. [ ] `git log --oneline -15` shows 10+ new commits with TC-5200 prefix
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes (0 new failures)
4. [ ] `reports/agents/agent-a/gov-1/evidence.md` exists and contains git log output
5. [ ] `python scripts/check_tc_evidence.py` runs without import error
6. [ ] `agents.md` contains `__pycache__` cleanup section

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: git status clean PASS
- [ ] Evidence captured: reports/agents/agent-a/gov-1/evidence.md
- [ ] Doc freshness: governance task — no spec drift possible

## E2E verification

```bash
git status --short | grep "^ M" | wc -l   # should be 0
git log --oneline -15
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q --tb=line 2>&1 | tail -5
python scripts/check_tc_evidence.py
```

**Expected results**:
- `grep "^ M" | wc -l` → 0 (no tracked modified files remaining)
- git log shows 10+ TC-5200 commits
- pytest: 0 new failures (5479+ passed)
- check_tc_evidence.py: runs cleanly (reports missing evidence for historical TCs — expected)

**Expected artifacts**:
- `reports/agents/agent-a/gov-1/evidence.md` — commit log and test output
- `reports/agents/agent-a/gov-1/self_review.md` — 12-dimension scored review
- `scripts/check_tc_evidence.py` — evidence gap detection utility
- `agents.md` updated with `__pycache__` cleanup section (line ~693)

## Integration boundary proven

**Upstream**: All prior sessions' work (152 tracked modifications produced by sessions 13–20)
**Downstream**: Agent-B (EVL tasks), Agent-C (GEN tasks) — clean working tree is prerequisite
**Contract**: git commit history; `git status` clean for tracked files
