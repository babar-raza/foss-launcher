# TC-3778 Linker Hardening Plan

## Context

Self-review of the LH-04/LH-05 execution identified 5 remaining gaps in the
linker integration. None are blockers, but 2 are medium-severity (robustness
bug and missing test coverage). This plan converts each into an executable
taskcard.

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| G-09 | `infer_section` returns `None` when `frontmatter={"section": None}` | **Medium** | LHH-01 |
| G-10 | No test for `linker_completed` event emission in GenerateWorker | **Medium** | LHH-02 |
| G-11 | Linker imports split: `infer_section` at module level, `link_pages`/`load_linker_config` inline in `run()` | **Low** | LHH-03 |
| G-12 | No per-page debug logging in `link_pages` (LH-05 spec included it) | **Low** | LHH-03 |
| G-13 | `linker_completed` event type has no schema definition in `specs/schemas/` | **Low** | LHH-04 |

---

## Taskcard LHH-01 — Guard infer_section against None section value

**Status:** Done
**Gap linkage:** G-09

### Role
Senior engineer. Drop-in, production-ready fix.

### Scope

**Fix:**
`infer_section` line 567 currently returns `frontmatter.get("section", "docs")`.
If frontmatter is `{"section": None}`, this returns `None` — breaking downstream
code that expects a string. Change to `frontmatter.get("section") or "docs"`.

**Allowed paths:**
- `src/launcher/shared/linker.py`
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New test `test_none_section_in_frontmatter` verifies `infer_section("overview", {"section": None}) == "docs"`.
- **Tests:** Existing `TestInferSection` tests still pass.
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestInferSection -v`
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

### Deliverables

1. One-line fix in `linker.py:567`: `frontmatter.get("section") or "docs"`
2. One new test in `TestInferSection`: `test_none_section_in_frontmatter`

### Hard rules

- Keep public signature unchanged.
- No new deps.
- Keep code/docs/tests in sync.
- Deterministic (pure function, no I/O).

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Correctness | None value handled, returns "docs" string always |
| Robustness | All falsy section values (None, "", 0) produce valid string |
| Testability | Dedicated test for the None case |

### Now (runbook)

```bash
# 1. Edit linker.py line 567: frontmatter.get("section") or "docs"
# 2. Add test_none_section_in_frontmatter to TestInferSection
# 3. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py::TestInferSection -v
```

---

## Taskcard LHH-02 — Add test for linker_completed event emission

**Status:** Done
**Gap linkage:** G-10

### Role
Senior engineer. Drop-in, production-ready test.

### Scope

**Fix:**
The `linker_completed` event emitted from `GenerateWorker.run()` has no test
coverage. Add a test that runs `link_pages` with a mock context and verifies
the event is emitted with the correct data shape from the worker level.

Since testing `GenerateWorker.run()` end-to-end requires heavy mocking
(understanding checkpoint, LLM, etc.), the cleaner approach is to test the
event emission pattern in isolation: verify the event data dict has the
expected keys and types given known cross_links.

**Allowed paths:**
- `tests/test_linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** New test `test_linker_event_data_shape` verifies that given a list
  of CrossLinks with known link_types, the event data dict construction
  produces correct `cross_links`, `see_also`, `toc_child` counts.
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k event`
- **No mock data in production paths:** Test uses only test fixtures.
- **No network in offline tests:** No LLM or network calls.

### Deliverables

1. New test class `TestLinkerEventData` in `tests/test_linker.py` with:
   - `test_event_data_shape`: constructs CrossLink list, computes event dict,
     verifies counts match.
   - `test_event_data_empty`: empty cross_links list produces all-zero counts.

### Hard rules

- No network calls.
- Deterministic (PYTHONHASHSEED=0).
- No new deps.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Test Quality | Event data shape tested for both populated and empty cases |
| Coverage | The `linker_completed` code path is now exercised in tests |
| Correctness | Count assertions match expected values exactly |

### Now (runbook)

```bash
# 1. Add TestLinkerEventData class to test_linker.py
# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v -k event
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/test_linker.py -v
```

---

## Taskcard LHH-03 — Consolidate linker imports + add per-page debug logging

**Status:** Done
**Gap linkage:** G-11, G-12

### Role
Senior engineer. Drop-in cleanup + observability.

### Scope

**Fix (G-11):**
In `worker.py`, `infer_section` is imported at module level (line 38) but
`link_pages` and `load_linker_config` are imported inline inside `run()`
(line 101). Move all linker imports to module level for consistency.

**Fix (G-12):**
In `linker.py:link_pages()`, add `logger.debug` per page after scoring:
```python
logger.debug("[Linker] %s: %d candidate links", pid, len(page_links))
```

**Allowed paths:**
- `src/launcher/workers/generate/worker.py`
- `src/launcher/shared/linker.py`

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes (no behavior change).
- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q`
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** N/A

