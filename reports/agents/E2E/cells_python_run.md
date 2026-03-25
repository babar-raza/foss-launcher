# E2E Run Report — cells/python, Understand phase

**Run ID**: `260314_062533_cells_python_3132`
**Date**: 2026-03-14
**Pipeline stop**: `--stop-after understand`
**Config**: `configs/pilots/aspose-cells-foss-python.yaml`
**Verdict**: `NO_GO` (schema validation failure — see Critical Issue below)

---

## 1. Pipeline Output Summary

The pipeline completed all three workers (intake, scout, understand) and produced all internal
artifacts, but **failed at output schema validation** before writing the phase store checkpoint.

### Workers completed

| Worker | Duration | Status |
|--------|----------|--------|
| intake | 1.1 s | OK |
| scout | 1.0 s | OK |
| understand | ~72 s (LLM call: 68.5 s) | Artifacts written; schema validation FAILED |

### Critical Issue: `syntax_valid` not in output schema

The `understand` worker appends a `syntax_valid` field to every snippet in its output. The
output schema (`understanding_bundle.schema.json`, `snippets` items definition, lines 520–572)
has `additionalProperties: false` and does NOT include `syntax_valid` in the top-level
`snippets` array item shape.

Error (31 occurrences, one per snippet):

```
understand.output: snippets/N: Additional properties are not allowed ('syntax_valid' was unexpected)
```

Root cause: TC-4265 correctly added `syntax_valid` to `Snippet` model and `_snippets.py`
construction sites, but did NOT add `syntax_valid` to the top-level `snippets` items schema
in `understanding_bundle.schema.json`. The field exists in the `SnippetFact` `$defs` entry
(line 982) but NOT in the `snippets` array item shape (lines 530–570).

**Impact**: The `phase_store/cells/python/understand.json` was NOT updated. It still contains
the pre-fix data (31 snippets, all `syntax_valid=None`).

### Other warnings

- `[Understand] docstring_claims_raw: cap=26 reached; 47/56 classes not processed — increase max_claims for better API coverage`
  — 56 public classes, only 26 docstring claims extracted due to cap.
- `[WARNING] pytrends not installed — skipping Google Trends`
  — expected; SEO keyword data degraded but non-blocking.
- `[WARNING] Syntax error in xml_chart_loader.py: invalid non-printable character U+FEFF`
  — BOM in source file; logged and skipped; not blocking.
- `snippet_import_validation [TC-HAL-07]: 5 snippets filtered (invalid import path)`
  — 5 of 36 extracted snippets dropped pre-dedup; expected behavior.

---

## 2. Claims — Count by Source and Confidence

These numbers come from `understanding_bundle.json` in the run dir (the artifacts ARE complete
even though the schema gate blocked phase_store update).

| Source | Count | Confidence |
|--------|-------|-----------|
| llm | 26 | 0.75 (uniform) |
| docstring | 26 | 1.0 (uniform) |
| deterministic | 8 | 0.50 (uniform) |
| **Total** | **60** | — |

**Confidence distribution**: `{0.5: 8, 0.75: 26, 1.0: 26}`

Comparison against phase_store (pre-TC-426x):
- Phase store had 62 claims; new run has 60 (-2). The 2-claim reduction is due to contradiction
  resolution: `resolve_contradictions: 2 contradictions resolved out of 60 claims` (60 kept post-
  resolution; the log means 2 pairs were merged, not that 2 were dropped).

---

## 3. syntax_valid Breakdown

| Value | New run (bundle) | Phase store (stale) |
|-------|-----------------|---------------------|
| True | **31** | 0 |
| False | 0 | 0 |
| None | **0** | 31 |

**Result: syntax_valid=None is now 0 in the run artifacts.** TC-4265 is working correctly.
All 31 Python snippets pass `ast.parse()` and have `syntax_valid=True`.

The fix did not make it into the phase store because the schema validation failure blocked the
checkpoint write. The phase store is stale and must be updated once the schema issue is fixed.

---

## 4. Deterministic Claims — Confidence Analysis

All 8 deterministic claims have `confidence=0.5` and `in_structured_section=None`.

These claims come from `_harvest_operation_claims_raw()` in `_entry.py`, NOT from the
README structured-section parser in `_deterministic.py`. They are API-stub claims generated
from the API surface (class briefs), not from README headings.

TC-4266 implemented confidence tiering (0.70) for README-based structured-section claims.
The Cells README does NOT contain headings matching `_STRUCTURED_SECTION_HEADINGS` (e.g.,
"Features:", "Capabilities:"), so no claims received the 0.70 tier. This is correct behavior:
the tiering only applies when the source document contains structured feature sections.

