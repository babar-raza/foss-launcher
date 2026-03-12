# PM-04: Add Viable-Class Observability Logging

## Status: Done

## Gap Linkage: PM-G5

## Role
Senior engineer. Drop-in, production-ready.

## Context
`_expand_per_module()` logs the count of viable classes and the budget, but does
not log *which* classes were selected or which were skipped. During pilot run
debugging, knowing "Workbook(3 claims) selected, Worksheet(1 claim) skipped"
is critical for understanding why certain pages were or weren't created.

## Scope

### Fix
- Add a `logger.info` call after the viable list is computed, listing:
  - Selected classes with their claim counts (capped at 10 for log readability)
  - Skipped classes (had >0 claims but below threshold) with counts (capped at 5)
- Keep log line under 200 chars to avoid log truncation

### Allowed paths
- `src/launcher/workers/planner/plan.py`

### Forbidden
- Any other file/path

## Acceptance checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- No new tests required (observability-only change)
- Existing tests pass (log output doesn't affect behavior)

### Config respected end-to-end
- N/A

### No mock data in production paths
- N/A

## Deliverables
- Modified `src/launcher/workers/planner/plan.py`: ~5 lines added to
  `_expand_per_module()` after line ~540

## Hard rules
- No behavioral changes
- Use existing `logger` instance
- No new deps

## Review dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Observability | Pilot run logs clearly show which classes were selected/skipped |
| Minimality | Pure logging addition, zero behavioral change |
| Performance | Negligible overhead (string formatting only when logging) |

## Now (runbook)

```bash
# 1. In _expand_per_module, after computing `viable` (line ~540), add:
#    viable_desc = ", ".join(f"{cls}({len(cids)})" for cls, cids in viable[:10])
#    skipped = [(cls, cids) for cls, cids in class_claim_idx.items()
#               if 0 < len(cids) < _MIN_CLAIMS_PER_CLASS]
#    skipped_desc = ", ".join(f"{cls}({len(cids)})" for cls, cids in skipped[:5])
#    logger.info("per_module selected: %s; below-threshold: %s",
#                viable_desc, skipped_desc or "none")

# 2. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
```
