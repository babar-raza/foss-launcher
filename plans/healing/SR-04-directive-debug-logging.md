# SR-04: Add Debug Logging for Directive Selection

**Status**: Open
**Gap**: `_get_structure_directive()` silently returns an empty string when no directive matches. No logging means unmatched headings are invisible during runs — the LLM gets no structural guidance and the operator has no signal.

## Scope

- `src/launcher/workers/generate/section_prompt.py` — `_get_structure_directive()`
- `src/launcher/workers/generate/worker.py` — template resolution path

## Acceptance Checks

1. `_get_structure_directive()` logs at DEBUG level when returning a matched directive (heading → directive key)
2. `_get_structure_directive()` logs at WARNING level when no directive matches (includes the unmatched heading text)
3. Template resolution in worker logs at INFO level: which template was selected (or "no template, using skeleton fallback")
4. Log messages include page_role and section_heading for traceability

## Deliverables

| # | File | Change |
|---|------|--------|
| 1 | `section_prompt.py` | Add logger; log matched/unmatched directives |
| 2 | `worker.py` | Log template resolution outcome |

## Hard Rules

- DEBUG for routine matches, WARNING for missing directives
- Do NOT add INFO-level logging for every section — only template resolution decisions
- Log messages must include enough context to identify the page and section

## Runbook

```bash
# 1. Add logging to _get_structure_directive()
# 2. Add logging to template resolution in worker.py
# 3. Run pilot with DEBUG logging to verify messages appear:
#    PYTHONHASHSEED=0 LOG_LEVEL=DEBUG .venv/Scripts/python.exe -m launcher ...
# 4. Run: PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest -v
```
