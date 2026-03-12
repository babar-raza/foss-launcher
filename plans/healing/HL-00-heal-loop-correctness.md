# Heal Loop Correctness — Gap Index & Taskcards

## Context

Self-review of `quirky-mapping-mccarthy.md` (LLM-Driven Heal, H1–H5) identified four
correctness gaps in `src/launcher/cli/heal.py`. The most critical is that the heal
loop never actually re-runs the pipeline — `outcome` is hardcoded to `"unchanged"`,
making the entire system a no-op. The other three gaps cause crashes, silent data
loss, or unobservable sessions.

These taskcards are ordered by priority. HL-01 is a prerequisite for HL-03 and all H5
work. HL-02 and HL-04 are independent and can be executed in parallel with HL-01.

---

## Gap Table

| Gap ID  | Description                                                         | Taskcard | Priority |
|---------|---------------------------------------------------------------------|----------|----------|
| GAP-01  | Heal loop hardcodes `outcome="unchanged"` — pipeline never re-runs  | HL-01    | CRITICAL |
| GAP-08  | Double `HealResult` construction — return value may differ from disk | HL-01    | MEDIUM   |
| GAP-02  | `HealDecision` schema_failure step uses raw `dict` for `action`     | HL-02    | CRITICAL |
| GAP-04  | No `emit_event` calls in heal loop — zero session observability     | HL-03    | HIGH     |
| GAP-10  | `system[:500]` silently truncates the diagnostician system prompt   | HL-04    | MEDIUM   |
| GAP-12  | Session-level timeout (1800 s) not enforced — only per-step check   | HL-04    | MEDIUM   |
| GAP-14  | `_FULL_STEPS = 3` defined as a local inside `_build_diagnostician_prompt` | HL-04 | LOW   |

---

## HL-01 — Wire Pipeline Re-Execution into the Heal Loop

**Status:** Not Started
**Gap linkage:** GAP-01, GAP-08

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
1. Add `_write_heal_metadata(run_dir, worker, target_pages, page_directives, global_directives, re_run_count)` — writes `run_dir/heal_metadata.json` atomically using `atomic_write_json`. Schema must match the `heal_metadata` contract in `WorkerContext` (see `src/launcher/orchestrator/worker_contract.py`).
2. Replace the stub block (`outcome = "unchanged"`, comment "deferred to integration test") in `run_heal()` with:
   a. Write `heal_metadata.json` via `_write_heal_metadata`.
   b. Invoke `_trigger_worker_rerun(run_dir, worker, heal_config)` — calls the run_loop resume path scoped to the targeted worker and target_pages only.
   c. After re-run completes, re-load eval report from disk via `_load_eval_report(run_dir)`.
   d. Compute `after_metrics = _extract_metrics(updated_report)`.
   e. Determine `outcome` via `_determine_outcome(before_metrics, after_metrics, regression_threshold)`.
   f. If `outcome == "regressed"`: call `_rollback_checkpoint(run_dir, checkpoint_id)` and add quarantine entry.
3. `_trigger_worker_rerun(run_dir, worker, heal_config)` signature:
   ```python
   def _trigger_worker_rerun(
       run_dir: Path,
       worker: str,
       heal_config: dict,
   ) -> None:
       """Re-invoke the pipeline from `worker` with heal_metadata injected.

       Uses run_loop resume entry point; sets FOSS_LAUNCHER_HEAL_WORKER env var
       so graph_builder skips all workers before `worker`. Blocks until complete.
       Raises PipelineRerunError on failure (non-zero exit or exception).
       """
   ```
4. `_determine_outcome` must implement the regression rule from the plan:
   - `"regressed"` if `after.critical_count > before.critical_count` OR `after.df_rate > before.df_rate + regression_threshold` OR any page that was A/B is now D/F.
   - `"improved"` if `_is_improved(before, after, threshold)` (existing helper).
   - `"unchanged"` otherwise.
