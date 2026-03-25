# Evidence — Agent B1: FPRPS-01 + FPRPS-03 + FPRPS-05

**Date**: 2026-03-24

## FPRPS-01: PascalCase regex fix

### Change
- `_linking.py:456`: `r"\b[A-Z][a-zA-Z0-9]+\b"` → `r"\b[A-Z][a-z][a-zA-Z0-9]*\b"`

### Verification
- `CSV`, `JSON`, `XLSX`, `TSV`, `HTML`, `PDF` — NOT matched (all-caps, no lowercase after capital)
- `Workbook`, `SaveFormat`, `CellsApi` — matched (PascalCase with lowercase)
- `test_all_caps_acronym_not_promoted` — PASSED
- `test_true_pascal_case_promoted` — PASSED

## FPRPS-03: Dedup regression tests

### Tests added
- `TestSourcePriorityDedup::test_dedup_prefers_llm_corroborated_over_llm` — PASSED
- `TestSourcePriorityDedup::test_dedup_prefers_docstring_over_llm_corroborated` — PASSED

## FPRPS-05: DEBUG logging

### Change
- `_linking.py:463-466`: Added `logger.debug("[Linking] promoted claim %s: matched docstring classes %s", ...)`

## Test Run

```
275 passed, 2 failed (pre-existing TestTC4093InstallRecipeVerification)
0 new regressions
```
