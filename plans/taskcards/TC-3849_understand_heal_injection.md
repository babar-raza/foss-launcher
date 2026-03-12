---
id: TC-3849
title: "Understand Worker Heal Directive Injection (H3.2)"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [heal, understand]
depends_on: [TC-3841]
allowed_paths:
  - plans/taskcards/TC-3849_understand_heal_injection.md
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/test_understand_heal.py
evidence_required:
  - reports/TC-3849/evidence.md
---

# Taskcard TC-3849 — Understand Worker Heal Directive Injection (H3.2)

## Objective

Add heal directive reading to `UnderstandWorker.run()` so that when the heal CLI
re-runs with `re_run_count > 0`, the understand worker tightens its extraction
focus based on `heal_metadata.page_directives`.

## Required spec references

- `specs/heal.md` (heal directive injection contract)

## Scope

### In scope
- Read `heal_metadata = context.heal_metadata` at start of `run()`
- If `heal_metadata.get("re_run_count", 0) > 0`, log a heal-mode notice
- Pass `focused_roles = heal_metadata.get("focus_page_roles", [])` to `run_scout()`
  if available (as a hint to tighten extraction — graceful if run_scout ignores it)
- Emit `understand_heal_mode` event when heal_metadata is non-empty
- Guard with `try/except` so heal metadata never crashes normal runs

### Out of scope
- Modifying `run_scout()` itself to honor focused_roles (deferred — run_scout may not accept it yet)
- Claim filtering logic — that's in the generate worker

## Inputs

- `src/launcher/workers/understand/worker.py` (279 lines)
- `context.heal_metadata` dict from WorkerContext (TC-3841 Done)

## Outputs

- `understand_heal_mode` event emitted when re_run_count > 0
- `heal_directives` field in UnderstandingBundle event metadata

## Allowed paths

- plans/taskcards/TC-3849_understand_heal_injection.md
- src/launcher/workers/understand/worker.py
- tests/unit/workers/test_understand_heal.py

### Allowed paths rationale

Only understand worker modified; one new test file.

## Implementation steps

### Step 1: Read heal_metadata at start of run()

At the beginning of `run()`, after resolving `product`:
```python
# Heal mode: read directives from heal_metadata if present
heal_metadata: dict = context.heal_metadata or {}
re_run_count: int = heal_metadata.get("re_run_count", 0) or 0
if re_run_count > 0:
    context.log.info(
        "[Understand] Heal mode (re_run=%d): tightening extraction focus",
        re_run_count,
    )
    context.emit_event(
        "understand_heal_mode",
        {
            "re_run_count": re_run_count,
            "focus_page_roles": heal_metadata.get("focus_page_roles", []),
            "page_directives": heal_metadata.get("page_directives", []),
        },
        worker=self.name,
    )
```

### Step 2: Pass focus_page_roles hint (optional)

After reading heal_metadata, if `focus_page_roles` is present, log it:
```python
focus_page_roles = heal_metadata.get("focus_page_roles", [])
if focus_page_roles:
    context.log.info(
        "[Understand] Heal focus: restricting to page roles %s", focus_page_roles
    )
```

The `run_scout()` call is not modified (run_scout doesn't accept focused_roles yet).
This is a preparatory injection point; the actual focusing happens in future TCs.

### Step 3: Add tests

`tests/unit/workers/test_understand_heal.py`:
- heal_metadata={} → no `understand_heal_mode` event emitted
- heal_metadata={"re_run_count": 1} → `understand_heal_mode` event emitted with re_run_count=1
- heal_metadata={"re_run_count": 2, "focus_page_roles": ["workflow_page"]} → event has focus_page_roles
- re_run_count=0 → treated as normal run, no event
- Exception in heal_metadata reading → no crash (try/except guard)

## Failure modes

### Failure mode 1: context.heal_metadata is None (unexpected)

**Detection**: `AttributeError` or `NoneType` error when accessing heal_metadata
**Resolution**: Use `context.heal_metadata or {}` — coerces None to empty dict
**Gate**: Unit test with heal_metadata=None

### Failure mode 2: run_scout() rejects unexpected kwargs

**Detection**: `TypeError: run_scout() got unexpected keyword argument 'focus_page_roles'`
**Resolution**: Do NOT pass focus_page_roles to run_scout() — only log it
**Gate**: Unit test verifying run_scout is called without focus_page_roles kwarg

### Failure mode 3: emit_event fails in test environment

**Detection**: AttributeError when calling context.emit_event
**Resolution**: Wrap in try/except; use mock WorkerContext in tests
**Gate**: Unit test using mock context

## Task-specific review checklist

1. [ ] `understand_heal_mode` event emitted only when re_run_count > 0
2. [ ] `understand_heal_mode` event has keys: re_run_count, focus_page_roles, page_directives
3. [ ] Normal run (heal_metadata={}) produces no `understand_heal_mode` event
4. [ ] No crash when heal_metadata is None or missing keys
5. [ ] run_scout() signature unchanged (no extra kwargs added)
6. [ ] All 5 tests pass

## Deliverables

1. `src/launcher/workers/understand/worker.py` — heal_metadata reading + event emission
2. `tests/unit/workers/test_understand_heal.py` — 5 test cases
3. `reports/TC-3849/evidence.md` — actual test output

## Acceptance checks

1. [x] `pytest tests/unit/workers/test_understand_heal.py -v` — 5/5 PASS
2. [x] `understand_heal_mode` event emitted for re_run_count > 0
3. [x] `pytest tests/ -q` — 0 failures (2483 passed)

## Self-review

### Verification results
- [x] Tests: 5/5 PASS
- [x] Validation: event emitted in heal mode, silent in normal mode
- [x] Evidence file: `reports/TC-3849/evidence.md`
- [x] Full suite: 2483 passed, 0 failed

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand_heal.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```

**Expected results**:
- 5 understand heal tests pass
- Full suite: 0 failures

## Integration boundary proven

**Upstream**: `context.heal_metadata` from WorkerContext (TC-3841)
**Downstream**: Heal CLI (TC-3851) sets heal_metadata before re-running understand worker
**Contract**: `understand_heal_mode` event has `{re_run_count: int, focus_page_roles: list, page_directives: list}`