5. Remove the duplicate `HealResult` construction at lines 481-492 (the return at end of function). The `finally` block already writes `heal_plan.json`; make `run_heal` store the result in a local and return it, so the in-memory object and disk artifact are built from the same data.
   ```python
   result: HealResult | None = None
   ...
   try:
       with RunLock(...):
           ...
           result = HealResult(...)  # build once, inside the try block
   except RunAlreadyActiveError:
       ...
       return None
   finally:
       if result is not None:
           _write_heal_plan(run_dir, ...)
   return result
   ```

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py` (NEW)
- `tests/integration/test_heal_rerun.py` (NEW)

**Forbidden:** any other file or path.

### Acceptance checks

**CLI:**
```bash
# After fix: creates heal_metadata.json and re-runs planner worker
python -m launcher.cli.main heal --run-dir /tmp/test_run --max-steps 1 --dry-run
# Dry-run must print prompt + metrics without writing heal_metadata.json

python -m launcher.cli.main heal --run-dir /tmp/test_run --max-steps 1
# Must write heal_metadata.json AND attempt pipeline re-run (even if LLM unavailable path)
```

**Tests:**
- `test_heal_metadata_written_before_rerun` — `heal_metadata.json` present after one step
- `test_outcome_improved_when_df_drops` — mock `_trigger_worker_rerun` + `_load_eval_report` returning better metrics → outcome "improved"
- `test_outcome_regressed_when_critical_increases` — mock returning worse metrics → outcome "regressed", quarantine entry added
- `test_rollback_called_on_regression` — regression → `_rollback_checkpoint` invoked with correct checkpoint_id
- `test_no_duplicate_healresult` — `heal_plan.json` on disk matches the returned `HealResult` exactly (compare `model_dump()`)
- `test_dry_run_does_not_write_heal_metadata` — no `heal_metadata.json` in dry-run mode
- All existing tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest`

**Config respected end-to-end:** `--regression-threshold` flag changes the regression boundary; test at boundary.

**No mock data in production paths:** `_trigger_worker_rerun` must call the real run_loop entry point, not a mock. Integration test uses a real (minimal) run_dir fixture.

### Deliverables
- Full replacement of `src/launcher/cli/heal.py` with stub removed, all helpers implemented
- `tests/unit/test_heal_loop.py` covering all acceptance checks above (happy path + regression path)
- `tests/integration/test_heal_rerun.py` covering at least: metadata written, re-run invoked, metrics refreshed

### Hard rules
- Public signatures of `run_heal()`, `heal()` (typer command) unchanged
- `_trigger_worker_rerun` must log `[heal] re-running worker=%s target_pages=%s` at INFO before execution
- `PYTHONHASHSEED=0` in all test commands
- No network calls in unit tests (mock `LLMProviderClient` and `_trigger_worker_rerun`)
- Integration test may use a local minimal run_dir fixture with pre-existing eval report
- No new pip dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | `outcome` reflects real pipeline delta; regression triggers rollback |
| Robustness | `_trigger_worker_rerun` failure → `stop_reason="pipeline_rerun_failed"`, session ends cleanly |
| Testability | Unit tests mock rerun; integration test exercises real code path |
| Observability | `[heal] step N outcome=improved df_before=0.40 df_after=0.25` logged at INFO |
| Minimality | Stub removed; no duplicate HealResult; no extra state variables |

