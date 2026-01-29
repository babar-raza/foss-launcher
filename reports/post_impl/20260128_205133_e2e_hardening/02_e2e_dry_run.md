# Phase 2: E2E Dry-Run Summary

## Overview

Executed dry-run pilot using resolved config with stub commit service. Run completed successfully but revealed that worker implementations are stubbed.

## Configuration

**Resolved Config**: `configs/pilots/pilot-aspose-note-foss-python.resolved.yaml`

**Resolved SHAs**:
- Site repo: `8d8661ad55a1c00fcf52ddc0c8af59b1899873be`
- Workflows repo: `f4f8f86ef4967d5a2f200dbe25d1ade363068488`
- Product repo: `0000000000000000000000000000000000000000` (BLOCKER: not accessible)

## Bug Fixed

**Issue**: [src/launch/io/run_layout.py:38](../../../src/launch/io/run_layout.py#L38)
`run_dir.mkdir(parents=True, exist_ok=False)` caused failure when directory already existed.

**Fix**: Changed to `exist_ok=True`

**Impact**: Critical for retry/resume scenarios

## Run Results

**Run ID**: `r_20260128T160951Z_launch_pilot-aspose-note-foss-python_0000000_8d8661a_60062a37`
**Final State**: `DONE`
**Exit Code**: `0`
**Duration**: ~0.1 seconds (16:09:51.258 to 16:09:51.382)

### State Transitions

The run transitioned through all expected states:
1. RUN_CREATED
2. CLONED_INPUTS
3. INGESTED
4. FACTS_READY
5. PLAN_READY
6. DRAFT_READY
7. LINKING
8. VALIDATING
9. PR_OPENED
10. DONE

### Key Finding: Stubbed Workers

**Discovery**: All worker nodes in the orchestrator graph are stubs.

**Evidence**: Inspection of [src/launch/orchestrator/graph.py](../../../src/launch/orchestrator/graph.py) shows:
```python
def clone_inputs_node(state: OrchestratorState) -> OrchestratorState:
    """Clone inputs (product repo, site repo, workflows repo).

    Stub for TC-300. Full implementation in TC-401 (W1 RepoScout).
    """
    state["run_state"] = RUN_STATE_CLONED_INPUTS
    return state
```

All 10 worker nodes follow this pattern - they update state and return immediately without performing actual work.

### What Works

**Implemented & Verified**:
1. Orchestrator framework (LangGraph-based state machine)
2. Run directory creation and layout
3. Event logging (events.ndjson)
4. Snapshot management (snapshot.json)
5. State transitions through graph
6. Stub commit service integration

**Not Implemented**:
1. W1 - Repo Scout (clone_inputs, ingest)
2. W2 - Facts Builder (build_facts)
3. W3 - Snippet Curator (part of planning)
4. W4 - IA Planner (plan_pages)
5. W5 - Section Writer (draft_sections)
6. W6 - Linker and Patcher (link_and_patch)
7. W7 - Validator (validate)
8. W8 - Fixer (fix)
9. W9 - PR Manager (open_pr)

## Artifacts Generated

**Files Created**:
- `runs/<run_id>/run_config.yaml` - Copy of input config
- `runs/<run_id>/snapshot.json` - Final state (empty artifacts)
- `runs/<run_id>/events.ndjson` - State transition events (10 entries)

**Missing Artifacts** (expected from real run):
- repo_inventory.json
- facts.json
- page_plan.json
- section drafts (products, docs, reference, kb, blog)
- patch_bundle.json
- validation_report.json
- PR metadata

## Commit Service Stub

**Status**: Running successfully on `http://127.0.0.1:4320/v1`

**Implementation**: [scripts/stub_commit_service.py](../../../scripts/stub_commit_service.py)

**Features Verified**:
- FastAPI server operational
- Health endpoint responding
- Ready to receive `/v1/commit` and `/v1/open_pr` requests
- Audit logging to `reports/post_impl/20260128_205133_e2e_hardening/stub_commit_service_audit.jsonl`

**Not Tested**: Actual commit/PR requests (orchestrator stubs don't invoke commit service)

## Determinism Test

**Status**: N/A

**Reason**: Since workers are stubbed and produce no artifacts, determinism cannot be meaningfully tested. A second run would produce identical empty results, but this doesn't validate true determinism of content generation.

## Implications

### Positive
1. Orchestration framework is sound and operational
2. Run lifecycle management works correctly
3. State machine transitions correctly
4. Infrastructure ready for worker implementation

### Gaps
1. No actual content generation
2. Cannot test real repo cloning (product repo blocker compounds this)
3. Cannot test LLM integration
4. Cannot test validation gates on generated content
5. Cannot test commit service with real artifacts

## Next Steps

**If continuing with implementation**:
1. Implement W1 (Repo Scout) - TC-401
2. Implement W2 (Facts Builder) - TC-410
3. Implement remaining workers sequentially per taskcards

**For E2E hardening given current state**:
1. Document what the system architecture provides
2. Verify all gates and tests still pass
3. Create evidence bundle showing current implementation state
4. Record blockers and implementation gaps

## Conclusion

The dry-run successfully validated the orchestration framework but revealed that worker implementations are not yet completed. The system has a solid foundation (state management, event logging, graph orchestration) but requires worker implementation before it can perform actual E2E content generation.

**Recommendation**: Proceed to Phase 3 (live run) to confirm behavior is consistent, then create comprehensive final summary documenting current implementation state versus target architecture.
