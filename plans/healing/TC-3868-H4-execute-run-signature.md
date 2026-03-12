---
id: TC-3868-H4
title: "Verify and fix execute_run() call signature in _execute_worker_rerun"
status: Done
priority: P1 / High
owner: unassigned
updated: "2026-03-08"
tags: [heal, integration-boundary, run-loop, correctness]
depends_on: []
allowed_paths:
  - plans/healing/TC-3868-H4-execute-run-signature.md
  - src/launcher/cli/heal.py
  - tests/unit/cli/test_heal_cli.py
  - tests/integration/test_heal_integration.py
---

# TC-3868-H4 — Verify and fix `execute_run()` call signature

## Status: Not Started

## Gap linkage

- **G-3868-04**: `_execute_worker_rerun` calls `execute_run()` with keyword arguments
  `resume_from`, `stop_after`, `run_id`, and `runs_root`. This call was written without
  verifying the actual signature of `launcher.orchestrator.run_loop.execute_run`. The
  function is imported with a deferred import (correct for circular-import avoidance) so
  no import-time error surfaces. A runtime `TypeError: execute_run() got an unexpected
  keyword argument` would only appear when a live heal run actually reaches the execute path,
  which none of the tests do (they all fall through to `config_not_found` because `tmp_path`
  has no `run_config.yaml`).

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix:

**Step 1 — Read `run_loop.py` and extract the real `execute_run` signature.**

Inspect `src/launcher/orchestrator/run_loop.py` and determine:
- The exact parameter names
- Which params are positional vs. keyword
- Whether `resume_from`, `stop_after`, `run_id`, `runs_root` exist under those names or
  under different names (e.g., `start_worker`, `end_worker`, `run_id`, `output_dir`)

**Step 2 — Update the call site in `heal.py` to match the real signature.**

The call currently is:
```python
result = await execute_run(
    config,
    resume_from=worker,
    stop_after="evaluate",
    run_id=original_run_id,
    runs_root=run_dir.parent,
)
```

After reading the real signature, update keyword argument names to match exactly.
If `execute_run` does not accept some of these concepts (e.g., `stop_after`), either:
(a) pass the closest equivalent parameter, or
(b) return `(current_metrics, "unchanged", "execute_run_unsupported")` with a
    `logger.warning` explaining which parameters are missing, until the run_loop is extended.

Option (b) is acceptable for this TC if the signature is materially different; the healing
plan TC for extending the run_loop would be a separate TC (not in scope here).

**Step 3 — Add a type-safe wrapper comment.**

Above the `execute_run` call, add:
```python
# Signature verified against run_loop.execute_run as of TC-3868-H4.
# If run_loop signature changes, update this call and the TC-3868-H4 taskcard.
```

**Step 4 — Add an integration test that exercises the execute path with a mocked execute_run.**

The test must patch `launcher.orchestrator.run_loop.execute_run` (not `heal.execute_run`) with a
coroutine mock that returns a synthetic result, then run `run_heal()` with a valid
`run_config.yaml` in `tmp_path`. This is the only test that currently reaches the `execute_run`
call site.

### Allowed paths:
- `plans/healing/TC-3868-H4-execute-run-signature.md`
- `src/launcher/cli/heal.py`
- `tests/unit/cli/test_heal_cli.py`
- `tests/integration/test_heal_integration.py`

### Forbidden:
- `src/launcher/orchestrator/run_loop.py` — must not be modified in this TC
- Any other file/path

## Acceptance checks

### CLI:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py \
    tests/integration/test_heal_integration.py \
    -v --tb=short
```
Zero `TypeError` failures. All existing tests pass.

### UI/Web/API:
N/A.

### Tests:
1. `test_execute_run_called_with_correct_kwargs` — in `TestHealModes`, patch
   `launcher.orchestrator.run_loop.execute_run` as an `AsyncMock` that returns a fake result
   object with `report=None`. Write a minimal `run_config.yaml` to `tmp_path`. Run
   `_execute_worker_rerun` with `mode="worker"` and a valid `checkpoint_id`. Assert the mock
   was called with the correct keyword arguments (matching the verified signature).
2. `test_execute_run_result_none_returns_unchanged` — same setup but `AsyncMock` returns `None`;
   assert `outcome == "unchanged"` (not a crash).
3. Verify existing test suite has no new failures.

### Config respected end-to-end:
`run_config.yaml` must be a valid YAML file loadable by `RunConfig.model_validate`. The test
should write a minimal valid config (using the minimal RunConfig fields).

### No mock data in production paths:
`execute_run` is mocked only in tests; the production path calls the real function.

## Deliverables

1. **`src/launcher/cli/heal.py`** — Updated `execute_run` call site with verified kwargs.
   Signature verification comment added. Full file replacement.
2. **`tests/unit/cli/test_heal_cli.py`** — Add `test_execute_run_called_with_correct_kwargs`
   and `test_execute_run_result_none_returns_unchanged` to `TestHealModes`. These are unit tests
   because they mock at the `run_loop` level.
3. **`tests/integration/test_heal_integration.py`** — Add a minimal `run_config.yaml`-writing
   helper and one integration test that exercises the full `worker` → `execute_run` path.

If the actual `execute_run` signature is materially incompatible (i.e., the named kwargs do not
exist), the deliverable for `heal.py` must include a safe fallback with a clear `logger.warning`
and `outcome="unchanged"`, plus a comment documenting the gap and the TC that should extend
`run_loop.py`.

Full file replacements — no stubs, no TODOs.

## Hard rules

- Do NOT modify `run_loop.py` in this TC. Read-only access to it.
- If the signature mismatches, document the delta in the evidence comment; do not silently
  pass wrong kwargs.
- No network in offline tests: `execute_run` must be mocked via `AsyncMock`.
- Deterministic runs: `PYTHONHASHSEED=0`.
- No new deps.

## Review dimensions

| Dimension | 5/5 target for this TC |
|-----------|------------------------|
| Correctness | Call site kwargs exactly match `execute_run`'s real parameter names |
| Integration fit | The heal→run_loop boundary is proven by a test that reaches `execute_run` |
| Robustness | `execute_run` returning `None` does not crash `_execute_worker_rerun` |
| Observability | Signature verification comment is present above the call site |
| Minimality | Only the call site and tests change; `run_loop.py` is untouched |
| Testability | `AsyncMock` test covers both the happy path and the `None` result path |

## Now (runbook)

```bash
# 1. Read the real execute_run signature
grep -n "^async def execute_run\|^def execute_run" \
    src/launcher/orchestrator/run_loop.py

# If not found at top level:
grep -n "def execute_run" src/launcher/orchestrator/run_loop.py

# 2. Read the full signature (parameters + defaults)
# Use Read tool on run_loop.py to inspect the function

# 3. Compare against the call in heal.py
grep -A8 "result = await execute_run" src/launcher/cli/heal.py

# 4. Update the call site in heal.py if kwargs differ

# 5. Write a minimal RunConfig YAML helper in the test file
# (look at existing tests to see what fields are required)
.venv/Scripts/python.exe -c "
from launcher.models.run_config import RunConfig
import inspect
print(inspect.signature(RunConfig))
"

# 6. Add the two new tests

# 7. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest \
    tests/unit/cli/test_heal_cli.py::TestHealModes::test_execute_run_called_with_correct_kwargs \
    tests/unit/cli/test_heal_cli.py::TestHealModes::test_execute_run_result_none_returns_unchanged \
    -v --tb=short

# 8. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=no | tail -5
```
