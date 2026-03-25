# Evidence — TC-4265 + TC-4266

## TC-4265: Snippet construction sites found

### Snippet construction sites in _snippets.py
1. **Fenced code block loop** (~line 584): `Snippet(code=code.strip(), language=effective_lang, source_type=source_type, source_file=rel_path, claim_ids=linked_claim_ids)`
2. **Source example file loop** (~line 685): `Snippet(code=normalized_code.strip(), language=file_lang, source_type="extracted", source_file=rel_path, claim_ids=linked_claim_ids)`

### Language detection already in place
- Fenced blocks: `effective_lang = lang.lower() if lang else getattr(product, "lang_tag", "python") or "python"`
- Source examples: `file_lang = LANG_BY_EXT.get(file_ext, "python")`
- Python validation: `_validate_python_syntax(code)` already called before Snippet construction (snippets with invalid Python are SKIPPED, never reach construction)
- TypeScript: `ts_analyzer.validate_snippet(code, effective_lang)` already called

### How syntax_valid is set
- Python snippets reaching construction: `_syntax_valid = True` (invalid Python is filtered before reaching Snippet construction)
- Empty code: `_syntax_valid = False` (guard for empty code edge case)
- TypeScript/JS: `ts_analyzer.validate_snippet(code, lang)` or `None` if ImportError
- Other languages (Java, Ruby, etc.): `_syntax_valid = None` (unknown — not False)

### Snippet.syntax_valid in claims.py
- Added: `syntax_valid: bool | None = None`
- Default `None` ensures backward compat with old bundles
- `SnippetFact` in `understanding.py` already had `syntax_valid: bool = True` — separate model, unchanged

---

## TC-4266 Part A: Confidence tiering

### Where confidence is assigned in _deterministic.py
- `_extract_claims_deterministic` produces raw dicts. Previously, bullet/table/paragraph claim dicts had NO `claim_source` key.
- This caused `_validate_and_normalize_claims` to default `claim_source="llm"` → `confidence=0.75` for all deterministic claims.
- Fix: Added `"claim_source": "deterministic"` to all three claim types (bullet, table, paragraph).

### Structured heading detection
- Added `_STRUCTURED_SECTION_HEADINGS` frozenset with 9 entries (features, capabilities, key features, supported formats, etc.)
- `_normalize_heading_key`: lowercase, strip punctuation, strip trailing colon
- `_is_structured_section_heading`: checks normalized key against frozenset
- `in_structured_section` tracked per-heading, reset on each heading change

### Exact code change in _validation.py
```python
# TC-4266: Boost deterministic claims from structured feature sections to 0.70.
# Must NOT exceed 0.70 (strictly below the 0.75 verified threshold).
if claim_source == "deterministic" and raw.get("in_structured_section"):
    confidence = 0.70
```

---

## TC-4266 Part B: Note deterministic claims investigation

```
Note deterministic claims:
  kind=api conf=0.5 text=Document.Save() is part of the public API for Aspose.Note.
  kind=api conf=0.5 text=PdfSaveOptions configures file export options in Aspose.Note.
  kind=api conf=0.5 text=SaveOptions configures file export options in Aspose.Note.
  kind=api conf=0.5 text=NoteTag.CreateYellowStar() is part of the public API for Aspose.Note.
  kind=api conf=0.5 text=LoadOptions configures file import options in Aspose.Note.
  kind=api conf=0.5 text=HtmlSaveOptions configures file export options in Aspose.Note.
  kind=api conf=0.5 text=ImageSaveOptions configures file export options in Aspose.Note.
  kind=api conf=0.5 text=OneSaveOptions configures file export options in Aspose.Note.
Total deterministic: 8
```

**Decision: Option C** — Leave `feature_blog` threshold unchanged.

**Rationale**: Note's deterministic claims are all `kind=api`, generated from method docstrings via `_extract_method_docstring_claims`. They do NOT come from structured feature section headings (Features:, Capabilities:, etc.) in documentation. The `feature_blog` sufficiency check uses `feature_verified = [c for c in verified_claims if c.kind in {"feature", "format", "config", "troubleshoot"}]` — these API-kind claims would not qualify anyway, so lowering the threshold to `confidence >= 0.65` would have no effect on Note. The actual fix for Note's feature_blog is to produce real feature/format claims from documentation, not to lower the bar for API claims.

---

## TC-4266 Part C: Note snippet sources

```
Note snippet sources:
   20  docs/onenote-api.md
   13  README.md
    1  examples/export_pdf.py
    1  examples/extract_text.py
    1  examples/save_images.py
Total: 36 snippets
```

**Finding**: `docs/onenote-api.md` (stem="onenote-api") contains "api" in the stem. Current `_score_doc_path` scoring did NOT penalize API reference docs — they got the same `docs_dir` score of 80 as any other doc in `docs/`.

**Fix applied**: In `_score_doc_path`, compute base score first, then apply `-20` if stem contains "api" or "reference". Result for `docs/onenote-api.md`: `80 - 20 = 60`. This deprioritizes it in context ordering (affects which files get budget first) without filtering it out entirely.

---

## Test run output

### tests/unit/workers/test_understand.py
```
307 passed in 3.54s
```

### tests/unit/workers/understand/ (excluding pre-existing scout failures)
```
299 passed in 3.30s
```

### New tests only
```
8 passed (TC4265 and TC4266 filter) in 1.74s
```

### Pre-existing failures (not caused by these changes)
- `tests/unit/workers/understand/test_scout.py::TestSkippedPathsPopulation::test_truncated_files_not_in_skipped`
- `tests/unit/workers/understand/test_scout.py::TestSkippedPathsPopulation::test_run_scout_wires_skipped_paths_to_repo_info`
- Verified pre-existing by stashing my changes and confirming same failures
