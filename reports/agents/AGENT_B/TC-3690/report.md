# TC-3690 Report — Product Display Name Field

**Date:** 2026-03-04
**Agent:** agent_b

## Summary
Implemented IT-01 fix: separated internal product slug from human-readable display name.

## Files Modified
| File | Change |
|------|--------|
| `configs/pilots/pilot-aspose-cells-foss-python.resolved.yaml` | Added `display_name: "Aspose.Cells FOSS for Python"` |
| `configs/pilots/pilot-aspose-note-foss-aspose-note-foss-for-python.resolved.yaml` | Added `display_name: "Aspose.Note FOSS for Python"` |
| `specs/schemas/run_config.schema.json` | Added optional `display_name` property |
| `src/launch/workers/w4_ia_planner/worker.py:189` | `_extract_shared_facts()` uses `display_name` field if present |
| `src/launch/workers/w4_ia_planner/worker.py:6320-6330` | Inject `display_name` from run_config into product_facts before `_extract_shared_facts()` |
| `src/launch/workers/w9_validator/gates/gate_product_name_placeholder.py` | NEW: detects pilot- prefix in headings |
| `src/launch/validation_engine/gates_registry.yaml` | Registered gate_product_name_placeholder at order 52 |
| `tests/unit/workers/w9/gates/test_gate_product_name_placeholder.py` | NEW: 11 unit tests |

## Key Design Decisions
- No RunConfig model changes (TC-250 restriction). W4 reads `display_name` from raw config dict.
- Shallow copy of product_facts before injection (do not mutate W2 output).
- Fallback chain: `display_name` → `product_name` (backward compatible).
- Gate scans both `work/site/` and `drafts/` directories.

## Test Results
- Gate tests: 11 passed (TestPilotPrefixInH1, TestPilotPrefixInFrontmatter, TestOverlongH1, TestCleanContent)
- Full suite: pending

## Commands
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/w9/gates/test_gate_product_name_placeholder.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