### Deliverables

1. `worker.py`: move `link_pages` and `load_linker_config` imports to module
   level alongside `infer_section`. Delete inline import on line 101.
2. `linker.py`: add `logger.debug("[Linker] %s: %d candidate links", pid, len(page_links))`
   after line 482 in `link_pages()`.

### Hard rules

- No behavior change.
- No new deps.
- Import order: alphabetical within `launcher.shared.linker`.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Maintainability | All linker imports in one place, alphabetically ordered |
| Observability | Per-page link counts visible at DEBUG level |
| Minimality | Two small edits, zero behavior change |

### Now (runbook)

```bash
# 1. Move inline imports to module level in worker.py
# 2. Add logger.debug in linker.py link_pages()
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## Taskcard LHH-04 — Add linker_completed event schema

**Status:** Done
**Gap linkage:** G-13

### Role
Senior engineer. Drop-in schema addition.

### Scope

**Fix:**
The `linker_completed` event type emitted by GenerateWorker has no schema
definition. If the pipeline validates events against known schemas, this
event would be silently dropped or fail validation.

Check if event schemas exist in `specs/schemas/` for other event types
(e.g., `worker_started`, `worker_completed`). If yes, add a matching
`linker_completed` schema. If no event schema validation exists, document
the event shape in a comment and close as "no schema infrastructure."

**Allowed paths:**
- `specs/schemas/` (if event schemas exist)
- `src/launcher/workers/generate/worker.py` (comment only, if no schema infra)

**Forbidden:** any other file/path

### Acceptance checks

- **Tests:** Full suite passes.
- **CLI:** If schema added, validate it with `jsonschema` or equivalent.
- **Config respected end-to-end:** Event shape matches schema.
- **No mock data in production paths:** N/A

### Deliverables

1. If event schemas exist: new schema file for `linker_completed` with
   properties `cross_links` (int), `see_also` (int), `toc_child` (int).
2. If no event schema infra: close with comment in worker.py documenting
   the event shape. Update this taskcard status to "Done (no schema infra)".

### Hard rules

- Schema must be backward compatible (all fields have defaults or are required).
- No new deps.
- Match existing event schema patterns exactly.

### Review dimensions (5/5 targets)

| Dimension | 5/5 means |
|-----------|-----------|
| Docs/Specs | Event shape formally documented or schema-validated |
| Compatibility | Schema is additive, backward compatible |
| Integration | Matches existing event schema patterns |

### Now (runbook)

```bash
# 1. Check if event schemas exist
ls specs/schemas/*event* 2>/dev/null
grep -r "event_schema" src/launcher/ 2>/dev/null | head -5
# 2. If yes: create schema file. If no: add comment in worker.py
# 3. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q
```

---

## Execution Order

Recommended sequence (all independent, can parallelize):

```
LHH-01 (None guard)           <- 1-line fix, immediate
LHH-02 (event test)           <- independent
LHH-03 (imports + debug log)  <- independent
LHH-04 (event schema)         <- requires investigation first
```

Parallelizable: {LHH-01, LHH-02, LHH-03} then {LHH-04}.
