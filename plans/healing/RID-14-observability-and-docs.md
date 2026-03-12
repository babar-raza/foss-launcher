# RID-14: Slug Sanitization Observability + Docstring Context

## Status: Done

## Gap Linkage
- G-RV3-06: No logging when `_sanitize_slug` transforms values; docstring missing MAX_PATH and `aspose-` stripping rationale

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix

1. **Add debug-level logging in `generate_run_id()`**: When `_sanitize_slug(family)`
   produces a value different from `family.lower()`, log at DEBUG:
   `"Sanitized family %r → %r", family, fam`. Same for platform.
   This helps diagnose unexpected directory names without cluttering INFO output.

2. **Expand `generate_run_id()` docstring**:
   - Document the full format including hex suffix (after RID-11 lands):
     ``YYMMDD_HHMMSS_{family}_{platform}_{hex4}``
   - Explain MAX_PATH budget: "Kept under ~35 chars to stay well within Windows
     MAX_PATH (260) when combined with deep `content_bundle/` paths (longest
     observed: ~200 chars at the run-dir level)."
   - Explain `aspose-` stripping: "The `aspose-` prefix is stripped from family
     names because all products share this prefix — it adds no discriminating
     information but costs 7 chars."

3. **Add inline comment on `max_len=16`**: Explain the budget:
   `# 16 chars max keeps worst-case run_id under 40 chars total`

### Allowed paths
- `src/launcher/util/run_id.py`

### Forbidden
- Any other file/path

## Acceptance Checks

### CLI
- `python -c "import logging; logging.basicConfig(level=logging.DEBUG); from launcher.util.run_id import generate_run_id; generate_run_id('aspose-cells', 'python')"` shows DEBUG log with `Sanitized family 'aspose-cells' → 'cells'`
- No DEBUG log for `generate_run_id('cells', 'python')` (no transformation)

### Tests
- Existing `test_run_id.py` still passes (no behavioral change)
- No new tests needed (logging is observability, not behavior)

### Config respected end-to-end
- DEBUG logging only fires when `logging.DEBUG` is active (no perf impact at INFO)

### No mock data in production paths
- N/A (documentation + logging only)

## Deliverables
- Updated `src/launcher/util/run_id.py` with logging + expanded docstring + inline comment

## Hard Rules
- Log at DEBUG only (not INFO/WARNING)
- No behavioral changes — only documentation and observability
- No new deps (`logging` is stdlib)
- Keep `_sanitize_slug` as a pure function — logging happens in caller `generate_run_id`

## Review Dimensions — what 5/5 means for this taskcard

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Observability | Slug transformations visible at DEBUG; rationale documented in docstring |
| Maintainability | New engineer can understand format, MAX_PATH budget, and prefix stripping from docstring alone |
| Performance | Zero overhead at INFO level (lazy % formatting) |
| Minimality | ~10 lines added to one file, no behavioral changes |
| Scope adherence | Single file, documentation + logging only |

## Now (Runbook)

```bash
# 1. Add `import logging` and `logger = logging.getLogger(__name__)` to run_id.py
# 2. Add debug logging in generate_run_id after sanitization
# 3. Expand docstring with MAX_PATH and aspose- rationale
# 4. Add inline comment on max_len=16
# 5. Run tests (no changes expected)
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/util/test_run_id.py -v
# 6. Verify debug output
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from launcher.util.run_id import generate_run_id; generate_run_id('aspose-cells', 'python')"
```