The 8 deterministic claims are:
- `Workbook.create_worksheet()` — public API, conf=0.50
- `CSVHandler.save_csv()` — public API, conf=0.50
- `MarkdownHandler.save_markdown()` — public API, conf=0.50
- `JsonHandler.save_json()` — public API, conf=0.50
- `CSVLoadOptions` — LoadOptions class, conf=0.50
- `CSVSaveOptions` — SaveOptions class, conf=0.50
- `JsonSaveOptions` — SaveOptions class, conf=0.50
- `MarkdownSaveOptions` — SaveOptions class, conf=0.50

All have `in_structured_section=None` because `_harvest_operation_claims_raw()` does not set
this field — it originates from API surface scanning, not heading-based extraction.

---

## 5. Page Evidence Index — Sufficient Pages

All 6 page roles are sufficient. No insufficient pages.

| Page role | sufficient | verified_claims | snippets |
|-----------|-----------|-----------------|---------|
| `_index` | True | 50 | 31 |
| `api_reference` | True | 32 | 31 |
| `feature_blog` | True | 16 | 31 |
| `format_conversion` | True | (full) | 31 |
| `howto_article` | True | (full) | 31 |
| `install_guide` | True | (full) | 31 |

No page role has insufficient evidence. This is consistent with Cells having a rich API surface
(56 public classes, 60 claims, 31 snippets, richness tier A).

---

## 6. Assessment: TC-4262 through TC-4266 Changes

### TC-4265 — syntax_valid at Snippet construction

**Status: Working correctly.**
- All 31 Python snippets now have `syntax_valid=True` (was: all None).
- The fix correctly calls `ast.parse()` at construction in `_snippets.py`.
- Blocker: schema validation failure prevents phase_store update.

### TC-4266 — Deterministic confidence tiering

**Status: Implemented but not triggered for Cells.**
- The `_STRUCTURED_SECTION_HEADINGS` frozenset and `_is_structured_section_heading()` function
  are present in `_deterministic.py`.
- Cells' README does not use matching section headings, so all deterministic claims remain at 0.50.
- This is correct behavior; the tiering will activate for products with richer README structure.

### TC-4262 — LLM doc window 128KB

**Effect**: The LLM call processed 1549.3 KB of source across 92 files, extracting 26 LLM claims
with no llm_fallback (rate=0.000). The evidence context injected was 1308 chars. The larger window
did not cause regressions.

### TC-4263 — Scout budget 5MB per-file caps

**Effect**: `budget_log_entries=3, budget_log_overflow=0, files_truncated=0`. No files were
truncated or dropped. The 5MB cap was not triggered for Cells.

### TC-4264 — Scout metadoc subdir filter

**Effect**: `1 docs, 30 examples` — the metadoc filter correctly limited doc ingestion to the
README and filtered subdirectory documentation. `dropped_by_category={}` (nothing filtered by
category; the filter produced the expected 1-doc result).

---

## 7. Regressions Detected

### BLOCKER: Schema validation failure (new regression introduced by TC-4265)

**Severity**: Critical — pipeline cannot complete Understand phase.

**Root cause**: `specs/schemas/understanding_bundle.schema.json` top-level `snippets` items
definition does not include `syntax_valid`. The `SnippetFact` definition in `$defs` has the
field (line 982), but the output validation uses the inline `snippets` item shape (lines 530–570)
which has `additionalProperties: false` and omits `syntax_valid`.

**Fix required**: Add `syntax_valid` to the top-level `snippets` items properties in
`understanding_bundle.schema.json`:

```json
"syntax_valid": {
  "type": ["boolean", "null"],
  "default": null,
  "description": "TC-4265: True=valid syntax, False=invalid, null=language unsupported."
}
```

This fix requires a taskcard (protected path: `specs/schemas/`).

### Phase store staleness

`phase_store/cells/python/understand.json` has 31 snippets with `syntax_valid=None` (old data).
It will remain stale until the schema issue is fixed and the pipeline re-runs successfully.

### docstring_claims_raw cap (existing, not a regression)

47/56 public classes were not processed for docstring claims due to the cap of 26. This is a
pre-existing limitation. The cap can be raised in `_entry.py` if higher API coverage is desired.

---

## 8. Summary

The TC-4262 through TC-4266 changes are functionally correct. `syntax_valid` is now set properly
at construction (TC-4265) and deterministic confidence tiering is in place (TC-4266). However,
TC-4265 introduced a schema gap: the `understanding_bundle.schema.json` output schema does not
permit `syntax_valid` in the top-level `snippets` items, causing the pipeline to fail at the
schema gate. This single fix is required before the pipeline can produce a successful run.

**Next action**: Create a taskcard to add `syntax_valid` to `understanding_bundle.schema.json`
`snippets` items (protected path: `specs/schemas/understanding_bundle.schema.json`).
