# Healing Plan: SR-3869 — Documentation & Process Debt

**Source**: Self-review of TC-3869 (resume skip guard in `graph_builder.py`)
**Priority**: MEDIUM — process violations and docstring debt; no correctness impact but violates AG-020 and CLAUDE.md governance

---

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| SR-03 | TC-3869 acceptance checks left unchecked despite tests passing | TC-SR-04 |
| SR-04 | `_make_worker_node` docstring not updated to document skip behavior | TC-SR-05 |
| SR-05 | `re_run_count == 0` assumption not documented in code | TC-SR-05 |
| SR-06 | `__heal_router__` redundancy not noted with code comment | TC-SR-06 |

---

## TC-SR-04 — Tick acceptance checks in TC-3869 taskcard

**Status**: Done
**Gap linkage**: SR-03
**Role**: Senior engineer. Drop-in, production-ready.

### Context

CLAUDE.md mandates: "Mark Done only when ALL acceptance checks are `[x]`". TC-3869 was marked
`status: Done` with its self-review verification results filled in, but the four `## Acceptance checks`
items remain as `[ ]`. This is a process violation that could mislead future engineers about whether
the task was fully verified.

### Scope

**Fix**:
In `plans/taskcards/TC-3869_resume_skip_cached_workers.md`, update the Acceptance checks section:

```markdown
# BEFORE
1. [ ] `pytest tests/unit/orchestrator/test_graph_builder.py -v` — 0 failures, 4 new tests pass
2. [ ] `worker_skipped` event emitted with `reason: resume_checkpoint` (verified in test)
3. [ ] Re-run iteration does NOT skip generate (verified by `test_worker_runs_on_rerun_despite_cached_output`)
4. [ ] `pytest tests/ -x -q` — 0 failures (full suite)

# AFTER
1. [x] `pytest tests/unit/orchestrator/test_graph_builder.py -v` — 0 failures, 5 new tests pass
2. [x] `worker_skipped` event emitted with `reason: resume_checkpoint` (verified in test)
3. [x] Re-run iteration does NOT skip generate (verified by `test_worker_runs_on_rerun_despite_cached_output`)
4. [x] `pytest tests/ -x -q` — 3073 passed, 0 failures (full suite)
```

Also update `updated:` date to today.

**Allowed paths**:
- `plans/taskcards/TC-3869_resume_skip_cached_workers.md`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: Manual inspection — all 4 items show `[x]`
- **UI/Web/API**: N/A
- **Tests**: N/A (this is a documentation fix)
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: N/A

### Deliverables

1. **`plans/taskcards/TC-3869_resume_skip_cached_workers.md`** — all acceptance checks ticked `[x]` with accurate counts

### Hard rules

- Do not alter the test counts (must match actual: 5 new tests, 3073 total)
- Do not alter any other section of the taskcard

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Consistency | Taskcard `[ ]` and self-review `[x]` are in full agreement |
| Minimality | Only the 4 checkbox lines and `updated:` date change |
| Maintainability | Future readers can trust Done = verified |

### Now (runbook)

```bash
# 1. Edit plans/taskcards/TC-3869_resume_skip_cached_workers.md
#    Change [ ] → [x] for all 4 acceptance checks
#    Update test count from "4 new" to "5 new"
#    Update updated: date
# 2. Visual inspect — no automated check needed
```

---

## TC-SR-05 — Update `_make_worker_node` docstring + add re_run_count comment

**Status**: Done
**Gap linkage**: SR-04, SR-05
**Role**: Senior engineer. Drop-in, production-ready.

### Context

Two documentation gaps in `graph_builder.py`:

1. **Docstring gap** (SR-04): `_make_worker_node`'s inner `_node()` function has no docstring
   update mentioning the resume skip. The existing docstring says "validate → run → self_review
   → validate → checkpoint" but skip is now the first possible exit path.

2. **Code comment gap** (SR-05): The `re_run_count == 0` guard relies on `_build_resume_state`
   always initializing `re_run_count=0`. This assumption is not stated anywhere in the code.
   If a future caller passes `re_run_count > 0` in the initial state, the guard silently
   disables with no warning. A comment + a single-line defensive log covers this.

### Scope

**Fix 1 — Update inner `_node` docstring** (line 184 in `graph_builder.py`):

```python
# BEFORE
async def _node(state: PipelineGraphState) -> dict[str, Any]:
    """Execute one worker: validate -> run -> self_review -> validate -> checkpoint."""

# AFTER
async def _node(state: PipelineGraphState) -> dict[str, Any]:
    """Execute one worker node in the pipeline graph.

    Exit paths (in order):
    1. Skip — output already in worker_outputs AND re_run_count == 0 (resume mode).
       Populated by _build_resume_state() from {worker}_checkpoint.json files.
    2. Skip — prior worker left errors in state["errors"].
    3. Full execution — validate input → run → self_review → validate output → checkpoint.
    """
```

**Fix 2 — Extend the guard comment** to document the `_build_resume_state` coupling and
the silent-disable risk. Replace the current comment block:

