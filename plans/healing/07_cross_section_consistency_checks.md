# Healing Plan: Cross-Section Consistency Checks

**Date**: 2026-02-19
**Status**: Ready for Execution
**Scope**: Add a W7 validation gate that catches contradictions, duplicate blocks, and terminology divergence across pages in the same pilot run.

## Context

W7 validates each page in isolation. Pages regularly contradict each other (e.g., one page says "supports Python 3.8+" another says "requires Python 3.10+"), duplicate long intro paragraphs verbatim, or use different names for the same class ("Document" vs "Doc"). Gate 10 (`gate_10_consistency`) exists but checks internal consistency; cross-page checks are absent.

## Gap → Taskcard Mapping

| Gap ID | Description                                             | Taskcard |
|--------|---------------------------------------------------------|----------|
| RD-07  | No cross-page consistency validation in W7              | RD-07    |

---

## Taskcard RD-07 — W7 Cross-Page Consistency Gate (Gate 20)

**Status**: Not Started
**Gap linkage**: RD-07 (00_REDESIGN.md §2.1 item 3, TC-2376)
**Role**: Senior engineer. Drop-in, production-ready.

### Scope

**Fix**: Add `gate_20_cross_page_consistency.py` to the W7 gates package. It receives all published markdown files and runs 3 deterministic checks:

1. **Duplicate block detection**: Any prose paragraph ≥ 100 chars appearing verbatim in ≥ 2 pages → warn
2. **Version contradiction detection**: Regex-extract Python/OS version ranges across pages; if ranges conflict → error
3. **Class name divergence**: Extract class/function names from code blocks; if same entity uses 2+ different names across pages → warn

All checks are deterministic (no LLM). Gate severity: errors fail the gate; warns are recorded but gate passes.

**Allowed paths**:
```
src/launch/workers/w9_validator/gates/gate_20_cross_page_consistency.py   (new)
src/launch/workers/w9_validator/gates/__init__.py
src/launch/workers/w9_validator/worker.py
tests/unit/workers/test_gate_17_formatting_quality.py                     (extend or add new file)
```

**Forbidden**: any other file or path.

### Acceptance Checks

**CLI**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd07_verify
# validation_report.json must include gate_20_cross_page_consistency result
# Gate must PASS on 3D pilot (no known contradictions in that content)
```

**UI/Web/API**: N/A

**Tests**:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v -k "gate_20"
# 4 new tests:
#   - duplicate_block_detected: 2 pages with same 100+ char paragraph → warn issued
#   - duplicate_block_clean: unique paragraphs → 0 warns
#   - version_contradiction: "Python 3.8+" vs "requires 3.10+" → error issued
#   - no_contradiction: consistent versions → 0 errors
```

**Config respected end-to-end**: Gate 20 is always-on in W7 (same as existing gates). No config flag needed.

**No mock data in production paths**: Gate operates on real published markdown files.

### Deliverables

- `gate_20_cross_page_consistency.py` (new): `run_gate_20(md_files: List[Path]) -> Tuple[bool, List[Dict]]`
- `gates/__init__.py`: add `"gate_20_cross_page_consistency"` to `__all__`
- `worker.py`: add gate_20 call in the W7 gate runner (after gate_19)
- 4 unit tests covering happy path + 3 detection scenarios
- No schema changes needed (gate output format matches existing issue dict)

### Hard Rules

- All 3 checks are deterministic (no LLM, no network)
- Duplicate detection uses exact string match (no fuzzy); ≥ 100 chars threshold prevents false positives on short phrases
- Version extraction: `r'Python\s+(\d+\.\d+)\+?'` pattern; only `error` if ranges don't overlap (not just different strings)
- Gate is additive: adding it cannot break existing PASS runs (gate fails only on genuine contradictions)
- No new deps (use stdlib `re`, `collections.Counter`)

### Review Dimensions

| Dimension | 5/5 means |
|-----------|-----------|
| Coverage | All 3 checks implemented; gate registered in __init__ and worker.py |
| Correctness | Known 3D pilot content passes without false positives |
| Evidence | Pilot validation_report.json showing gate_20 PASS; test showing detection |
| Test Quality | 4 tests: 2 detection + 2 clean-pass |
| Maintainability | Each check is a standalone function; easy to add check 4 |
| Safety | Additive gate; cannot retroactively fail existing passing content |
| Security | N/A |
| Reliability | Deterministic string matching; no external calls |
| Observability | Gate result in validation_report.json `gate_results[]` |
| Performance | O(pages²) for duplicate check; < 1s for 21 pages |
| Compatibility | Gate output format identical to existing gates; no model changes |
| Docs/Specs Fidelity | `specs/09_validation_gates.md` updated with Gate 20 definition |

### Now (Runbook)

```bash
# 1. Create gate_20_cross_page_consistency.py with run_gate_20()
#    Helper: _find_duplicate_blocks(md_files) -> List[issue_dict]
#    Helper: _find_version_contradictions(md_files) -> List[issue_dict]
#    Helper: _find_class_name_divergence(md_files) -> List[issue_dict]

# 2. Register in __init__.py and worker.py

# 3. Add 4 unit tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -v -k "gate_20"
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q

# 4. Run pilot
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py \
  --pilot pilot-aspose-3d-foss-python --output runs/rd07_verify

# 5. Inspect gate_20 result in validation_report.json
.venv/Scripts/python.exe -c "
import json, pathlib
vr = json.loads(list(pathlib.Path('runs/rd07_verify').glob(
  '*/artifacts/validation_report.json'))[0].read_text())
gate = next((g for g in vr.get('gate_results',[]) if 'gate_20' in g.get('name','')), None)
print('gate_20:', gate)
"
```
