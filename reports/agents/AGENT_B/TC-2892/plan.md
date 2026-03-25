# Agent B — TC-2892 Bake-in + Promote Plan

## Assumptions (VERIFIED)
- TC-2892 taskcard exists and is In-Progress ✓
- `lint_fq8_adjacent_fences()` exists at gate_17_prelints.py:205 with severity="warn" ✓
- `_ERROR_CODES` at gate_17_prelints.py:291 does NOT include G17-FQ-8 ✓
- W10 handler for FQ-8 exists at w10_fixer/worker.py:739 ✓
- 11 existing FQ-8 tests in test_gate_17_fq8.py ✓

## Steps
1. Run pilot-aspose-3d-foss-python → capture evidence
2. Run pilot-aspose-note-foss-python → capture evidence
3. Run pilot-aspose-cells-foss-python → capture evidence
4. Verify all 3 pilots: no false merges, no unresolved adjacent fences
5. Promote severity: gate_17_prelints.py line 268 warn→error
6. Add to _ERROR_CODES: gate_17_prelints.py line 291
7. Update docstring: gate_17_prelints.py lines 214-215
8. Update test assertions: test_gate_17_fq8.py lines 32, 97
9. Add new test: test_fq8_severity_is_error
10. Run full test suite

## Rollback
- Revert severity back to "warn" and remove from _ERROR_CODES if any pilot shows false merges

## Acceptance Checklist
- [ ] 3 evidence files in plans/healing/evidence/
- [ ] severity == "error" in lint_fq8_adjacent_fences()
- [ ] "G17-FQ-8" in _ERROR_CODES frozenset
- [ ] test_fq8_severity_is_error passes
- [ ] Full test suite green
