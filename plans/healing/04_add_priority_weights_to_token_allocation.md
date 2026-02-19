# Healing Plan: Priority-Weighted Token Allocation

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Allocate LLM tokens by section priority rather than equal distribution.

## Context

Equal token distribution causes "Getting Started" (highest user value) to receive the same budget as "License" (boilerplate). Manual review of both pilots confirms critical sections are under-resourced (< 300 words) while low-value sections are padded. W4 already writes `content_strategy.priority_weight` to `page_plan.json` but W5 never reads it.

## Gap → Taskcard Mapping

| Gap ID | Description                                        | Taskcard |
|--------|----------------------------------------------------|----------|
| RD-04  | Equal token distribution ignores section priority  | RD-04    |

---

## Taskcard RD-04 — Priority-Weighted Token Allocation in W5

**Status**: Not Started
**Gap linkage**: RD-04 (00_REDESIGN.md §2.2 item 2, TC-2373)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add `_compute_token_budget(page, base_tokens, run_config) -> int` helper to W5 `worker.py`. Read `page["content_strategy"]["priority_weight"]` (float 0.5–2.0); fall back to `SECTION_TYPE_WEIGHTS` dict keyed by `page["page_type"]`; clamp to `[0.5×base, 2.0×base]`. Call this inside `_generate_single_page()` before the LLM call.

**Allowed paths**:
```
src/launch/workers/w5_section_writer/worker.py
tests/unit/workers/test_tc_440_section_writer.py
```

**Forbidden**: any other file or path (no W4 changes, no schema changes).

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd04_verify
# Inspect run logs for DEBUG lines: [W5] slug: base=N weight=W effective=M
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_440_section_writer.py -x -v -k "token_budget"
# 3 new tests: weight from page field, fallback to section type, clamp at 2.0x
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Config respected end-to-end**: `priority_weights_enabled: true` (default). `false` → all weights 1.0.

**No mock data in production paths**: Weight read from live `page_plan.json` only.

### Deliverables

- `worker.py`: `SECTION_TYPE_WEIGHTS` module-level dict; `_compute_token_budget()` helper; wired into `_generate_single_page()`
- 3 unit tests: weight from page field (assert multiplied budget), fallback to type dict, clamp boundary (weight=3.0 → 2.0× max)
- DEBUG log per page: `[W5] {slug}: base={n} weight={w:.2f} effective={m}`

### Hard Rules

- Clamp: `effective = max(int(base * 0.5), min(int(base * 2.0), int(base * weight)))`
- `page_plan.json` never mutated — W5 computes effective budget locally only
- Sequential and parallel modes both call `_compute_token_budget()`
- No new deps (`SECTION_TYPE_WEIGHTS` is a module-level constant dict)
- Default weight 1.0 → identical behavior when field absent

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All page types get weight applied; fallback handles unmapped types |
| Correctness | getting_started effective_budget ≥ api_reference effective_budget |
| Evidence | DEBUG log lines + pilot word count comparison |
| Test Quality | 3 unit tests with numeric assertions; clamp boundary verified |
| Maintainability | Single helper; readable weight dict with inline comments |
| Safety | Default 1.0 → zero behavioral change when weight absent |
| Security | N/A |
| Reliability | Deterministic; integer arithmetic |
| Observability | DEBUG log per page visible in run logs |
| Performance | < 0.1ms per page |
| Compatibility | No signature changes; new optional config key |
| Docs/Specs Fidelity | `specs/21_worker_contracts.md` §W5 updated |

### Now (Runbook)

```bash
# 1. Check if priority_weight is in page_plan.json
.venv/Scripts/python.exe -c "
import json, pathlib
pp = json.loads(pathlib.Path(
  'runs/r_20260219T110951Z_launch_pilot-aspose-3d-foss-python_3711472_default_98a0a866'
  '/artifacts/page_plan.json').read_text('utf-8','replace'))
for p in pp.get('pages', [])[:3]:
    cs = p.get('content_strategy', {})
    print(p.get('slug','?'), cs.get('priority_weight','MISSING'), p.get('page_type','?'))
"

# 2. Add SECTION_TYPE_WEIGHTS + _compute_token_budget() to worker.py
# 3. Wire into _generate_single_page
# 4. Add 3 unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
  tests/unit/workers/test_tc_440_section_writer.py -x -v -k "token_budget"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 5. Run pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd04_verify
```
