# SEO-03: Type Safety — Protocol Types + Public Entity Stripper

## Status: Done

## Gap Linkage
- **G-04**: `_strip_html_entities` imported as private cross-module — fragile coupling
- **G-05**: `Any` typing for `keyword_bundle` and `gemini_client` — no contract safety

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. **Make `_strip_html_entities` public** in `slug_engine.py`:
   - Rename to `strip_html_entities` (remove leading underscore)
   - Update ALL internal callers within `slug_engine.py` (3 call sites)
   - Update the import in `seo_metadata.py`
   - Keep backward compat: add `_strip_html_entities = strip_html_entities`
     alias at module level (existing private callers outside the module won't break)

2. **Create `SEOProtocols`** in a new section at top of `seo_metadata.py`
   (no new file — keep it co-located with the only consumer):
   ```python
   from typing import Protocol, runtime_checkable

   @runtime_checkable
   class KeywordBundleLike(Protocol):
       primary_keywords: list[str]
       per_page: dict[str, list[str]]

   @runtime_checkable
   class GeminiClientLike(Protocol):
       @property
       def available(self) -> bool: ...
       def generate_description(self, title: str, product_name: str, claims_summary: str) -> str: ...
   ```
   Replace `Any` with these protocols in `optimize_seo_metadata`, `_generate_description`,
   and `_enhance_keywords` signatures.

3. Update `plan.py` `_generate_seo_keywords` to use `KeywordBundleLike | None`
   instead of `Any`.

### Allowed paths
- `src/launcher/shared/slug_engine.py` (rename + alias)
- `src/launcher/workers/generate/seo_metadata.py` (protocol + import update)
- `src/launcher/workers/planner/plan.py` (type annotation update)
- `tests/unit/workers/test_seo_metadata.py` (verify protocol compliance)
- `plans/healing/SEO-03-type-safety.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- Existing tests must pass without modification (backward compat alias works)
- New test: `test_keyword_bundle_protocol_compliance` — verify that
  `KeywordResearchBundle` from `keyword_research.py` satisfies `KeywordBundleLike`
  at runtime via `isinstance` check
- New test: `test_gemini_client_protocol_compliance` — verify that
  `GeminiSEOClient` satisfies `GeminiClientLike` at runtime

### Config respected end-to-end
- N/A

### No mock data in production paths
- Protocol types are structural, no mock data

## Deliverables
- Renamed `strip_html_entities` with backward-compat alias in `slug_engine.py`
- Protocol types in `seo_metadata.py`
- Updated type annotations in `seo_metadata.py` and `plan.py`
- 2 new protocol compliance tests

## Hard Rules
- Keep public signatures backward-compatible (alias for old private name)
- Update all call sites for the renamed function
- No network in tests
- No new deps (Protocol is stdlib `typing`)
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Consistency | All SEO code uses Protocol types, not Any |
| Maintainability | IDE autocompletion and type checking work for keyword_bundle/gemini_client |
| Integration | Backward-compat alias prevents breakage in any caller of `_strip_html_entities` |
| Correctness | Protocol matches actual interface of KeywordResearchBundle and GeminiSEOClient |
| Minimality | Only type annotations + rename, no behavioral changes |

## Runbook

```bash
# 1. Rename _strip_html_entities -> strip_html_entities in slug_engine.py
# 2. Add backward-compat alias
# 3. Update 3 internal callers in slug_engine.py
# 4. Update import in seo_metadata.py
# 5. Add Protocol types to seo_metadata.py
# 6. Update type annotations in seo_metadata.py and plan.py
# 7. Add 2 protocol compliance tests
# 8. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 9. Mark Done
```
