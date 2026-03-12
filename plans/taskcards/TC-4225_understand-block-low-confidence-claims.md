---
id: TC-4225
title: "U-2: Block low-confidence claims from checkpoint"
status: Done
priority: High
owner: "Agent-B"
updated: "2026-03-12"
tags: [understand, claims, confidence, checkpoint]
depends_on: [TC-4224]
allowed_paths:
  - plans/taskcards/TC-4225_understand-block-low-confidence-claims.md
  - src/launcher/workers/understand/extract/_entry.py
  - src/launcher/workers/understand/worker.py
  - tests/unit/workers/understand/
evidence_required:
  - reports/TC-4225/evidence.md
---

# Taskcard TC-4225 — U-2: Block low-confidence claims from checkpoint

## Objective

Filter out claims with `confidence < 0.5` before writing the understand checkpoint, preventing `llm_fallback` claims (confidence=0.35) from reaching downstream phases. This eliminates the root cause of hallucination_rate CRITICAL findings in the evaluate phase.

## Required spec references

- `specs/worker_understand.md` (Section: Claim confidence thresholds)
- `specs/schemas/understanding_bundle.schema.json` (Section: claims array)

## Scope

### In scope
- Add confidence filter in `_entry.py` or `worker.py` before checkpoint write
- Log count of filtered claims at INFO level
- Unit tests covering filter boundary (exactly 0.5 passes, below 0.5 blocked)

### Out of scope
- Changing confidence values assigned by LLM (TC-4226 scope)
- Changing the confidence field definition (TC-HAL-06 already done)
- Downstream generate/evaluate changes

## Inputs

- `src/launcher/workers/understand/extract/_entry.py` — claim pipeline entry
- `src/launcher/workers/understand/worker.py` — checkpoint write location
- `specs/schemas/understanding_bundle.schema.json` — bundle schema

## Outputs

- Modified `_entry.py` or `worker.py` with confidence filter
- Updated tests in `tests/unit/workers/understand/`

## Allowed paths

- plans/taskcards/TC-4225_understand-block-low-confidence-claims.md
- src/launcher/workers/understand/extract/_entry.py
- src/launcher/workers/understand/worker.py
- tests/unit/workers/understand/

### Allowed paths rationale
Filter must be applied before checkpoint write. Either `_entry.py` (post-extraction) or `worker.py` (pre-write) is appropriate; choose the location closest to the write boundary.

## Implementation steps

### Step 1: Locate checkpoint write in worker.py

Read `src/launcher/workers/understand/worker.py` to find where `understand_checkpoint.json` is written.

### Step 2: Add confidence filter

Before writing claims to checkpoint, apply:
```python
CONFIDENCE_THRESHOLD = 0.5
original_count = len(claims)
claims = [c for c in claims if c.confidence >= CONFIDENCE_THRESHOLD]
filtered_count = original_count - len(claims)
if filtered_count > 0:
    logger.info(f"Filtered {filtered_count} low-confidence claims (< {CONFIDENCE_THRESHOLD}) from checkpoint")
```

### Step 3: Write unit tests

Add tests covering:
1. Claims with confidence=0.35 are excluded from checkpoint
2. Claims with confidence=0.5 (boundary) are included
3. Claims with confidence=0.8 pass through unchanged
4. Log message emitted when claims are filtered

### Step 4: Run tests

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v -q
```

## Failure modes

### Failure mode 1: Over-filtering eliminates all claims

**Detection**: Understand checkpoint has 0 claims; downstream planner generates no pages.
**Resolution**: Check source of low confidence — if all claims are low-confidence, upstream LLM quality is the issue (TC-4224/TC-4226 scope). Lower threshold to 0.35 as emergency measure.
**Gate**: Understand checkpoint `claims` count > 0

### Failure mode 2: Boundary condition excludes valid claims

**Detection**: Claims with confidence=0.5 unexpectedly excluded.
**Resolution**: Use `>= 0.5` (inclusive) not `> 0.5`.
**Gate**: Unit test for boundary case

### Failure mode 3: Filter applied after checkpoint write (no-op)

**Detection**: Low-confidence claims still appear in checkpoint JSON.
**Resolution**: Verify filter is applied before the `json.dump` / `write_json` call, not after.
**Gate**: Integration test reading checkpoint after run

## Task-specific review checklist

1. [ ] Filter threshold is `confidence >= 0.5` (inclusive at 0.5)
2. [ ] Filter applied BEFORE checkpoint write, not after
3. [ ] Filtered count logged at INFO level
4. [ ] Unit test: confidence=0.35 excluded
5. [ ] Unit test: confidence=0.5 included (boundary)
6. [ ] Unit test: log message emitted when filter removes claims
7. [ ] Docstrings updated for modified functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
10. [ ] Checked `docs/README.md` ownership map — trigger event check done
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. Modified `_entry.py` or `worker.py` — confidence filter applied pre-checkpoint
2. `tests/unit/workers/understand/` — boundary + log tests
3. `reports/TC-4225/evidence.md` — checkpoint JSON showing no low-conf claims

## Acceptance checks

1. [ ] All tests pass: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v`
2. [ ] Understand checkpoint contains zero claims with confidence < 0.5 — verified by inspection
3. [ ] Pilot run: hallucination_rate CRITICAL findings = 0

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: checkpoint confidence filter PASS
- [ ] Evidence captured: reports/TC-4225/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/ -v
```

**Expected results**:
- Boundary condition tests pass
- No regressions in existing understand tests

## Integration boundary proven

**Upstream**: `_extract_claims_llm` / deterministic extractor — provides raw claims with confidence scores
**Downstream**: Understand checkpoint JSON — consumed by planner and generate workers
**Contract**: All claims in checkpoint have `confidence >= 0.5`
