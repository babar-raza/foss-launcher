---
id: TC-4224
title: "U-1: Add retry before LLM fallback in claim extraction"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [understand, llm, retry, stability]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4224_understand-llm-retry-before-fallback.md
  - src/launcher/workers/understand/extract/_llm.py
  - tests/unit/workers/understand/
evidence_required:
  - reports/TC-4224/evidence.md
---

# Taskcard TC-4224 — U-1: Add retry before LLM fallback in claim extraction

## Objective

Add 2-retry logic before falling back to deterministic extraction in `_extract_claims_llm`. Log exact exception reason on fallback. This eliminates cross-run instability caused by transient LLM failures triggering immediate deterministic fallback.

## Required spec references

- `specs/worker_understand.md` (Section: LLM claim extraction reliability)
- `specs/system_contract.md` (Section: Retry policy)

## Scope

### In scope
- Wrap LLM call in `_extract_claims_llm()` with retry loop (max_attempts=3)
- Retry on empty-result or exception
- Log exact exception reason when fallback is triggered after all retries exhausted
- Unit tests covering retry-then-success and retry-then-fallback scenarios

### Out of scope
- Changes to deterministic extraction logic
- Changes to checkpoint write logic (TC-4225)
- Changes to temperature settings (TC-4226)

## Inputs

- `src/launcher/workers/understand/extract/_llm.py` — current implementation
- LLM client interface in `src/launcher/clients/`

## Outputs

- Modified `_llm.py` with retry loop
- Updated tests in `tests/unit/workers/understand/`

## Allowed paths

- plans/taskcards/TC-4224_understand-llm-retry-before-fallback.md
- src/launcher/workers/understand/extract/_llm.py
- tests/unit/workers/understand/

### Allowed paths rationale
`_llm.py` is the sole location of the LLM claim extraction call. Test directory covers understand unit tests.

## Implementation steps

### Step 1: Read current _extract_claims_llm implementation

Read `src/launcher/workers/understand/extract/_llm.py` to understand the current call structure and fallback trigger.

### Step 2: Add retry loop

In `_extract_claims_llm()`, wrap the LLM call in a `for attempt in range(max_attempts)` loop with `max_attempts=3`. On empty result or exception, log `f"LLM claim extraction attempt {attempt+1} failed: {exc}"` and continue. After exhausting retries, log `f"LLM claim extraction falling back to deterministic after {max_attempts} attempts: {last_exc}"` before triggering fallback.

### Step 3: Write unit tests

Add tests in `tests/unit/workers/understand/` covering:
1. First attempt fails, second succeeds — no fallback triggered
2. All 3 attempts fail — fallback triggered with logged reason
3. First attempt returns empty list — treated as failure, retry occurs

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -q
```

## Failure modes

### Failure mode 1: Retry loop hides permanent errors

**Detection**: Logs show 3 identical exceptions followed by fallback; fallback_rate stays > 0 after fix.
**Resolution**: Check if the LLM endpoint is reachable; verify API key is set. The retry loop only masks transient failures — permanent errors will still exhaust retries and fall back.
**Gate**: understand checkpoint fallback_rate field

### Failure mode 2: Retry adds excessive latency

**Detection**: Understand phase wall-clock time increases by > 3x baseline.
**Resolution**: Verify `max_attempts=3` with no sleep between retries. Add exponential backoff only if endpoint explicitly rate-limits.
**Gate**: Pipeline run time budget

### Failure mode 3: Unit tests mock LLM incorrectly

**Detection**: Tests pass but production still falls back on first failure.
**Resolution**: Ensure mock raises the same exception type the real client raises. Check client exception hierarchy.
**Gate**: Test coverage on retry path

## Task-specific review checklist

1. [ ] `_extract_claims_llm()` has `max_attempts=3` loop — verified by code read
2. [ ] Fallback is only triggered after all retries exhausted — not on first failure
3. [ ] Exception message logged verbatim on each retry and on final fallback
4. [ ] Unit test: retry-then-success path covered
5. [ ] Unit test: retry-then-fallback path covered
6. [ ] Unit test: empty-result treated as failure and retried
7. [ ] Docstrings updated for `_extract_claims_llm` to document retry behavior
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. `src/launcher/workers/understand/extract/_llm.py` — retry logic added
2. `tests/unit/workers/understand/` — 3 new test cases
3. `reports/TC-4224/evidence.md` — test output confirming retry paths

## Acceptance checks

1. [ ] All new tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v`
2. [ ] `_extract_claims_llm` retries 3 times before fallback — confirmed by log output
3. [ ] fallback_rate = 0.0 in understand checkpoint on clean pilot run

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: understand checkpoint fallback_rate PASS
- [ ] Evidence captured: reports/TC-4224/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v
```

**Expected results**:
- All retry-path tests pass
- No regressions in existing understand tests

## Integration boundary proven

**Upstream**: LLM client (`src/launcher/clients/`) — provides raw LLM response
**Downstream**: `_entry.py` claim pipeline — receives extracted claims list
**Contract**: `_extract_claims_llm` returns `list[Claim]`; empty list triggers deterministic fallback (after retries)