### Now (runbook)
```bash
# 1. Read current heal.py stub (lines 427-492) to understand what must be replaced
# 2. Read orchestrator/run_loop.py resume path to find correct entry point
# 3. Read worker_contract.py to confirm heal_metadata field shape
# 4. Implement _write_heal_metadata + _trigger_worker_rerun + _determine_outcome
# 5. Replace stub block; fix double HealResult
# 6. Write tests
# 7. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py -v
# 8. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/integration/test_heal_rerun.py -v
# 9. Run full suite: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## HL-02 — Fix HealDecision Schema_Failure Type Mismatch

**Status:** Not Started
**Gap linkage:** GAP-02

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
In `run_heal()`, the `schema_failure` step constructs `HealDecision` with `action={"worker": ..., ...}` — a raw dict where Pydantic expects a `HealAction` instance. This passes construction (Pydantic coerces dicts to models) but the `action` field type annotation is `HealAction`, and the raw dict will not have the correct model methods, causing a `ValidationError` on `model_dump(mode="json")` when the step is serialized.

Replace lines ~373–390:
```python
# BEFORE (broken):
decision=HealDecision(
    analysis="Failed to parse response",
    root_causes=[],
    action={"worker": "generate", "target_pages": [],
            "strategy": "schema_failure", "priority_checks": []},
    confidence=0.0,
    stop_recommendation=False,
),

# AFTER (correct):
decision=HealDecision(
    analysis="Failed to parse response",
    root_causes=[],
    action=HealAction(
        worker="generate",
        target_pages=[],
        strategy="schema_failure",
        priority_checks=[],
    ),
    confidence=0.0,
    stop_recommendation=False,
    stop_reason=None,
),
```

Also verify `HealAction` is imported at the top of `heal.py` from `launcher.models.evaluation`.

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py` (add test to existing file, or create if HL-01 not yet merged)

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_schema_failure_step_serializes_cleanly` — construct the schema_failure `HealStep`, call `step.model_dump(mode="json")`, assert no exception, assert `result["decision"]["action"]["worker"] == "generate"`
- `test_schema_failure_outcome_recorded` — after a mock LLM response that fails JSON parse, the step is appended with `outcome="schema_failure"` and `confidence=0.0`
- `test_full_result_serializes_after_schema_failure` — `HealResult` with one schema_failure step serializes to JSON without ValidationError

**CLI:**
```bash
# Simulate schema failure: set LLM to return invalid JSON, run one step
python -m launcher.cli.main heal --run-dir /tmp/test_run --max-steps 1
# heal_plan.json must exist and be valid JSON with steps[0].outcome == "schema_failure"
```

**No mock data in production paths:** The HealAction construction uses the model, not a dict.

### Deliverables
- Patched `src/launcher/cli/heal.py` with correct `HealAction` construction
- `test_schema_failure_step_serializes_cleanly` and two companion tests

### Hard rules
- `HealAction` imported from `launcher.models.evaluation` at top of file (not inline)
- `stop_reason=None` explicitly set on the schema_failure `HealDecision` (Pydantic optional field must be explicit)
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | `step.model_dump(mode="json")` succeeds for schema_failure steps |
| Minimality | One-line change + import; no surrounding refactor |
| Testability | Isolated unit test that asserts serialization succeeds |

### Now (runbook)
```bash
# 1. Confirm HealAction is exported from launcher.models.evaluation
grep -n "HealAction" src/launcher/models/evaluation.py
# 2. Edit the 6-line block in heal.py (lines ~373-381)
# 3. Add HealAction to the import line at top of heal.py
# 4. Write test
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py::test_schema_failure_step_serializes_cleanly -v
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## HL-03 — Add emit_event Observability to Heal Loop

**Status:** Not Started
**Gap linkage:** GAP-04

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix:**
The v2 event system (`src/launcher/state/event_log.py`) is the primary observability path. A heal session that emits zero events is invisible to monitoring and to the post-run event viewer.

Add event emissions at four points in `run_heal()`:

1. **Session start** (before the `for step_idx` loop):
   ```python
   _emit_heal_event(run_dir, "heal_session_started", {
       "run_id": run_dir.name,
       "max_steps": max_steps,
       "initial_df_rate": initial_metrics.df_rate,
       "initial_ab_rate": initial_metrics.ab_rate,
   })
   ```

2. **Step start** (top of loop body, after budget check):
   ```python
   _emit_heal_event(run_dir, "heal_step_started", {
       "step_idx": step_idx,
       "df_rate": current_metrics.df_rate,
   })
   ```

