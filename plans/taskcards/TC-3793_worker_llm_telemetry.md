---
id: TC-3793
title: "Worker LLM Telemetry Passthrough"
status: Done
priority: Normal
owner: "agent-E"
updated: "2026-03-07"
tags: [telemetry, workers, observability]
depends_on: [TC-3792]
allowed_paths:
  - plans/taskcards/TC-3793_worker_llm_telemetry.md
  - src/launcher/workers/generate/worker.py
  - src/launcher/workers/understand/extract.py
  - src/launcher/workers/evaluate/llm_review.py
  - tests/unit/workers/test_worker_telemetry_passthrough.py
evidence_required:
  - reports/agents/telemetry/TC-3793/evidence.md
---

# Taskcard TC-3793 — Worker LLM Telemetry Passthrough

## Objective

Pass telemetry parameters from WorkerContext to LLMProviderClient in all three workers that construct LLM clients, enabling automatic LLM call telemetry tracking.

## Required spec references

- `specs/toolchain_ci_telemetry.md` (Section: Telemetry Events — llm_call_count, llm_total_tokens)
- `specs/11_state_and_events.md` (Section: LLM event types)

## Scope

### In scope
- Pass telemetry_client, telemetry_run_id, telemetry_trace_id, telemetry_parent_span_id when constructing LLMProviderClient in:
  - `src/launcher/workers/generate/worker.py` (lines 417 and 443)
  - `src/launcher/workers/understand/extract.py` (line 808)
  - `src/launcher/workers/evaluate/llm_review.py` (line 109)

### Out of scope
- Modifying LLMProviderClient (already accepts these params)
- Modifying LLMTelemetryContext (already implemented)
- Adding new LLM call sites

## Inputs

- WorkerContext with telemetry_client and telemetry_trace_id (from TC-3792)
- LLMProviderClient constructor (already accepts telemetry params)

## Outputs

- Modified worker files with telemetry params passed through
- Unit test verifying passthrough

## Allowed paths

- plans/taskcards/TC-3793_worker_llm_telemetry.md
- src/launcher/workers/generate/worker.py
- src/launcher/workers/understand/extract.py
- src/launcher/workers/evaluate/llm_review.py
- tests/unit/workers/test_worker_telemetry_passthrough.py

### Allowed paths rationale
- Three worker files: add telemetry params to LLMProviderClient construction
- Test file: verification

## Implementation steps

### Step 1: Update extract.py (Understand worker)

At line 808, add to LLMProviderClient constructor:
```python
telemetry_client=context.telemetry_client,
telemetry_run_id=context.run_id,
telemetry_trace_id=context.telemetry_trace_id,
telemetry_parent_span_id="",
```

### Step 2: Update generate/worker.py (Generate worker)

At lines 417 and 443, add same telemetry params.

### Step 3: Update llm_review.py (Evaluate worker)

At line 109, add same telemetry params.

### Step 4: Write unit test

Verify that constructing an LLMProviderClient with mock telemetry params works.

## Failure modes

### Failure mode 1: WorkerContext missing telemetry_client attribute
**Detection**: AttributeError at runtime
**Resolution**: Ensure TC-3792 is merged first; telemetry_client defaults to None
**Gate**: Unit test with mock context

### Failure mode 2: LLMProviderClient rejects telemetry params
**Detection**: TypeError in constructor
**Resolution**: Verify param names match constructor signature
**Gate**: Import test

### Failure mode 3: Telemetry failure crashes LLM call
**Detection**: LLM calls fail when telemetry endpoint unreachable
**Resolution**: LLMTelemetryContext is already non-fatal by design (all exceptions caught)
**Gate**: Test with None telemetry_client

## Task-specific review checklist

1. [ ] All 4 LLMProviderClient construction sites updated (extract:808, generate:417, generate:443, llm_review:109)
2. [ ] telemetry_client passed from context (can be None)
3. [ ] telemetry_run_id set to context.run_id
4. [ ] telemetry_trace_id passed from context
5. [ ] telemetry_parent_span_id set (empty string is fine)
6. [ ] No import changes needed (LLMProviderClient already accepts params)

## Deliverables

1. Modified `src/launcher/workers/generate/worker.py`
2. Modified `src/launcher/workers/understand/extract.py`
3. Modified `src/launcher/workers/evaluate/llm_review.py`
4. `tests/unit/workers/test_worker_telemetry_passthrough.py`

## Acceptance checks

1. [ ] All 4 construction sites pass telemetry params
2. [ ] Works with telemetry_client=None (backward compat)
3. [ ] All existing tests pass (PYTHONHASHSEED=0)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] All 4 sites verified
- [ ] Evidence captured

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x --tb=short -q
```

**Expected results**:
- No regressions
- Telemetry params passed correctly

## Integration boundary proven

**Upstream**: WorkerContext.telemetry_client from TC-3792
**Downstream**: LLMProviderClient uses telemetry to create LLMTelemetryContext per call
**Contract**: LLMProviderClient(telemetry_client=Optional[TelemetryClient], telemetry_run_id=str, telemetry_trace_id=str, telemetry_parent_span_id=str)
