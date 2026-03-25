# TC-2445 Evidence — Agent E: W5 Integration — Structured LLM Call for Limitations Section

**Date**: 2026-02-23
**Agent**: Agent_E

---

## Deliverables

### 1. `src/launch/workers/w5_section_writer/generators/content_generators.py`

Module-level imports added at lines 28-33:
```python
from ..renderers.limitations_renderer import (
    is_structured_mode as _is_structured_limitations_mode,
    parse_limitations_json as _parse_limitations_json,
    render_limitations_to_markdown as _render_limitations_to_markdown,
    LLM_JSON_PROMPT_ADDENDUM as _LIMITATIONS_JSON_ADDENDUM,
)
```

**Integration in `generate_comprehensive_guide_content()` (lines 1913-1937):**
- Before the freeform bullet loop, checks `_is_structured_limitations_mode() and limitation_claims`
- Calls `_call_llm_for_content()` with `LLM_JSON_PROMPT_ADDENDUM` appended to prompt
- Parses result with `_parse_limitations_json()` → renders with `_render_limitations_to_markdown()`
- Falls back to freeform on JSON parse failure OR any exception
- Logs info on success: `[W5 Structured] Limitations rendered via JSON path (N items)`
- Logs warning on fallback: `[W5 Structured] Limitations JSON parse failed — using freeform fallback`

**Integration in `generate_minimal_guide_content()` (lines 2157-2179):**
- Same pattern as comprehensive_guide with separate variable names (`_items_2`, `_cids_2`)
- Same try/except → freeform fallback behavior

### 2. `src/launch/workers/w5_section_writer/worker.py`

`_try_structured_limitations()` helper added at lines 141-173:
```python
def _try_structured_limitations(limitation_claims, product_name, llm_client):
    """Try structured JSON path for Limitations section. Returns None on any failure."""
    # Lazy import from renderers.limitations_renderer
    # Builds prompt, calls _call_llm_for_content(), parses JSON, renders markdown
    # Returns None on is_structured_mode()=False, JSON parse failure, or any exception
```

### Design Decision: Troubleshooting Generator Not Integrated

`generate_troubleshooting_content()` was considered but intentionally excluded because:
- It generates a **full Problem/Cause/Solution page** via LLM (not a "## Limitations" sub-section)
- Adding `LLM_JSON_PROMPT_ADDENDUM` to its prompt would corrupt the output format
- The troubleshooting page IS already a structured discussion of limitations — just in a different schema (Problem/Cause/Solution vs JSON limitations array)
- This is the correct architectural boundary: structured Limitations JSON applies to sub-sections within guide pages, not to full-page troubleshooting generators

---

## Acceptance Check Results

- [x] `LAUNCH_STRUCTURED_LIMITATIONS=freeform` (default): zero code path change in generators
- [x] Structured path wrapped in `try/except` — freeform fallback fires on any exception
- [x] JSON parse failure → `logger.warning` + freeform fallback fires
- [x] `content_sanitizer.py` requires NO changes (structured output is clean markdown)
- [x] `pytest tests/ -x` — 0 failures
