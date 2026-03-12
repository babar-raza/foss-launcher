# EV-04 — Permalink Doubled Segments + Keyword Stuffing Precision

**Status:** Done (pre-existing)
**Gap linkage:** G-EV-07, G-EV-08
**Role:** Senior engineer. Drop-in, production-ready.

## Context

**G-EV-07:** The original plan specified P0 detection of doubled path segments in URLs (e.g., `/python/python/`, `/cells/cells/overview/`). The permalink check in `worker.py` only detects slug collisions between pages — it does not inspect frontmatter `url` fields for doubled segments. This defect was found in 2+ pilot files.

**G-EV-08:** The keyword stuffing detector in `artifacts.py:102` uses regex `\b[A-Z][a-z]+\.[A-Z][A-Za-z]+\b` which matches any PascalCase.PascalCase pattern (e.g., `System.Drawing`, `Path.Combine`, `Type.Method`). This produces false positives when content legitimately references .NET types or other dotted names that are not the product name.

## Scope

### Fix

**G-EV-07 — Doubled path segments:**
1. Add a per-page check for doubled path segments in frontmatter `url` field.
2. Location: either a new function in `semantic_structure.py` or a small addition to `check_seo.py` (which already parses frontmatter).
3. Best fit: add to `check_seo.py` since it already extracts frontmatter fields and validates URL/slug formatting.
4. Detection: Parse `url` from frontmatter → split on `/` → check for consecutive identical segments.
5. Severity: `high` (Defect 6 from content_review.md).

**G-EV-08 — Keyword stuffing precision:**
1. Replace generic PascalCase.PascalCase regex with product-name-aware detection.
2. Pass `product_name` kwarg to `check_artifacts` (update signature).
3. If `product_name` is provided, count only exact occurrences of that product name. If not provided, fall back to current generic pattern (backwards compatible).
4. Update `_run_deterministic_checks` to pass `product_name` to `check_artifacts`.

### Allowed paths
- `src/launcher/workers/evaluate/checks/seo.py`
- `src/launcher/workers/evaluate/checks/artifacts.py`
- `src/launcher/workers/evaluate/worker.py` (only the `_run_deterministic_checks` call to `check_artifacts`)
- `tests/unit/workers/test_evaluate.py`

### Forbidden
- Any other file/path

## Acceptance checks

- **CLI:** `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v` — all pass
- **Tests:**
  - `test_doubled_path_segment_detected`: Content with `url: /cells/cells/overview/` produces high-severity finding
  - `test_clean_url_no_finding`: Content with `url: /cells/python/overview/` produces no finding
  - `test_keyword_stuffing_product_specific`: Content with 20x "Aspose.Cells" in 50 words triggers stuffing
  - `test_keyword_stuffing_no_false_positive`: Content with "System.Drawing", "Path.Combine" does NOT trigger stuffing
- **Config respected end-to-end:** N/A
- **No mock data in production paths:** Product name comes from config, not hardcoded

## Deliverables

- Modified `seo.py` with doubled-segment detection in frontmatter `url`
- Modified `artifacts.py` with product-name-aware keyword stuffing
- Modified `worker.py` — pass `product_name` to `check_artifacts`
- New tests for both fixes + regression tests for false positives

## Hard rules

- Keep `check_seo` public signature unchanged (url is already in frontmatter it parses)
- `check_artifacts` signature gains optional `product_name` kwarg — backward compatible
- No network in offline tests
- No new deps
- Deterministic

## Review dimensions — what 5/5 means

| Dimension | 5/5 Criteria |
|-----------|-------------|
| Correctness | `/python/python/` flagged; `/python/overview/` not flagged; `System.Drawing` not flagged as stuffing |
| Robustness | Missing `url` field gracefully skipped; empty product_name falls back to generic detection |
| Testability | Each fix has positive + negative test cases |
| Minimality | Doubled-segment check is <15 lines in seo.py; stuffing fix is regex swap in artifacts.py |
| Integration | Both changes fit existing check patterns; no new files needed |

## Now (runbook)

```bash
# 1. Read seo.py to understand existing frontmatter parsing
cat src/launcher/workers/evaluate/checks/seo.py

# 2. Add doubled-segment check after existing URL validation in check_seo:
#    url = ... (already parsed)
#    if url:
#        segments = [s for s in url.split("/") if s]
#        for i in range(len(segments) - 1):
#            if segments[i] == segments[i + 1]:
#                findings.append(Finding(
#                    check="seo", message=f"Doubled path segment: '/{segments[i]}/{segments[i]}/'",
#                    severity="high", location=slug,
#                ))

# 3. Update artifacts.py check_artifacts signature:
#    def check_artifacts(content: str, slug: str, *, product_name: str = "") -> list[Finding]:
#    Replace generic regex with:
#    if product_name:
#        mentions = prose.lower().count(product_name.lower())
#    else:
#        mentions = len(re.findall(r"\b[A-Z][a-z]+\.[A-Z][A-Za-z]+\b", prose))

# 4. Update worker.py _run_deterministic_checks:
#    check_artifacts(content, slug, product_name=product_name)

# 5. Write tests

# 6. Run tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py -v

# 7. Full suite
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=short -q
```