3. **Step end** (after outcome determined, before quarantine update):
   ```python
   _emit_heal_event(run_dir, "heal_step_completed", {
       "step_idx": step_idx,
       "worker": worker,
       "outcome": outcome,
       "confidence": decision.confidence,
       "tokens_used": tokens_used,
       "execution_seconds": round(time.monotonic() - step_start, 2),
   })
   ```

4. **Session end** (in `finally` block, after `_write_heal_plan`):
   ```python
   _emit_heal_event(run_dir, "heal_session_completed", {
       "run_id": run_dir.name,
       "stop_reason": stop_reason,
       "total_steps": len(steps),
       "total_fixes": sum(1 for s in steps if s.outcome == "improved"),
       "total_regressions": sum(1 for s in steps if s.outcome == "regressed"),
       "final_df_rate": current_metrics.df_rate,
       "final_ab_rate": current_metrics.ab_rate,
   })
   ```

`_emit_heal_event` helper:
```python
def _emit_heal_event(run_dir: Path, event_type: str, payload: dict) -> None:
    """Append a heal event to events.ndjson in run_dir. Never raises."""
    try:
        from launcher.state.event_log import append_event
        append_event(run_dir, event_type=event_type, payload=payload)
    except Exception as exc:
        logger.debug("[heal] Event emit failed (%s): %s", event_type, exc)
```

Event type names must match the constants defined in H1.3 (`HEAL_SESSION_STARTED`, etc.) from `src/launcher/models/event.py`. If those constants don't yet exist, import and use the string literals directly until H1.3 is merged; add a `# TODO: use EventType.HEAL_SESSION_STARTED` comment.

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**CLI:**
```bash
python -m launcher.cli.main heal --run-dir /tmp/test_run --max-steps 2
grep "heal_session_started\|heal_step_started\|heal_session_completed" /tmp/test_run/events.ndjson
# Must show at least 4 lines: session_started, step_started x1, step_completed x1, session_completed
```

**Tests:**
- `test_session_started_event_emitted` — mock `append_event`; after `run_heal()`, assert called with `event_type="heal_session_started"`
- `test_step_events_emitted` — after one step, assert both `heal_step_started` and `heal_step_completed` called
- `test_session_completed_event_in_finally` — force an exception mid-loop; assert `heal_session_completed` still emitted
- `test_event_emit_failure_does_not_crash_session` — mock `append_event` to raise; assert `run_heal` completes normally

**No mock data in production paths:** `append_event` called with real payload dicts.

### Deliverables
- Patched `src/launcher/cli/heal.py` with `_emit_heal_event` helper and 4 emission points
- 4 unit tests covering emission and failure isolation

### Hard rules
- `_emit_heal_event` must NEVER raise — all exceptions swallowed at DEBUG level
- Event payloads must not contain non-serializable objects (Path, datetime — convert to str first)
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Observability | 4 event types emitted; `events.ndjson` shows full session timeline |
| Robustness | Emit failure never propagates to session logic |
| Correctness | Event type names consistent with `models/event.py` constants |

### Now (runbook)
```bash
# 1. Read src/launcher/state/event_log.py to confirm append_event signature
# 2. Read src/launcher/models/event.py to check heal event type constants
# 3. Add _emit_heal_event helper + 4 call sites in heal.py
# 4. Write unit tests (mock append_event)
# 5. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py -v -k event
# 6. PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```

---

## HL-04 — Fix Prompt Truncation, Session Timeout, and _FULL_STEPS Constant

**Status:** Not Started
**Gap linkage:** GAP-10, GAP-12, GAP-14

### Role
Senior engineer. Drop-in, production-ready. No stubs. No TODOs.

### Scope

**Fix (three independent sub-fixes, all in the same file):**

