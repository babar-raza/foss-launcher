# Healing Plan: Outline→Expand→Review Generation Cycle

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Replace single-turn W5 generation with a 3-step cycle that catches structural issues before final output.

## Context

Current W5 generation is single-turn: one LLM call produces the full page. This produces structurally inconsistent output (wrong heading hierarchy, missing sections, uncited claims) because the model has no intermediate checkpoint. The `MultiPassOrchestrator` already exists but only does Pass 1 (Draft) + Pass 2 (Refine). This task adds a formal Outline pass before Draft.

## Gap → Taskcard Mapping

| Gap ID | Description                                       | Taskcard |
|--------|---------------------------------------------------|----------|
| RD-05  | Single-turn generation produces structural issues | RD-05    |

---

## Taskcard RD-05 — Outline→Expand→Review Cycle in MultiPassOrchestrator

**Status**: Not Started
**Gap linkage**: RD-05 (00_REDESIGN.md §2.2 item 3, TC-2374)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Extend `MultiPassOrchestrator` with a pre-pass: `Pass 0 (Outline)`. The LLM produces a structured outline (heading hierarchy + claim IDs per section). Pass 1 (Draft) receives the outline as additional context and must follow it. Pass 2 (Refine) checks the draft against the outline and corrects deviations.

Control via `outline_pass_enabled: bool` (default `false` — zero impact on existing runs).

**Allowed paths**:
```
src/launch/workers/w5_section_writer/multi_pass.py
src/launch/workers/w5_section_writer/prompts/outline.txt        (new prompt file)
tests/unit/workers/test_tc_1780_prompt_multipass.py
```

**Forbidden**: any other file or path (no changes to generator dispatch, worker.py, or W7).

### Acceptance Checks

**CLI**:
```bash
# Enable outline pass in pilot run_config:
# outline_pass_enabled: true
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd05_verify
# Inspect draft_manifest.json: pages should have outline_draft field
# Confirm heading hierarchy is valid (no h1→h3 skips) in 5 sampled pages
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_1780_prompt_multipass.py -x -v -k "outline"
# New tests: outline_pass_enabled=True triggers Pass 0; outline stored in orchestrator state;
#            outline_pass_enabled=False (default) skips Pass 0 entirely
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Config respected end-to-end**: `outline_pass_enabled: false` (default). Set `true` in run_config to activate.

**No mock data in production paths**: Outline is LLM output; injected into Pass 1 context as real string.

### Deliverables

- `multi_pass.py`: Add `_run_outline_pass(context) -> str` method; call it in `run()` when `outline_pass_enabled=True`; pass outline string to `_run_draft_pass()` via extended context
- `prompts/outline.txt` (new): System prompt instructing LLM to produce a structured heading outline with `[claim: claim_id]` markers (max 800 tokens)
- 3 unit tests: outline pass fires when enabled; Pass 1 receives outline in context; Pass 0 skipped when disabled
- Outline stored as `state["outline_draft"]` in orchestrator (visible in manifest for debugging)

### Hard Rules

- Default `outline_pass_enabled=False` → MultiPassOrchestrator behavior byte-for-byte identical
- Outline pass adds 1 LLM call per page → document cost in spec amendment
- Outline prompt must stay ≤ 800 output tokens (guard in `_run_outline_pass`)
- No new deps
- Outline format: plain markdown headings + `[claim: id]` markers (reuses existing marker syntax)

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | Pass 0 fires when enabled; outline passed to Pass 1; Pass 2 references outline |
| Correctness | Outline-guided pages have valid heading hierarchy (no FQ-1 violations) |
| Evidence | Pilot manifest showing `outline_draft` field; FQ-1 defect count before/after |
| Test Quality | 3 unit tests: enabled/disabled/outline-in-context |
| Maintainability | `_run_outline_pass()` is a standalone method; no changes to Pass 1/2 internal logic |
| Safety | Default-off; one extra LLM call only when explicitly enabled |
| Security | N/A |
| Reliability | Outline pass failing gracefully (exception → log warning + skip outline, proceed without) |
| Observability | `outline_draft` in manifest; LLM call logged as `pass_0_outline` call_id |
| Performance | +1 LLM call per page when enabled (~30s); no overhead when disabled |
| Compatibility | `MultiPassOrchestrator` public interface unchanged |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §W5 MultiPass section updated |

### Now (Runbook)

```bash
# 1. Read current multi_pass.py to understand Pass 1/2 structure
# 2. Add _run_outline_pass() method to MultiPassOrchestrator
# 3. Create prompts/outline.txt (use format similar to existing draft prompt)
# 4. Wire: if self._outline_enabled: outline = self._run_outline_pass(ctx)
#            pass outline to _run_draft_pass as additional context
# 5. Add 3 unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_1780_prompt_multipass.py -x -v -k "outline"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. Run pilot with outline_pass_enabled: true
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd05_verify
```