```python
# BEFORE
        # -- skip if output already cached (resume mode, first pass only) -------
        # re_run_count > 0 means evaluate triggered a re-run loop — in that case
        # worker_outputs may still hold a stale first-pass output so we MUST NOT
        # skip: the re-run target (e.g. generate) needs to produce fresh output.
        if state.get("re_run_count", 0) == 0 and worker_name in (state.get("worker_outputs") or {}):

# AFTER
        # -- skip if output already cached (resume mode, first pass only) -------
        # worker_outputs is populated by _build_resume_state() (run_loop.py) from
        # {worker}_checkpoint.json files before the graph executes on resume.
        #
        # Guard: re_run_count == 0 only.
        # When re_run_count > 0, the evaluate→__re_run__→generate loop is active;
        # worker_outputs may hold a stale first-pass output and MUST NOT block the
        # re-run target from producing fresh output.
        #
        # NOTE: _build_resume_state always initialises re_run_count=0 (run_loop.py:177).
        # If a caller sets re_run_count > 0 in the initial state, this guard is silently
        # disabled — all workers will execute regardless of worker_outputs content.
        _cached_output = (state.get("worker_outputs") or {}).get(worker_name)
        if state.get("re_run_count", 0) == 0 and _cached_output is not None:
```

(Note: this also incorporates the SR-01 None-value guard fix — coordinate with TC-SR-01.)

**Allowed paths**:
- `src/launcher/orchestrator/graph_builder.py`

**Forbidden**: Any other file or path. No test changes needed for this taskcard.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 0 failures (docstring changes must not break anything)
- **UI/Web/API**: N/A
- **Tests**: Existing tests unchanged; no new tests required (purely documentation)
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: N/A

### Deliverables

1. **`src/launcher/orchestrator/graph_builder.py`** — `_node` docstring updated; guard comment expanded; variable renamed from inline to `_cached_output` (coordinate with TC-SR-01)

### Hard rules

- Docstring must accurately list all 3 exit paths in order
- Comment must mention `_build_resume_state` by name and file
- No logic changes in this taskcard (pure documentation + variable rename)

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | Future engineers understand skip behavior from the docstring alone |
| Consistency | Docstring and code comment are in sync with TC-SR-01's guard logic |
| Minimality | Only docstring + comment changes; no logic delta |
| Observability | Silent-disable risk is documented inline |

### Now (runbook)

```bash
# 1. Edit graph_builder.py:
#    a. Update _node() docstring (3-exit-path format)
#    b. Expand guard comment (see Scope above)
#    c. Extract guard to _cached_output variable (coordinate with TC-SR-01)
# 2. Verify no logic change:
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_graph_builder.py -v
# 3. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

---

## TC-SR-06 — Add code comment noting __heal_router__ redundancy

**Status**: Done
**Gap linkage**: SR-06
**Role**: Senior engineer. Drop-in, production-ready.

### Context

With TC-3869's skip guard in place, the `__heal_router__` bypass (lines 507–585 of `graph_builder.py`)
is now partially redundant for the `responsible_worker == "generate"` case: the skip guard would also
skip `understand` and `planner` when their checkpoints are in `worker_outputs`. However, the heal
bypass remains more efficient (routing around nodes via conditional edges, avoiding even ctx build).
No code removal is warranted, but a comment is needed so future engineers understand the layering
and don't introduce conflicting logic.

### Scope

**Fix**: Add a brief comment inside the `_heal_router_node` function in `graph_builder.py`,
just before the `if heal_meta.get("responsible_worker") != "generate":` line:

```python
        async def _heal_router_node(state: PipelineGraphState) -> dict[str, Any]:
            """Entry node: load Understand/Planner checkpoints when heal bypass is active.

            This bypass (responsible_worker == 'generate') is an optimization:
            it routes via conditional edges past understand/planner entirely, avoiding
            even their ctx build overhead. Since TC-3869, the skip guard in _node()
            provides the same correctness guarantee for all resume_from values — this
            bypass is now partially redundant but kept for performance on the common
            generate-heal path.
            """
            heal_meta: dict[str, Any] = state.get("heal_metadata") or {}
            if heal_meta.get("responsible_worker") != "generate":
```

**Allowed paths**:
- `src/launcher/orchestrator/graph_builder.py`

**Forbidden**: Any other file or path.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — 0 failures
- **UI/Web/API**: N/A
- **Tests**: No new tests; existing heal bypass tests unchanged
- **Config respected end-to-end**: N/A
- **No mock data in production paths**: N/A

### Deliverables

1. **`src/launcher/orchestrator/graph_builder.py`** — `_heal_router_node` docstring added/updated to explain redundancy and performance rationale

### Hard rules

- No logic changes — purely documentation
- Do not remove or modify any conditional routing code

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | Next engineer understands why both mechanisms exist and which is primary |
| Minimality | Single docstring addition; zero logic delta |
| Consistency | Docstring references TC-3869 by ID for traceability |

### Now (runbook)

```bash
# 1. Edit graph_builder.py:
#    Add docstring to _heal_router_node (see Scope above)
# 2. Visual inspect — confirm no logic lines touched
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
