# TC-300 Implementation Plan

**Document**: 01_plan.md
**Timestamp**: 2026-01-28 UTC
**Work Folder**: `reports/impl/20260128_162921/`

## Overview

Transform orchestrator from state-only stubs to real end-to-end pipeline that invokes actual worker implementations.

## Stage Budgets

- **STAGE 0 (Setup + Preflight)**: 15% ✅ COMPLETE
- **STAGE 1 (Implement TC-300 Wiring)**: 45%
- **STAGE 2 (Pilot Config Runnable)**: 15%
- **STAGE 3 (E2E Pilot Runs)**: 25%
- **STAGE 4 (Finalization)**: Remaining

## STAGE 1 Implementation Steps

### 1.1 Update Orchestrator Graph

**File**: `src/launch/orchestrator/graph.py`

**Current state**: Stub node implementations that only update state

**Required changes**:
1. Add W3 invocation in `build_facts_node`:
   - Current: Only changes state to FACTS_READY
   - Required: Invoke W2 FactsBuilder → W3 SnippetCurator (ordered sequence)
   - Per specs/state-graph.md:66-70

2. Update all nodes to invoke real workers via WorkerInvoker:
   - `clone_inputs_node`: Invoke W1 RepoScout
   - `ingest_node`: No-op (reserved, deterministic transition)
   - `build_facts_node`: Invoke W2 → W3 (ordered)
   - `plan_pages_node`: Invoke W4 IAPlanner
   - `draft_sections_node`: Invoke W5 SectionWriter (fan-out for each section)
   - `link_and_patch_node`: Invoke W6 LinkerAndPatcher
   - `validate_node`: Invoke W7 Validator
   - `fix_node`: Invoke W8 Fixer
   - `open_pr_node`: Invoke W9 PRManager

3. Ensure WorkerInvoker instance is available to nodes:
   - Pass via state or create within nodes from run_dir/trace context

### 1.2 Implement Real WorkerInvoker Dispatch

**File**: `src/launch/orchestrator/worker_invoker.py`

**Current state**: `invoke_worker()` is stub returning `{"status": "success"}`

**Required changes**:
1. Create dispatch map for all 9 workers:
   ```python
   WORKER_DISPATCH = {
       "W1.RepoScout": "launch.workers.w1_repo_scout.execute_repo_scout",
       "W2.FactsBuilder": "launch.workers.w2_facts_builder.execute_facts_builder",
       "W3.SnippetCurator": "launch.workers.w3_snippet_curator.execute_snippet_curator",
       "W4.IAPlanner": "launch.workers.w4_ia_planner.execute_ia_planner",
       "W5.SectionWriter": "launch.workers.w5_section_writer.execute_section_writer",
       "W6.LinkerAndPatcher": "launch.workers.w6_linker_and_patcher.execute_linker_and_patcher",
       "W7.Validator": "launch.workers.w7_validator.execute_validator",
       "W8.Fixer": "launch.workers.w8_fixer.execute_fixer",
       "W9.PRManager": "launch.workers.w9_pr_manager.execute_pr_manager",
   }
   ```

2. Update `invoke_worker()`:
   - Dynamically import and call the worker function
   - Pass `run_dir` and `run_config` (standard worker signature)
   - Catch exceptions and emit WORK_ITEM_FINISHED with error
   - Return worker result

3. Handle worker signature variations:
   - If worker accepts trace/span context, pass it
   - If not, document and proceed deterministically

### 1.3 Fix Snapshot Correctness via Event Replay

**Files**:
- `src/launch/orchestrator/run_loop.py`
- `src/launch/state/snapshot_manager.py`

**Current state**: Snapshot may not accurately reflect event stream

**Required changes**:
1. In `run_loop.py`, after each node execution:
   - Call `replay_events(run_dir / "events.ndjson", run_id)` to reconstruct state
   - Write `snapshot.json` from replayed state
   - Ensure snapshot includes: artifacts_index, work_items, issues

2. Fix RUN_STATE_CHANGED event emission:
   - Current code may emit wrong `old_state` value
   - Must emit correct old_state → new_state transition
   - Read current state before changing, emit event, then update

3. Ensure snapshot schema compliance:
   - Per `specs/schemas/snapshot.schema.json`
   - Required fields: run_id, run_state, artifacts_index, work_items, issues

### 1.4 Ensure Artifacts Index Population

**Files**: All workers (W1-W9)

**Current state**: Workers may not emit ARTIFACT_WRITTEN events