**Sub-fix A — Remove `system[:500]` cap (GAP-10):**
In `_build_diagnostician_prompt`, the system prompt is truncated to 500 chars:
```python
f"SYSTEM:\n{system[:500]}\n\n"
```
This silently cuts critical instructions from `heal_diagnostician.txt`. Remove the cap entirely. The size control belongs at the *history* compression level, not the system prompt level:
```python
f"SYSTEM:\n{system}\n\n"
```
If prompt total length becomes a concern, the rolling history compression (last 3 full + older compressed) already handles it.

**Sub-fix B — Add session-level timeout (GAP-12):**
The plan specifies a 1800 s session timeout. Currently only per-step budget checks exist. Add:
```python
_session_start = time.monotonic()
_SESSION_TIMEOUT_S = 1800  # hard cap, configurable via BudgetTracker

# At the top of each loop iteration (after existing budget.check_runtime()):
if time.monotonic() - _session_start > _SESSION_TIMEOUT_S:
    stop_reason = "session_timeout"
    typer.echo(f"[heal] Session timeout ({_SESSION_TIMEOUT_S}s) at step {step_idx}")
    break
```
`_SESSION_TIMEOUT_S` should be read from `_DEFAULT_BUDGETS["max_runtime_s"]` rather than hardcoded separately, so a single constant governs both.

**Sub-fix C — Hoist `_FULL_STEPS` to module constant (GAP-14):**
Move `_FULL_STEPS = 3` from inside `_build_diagnostician_prompt` to module level alongside the other `_DEFAULT_*` constants. Add a comment:
```python
# Rolling history: last _FULL_STEPS steps shown in full JSON; older steps compressed.
_FULL_STEPS: int = 3
```

**Allowed paths:**
- `src/launcher/cli/heal.py`
- `tests/unit/test_heal_loop.py`

**Forbidden:** any other file or path.

### Acceptance checks

**Tests:**
- `test_system_prompt_not_truncated` — load a 1000-char system prompt file; assert `_build_diagnostician_prompt(...)` output contains the full text
- `test_session_timeout_stops_loop` — mock `time.monotonic` to advance 1801 s; assert `run_heal` returns with `stop_reason="session_timeout"` after ≤1 iteration
- `test_full_steps_constant_at_module_level` — import `heal` module; assert `hasattr(heal_module, "_FULL_STEPS")` is True
- `test_session_timeout_respects_max_runtime_s` — `_DEFAULT_BUDGETS["max_runtime_s"]` == 1800 == `_SESSION_TIMEOUT_S` (or derived from it)

**CLI:**
```bash
# Confirm prompt not truncated: run heal with a deliberately long diagnostician.txt
python -c "
from launcher.cli.heal import _build_diagnostician_prompt
from launcher.models.evaluation import EvaluationReport
# build a prompt and check system section length
"
```

### Deliverables
- Patched `src/launcher/cli/heal.py` with three sub-fixes
- 4 unit tests covering each sub-fix

### Hard rules
- `_SESSION_TIMEOUT_S` must not be a new constant separate from `_DEFAULT_BUDGETS["max_runtime_s"]` — derive it: `_SESSION_TIMEOUT_S = _DEFAULT_BUDGETS["max_runtime_s"]`
- Session timeout check must happen BEFORE the LLM call in each iteration, not after
- No new dependencies

### Review dimensions (what 5/5 means here)
| Dimension | 5/5 |
|-----------|-----|
| Correctness | System prompt full length in every call; session stops at 1800s |
| Minimality | Three targeted lines changed; no surrounding refactor |
| Maintainability | `_FULL_STEPS` visible at module level with a comment |

### Now (runbook)
```bash
# Sub-fix A: remove [:500] from _build_diagnostician_prompt line ~166
# Sub-fix B: add _session_start = time.monotonic() before loop; add timeout check at loop top
# Sub-fix C: move _FULL_STEPS = 3 to module level (after _DEFAULT_BUDGETS block)
# Write tests
# PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/test_heal_loop.py -v
# PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -x -q
```
