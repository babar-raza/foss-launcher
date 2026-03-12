# AQ-03 — Page-Relevant Class Selection in API Surface Prompt

**Status**: Done
**Gap linkage**: GAP-03 (High — all pages get same 15 classes regardless of topic)
**Role**: Senior engineer. Drop-in, production-ready.

## Context

The plan (Change A) explicitly states: "For each page, prioritize classes mentioned in the page's assigned claims. A reference page about `Document` gets Document's full method list; a howto page about PDF export gets `PdfSaveOptions` and `PdfExporter`."

Current implementation in `_format_api_surface()` takes the first 15 classes from `public_classes` for ALL pages identically. A page about PDF export may not see `PdfSaveOptions` if it's class #16+ in the sorted list. This defeats the purpose of rich briefs for targeted pages.

## Scope

### Fix

In `build_section_prompt()`, before calling `_format_api_surface()`, filter/prioritize `class_briefs` based on the page's assigned claims. Classes mentioned by name in claim text get priority, then backfill remaining classes up to cap.

### Allowed paths
- `src/launcher/workers/generate/section_prompt.py`
- `tests/unit/workers/generate/test_section_prompt.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/ -q --tb=short` — all pass
- **Tests**: Page with claims mentioning "Document" → `Document` ClassBrief appears in top 5 of prompt
- **Tests**: Page with claims mentioning "PdfSaveOptions" → `PdfSaveOptions` in prompt even if it's class #30
- **Tests**: Page with no matching classes → falls back to first 15 (existing behavior)
- **No mock data in production paths**: Uses real Claim/ClassBrief objects

## Deliverables

1. New function `_prioritize_class_briefs(class_briefs, page_claims)` in `section_prompt.py`
2. Call it from `build_section_prompt()` before `_format_api_surface()`
3. Tests for priority ordering, fallback, and cap behavior

## Hard rules

- Keep public signatures unless justified; update all call sites
- No network in offline tests
- Deterministic runs (seed/stable ordering) — priority classes sorted alphabetically within tier
- No new deps without explicit justification
- Keep code/docs/tests in sync

## Review dimensions — what 5/5 means

| Dimension | 5/5 target |
|-----------|-----------|
| Correctness & spec alignment | Plan says "prioritize classes mentioned in the page's assigned claims" — exactly that |
| Production grading | Every page gets contextually relevant API surface, not a generic dump |
| Robustness | Empty claims → full fallback; empty class_briefs → empty; no crashes |
| Performance | O(n*m) where n=claims, m=briefs — both capped, so negligible |
| Minimality | One new helper function + one call site change + tests |

## Now (runbook)

```bash
# 1. Add _prioritize_class_briefs() to section_prompt.py:
#    def _prioritize_class_briefs(class_briefs, page_claims, cap=15):
#        """Reorder class_briefs: claim-mentioned classes first, then rest."""
#        claim_text = " ".join(c.text for c in page_claims).lower()
#        mentioned = [b for b in class_briefs if b.name.lower() in claim_text]
#        rest = [b for b in class_briefs if b not in mentioned]
#        return (mentioned + rest)[:cap]

# 2. In build_section_prompt(), before _format_api_surface() call:
#    if class_briefs:
#        class_briefs = _prioritize_class_briefs(class_briefs, page_claims)

# 3. Add tests

# 4. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/generate/test_section_prompt.py -v --tb=short

# 5. Run full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -q --tb=short
```
