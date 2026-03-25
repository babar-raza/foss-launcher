# Changes — TC-4265 + TC-4266

## TC-4265: syntax_valid at Snippet construction

### src/launcher/models/claims.py
- Added `syntax_valid: bool | None = None` field to `Snippet` model
- Comment: `TC-4265: None=unknown, True=valid, False=invalid`

### src/launcher/workers/understand/extract/_snippets.py
- **Fenced code block loop** (around line 584): After `_link_snippet_to_claims`, compute `_syntax_valid`:
  - Empty code → `False`
  - `effective_lang == "python"` → `True` (already passed `_validate_python_syntax` to reach this point)
  - TypeScript/JS → `ts_analyzer.validate_snippet(code, lang)` or `None` if ImportError
  - Other languages → `None`
  - Pass `syntax_valid=_syntax_valid` to `Snippet(...)`
- **Source example file loop** (around line 685): Same logic with `_src_syntax_valid`, pass to `Snippet(...)`
- **`_score_doc_path`**: Added TC-4266 Part C penalty: `-20` for stems containing "api" or "reference"

---

## TC-4266: Confidence tiering + Note snippet concentration

### src/launcher/workers/understand/extract/_deterministic.py
- Added `_STRUCTURED_SECTION_HEADINGS` frozenset constant after `_SECTION_KIND_MAP`
- Added `_normalize_heading_key(heading)` helper function
- Added `_is_structured_section_heading(heading)` helper function
- In `_extract_claims_deterministic` main loop:
  - Added `in_structured_section = False` alongside `current_heading`, `current_kind`
  - On heading detection: `in_structured_section = _is_structured_section_heading(current_heading)`
  - Added `"claim_source": "deterministic"` to bullet, table, and paragraph claim dicts (was missing!)
  - Added `"in_structured_section": in_structured_section` to bullet, table, and paragraph claim dicts

### src/launcher/workers/understand/extract/_validation.py
- After `confidence = _CONFIDENCE_BY_SOURCE.get(claim_source, 0.75)`:
  - Added TC-4266 boost: if `claim_source == "deterministic"` and `raw.get("in_structured_section")`: `confidence = 0.70`
  - Constraint: never exceeds 0.70 (strictly below 0.75 verified threshold)

### src/launcher/workers/understand/worker.py
- **No change** — Option C chosen for Part B: Note's deterministic claims are `kind=api` from method docstrings, not from structured feature sections. `feature_blog` threshold unchanged.

---

## Tests

### tests/unit/workers/test_understand.py
- Updated `TestScoreDocPath.test_docs_dir`: now tests `docs/guide.md == 80` and `docs/api.md == 60`
- Updated `TestScoreDocPath.test_ordering`: adjusted ordering chain to account for API penalty

### tests/unit/workers/understand/test_extract.py
- Added `TestTC4265SyntaxValidAtConstruction` (4 tests):
  - `test_python_snippet_syntax_valid_not_none`
  - `test_python_snippet_syntax_invalid_false`
  - `test_syntax_valid_field_exists_on_snippet_model`
  - `test_non_python_snippet_syntax_valid_is_none`
- Added `TestTC4266ConfidenceTiering` (4 tests):
  - `test_structured_section_claim_confidence_070`
  - `test_generic_deterministic_claim_confidence_050`
  - `test_capabilities_heading_also_gets_070`
  - `test_confidence_never_exceeds_070_for_deterministic`
