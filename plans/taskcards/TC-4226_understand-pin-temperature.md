---
id: TC-4226
title: "U-3: Pin temperature=0.0 for claim extraction LLM call"
status: Done
priority: Medium
owner: "Agent-B"
updated: "2026-03-12"
tags: [understand, llm, temperature, determinism]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4226_understand-pin-temperature.md
  - src/launcher/workers/understand/extract/_llm.py
evidence_required:
  - reports/TC-4226/evidence.md
---

# Taskcard TC-4226 — U-3: Pin temperature=0.0 for claim extraction LLM call

## Objective

Ensure the claim extraction LLM call in `_extract_claims_llm` always passes `temperature=0.0` explicitly, regardless of client defaults or config overrides. This eliminates cross-run non-determinism in claim content.

## Required spec references

- `specs/worker_understand.md` (Section: LLM call parameters)
- `CLAUDE.md` (Section: LLM Configuration — Temperature: 0.0 (deterministic))

## Scope

### In scope
- Verify and explicitly set `temperature=0.0` in the LLM call kwargs in `_llm.py`
- Add a comment explaining why temperature is pinned

### Out of scope
- Changing temperature for other LLM calls (generate, evaluate)
- Config-level temperature changes

## Inputs

- `src/launcher/workers/understand/extract/_llm.py` — LLM call site

## Outputs

- Modified `_llm.py` with explicit `temperature=0.0`

## Allowed paths

- plans/taskcards/TC-4226_understand-pin-temperature.md
- src/launcher/workers/understand/extract/_llm.py

### Allowed paths rationale
Single file change: the LLM call site in claim extraction.

## Implementation steps

### Step 1: Read _llm.py to find call site

Read the file and locate the LLM client invocation in `_extract_claims_llm`.

### Step 2: Add explicit temperature

In the LLM call kwargs, add or override `temperature=0.0`. Example:
```python
response = await client.complete(
    messages=messages,
    temperature=0.0,  # pinned: claim extraction must be deterministic
    **other_kwargs,
)
```

### Step 3: Verify no other call sites in same file use non-zero temperature

Search for any other LLM calls in `_llm.py` and confirm they also use temperature=0.0.

## Failure modes

### Failure mode 1: Client ignores temperature kwarg

**Detection**: Cross-run claim variation persists despite explicit temperature=0.0.
**Resolution**: Check client implementation to verify temperature kwarg is forwarded to the API. Add assertion in test.
**Gate**: Cross-run determinism check

### Failure mode 2: temperature kwarg conflicts with existing kwarg

**Detection**: `TypeError: duplicate keyword argument` at runtime.
**Resolution**: Remove temperature from `**other_kwargs` before adding explicit `temperature=0.0`, or pass it as a positional-aware override.
**Gate**: Unit test that calls the function

### Failure mode 3: Config-level temperature overrides pinned value

**Detection**: LLM request logs show temperature != 0.0 despite code change.
**Resolution**: Verify client merges kwargs with explicit value taking precedence over config default.
**Gate**: LLM request telemetry

## Task-specific review checklist

1. [ ] `temperature=0.0` explicitly present in LLM call kwargs
2. [ ] Comment explains why temperature is pinned
3. [ ] No other LLM calls in `_llm.py` use non-zero temperature
4. [ ] Code read confirms kwarg is forwarded to API client
5. [ ] No duplicate `temperature` kwarg conflict possible
6. [ ] Existing tests still pass after change
7. [ ] Docstrings updated for modified functions
8. [ ] Spec file updated if worker behavior changed (confirmed: CLAUDE.md already specifies 0.0)
9. [ ] Schema `"description"` fields not applicable (no schema change)
10. [ ] Checked `docs/README.md` ownership map — no trigger event
11. [ ] No new docs/guides/ file added

## Deliverables

1. `src/launcher/workers/understand/extract/_llm.py` — explicit temperature=0.0
2. `reports/TC-4226/evidence.md` — diff showing temperature pin

## Acceptance checks

1. [ ] `temperature=0.0` present in `_llm.py` LLM call — verified by grep
2. [ ] All existing understand tests pass without regression
3. [ ] Cross-run claim extraction produces identical output (verified by running twice on same input)

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: temperature=0.0 in call site PASS
- [ ] Evidence captured: reports/TC-4226/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v
```

**Expected results**:
- All existing tests pass
- No regressions

## Integration boundary proven

**Upstream**: LLM client — receives temperature parameter
**Downstream**: Claim list returned by `_extract_claims_llm`
**Contract**: temperature=0.0 guaranteed for every claim extraction LLM call
