# SEO-02: Keyword Density Body-Presence Check in Evaluate

## Status: Done

## Gap Linkage
- **G-03**: Keyword density/body-presence check missing from Evaluate (plan spec)

## Role
Senior engineer. Drop-in, production-ready.

## Scope

### Fix
1. Add a keyword body-presence check to `check_seo()` in `seo.py`:
   scan the first 2000 characters of markdown body (after frontmatter closing
   `---`) for the presence of at least 1 keyword from the page's `keywords`
   list. If no keywords appear in body text, emit a `low` severity finding.
2. Skip the check for `_index` pages and pages with empty keyword lists.
3. The scan should be case-insensitive and only check prose (not code fences).

### Allowed paths
- `src/launcher/workers/evaluate/checks/seo.py`
- `tests/unit/workers/test_seo_check.py`
- `plans/healing/SEO-02-keyword-density-check.md`

### Forbidden
Any other file/path.

## Acceptance Checks

### CLI
- `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q` — all pass

### Tests
- New test: `test_keyword_found_in_body_no_finding` — content body contains a
  keyword from the list. Verify no "keyword" finding emitted.
- New test: `test_keyword_missing_from_body` — content body has no keywords.
  Verify finding with "No keywords found in page body" message.
- New test: `test_keyword_check_skipped_for_index` — `_index` slug with no
  keywords in body. Verify no keyword-body finding.
- New test: `test_keyword_check_case_insensitive` — keyword is "Python",
  body contains "python". Verify no finding (case-insensitive match).

### Config respected end-to-end
- N/A

### No mock data in production paths
- Test content strings only in test files

## Deliverables
- Updated `check_seo()` with keyword body-presence check (~15 lines)
- 4 new tests in `test_seo_check.py`

## Hard Rules
- Keep `check_seo` public signature unchanged
- No network in tests
- Deterministic (string operations only)
- No new deps
- Code/tests in sync

## Review Dimensions — What 5/5 Means

| Dimension | 5/5 Definition |
|-----------|----------------|
| Thoroughness | Body scan handles code fences, empty body, empty keywords |
| Correctness | Case-insensitive matching, 2000-char cap, skip index pages |
| Spec alignment | Matches plan: "keyword density check: Scan body for keyword presence" |
| Performance | 2000-char cap prevents expensive full-body scans |
| Testability | 4 tests covering present/absent/index/case scenarios |
| Minimality | Only the body-presence check added, no other changes |

## Runbook

```bash
# 1. Add keyword body-presence logic to check_seo() in seo.py
# 2. Add 4 tests to test_seo_check.py
# 3. Run targeted tests
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_seo_check.py -x -v
# 4. Run existing seo tests to verify no regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_evaluate.py::TestCheckSeo -x -v
# 5. Full regression
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x -q
# 6. Mark Done
```
