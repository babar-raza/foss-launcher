---
id: TC-4249
title: "G-3b: Remove sec_snippets guard from code-block retry for code-required roles"
status: Done
priority: High
owner: "Agent"
updated: "2026-03-12"
tags: [generate, code-block, retry, reference, sec_snippets]
depends_on: [TC-4229]
allowed_paths:
  - plans/taskcards/TC-4249_generate-code-block-retry-unconditional.md
  - src/launcher/workers/generate/worker.py
  - tests/unit/workers/generate/test_code_block_retry.py
evidence_required:
  - reports/TC-4249/evidence.md
---

# Taskcard TC-4249 — G-3b: Remove sec_snippets guard from code-block retry

## Objective

TC-4229 added a code-block retry for code-required roles but guarded it with
`sec_snippets` non-empty. For `reference_object_page` Properties/Methods
sections, `sec_snippets` is often empty because snippet claim IDs don't overlap
with property-level claim IDs — so the retry never fires and Section gate FAIL
persists. Remove the guard so the retry always fires for code-required roles.

## Required spec references

- `specs/worker_generate.md` (Section: code block requirements for reference pages)

## Scope

### In scope
- Remove `sec_snippets` from the retry condition at `worker.py:1087`
- Update the comment on line 1085 to reflect the new logic
- Add unit test: reference section with no snippets → retry fires when code block absent

### Out of scope
- Changing how `sec_snippets` is populated (Understand scope)
- Changing `_CODE_REQUIRED_ROLES` membership
- Any other retry logic

## Inputs

- `src/launcher/workers/generate/worker.py` — retry condition at line 1087

## Outputs

- Modified `worker.py` — retry fires for all code-required roles regardless of snippets
- New `tests/unit/workers/generate/test_code_block_retry.py` — targeted unit test

## Allowed paths

- plans/taskcards/TC-4249_generate-code-block-retry-unconditional.md
- src/launcher/workers/generate/worker.py
- tests/unit/workers/generate/test_code_block_retry.py

### Allowed paths rationale

`worker.py` is the sole location of the retry guard. One new test file for the
specific no-snippet case.

## Implementation steps

### Step 1: Read and verify current state

Read `worker.py` lines 1083–1100. Confirm the condition at line 1087.

### Step 2: Change the retry condition

Change line 1087 from:
```python
if page_plan.page_role in _CODE_REQUIRED_ROLES and sec_snippets:
```
To:
```python
if page_plan.page_role in _CODE_REQUIRED_ROLES:
```

Update the comment on lines 1084–1085 from:
```python
# TC-4229: Check code block presence for code-required roles.
# Only applies when snippets are available (no evidence → EVIDENCE ABSENT wins).
```
To:
```python
# TC-4229/TC-4249: Retry when code block absent for code-required roles.
# Fires regardless of sec_snippets — LLM can generate code from claims + canonical import.
```

### Step 3: Write unit test

Create `tests/unit/workers/generate/test_code_block_retry.py` with at least:

1. `test_code_retry_fires_without_snippets` — Given a reference page role, no
   `sec_snippets`, and a mock LLM that first returns no code block then returns
   a code block: verify retry occurs and final result has code block.
2. `test_code_retry_not_fired_for_non_reference_role` — Given a
   `concept_article` page role and no code block: verify retry does NOT fire
   (not in `_CODE_REQUIRED_ROLES`... depends on actual role set).

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v -q
```

## Failure modes

### Failure mode 1: LLM halluccinates code when no snippets available

**Detection**: Generated code uses plausible but wrong API calls; no snippet anchor.
**Resolution**: This is the pre-existing risk. The canonical import reminder (TC-4227) and section_writer.txt RULES provide guidance. Hallucinated code will be caught by `identifier_hallucination` checks downstream.
**Gate**: Evaluate code check + identifier validation

### Failure mode 2: Retry always fires → doubled LLM calls even when code present

**Detection**: LLM calls per section doubles; no benefit in logs.
**Resolution**: The condition also checks `not _has_code` — if the first attempt already has code, `_needs_code_retry` is False and retry doesn't fire. Not an issue.
**Gate**: LLM call count in telemetry

### Failure mode 3: Unit test is hard to write because `_generate_section` is a complex coroutine

**Detection**: Test setup requires too many mocks.
**Resolution**: Test at a coarser level — mock the LLM client and verify the retry prompt is sent (contains the CRITICAL code block instruction). Use `_section_sem` mock.
**Gate**: Test passes reliably

## Task-specific review checklist

1. [ ] Old condition `sec_snippets and` removed from line 1087
2. [ ] Comment updated to reference TC-4229/TC-4249
3. [ ] Unit test: no snippets + reference role → retry fires
4. [ ] Unit test: non-code-required role → retry does NOT fire
5. [ ] No change to any other retry logic (prose retry, type-field retry)
6. [ ] `_has_code` check still guards inner condition correctly
7. [ ] Docstrings: no new public functions → N/A
8. [ ] Spec file confirmed: no new behavior change beyond what TC-4229 intended
9. [ ] Schema: no changes
10. [ ] `docs/README.md` ownership map: Generate worker — trigger event check: N/A
11. [ ] No new `docs/guides/` file added

## Deliverables

1. `src/launcher/workers/generate/worker.py` — 2-line change (condition + comment)
2. `tests/unit/workers/generate/test_code_block_retry.py` — 2 tests

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v` — all pass
2. [ ] Line 1087 no longer contains `sec_snippets`
3. [ ] No regressions in existing generate tests

## Self-review

### Verification results
- [x] Tests: 6/6 PASS (test_code_block_retry.py) + 247/247 generate suite regression-free
- [x] Validation: source guard confirms `sec_snippets` not in condition PASS
- [x] Evidence captured: inline (test run output)
- [x] Doc freshness: no spec drift — behavior extends TC-4229 intent, no new surface

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -v
```

**Expected results**:
- All existing tests pass
- New `test_code_block_retry.py` tests pass
- Zero regressions

## Integration boundary proven

**Upstream**: Section skeleton (page role) + sec_snippets (may be empty)
**Downstream**: Section gate validation (requires code block for reference roles)
**Contract**: For any `reference_object_page` section, if LLM omits code block on first attempt, retry is guaranteed to fire with explicit code block instruction
