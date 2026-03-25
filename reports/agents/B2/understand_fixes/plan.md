# Agent B2 — Understand Fixes Plan

## TC-4265: syntax_valid population at Snippet construction

**Goal**: Add `syntax_valid: bool | None` to `Snippet` model and populate it at every `Snippet(...)` construction site.

**Approach**:
1. Add field to `src/launcher/models/claims.py`
2. Set in `_snippets.py` at both Snippet construction sites (fenced blocks + source files)
3. Python: `True` if reached (already validated), `False` if empty code
4. TypeScript/JS: delegate to `ts_analyzer.validate_snippet` if available, else `None`
5. Other languages: `None` (unknown — do not assume invalid)
6. Add tests in `test_extract.py`

## TC-4266: Deterministic claim confidence tiering + Note snippet concentration

### Part A: Confidence tiering in _deterministic.py
- Add `_STRUCTURED_SECTION_HEADINGS` frozenset constant
- Add `_normalize_heading_key()` and `_is_structured_section_heading()` helpers
- Track `in_structured_section` flag during markdown parsing
- Add `in_structured_section` to claim dicts
- In `_validation.py`, boost deterministic claims from structured sections to `confidence=0.70`
- Also add `claim_source="deterministic"` to bullet/table/paragraph claims (was missing)

### Part B: Note snippet source assessment
- Read `phase_store/note/python/understand.json` to check deterministic claims
- Finding: All Note deterministic claims are `kind=api, confidence=0.5`, from method docstrings
- They do NOT come from structured feature sections — no heading context
- Decision: **Option C** (leave `feature_blog` threshold unchanged)

### Part C: Note snippet source concentration
- Top sources: `docs/onenote-api.md` (20), `README.md` (13), 3 example files (1 each)
- Current scoring does NOT penalize API reference docs
- Fix: Apply `-20` penalty to `_score_doc_path` for stems containing "api" or "reference"
- Update tests to match new expected scores

### Part D: Tests
- Add `TestTC4265SyntaxValidAtConstruction` class (4 tests)
- Add `TestTC4266ConfidenceTiering` class (4 tests)