**Required changes**:
1. Audit each worker for ARTIFACT_WRITTEN emission:
   - Check that `writer_worker` field is set correctly
   - Check that `artifact_path` is relative to RUN_DIR
   - Check that `artifact_type` matches schema

2. If any worker missing ARTIFACT_WRITTEN:
   - Add event emission after file write
   - Use helper: `emit_artifact_written(run_dir, artifact_path, artifact_type, worker_name)`

3. Validate against state requirements:
   - CLONED_INPUTS: repo_inventory.json, frontmatter_contract.json
   - FACTS_READY: product_facts.json, evidence_map.json, snippet_catalog.json
   - PLAN_READY: page_plan.json
   - etc.

## STAGE 2 Implementation Steps

### 2.1 Implement TC-401: Placeholder Ref Handling

**File**: `src/launch/workers/_git/clone_helpers.py` or W1 wrapper

**Current state**: Clone uses `git clone --branch <ref>` which fails for all-zero SHAs

**Required changes**:
1. Detect placeholder ref: `ref == "0" * 40`
2. If placeholder:
   - Run `git ls-remote <repo_url> HEAD` to get default branch SHA
   - Clone without `--branch` flag
   - Checkout resolved SHA
   - Record in artifact: `requested_ref="HEAD (placeholder)"`, `resolved_sha=<sha>`
3. Update `repo_inventory.json` to include resolved SHAs

### 2.2 Implement TC-403: Frontmatter Contract Output

**File**: `src/launch/workers/w1_repo_scout/worker.py`

**Current state**: May not produce `frontmatter_contract.json`

**Required changes**:
1. Extract frontmatter schema from site config
2. Write `RUN_DIR/artifacts/frontmatter_contract.json`
3. Emit ARTIFACT_WRITTEN event

### 2.3 Implement TC-404: Site Context & Hugo Facts

**File**: `src/launch/workers/w1_repo_scout/worker.py`

**Current state**: May not produce `site_context.json` and `hugo_facts.json`

**Required changes**:
1. Parse Hugo config for site context
2. Write `RUN_DIR/artifacts/site_context.json`
3. Parse Hugo theme for hugo facts
4. Write `RUN_DIR/artifacts/hugo_facts.json`
5. Emit ARTIFACT_WRITTEN events for both

## STAGE 3 Implementation Steps

### 3.1 W9 Dry-Run Mode

**File**: `src/launch/workers/w9_pr_manager/worker.py`

**Current state**: May fail if commit_service unreachable

**Required changes**:
1. Check commit_service reachability before PR creation
2. If unreachable:
   - Write `RUN_DIR/artifacts/pr_request_bundle.json` with:
     - PR request payload
     - Idempotency keys
     - Timestamp
   - Emit ARTIFACT_WRITTEN
   - Mark run as DONE (not failed)
   - Log "PR deferred: commit_service unreachable"

### 3.2 Execute Pilot Dry-Run

**Pilot config**: `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`

**Steps**:
1. Run: `launch run --config <pilot_config>`
2. Check `launch status <run_id> --verbose`
3. Verify artifacts per state (specs/state-graph.md)
4. Check validation_report.json
5. Document in `03_e2e_dry_run.md`

### 3.3 Fix Loop Verification

**Steps**:
1. If validation fails, verify orchestrator picks first issue
2. Verify W8 is invoked with correct issue
3. Verify fix loop returns to W7
4. Verify max_fix_attempts honored
5. Document in `03_e2e_dry_run.md`

### 3.4 Execute Pilot Live-Run

Same as dry-run, but allow actual PR opening if commit_service available.
Document in `04_e2e_live_run.md`.

## STAGE 4 Finalization

### 4.1 Create FINAL_SUMMARY.md

Document:
- What was missing (stubs)
- What is now real (worker invocations)
- Exact files changed
- Exact commands run
- Run IDs
- PR status (opened or deferred)
- Remaining gaps (if any)

### 4.2 Final Validation

Run:
```bash
.venv/Scripts/python.exe scripts/validate_spec_pack.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest
```

## Milestone Commits/Zips

- ✅ Milestone #1: Preflight green (committed: a0e2e14)
- Milestone #2: TC-300 wiring complete (after STAGE 1)
- Milestone #3: W1 contract outputs complete (after STAGE 2)
- Milestone #4: E2E dry-run complete (after STAGE 3.2)
- Milestone #5: E2E live-run complete (after STAGE 3.4)

## Risk Mitigation

- If approaching tool/runtime limit: create emergency zip before hitting limit
- If git push fails: commit locally + write zip + patch file
- If worker signature mismatch: adapt deterministically and document
- If external blocker: proceed as far as possible and document blocker
