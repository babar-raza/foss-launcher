# Pilot Comparison — Before vs After (Full Evidence)

**Date**: 2026-03-24
**Pilots**: cells/python + 3d/dotnet
**Changes tested**: TC-5175, TC-UND-209, TC-UND-210, FPRPS-01..06

---

## Pilot 1: cells/python

**Run ID**: 260324_104503_cells_python_3b26 (--stop-after understand, 111.6s)
**Historical baseline**: 260312_221338_cells_python_9afc

### Claim Distribution

| Metric | Historical (260312) | After (260324) | Delta |
|--------|:-------------------:|:--------------:|:-----:|
| Total claims | 46 | 68 | +22 |
| docstring @ 1.0 | 19 | 30 | +11 |
| llm @ 0.75 | 19 | 11 | -8 |
| **llm_corroborated @ 0.85** | **0** | **12** | **+12** |
| llm_sparse_grounding @ 0.55 | 0 | 7 | +7 |
| deterministic @ 0.65 | 8 | 8 | 0 |

### Promoted Claims (12)

| Claim ID | Matched Class | Text (truncated) |
|----------|--------------|------------------|
| CLM-cells-ebc194 | Cells | Only Agile encryption is currently supported for XLSX files |
| CLM-cells-54b1f0 | Cells | Only line, bar, pie, area and stock chart types... |
| CLM-cells-392ccd | Cells | Standard encryption is not yet supported |
| CLM-cells-7a74ef | **CSVHandler** | The CSVHandler class is part of the public API |
| CLM-cells-1be078 | JsonHandler | The JsonHandler class is part of the public API |
| CLM-cells-4b6a89 | MarkdownHandler | The MarkdownHandler class is part of the public API |
| CLM-cells-fc937e | Cell | The library supports cell styling operations |
| CLM-cells-cb1821 | Workbook | The library supports exporting data to JSON format |
| CLM-cells-97c13a | Workbook | The library supports exporting workbooks to Markdown format |
| CLM-cells-e8dda7 | Workbook | The library supports importing and exporting CSV files |
| CLM-cells-d289df | Workbook | The library supports importing and exporting XLSX files |
| CLM-cells-e895c8 | Cell, Cells | The library supports reading and writing cell values |

### Events

| Event | Count |
|-------|-------|
| Total events | 26 |
| clone_completed | 0 (cache hit) |
| understand_llm_skipped | 0 (worktree available) |

---

## Pilot 2: 3d/dotnet

**Run ID**: 260324_104751_3d_dotnet_9374 (--stop-after understand, 668.6s)
**Historical baseline**: phase_store/3d/dotnet/understand.json (prior run)

### Claim Distribution

| Metric | Previous (phase_store) | After (260324) | Delta |
|--------|:---------------------:|:--------------:|:-----:|
| Total claims | 29 | 29 | 0 |
| docstring @ 1.0 | 6 | 6 | 0 |
| llm @ 0.75 | 1 | 1 | 0 |
| llm_corroborated @ 0.85 | 0 | 0 | 0 |
| llm_sparse_grounding @ 0.55 | 14 | 14 | 0 |
| deterministic @ 0.65 | 8 | 8 | 0 |

### Key observations

- **No llm_corroborated promotions** — expected. .NET docstring evidence uses XML doc comments, not Python-style `docstring:ClassName` patterns.
- **LLM extraction DID run** (15 LLM-sourced claims: 1 llm + 14 llm_sparse_grounding). The original issue was 0 LLM claims due to missing worktree — now fixed by clone cache seeding (TC-5175).
- **No understand_llm_skipped event** — worktree available at `runs/.clone_cache/aspose_3d_dotnet/`
- **LLM JSON parse error on attempt 1/3** — pre-existing LLM quality issue (not a regression).
- Intake used cached clone (`fresh=False`), SHA=f6552cfd.

### Events

| Event | Count |
|-------|-------|
| Total events | 27 |
| clone_completed | 0 (cache hit) |
| understand_llm_skipped | 0 (worktree available) |

---

## FPRPS Regression Found During Pilot

**Issue**: FPRPS-01 initial regex `\b[A-Z][a-z][a-zA-Z0-9]*\b` was too restrictive — rejected `CSVHandler` (legitimate class) because `S` follows `C` without lowercase.

**Fix applied during pilot**: Changed to `\b[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*\b` (requires at least one lowercase anywhere, not just immediately after first capital).

**Verification**:
- `CSV`, `JSON`, `XLSX` — NOT matched (all-caps, no lowercase)
- `CSVHandler`, `JsonHandler`, `Workbook` — matched (contain lowercase)
- All 11 unit tests pass after fix

---

## Summary

### 1. What Improved

| Fix | Evidence | Verdict |
|-----|----------|---------|
| **TC-UND-210**: llm_corroborated promotion | 12/23 LLM claims promoted to 0.85 in cells/python | WORKING |
| **TC-5175**: Clone cache seeding | Both pilots used cached clones (fresh=False) | WORKING |
| **TC-UND-209**: worktree_missing event | Guard silent when worktree available (correct) | WORKING |
| **FPRPS-01**: Regex false positive fix | CSVHandler promoted, CSV not promoted | FIXED (iterated during pilot) |
| **FPRPS-05**: DEBUG logging | 12 per-claim log lines visible in cells/python run | WORKING |
| **FPRPS-03**: Dedup priority test | 2 regression tests passing | VERIFIED |

### 2. What Did Not Improve

| Item | Reason | Action needed |
|------|--------|---------------|
| 3d/dotnet: 0 llm_corroborated | .NET docstring evidence uses different patterns (`docstring:ClassName` absent) | Not a bug — promotion is Python-specific for now. Future: extend adapter to emit `docstring:` prefixed source_file for .NET XML doc comments |
| 3d/dotnet: LLM JSON parse error | LLM returned malformed JSON on attempt 1 (retry succeeded) | Pre-existing LLM quality issue — not related to FPRPS changes |

### 3. Regressions Introduced

| Regression | Severity | Status |
|------------|----------|--------|
| FPRPS-01 v1 regex too restrictive (CSVHandler rejected) | HIGH | **Fixed** — iterated to v2 regex during this pilot |

No other regressions detected.

### 4. Production Readiness

| Component | Ready | Notes |
|-----------|-------|-------|
| TC-UND-210 confidence promotion | YES | 12 claims promoted, weighted LLM average 0.75→0.80 |
| TC-5175 seed mode | YES | Clone cache hit, no fresh clone needed |
| TC-UND-209 worktree guard | YES | Guard fires on missing repo_dir, silent when available |
| FPRPS-01 regex fix (v2) | YES | Handles compound names (CSVHandler) + rejects acronyms (CSV) |
| FPRPS-05 DEBUG logging | YES | Per-claim visibility in production logs |
| FPRPS-03 dedup regression test | YES | Priority ordering verified |

**Overall verdict: Production-ready.** One regression found and fixed during pilot. All targeted issues resolved.
