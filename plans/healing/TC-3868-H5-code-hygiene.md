---
id: TC-3868-H5
title: "Code hygiene: dead Literal, atomic writes, token accounting, duplicate HealResult"
status: Done
priority: P2 / Medium
owner: unassigned
updated: "2026-03-08"
tags: [heal, code-quality, atomicity, telemetry, minimality]
depends_on: [TC-3868-H3]
allowed_paths:
  - plans/healing/TC-3868-H5-code-hygiene.md
  - src/launcher/models/evaluation.py
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
---

# TC-3868-H5 — Code hygiene: dead Literal, atomic writes, token accounting, duplicate HealResult

## Status: Not Started

## Gap linkage

- **G-3868-05**: `outcome="checkpoint_invalid"` is present in `HealStep.outcome` Literal but is
  never assigned as an outcome anywhere in the codebase. It only appears as a `fallback_reason`
  value. Dead Literal values are a misleading API surface.
- **G-3868-06**: `_write_diagnosis` uses `Path.write_text` directly. Every other file writer in
  `heal.py` uses `atomic_write_json` from `launcher.io.atomic`. A crash mid-write would leave a
  corrupt `heal_diagnosis.json`.
- **G-3868-07**: Token counting uses `len(prompt.split()) + 1024` — the `+ 1024` is a fixed
  inflation regardless of actual LLM response size. `HealResult.total_tokens` is inflated by
  ~1024 × step_count, making the telemetry field unreliable for capacity planning.
- **G-3868-08**: `HealResult` is constructed twice: once inside `_write_heal_plan()` (called in
  `finally`) and once in the explicit `return` statement at the bottom of `run_heal()`. The
  return statement creates a second, identical object that duplicates logic and could diverge if
  either copy is modified independently.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix G-3868-05 — Remove dead Literal value:

In `evaluation.py`, remove `"checkpoint_invalid"` from `HealStep.outcome` Literal:

```python
outcome: Literal[
    "improved", "regressed", "unchanged", "rejected",
    "schema_failure", "timeout",
    "budget_exceeded", "diagnose_only",
]
```

Grep for any assignment `outcome = "checkpoint_invalid"` to confirm there are none.
`fallback_reason = "checkpoint_invalid"` is correct and must remain.

### Fix G-3868-06 — Use atomic_write_json in _write_diagnosis:

Replace:
```python
(run_dir / "heal_diagnosis.json").write_text(json.dumps(diagnosis, indent=2), encoding="utf-8")
```

With:
```python
from launcher.io.atomic import atomic_write_json
atomic_write_json(run_dir / "heal_diagnosis.json", diagnosis)
```

Move `import datetime` to module top (remove the `import datetime as _dt` inside function body).

### Fix G-3868-07 — Improve token accounting:

Replace the approximate counting block:
```python
tokens_used = len(prompt.split()) + 1024  # approximate
```

With a two-part count that separately tracks prompt tokens and a configurable output estimate:
```python
_ESTIMATED_OUTPUT_TOKENS: int = 512  # conservative estimate for HealDecision JSON
prompt_tokens = len(prompt.split())
tokens_used = prompt_tokens + _ESTIMATED_OUTPUT_TOKENS
```

The constant `_ESTIMATED_OUTPUT_TOKENS = 512` is placed at module top alongside the other
module-level constants, replacing the magic `1024`. The comment explains it is an estimate.

This does not reduce accuracy to zero (token counting is always approximate without a real
tokenizer), but it:
1. Names the estimate constant so it can be tuned
2. Reduces the inflation from 1024 to 512 (closer to real HealDecision JSON size)
3. Makes the estimate visible and findable via grep

### Fix G-3868-08 — Remove duplicate HealResult construction:

Refactor `run_heal()` to cache the `HealResult` in the `finally` block instead of calling
`_write_heal_plan` (which constructs it internally). Options:

**Option A (minimal diff):** Have `_write_heal_plan` return the `HealResult` it constructs, and
store it:

```python
# In finally:
heal_result = _write_heal_plan(run_dir, steps, stop_reason, initial_metrics, current_metrics)
typer.echo(...)

# At bottom of run_heal():
return heal_result
```

Update `_write_heal_plan` signature to return `HealResult` (currently returns `None`).

**Option B:** Keep `_write_heal_plan` returning `None`; construct the `HealResult` once at the
bottom, then call a separate `_persist_heal_result(run_dir, result)` in `finally`.

Option A is preferred (fewer lines changed, simpler refactor).

