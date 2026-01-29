# Completeness Audit: What It Produces & How It Produces It

## Executive Summary

The FOSS Launcher system has a **complete orchestration framework** but **stubbed worker implementations**. It successfully demonstrates state machine orchestration, event logging, and run lifecycle management, but does not yet generate actual content artifacts.

## Architecture Overview

**Implemented**: Orchestration Control Plane
**Status**: Workers are stubs (no actual work performed)

### Pipeline Stages (All Stubbed)

| Stage | Worker | State Transition | Entry Point | Status |
|-------|--------|------------------|-------------|---------|
| Clone | W1 RepoScout | CREATED → CLONED_INPUTS | [graph.py:115](../../../src/launch/orchestrator/graph.py#L115) | Stub |
| Ingest | W1 RepoScout | CLONED_INPUTS → INGESTED | [graph.py:124](../../../src/launch/orchestrator/graph.py#L124) | Stub |
| Facts | W2 FactsBuilder | INGESTED → FACTS_READY | [graph.py:133](../../../src/launch/orchestrator/graph.py#L133) | Stub |
| Plan | W4 IAPlanner | FACTS_READY → PLAN_READY | [graph.py:142](../../../src/launch/orchestrator/graph.py#L142) | Stub |
| Draft | W5 SectionWriter | PLAN_READY → DRAFT_READY | [graph.py:151](../../../src/launch/orchestrator/graph.py#L151) | Stub |
| Link | W6 LinkerPatcher | DRAFT_READY → LINKING | [graph.py:160](../../../src/launch/orchestrator/graph.py#L160) | Stub |
| Validate | W7 Validator | LINKING → VALIDATING | [graph.py:169](../../../src/launch/orchestrator/graph.py#L169) | Stub |
| Fix | W8 Fixer | VALIDATING → FIXING | [graph.py:178](../../../src/launch/orchestrator/graph.py#L178) | Stub (conditional) |
| PR | W9 PRManager | READY_FOR_PR → PR_OPENED | [graph.py:196](../../../src/launch/orchestrator/graph.py#L196) | Stub |
| Finalize | Orchestrator | PR_OPENED → DONE | [graph.py:205](../../../src/launch/orchestrator/graph.py#L205) | Stub |

## Current Output: What It Produces

### Actual Artifacts (Generated)

**Run Directory Structure**: `runs/<run_id>/`
- ✅ `run_config.yaml` - Validated config copy
- ✅ `snapshot.json` - Final state JSON (empty artifacts_index)
- ✅ `events.ndjson` - State transition event log (10 entries)
- ✅ `telemetry_outbox.jsonl` - Telemetry queue (empty)
- ✅ `work/` - Working directories (repo, site, workflows) - empty
- ✅ `artifacts/` - Artifact storage - empty
- ✅ `logs/` - Worker logs - empty
- ✅ `reports/` - Validation reports - empty
- ✅ `drafts/` - Section drafts by subdomain - empty

### Expected Artifacts (NOT Generated - Workers Stubbed)

**From W1 RepoScout**:
- ❌ `artifacts/repo_inventory.json` - Product repo fingerprint
- ❌ `artifacts/site_inventory.json` - Site repo baseline
- ❌ `work/repo/` - Cloned product repo
- ❌ `work/site/` - Cloned site repo
- ❌ `work/workflows/` - Cloned workflows repo

**From W2 FactsBuilder**:
- ❌ `artifacts/facts.json` - Extracted product facts
- ❌ `artifacts/evidence_map.json` - Evidence linking
- ❌ `artifacts/truth_lock.json` - Minimal truth set

**From W3 SnippetCurator**:
- ❌ `artifacts/snippet_inventory.json` - Code snippet index
- ❌ `artifacts/snippets/` - Selected code snippets

**From W4 IAPlanner**:
- ❌ `artifacts/page_plan.json` - IA hierarchy and page specs

**From W5 SectionWriter**:
- ❌ `drafts/products/*.md` - Product page drafts
- ❌ `drafts/docs/*.md` - Documentation drafts
- ❌ `drafts/reference/*.md` - API reference drafts
- ❌ `drafts/kb/*.md` - Knowledge base drafts
- ❌ `drafts/blog/*.md` - Blog post drafts

**From W6 LinkerPatcher**:
- ❌ `artifacts/patch_bundle.json` - Patchable content bundle

**From W7 Validator**:
- ❌ `artifacts/validation_report.json` - Gate results

**From W8 Fixer** (conditional):
- ❌ `artifacts/fix_attempt_<N>.json` - Fix attempt logs

**From W9 PRManager**:
- ❌ `artifacts/commit_metadata.json` - Commit SHA and details
- ❌ `artifacts/pr_metadata.json` - PR number and URL

## How It Produces: Current Implementation

### Orchestration Layer (✅ Implemented)

**State Machine**: [src/launch/orchestrator/graph.py](../../../src/launch/orchestrator/graph.py)
- LangGraph-based StateGraph
- 10 worker nodes + conditional edges
- State persistence via snapshot.json
- Event logging via events.ndjson

**Run Execution**: [src/launch/orchestrator/run_loop.py](../../../src/launch/orchestrator/run_loop.py)
- Single-run execution (batch blocked by OQ-BATCH-001)
- Trace context propagation
- Event emission per state transition
- Final state aggregation

**CLI Interface**: [src/launch/cli/main.py](../../../src/launch/cli/main.py)
- `launch run --config <yaml>` - Start run
- `launch status <run_id>` - Check status
- `launch validate <run_id>` - Run validation
- Config validation and RUN_DIR generation

### Worker Layer (❌ Stubbed)

**All Workers**: `src/launch/orchestrator/graph.py:115-213`

Each worker node:
```python
def <worker>_node(state: OrchestratorState) -> OrchestratorState:
    """<Description>

    Stub for TC-300. Full implementation in TC-<XXX>.
    """
    state["run_state"] = RUN_STATE_<NEXT>
    return state
```

**Real Implementation Locations** (per taskcards):
- W1: TC-401 (Clone) + TC-400 (Ingest)
- W2: TC-410 (Facts Builder)
- W3: TC-420 (Snippet Curator)
- W4: TC-430 (IA Planner)
- W5: TC-440 (Section Writer)
- W6: TC-450 (Linker and Patcher)
- W7: TC-460 (Validator)
- W8: TC-470 (Fixer)
- W9: TC-480 (PR Manager)

### Support Services

**Stub Commit Service** (✅ Implemented for Testing):
- [scripts/stub_commit_service.py](../../../scripts/stub_commit_service.py)
- FastAPI server on `http://127.0.0.1:4320/v1`
- Validates `/v1/commit` and `/v1/open_pr` requests
- Enforces allowed_paths
- Returns deterministic fake responses
- Logs to audit file

**Validation Gates** (✅ Implemented):
- [tools/validate_swarm_ready.py](../../../tools/validate_swarm_ready.py) - All gates
- [tools/validate_taskcards.py](../../../tools/validate_taskcards.py) - Taskcard validation
- [tools/validate_pilots_contract.py](../../../tools/validate_pilots_contract.py) - Pilot configs
- [tools/validate_mcp_contract.py](../../../tools/validate_mcp_contract.py) - MCP tools
- [tools/validate_secrets_hygiene.py](../../../tools/validate_secrets_hygiene.py) - Secrets scanning
- [tools/validate_untrusted_code_policy.py](../../../tools/validate_untrusted_code_policy.py) - Subprocess safety

## Implementation Maturity Matrix

| Component | Status | Evidence | Next Task |
|-----------|--------|----------|-----------|
| Orchestrator Framework | ✅ Complete | [graph.py](../../../src/launch/orchestrator/graph.py), [run_loop.py](../../../src/launch/orchestrator/run_loop.py) | - |
| CLI Entrypoints | ✅ Complete | [main.py](../../../src/launch/cli/main.py), pyproject.toml scripts | - |
| Run Layout Management | ✅ Complete | [run_layout.py](../../../src/launch/io/run_layout.py) | - |
| Event Logging | ✅ Complete | [event_log.py](../../../src/launch/state/event_log.py) | - |
| Snapshot Management | ✅ Complete | [snapshot_manager.py](../../../src/launch/state/snapshot_manager.py) | - |
| Validation Gates | ✅ Complete | [tools/validate_*.py](../../../tools/) | - |
| W1 RepoScout | ❌ Stubbed | [graph.py:115-130](../../../src/launch/orchestrator/graph.py#L115-L130) | TC-401, TC-400 |
| W2 FactsBuilder | ❌ Stubbed | [graph.py:133-139](../../../src/launch/orchestrator/graph.py#L133-L139) | TC-410 |
| W3 SnippetCurator | ❌ Stubbed | Needs integration | TC-420 |
| W4 IAPlanner | ❌ Stubbed | [graph.py:142-148](../../../src/launch/orchestrator/graph.py#L142-L148) | TC-430 |
| W5 SectionWriter | ❌ Stubbed | [graph.py:151-157](../../../src/launch/orchestrator/graph.py#L151-L157) | TC-440 |
| W6 LinkerPatcher | ❌ Stubbed | [graph.py:160-166](../../../src/launch/orchestrator/graph.py#L160-L166) | TC-450 |
| W7 Validator | ❌ Stubbed | [graph.py:169-175](../../../src/launch/orchestrator/graph.py#L169-L175) | TC-460 |
| W8 Fixer | ❌ Stubbed | [graph.py:178-193](../../../src/launch/orchestrator/graph.py#L178-L193) | TC-470 |
| W9 PRManager | ❌ Stubbed | [graph.py:196-202](../../../src/launch/orchestrator/graph.py#L196-L202) | TC-480 |

## Conclusion

**What the system produces NOW**:
- Run lifecycle artifacts (config, snapshot, events)
- Empty directory structure
- State transition logs

**What the system WILL produce** (when workers are implemented):
- Product documentation pages (products, docs, reference, kb, blog)
- Patch bundles for site repo
- Validation reports
- GitHub commits and PRs

**How it produces it NOW**:
- Orchestrator framework cycles through states
- Workers are no-ops that just update state
- No actual content generation or repo interaction

**How it WILL produce it** (design is ready):
- Orchestrator invokes real workers
- Workers clone repos, extract facts, plan pages, draft content
- Content goes through linking, validation, fixing cycles
- Final artifacts committed via commit service
- PR opened to target repo

**Implementation Gap**: ~9 worker implementations (TC-401 through TC-480)
