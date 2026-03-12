---
id: SNP-03
title: "Restore snippet_extraction_complete telemetry event in _entry.py"
status: Done
priority: Normal
owner: agent
updated: "2026-03-11"
tags: [understand, snippets, telemetry, observability, TC-4062]
depends_on: [TC-4062, SNP-02]
allowed_paths:
  - plans/healing/SNP-03-telemetry-restoration.md
  - src/launcher/workers/understand/extract/_entry.py
evidence_required:
  - reports/SNP-03/evidence.md
---

# SNP-03 — Restore `snippet_extraction_complete` telemetry event in `_entry.py`

## Objective

TC-4062 removed `_generate_synthetic_snippets()`. Along with it, the `synthetic_snippets_generated`
event emission was deleted. No replacement event was added for the new extraction-only path.
Downstream telemetry consumers (dashboards, alerts) that tracked snippet counts now have a gap.
This taskcard adds a `snippet_extraction_complete` event that captures the same signals with
the corrected semantics (no synthetic count — only extracted + dedup_skipped).

## Required spec references

- `specs/state_events_checkpoints.md` (event schema, `context.emit_event` contract)
- `specs/worker_understand.md` (Phase B.3: snippet extraction telemetry)

## Scope

### In scope
- Add `context.emit_event("snippet_extraction_complete", {...}, worker="understand")` call
  in `run_extract()` after the `_extract_snippets()` call, replacing the deleted event
- Payload fields: `extracted: int`, `dedup_skipped: int` (from SNP-02 counter if available,
  otherwise compute from `len(snippets)` only)
- If `dedup_skipped` is not yet available from `_snippets.py` (SNP-02 not done), emit with
  `extracted: len(snippets)` only and add a TODO comment for SNP-02 wiring

### Out of scope
- Changing the event schema in `specs/schemas/event_schemas/`
- Adding a new event type to the event schema (reuse `snippet_extraction_complete` if it
  already exists in the schema, or emit as untyped dict if not)
- Dashboard or alert changes

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` (current state post-TC-4062)
- `specs/state_events_checkpoints.md` (event emission contract)

## Outputs

- `_entry.py` with `snippet_extraction_complete` event emitted after `_extract_snippets()`

## Allowed paths

- plans/healing/SNP-03-telemetry-restoration.md
- src/launcher/workers/understand/extract/_entry.py

### Allowed paths rationale
Only `_entry.py` needs the event emission call restored.

## Implementation steps

### Step 1: Locate the current snippet extraction section in `_entry.py`

Find the block that reads:
```python
snippets = _extract_snippets(repo_dir, repo_info, product, api_surface, claims)
# TC-4062: Synthetic snippet generation removed ...
```

### Step 2: Add telemetry emission after the extraction call

Add immediately after the `_extract_snippets(...)` call:
```python
context.emit_event(
    "snippet_extraction_complete",
    {
        "extracted": len(snippets),
        # SNP-02: dedup_skipped will be wired here once _snippets.py exposes the counter
    },
    worker="understand",
)
```

If `context` is not available at that point in `run_extract()`, use whatever event-emission
mechanism the surrounding code uses (check existing `context.emit_event` call sites in the file).

### Step 3: Verify `emit_event` signature

Read the `context.emit_event` call sites in `_entry.py` to confirm the exact signature.
Match the pattern of existing calls (positional vs keyword args, `worker=` parameter).

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -q
```

## Failure modes

### Failure mode 1: `context` not in scope at the emit_event call site

**Detection**: `NameError: name 'context' is not defined`
**Resolution**: Check how `context` is passed into `run_extract()`. If it is a parameter,
confirm it is forwarded into the extraction section. If it is a module-level singleton,
import it.
**Gate**: Module load + unit tests

### Failure mode 2: `snippet_extraction_complete` event type not in schema

**Detection**: Schema validation rejects the emitted event
**Resolution**: Check `specs/schemas/event_schemas/` for `snippet_extraction_complete`.
If absent, emit without schema validation (use raw dict) OR add the event type to the schema
in a separate taskcard (scope creep — defer to a new taskcard).
**Gate**: Schema validation in `io/schema_validation.py`

### Failure mode 3: Duplicate emission (event fired twice per extraction)

**Detection**: Event log contains two `snippet_extraction_complete` entries per run
**Resolution**: Ensure the emit is outside any loop; confirm it is called exactly once
after `_extract_snippets()` returns
**Gate**: Integration test or log inspection

## Task-specific review checklist

1. [ ] `context.emit_event("snippet_extraction_complete", ...)` present in `_entry.py`
2. [ ] Payload contains at minimum `extracted: len(snippets)`
3. [ ] Event is emitted once per `run_extract()` invocation, not per snippet
4. [ ] `worker="understand"` parameter matches existing emit_event call pattern
5. [ ] TODO comment added for `dedup_skipped` wiring if SNP-02 not yet merged
6. [ ] No schema changes attempted in this taskcard (defer to separate TC if needed)
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — no guide trigger from telemetry-only change
11. [ ] N/A — no new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/understand/extract/_entry.py` with `snippet_extraction_complete` event
2. `reports/SNP-03/evidence.md` with grep showing the event emission

## Acceptance checks

1. [ ] `grep "snippet_extraction_complete" src/launcher/workers/understand/extract/_entry.py` → matches
2. [ ] `grep "extracted.*len(snippets)" src/launcher/workers/understand/extract/_entry.py` → matches
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/ -x -q` passes

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Evidence captured: reports/SNP-03/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -q
```

**Expected results**:
- All unit tests pass
- `snippet_extraction_complete` event visible in event log during integration test run

## Integration boundary proven

**Upstream**: `_extract_snippets()` returns `list[Snippet]`
**Downstream**: Event log consumer / telemetry dashboard
**Contract**: `snippet_extraction_complete` event with `extracted: int` payload emitted once per `run_extract()` call
