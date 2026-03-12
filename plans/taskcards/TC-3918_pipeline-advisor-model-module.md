---
id: TC-3918
title: "Add PipelineAdvice model, pipeline_advisor module, and prompt"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-10"
tags: [models, orchestrator, llm, routing]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-3918_pipeline-advisor-model-module.md
  - src/launcher/models/evaluation.py
  - src/launcher/orchestrator/pipeline_advisor.py
  - src/launcher/prompts/pipeline_advisor.txt
  - tests/unit/orchestrator/test_pipeline_advisor.py
evidence_required:
  - reports/TC-3918/evidence.md
---

# Taskcard TC-3918 — Add PipelineAdvice model, pipeline_advisor module, and prompt

## Objective

Add the `PipelineAdvice` Pydantic model to `evaluation.py`, create the `pipeline_advisor.py` orchestrator module with LLM-driven routing logic, and write the `pipeline_advisor.txt` prompt so the evaluate worker can delegate post-NO_GO routing decisions to a vetted LLM call with deterministic fallback.

## Required spec references

- `specs/05_evaluate_worker.md` (Section: go/no-go verdict and routing)
- `specs/11_state_and_events.md` (Section: LLM call telemetry)
- `specs/10_determinism_and_caching.md` (Section: temperature=0.0 determinism)

## Scope

### In scope
- `PipelineAdvice` Pydantic model in `evaluation.py`
- `pipeline_advisor.py` with `call_pipeline_advisor`, `_build_advisor_prompt`, `_call_llm`, `_parse_advice`, `_static_fallback`
- `pipeline_advisor.txt` prompt template with `{re_run_status}`, `{eval_summary}`, `{failing_checks}` slots
- 8 unit tests in `tests/unit/orchestrator/test_pipeline_advisor.py`

### Out of scope
- Wiring `call_pipeline_advisor` into the run loop (separate TC)
- "heal_upstream" routing option (intentionally deferred pending empirical data)
- LLM cache integration for advisor calls

## Inputs

- `src/launcher/models/evaluation.py` — `HealDecision` class marks insertion point
- `src/launcher/cli/heal.py` — reference for `_call_llm_sync` / `_parse_heal_decision` patterns
- `src/launcher/clients/llm_provider.py` — `LLMProviderClient` API

## Outputs

- `src/launcher/models/evaluation.py` — with `PipelineAdvice` model appended after `HealDecision`
- `src/launcher/orchestrator/pipeline_advisor.py` — new module
- `src/launcher/prompts/pipeline_advisor.txt` — new prompt template
- `tests/unit/orchestrator/test_pipeline_advisor.py` — 8 unit tests

## Allowed paths

- plans/taskcards/TC-3918_pipeline-advisor-model-module.md
- src/launcher/models/evaluation.py
- src/launcher/orchestrator/pipeline_advisor.py
- src/launcher/prompts/pipeline_advisor.txt
- tests/unit/orchestrator/test_pipeline_advisor.py

### Allowed paths rationale
- `evaluation.py` — only model file that houses evaluation-related models (HealDecision, EvaluationReport, etc.)
- `pipeline_advisor.py` — new orchestrator-layer module; orchestrator/ is the correct home for pipeline routing logic
- `pipeline_advisor.txt` — prompt template; all prompts live in `src/launcher/prompts/`
- `test_pipeline_advisor.py` — unit tests mirror the module structure under `tests/unit/orchestrator/`

## Implementation steps

### Step 1: Add PipelineAdvice model to evaluation.py

Insert the `PipelineAdvice` class immediately after the `HealDecision` class. `Literal` is already imported.

### Step 2: Create pipeline_advisor.txt prompt

Write the prompt with three `{re_run_status}`, `{eval_summary}`, `{failing_checks}` format slots and clear routing option rules.

### Step 3: Create pipeline_advisor.py

Implement `_build_advisor_prompt`, `_call_llm` (using `LLMProviderClient.chat_completion`), `_parse_advice` (with fence stripping and confidence gate), `_static_fallback`, and `call_pipeline_advisor` (never raises).

### Step 4: Write 8 unit tests

