# TC-2444 Evidence — Agent E: limitations_renderer.py

**Date**: 2026-02-23
**Agent**: Agent_E

---

## Deliverables

### 1. `src/launch/workers/w5_section_writer/renderers/limitations_renderer.py`

New module providing structured Limitations section rendering:

Feature flag: `LAUNCH_STRUCTURED_LIMITATIONS=json|freeform` (default: freeform)
In freeform mode (default): module functions available but NOT called by W5.
In json mode: LLM generates JSON, this module parses + renders deterministic markdown.
Falls back to freeform on any parse/validation failure.

**Functions implemented:**
- `is_structured_mode() -> bool` — reads `_STRUCTURED_MODE` module variable (set from env var at import time); returns `True` only when `== "json"`
- `parse_limitations_json(raw: str) -> Optional[List[Dict]]` — handles bare JSON array, fenced JSON, leading prose; validates title ≥3 chars, description ≥10 chars; returns `None` on any failure
- `render_limitations_to_markdown(items, product_name, claim_ids=None) -> str` — deterministic: intro sentence + bold title + description + optional workaround + claim comment markers
- `LLM_JSON_PROMPT_ADDENDUM` — constant string appended to LLM prompt to request JSON array output

**Edge cases handled:**
- Bare JSON array / fenced JSON / leading prose
- Null and empty workaround → None
- Short title/description items → filtered out; all-invalid → None (freeform fallback)

### 2. `src/launch/workers/w5_section_writer/renderers/__init__.py`

Empty package marker created.

### 3. `tests/unit/workers/test_w5_limitations_renderer.py`

29 tests across 4 classes:
- `TestParseLimitationsJson` (12) — parse variants, validation rejects
- `TestRenderLimitationsToMarkdown` (10) — rendering, determinism, bold format
- `TestIsStructuredMode` (3) — json/freeform/unknown modes
- `TestFeatureFlagEnvVar` (3) — monkeypatch env var tests, sanitizer integration

---

## Acceptance Check Results

- [x] `pytest tests/unit/workers/test_w5_limitations_renderer.py` — **29 passed, 0 failures**
- [x] `render_limitations_to_markdown(items, name)` called twice → identical output
- [x] `parse_limitations_json("")` returns `None` (not exception)
- [x] Code fence stripping works (`parse_limitations_json("```json\n[...]\n```")`)
- [x] `render_limitations_to_markdown([], "Aspose.3D")` returns non-empty fallback
- [x] `is_structured_mode()` returns `False` by default
