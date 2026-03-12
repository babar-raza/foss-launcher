# Healing Plan: SR-3869 — Resume Validation Gap (Secondary Finding)

**Source**: Secondary gap identified during TC-3869 broader investigation of resume capabilities
**Priority**: LOW-MEDIUM — silent degradation risk; pipeline continues with a warning but
  invalid `resume_from` values produce confusing behavior rather than a clear error

---

## Gap Table

| Gap ID | Description | Taskcard |
|--------|-------------|----------|
| SR-07 | `resume_from` is never validated against known pipeline workers | TC-SR-07 |

---

## TC-SR-07 — Validate `resume_from` against known pipeline worker names

**Status**: Done
**Gap linkage**: SR-07
**Role**: Senior engineer. Drop-in, production-ready.

### Context

`execute_run()` in `run_loop.py` accepts `resume_from: str = ""` but never validates that it names
a worker that exists in the pipeline. `_build_resume_state()` silently produces an empty
`worker_outputs` dict if `resume_from` doesn't match any worker — then emits only a WARNING log
(lines 164–169). This means:

- `resume_from="nonexistent"` → no checkpoints loaded, no error → all workers re-run silently
- `resume_from="generate "` (trailing space) → same silent degradation
- `resume_from="Generate"` (wrong case) → same

The fix adds a validation step in `execute_run()` after the pipeline topology is loaded but before
`_build_resume_state()` is called. The known worker list comes from the compiled topology (already
available at that point in the function) rather than from `_build_resume_state`'s hardcoded list,
so it stays config-driven.

### Scope

**Fix**: In `src/launcher/orchestrator/run_loop.py`, inside `execute_run()`, after the graph is
compiled (`compiled_graph = build_pipeline(...)`) and before the `if resume_from:` block, add:

```python
    # -- Validate resume_from against known pipeline workers ----------------
    if resume_from:
        _known_workers = ["intake", "understand", "planner", "generate", "evaluate", "publish"]
        if resume_from not in _known_workers:
            raise ValueError(
                f"resume_from='{resume_from}' is not a known pipeline worker. "
                f"Valid values: {_known_workers}"
            )
```

**Placement note**: `_known_workers` should ideally come from the topology (not a hardcoded list).
If `build_pipeline` exposes worker names, prefer:
```python
        # Prefer deriving from topology if accessible:
        # _known_workers = [e.name for e in topology.workers]
```
Check whether `PipelineTopology` or `build_pipeline` returns parseable worker names; if yes,
use that. If not, the hardcoded list is acceptable since it matches `_build_resume_state`'s list.

**Allowed paths**:
- `src/launcher/orchestrator/run_loop.py`
- `tests/unit/orchestrator/test_run_loop.py` (existing file)

**Forbidden**: Any other file or path. Do not modify `_build_resume_state` itself.

### Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_loop.py -v` — 0 failures
- **UI/Web/API**: N/A
- **Tests**:
  - New test: `resume_from="nonexistent"` raises `ValueError` with clear message
  - New test: `resume_from="generate"` (valid) does NOT raise
  - New test: `resume_from="Generate"` (wrong case) raises `ValueError`
  - Existing resume tests must still pass
- **Config respected end-to-end**: `--resume-from` CLI flag passes through to `execute_run`; invalid value must produce a clear CLI error not a silent degradation
- **No mock data in production paths**: validation reads from the same source as `_build_resume_state`

### Deliverables

1. **`src/launcher/orchestrator/run_loop.py`** — `ValueError` raised for unknown `resume_from`
2. **`tests/unit/orchestrator/test_run_loop.py`** — 3 new test cases covering invalid, valid, and case-sensitive scenarios

### Hard rules

- `ValueError` message must include the invalid value AND the list of valid values
- Do not raise for `resume_from = ""` (empty string = no resume; existing behavior)
- Validation must fire BEFORE `_build_resume_state` is called (fail fast)
- No new deps introduced
- Keep existing call sites in `heal.py` and `cli/main.py` working — they already pass valid names

### Review dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Robustness | Any invalid `resume_from` raises immediately with an actionable message |
| Correctness | Valid values pass; empty string passes; invalid values fail |
| Testability | 3 tests cover the invalid/valid/case-sensitive triad |
| Minimality | ~6 lines of validation + 3 tests; no refactoring beyond the check |
| Observability | `ValueError` message includes the full valid list — operator can self-diagnose |

### Now (runbook)

```bash
# 1. Read run_loop.py to find exact insertion point (after build_pipeline, before if resume_from:)
# 2. Add validation block (see Scope above)
# 3. Check whether topology worker names are accessible — if yes, derive dynamically
# 4. Add tests to test_run_loop.py
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/orchestrator/test_run_loop.py -v
# 5. Verify heal.py and cli/main.py pass valid names (no call site changes needed)
# 6. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

### Coordination notes

- This taskcard is independent of TC-SR-01 through TC-SR-06; can be executed in any order
- The hardcoded `_known_workers` list duplicates `_build_resume_state`'s list — if a new worker
  is added to the pipeline, BOTH lists must be updated. Consider extracting to a module-level
  constant to avoid drift. Document this in a comment at the definition site.