Cover model validation, routing round-trip, invalid routing, confidence out-of-range, fence stripping, static fallback (below/at ceiling), and LLM-unavailable path.

### Step 5: Run tests and verify

Run `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_pipeline_advisor.py -v` — all 8 must pass.

## Failure modes

### Failure mode 1: LLM unavailable or litellm_key unset

**Detection**: `_call_llm` returns `None`; logs `"litellm_key not set"` or `"LLM call failed"`
**Resolution**: `call_pipeline_advisor` falls through to `_static_fallback` automatically; no action needed
**Gate**: Covered by `test_call_advisor_llm_unavailable`

### Failure mode 2: LLM returns malformed JSON or fails schema validation

**Detection**: `_parse_advice` logs `"JSON parse failed"` or `"schema validation failed"` and returns `None`
**Resolution**: `call_pipeline_advisor` falls through to `_static_fallback`; root-cause is prompt or model regression
**Gate**: Covered by `test_parse_advice_strips_json_fences` (positive) and confidence tests (negative)

### Failure mode 3: LLM returns low-confidence routing

**Detection**: `_parse_advice` returns `None` when `advice.confidence < 0.6`; logs `"confidence < 0.6, using fallback"`
**Resolution**: `_static_fallback` used; may indicate prompt needs tuning or source material insufficient
**Gate**: Covered by `test_parse_advice_low_confidence_returns_none`

## Task-specific review checklist

1. [ ] `PipelineAdvice` inserted immediately after `HealDecision` — no gap in file
2. [ ] `Literal` import confirmed present (already in evaluation.py)
3. [ ] `_call_llm` uses `LLMProviderClient.chat_completion` (not `.complete` or `.chat`) with correct constructor signature (`api_base_url`, `model`, `run_dir`, `api_key`, `temperature`)
4. [ ] `_parse_advice` strips both ` ```json ` and plain ` ``` ` fences before JSON parse
5. [ ] `_static_fallback` returns `heal_generate` when `re_run_count < max_re_runs`, `stop` otherwise
6. [ ] `call_pipeline_advisor` never raises — all exceptions are caught and fallback is used
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift — routing wiring is a separate TC)
9. [ ] Schema `"description"` fields present in model docstrings for all new properties
10. [ ] Checked `docs/README.md` ownership map — no trigger event applies (model/module addition, no worker behavior change)
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated — N/A

## Deliverables

1. `src/launcher/models/evaluation.py` — with `PipelineAdvice` model
2. `src/launcher/orchestrator/pipeline_advisor.py` — new module
3. `src/launcher/prompts/pipeline_advisor.txt` — new prompt
4. `tests/unit/orchestrator/test_pipeline_advisor.py` — 8 unit tests, all passing

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_pipeline_advisor.py -v` — 8/8 PASS
2. [ ] Full suite `tests/` — no regressions
3. [ ] `from launcher.models.evaluation import PipelineAdvice` succeeds in a clean Python session
4. [ ] `from launcher.orchestrator.pipeline_advisor import call_pipeline_advisor` succeeds
5. [ ] `_static_fallback(0, 2).routing == "heal_generate"` and `_static_fallback(2, 2).routing == "stop"`

## Self-review

### Verification results
- [x] Tests: 8/8 PASS
- [x] Validation: import smoke test PASS (verified via test collection)
- [x] Evidence captured: full suite 3298 passed, 1 skipped, 3 xfailed — 0 regressions
- [x] Doc freshness: N/A — no spec drift; routing wiring is a separate TC

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_pipeline_advisor.py -v
```

**Expected results**:
- 8 tests collected, 8 passed
- No import errors for `launcher.models.evaluation.PipelineAdvice` or `launcher.orchestrator.pipeline_advisor`

## Integration boundary proven

**Upstream**: `EvaluationReport` (evaluate worker output) + `re_run_count`/`max_re_runs` from orchestrator run loop
**Downstream**: Run loop consumes `PipelineAdvice.routing` to decide next pipeline step
**Contract**: `PipelineAdvice` is a Pydantic model — routing is one of `Literal["publish", "heal_generate", "stop"]`; confidence is float in [0, 1]
