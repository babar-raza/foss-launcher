---
id: TC-HO-01
title: "Limitations Contradiction Check — detect affirmed unsupported features"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [evaluate, wave4a, understand-hardening]
depends_on: [TC-HO-03]
allowed_paths:
  - plans/taskcards/TC-HO-01_limitations-contradiction-check.md
  - src/launcher/workers/evaluate/checks/limitations.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/evaluate/checks/__init__.py
  - tests/unit/workers/evaluate/checks/test_limitations.py
  - reports/agents/wave4a/TC-HO-01/evidence.md
evidence_required:
  - reports/agents/wave4a/TC-HO-01/evidence.md
---

# Taskcard TC-HO-01 — Limitations Contradiction Check

## Objective

Add `check_limitations_contradiction()` to the evaluate worker's deterministic
check pipeline. The check emits a `LIMITATION_VIOLATED` error finding when
generated page content affirms a feature that `product_evidence.limitations`
marks as `unsupported` or `deprecated`, catching LLM hallucinations that
contradict known product limitations.

## Required spec references

- `specs/worker_evaluate.md` (Section: deterministic checks — Phase A)
- `specs/worker_understand.md` (Section: product_evidence.limitations)
- `specs/schemas/understanding_bundle.schema.json` (LimitationEntry definition)

## Scope

### In scope
- New file `src/launcher/workers/evaluate/checks/limitations.py`
- Export from `checks/__init__.py`
- Integration in `_run_deterministic_checks()` in `worker.py`
- Unit tests covering affirmation detection, negation guard, status filtering, missing data

### Out of scope
- Changing LimitationEntry model (already defined in understanding.py)
- LLM-based limitations review (Phase B — out of scope for Wave 4A)
- Checking deprecated features with non-affirmative language

## Inputs

- `content`: Generated markdown text for a page
- `slug`: Page slug for Finding location
- `product_evidence`: dict loaded from `understand_checkpoint.json` via `_load_understand_checkpoint`
- `LimitationEntry` list from `product_evidence["limitations"]`

## Outputs

- `list[Finding]` where each Finding has:
  - `check="limitation_violated"`
  - `severity="error"` (mapped to `"high"`)
  - `message` includes feature name and matched sentence
  - `location=slug`

## Allowed paths

- plans/taskcards/TC-HO-01_limitations-contradiction-check.md
- src/launcher/workers/evaluate/checks/limitations.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/evaluate/checks/__init__.py
- tests/unit/workers/evaluate/checks/test_limitations.py
- reports/agents/wave4a/TC-HO-01/evidence.md

### Allowed paths rationale
- `limitations.py`: new check implementation
- `checks/__init__.py`: add export for new check
- `worker.py`: integrate check into `_run_deterministic_checks()`
- `tests/`: unit tests for all four test cases specified in sprint brief
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Implement limitations.py

Create `src/launcher/workers/evaluate/checks/limitations.py` with:
- `check_limitations_contradiction(content, slug, *, product_evidence)` function
- Filter limitations where `status in ("unsupported", "deprecated")`
- Per-limitation: scan prose lines for affirmative patterns containing `limitation.feature`
- Negation guard: skip lines with "not", "no", "doesn't", "does not", "cannot", "can't"
- Emit `Finding(check="limitation_violated", severity="high", ...)` per violation
- Handle `ValueError` from checkpoint gracefully (log warning, return `[]`)

### Step 2: Export from checks/__init__.py

Add:
```python
from .limitations import check_limitations_contradiction  # TC-HO-01
```
And add to `__all__`.

### Step 3: Integrate in worker.py

In `_run_deterministic_checks()`:
1. Add `product_evidence: dict | None = None` parameter
2. Call `check_limitations_contradiction(content, slug, product_evidence=product_evidence or {})`

In `_evaluate_page_llm()`:
- Load `product_evidence` from checkpoint once per page (using `_load_understand_checkpoint`)
- Pass to `_run_deterministic_checks()`

### Step 4: Write unit tests

Create `tests/unit/workers/evaluate/checks/test_limitations.py` with Tests A–D.

### Step 5: Create evidence artifact

Write `reports/agents/wave4a/TC-HO-01/evidence.md`.

## Failure modes

### Failure mode 1: Checkpoint not available during tests

**Detection**: `ValueError` from `_load_understand_checkpoint` in unit tests
**Resolution**: Tests pass `product_evidence` directly to the check function — checkpoint loading is only in `worker.py`, not in the check itself. Tests do not need a real checkpoint file.
**Gate**: Unit tests must pass without a real run_dir

### Failure mode 2: Negation false positives

**Detection**: Test B ("does not support async") incorrectly emits LIMITATION_VIOLATED
**Resolution**: Negation guard checks for "not", "no", "doesn't", "does not", "cannot", "can't" in the line before matching affirmative patterns
**Gate**: Test B must pass (no finding)

### Failure mode 3: Feature text substring ambiguity

**Detection**: Short feature words like "io" or "a" matching unrelated prose
**Resolution**: Use word-boundary regex `\bfeature_word\b` when feature is 3+ chars; use case-insensitive matching
**Gate**: Test D (no limitations) must return empty list; no false positives on unrelated prose

## Task-specific review checklist

1. [ ] `check_limitations_contradiction` only fires for `status in ("unsupported", "deprecated")` — not "warning" or "experimental"
2. [ ] Negation guard prevents false positives when content says "does not support X"
3. [ ] Finding `severity` is `"high"` (maps to error-level in grader)
4. [ ] `check="limitation_violated"` is consistent across all emitted findings
5. [ ] Function handles empty `product_evidence` dict gracefully (returns `[]`)
6. [ ] Function handles missing `limitations` key in `product_evidence` gracefully
7. [ ] Docstrings present for all public functions
8. [ ] Spec file confirmed: no new spec needed (check is additive to existing evaluate worker spec)
9. [ ] Schema `"description"` fields: no schema changes needed (Finding model unchanged)
10. [ ] Checked `docs/README.md` ownership map — evaluate worker guide may need update
11. [ ] No new `docs/guides/` file needed for this check

## Deliverables

1. `src/launcher/workers/evaluate/checks/limitations.py`
2. Updated `src/launcher/workers/evaluate/checks/__init__.py`
3. Updated `src/launcher/workers/evaluate/worker.py`
4. `tests/unit/workers/evaluate/checks/test_limitations.py`
5. `reports/agents/wave4a/TC-HO-01/evidence.md`

## Acceptance checks

1. [ ] All 4 unit tests (A–D) pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q` passes
3. [ ] `check_limitations_contradiction` exported from `checks/__init__.py`
4. [ ] `_run_deterministic_checks()` calls the new check
5. [ ] No existing tests broken by changes to `worker.py` or `__init__.py`

## Self-review

### Verification results
- [ ] Tests: 4/4 PASS
- [ ] Validation: import from checks package PASS
- [ ] Evidence captured: reports/agents/wave4a/TC-HO-01/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/test_limitations.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q
```

**Expected results**:
- 4 tests pass in test_limitations.py
- All workers unit tests pass

## Integration boundary proven

**Upstream**: `_load_understand_checkpoint(context)` in `worker.py` provides `product_evidence` dict
**Downstream**: `grade_page(findings)` consumes the `LIMITATION_VIOLATED` findings
**Contract**: `Finding(check="limitation_violated", severity="high", message=..., location=slug)`