### Allowed paths:
- `plans/healing/TC-3868-H5-code-hygiene.md`
- `src/launcher/models/evaluation.py`
- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_cli.py`

### Forbidden: any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    -v --tb=short
```

### UI/Web/API:
N/A.

### Tests:
1. `test_dead_literal_not_present` — assert `"checkpoint_invalid"` is NOT in
   `HealStep.model_fields["outcome"].annotation.__args__` (inspects the Literal at runtime).
2. `test_write_diagnosis_is_atomic` — patch `launcher.io.atomic.atomic_write_json` as a
   `MagicMock`; call `_write_diagnosis(tmp_path, [])`; assert the mock was called with
   `tmp_path / "heal_diagnosis.json"` and a dict containing `"actions"`.
3. `test_write_heal_plan_returns_result` — call `_write_heal_plan(...)` and assert the return
   value is a `HealResult` with the correct fields (verifies the Option A refactor).
4. `test_tokens_used_uses_module_constant` — assert `tokens_used` for a step equals
   `len(prompt.split()) + _ESTIMATED_OUTPUT_TOKENS` (import the constant from `heal`).
5. `test_run_heal_result_equals_written_plan` — run a dry-run and assert that the returned
   `HealResult` and the written `heal_plan.json` have identical `run_id` and `stop_reason`
   (no divergence between the two construction sites).
6. All existing tests pass.

### Config respected end-to-end:
`_ESTIMATED_OUTPUT_TOKENS` at module top can be overridden in tests without patching internals.

### No mock data in production paths:
`atomic_write_json` is mocked only in the atomicity test; the production path calls the real
function.

## Deliverables

1. **`src/launcher/models/evaluation.py`** — Remove `"checkpoint_invalid"` from `HealStep.outcome`
   Literal. Full file replacement.
2. **`src/launcher/cli/heal.py`** — Full file replacement with:
   - `_ESTIMATED_OUTPUT_TOKENS = 512` constant at module top
   - `import datetime` at module top (not inside function)
   - `_write_diagnosis` uses `atomic_write_json`
   - `_write_heal_plan` returns `HealResult`
   - `run_heal` stores returned `HealResult` from `_write_heal_plan` and returns it
3. **`tests/unit/cli/test_heal_cli.py`** — Add 5 tests listed above (can go into a new
   `TestHealCodeHygiene` class or append to `TestHealModes`).

Full file replacements — no stubs, no TODOs.

Contracts/schemas: removing `"checkpoint_invalid"` from the Literal is a breaking change for
any code that *assigns* `outcome = "checkpoint_invalid"`. Grep confirms no such assignment
exists before making the change.

## Hard rules

- Before removing the Literal value, confirm zero assignment sites exist:
  `grep -rn '"checkpoint_invalid"' src/` must return only `fallback_reason` assignments.
- `_write_heal_plan` return type must be updated in the function signature (`-> HealResult`).
- All callers of `_write_heal_plan` must handle the return value (currently only one caller
  in `run_heal` finally block).
- No network in offline tests.
- Deterministic runs: `PYTHONHASHSEED=0`.
- No new deps: `atomic_write_json` is already imported elsewhere in `heal.py`.
- Keep the `import datetime` move surgical — do not rearrange other imports.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Minimality | Each fix is ≤5 lines changed; total diff is clean and focused |
| Correctness | `"checkpoint_invalid"` Literal removal verified by grep before change |
| Atomicity | `heal_diagnosis.json` uses same `atomic_write_json` pattern as all other outputs |
| Telemetry | `total_tokens` is within 20% of actual for a 1000-token prompt (512 vs 1024 saved) |
| Maintainability | No duplicate `HealResult` construction; single source of truth |
| Testability | Each fix has a corresponding test that would catch a regression |

## Now (runbook)

```bash
# G-3868-05: Confirm no assignment of checkpoint_invalid as outcome
grep -rn '"checkpoint_invalid"' src/launcher/

# G-3868-06: Confirm _write_diagnosis does not already use atomic_write_json
grep -n "write_text\|atomic_write" src/launcher/cli/heal.py

# G-3868-07: Find the token counting line
grep -n "tokens_used\|1024" src/launcher/cli/heal.py

# G-3868-08: Find both HealResult construction sites
grep -n "HealResult(" src/launcher/cli/heal.py

# Apply all four fixes in heal.py + evaluation.py

# Verify no "checkpoint_invalid" as outcome assignment remains:
grep -rn 'outcome.*=.*"checkpoint_invalid"' src/

# Verify atomic_write_json is used in _write_diagnosis:
grep -A3 "_write_diagnosis" src/launcher/cli/heal.py | grep atomic

# Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    -v --tb=short

# Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```
