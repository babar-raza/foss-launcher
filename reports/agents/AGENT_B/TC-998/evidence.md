# TC-998 Evidence Report

## Taskcard
- **ID:** TC-998
- **Title:** Fix Stale expected_page_plan.json url_path Values
- **Agent:** Agent-B
- **Date:** 2026-02-06

## Problem Statement

The expected_page_plan.json files in specs/pilots/ contained stale url_path values that included section names (docs, kb, blog, reference, products) in the path. Per specs/33_public_url_mapping.md, section names belong in subdomains (e.g., kb.aspose.org), not in the URL path. The correct format is `/<family>/<platform>/<slug>/`.

## Changes Made

### File: specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json

| Field | Before | After |
|-------|--------|-------|
| url_path (getting-started) | `/3d/python/docs/getting-started/` | `/3d/python/getting-started/` |
| url_path (api-overview) | `/3d/python/reference/api-overview/` | `/3d/python/api-overview/` |
| url_path (faq) | `/3d/python/kb/faq/` | `/3d/python/faq/` |
| url_path (announcement) | `/3d/python/blog/announcement/` | `/3d/python/announcement/` |
| cross_link (getting-started page) | `/3d/python/reference/api-overview/` | `/3d/python/api-overview/` |
| cross_link (faq page) | `/3d/python/docs/getting-started/` | `/3d/python/getting-started/` |

### File: specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json

| Field | Before | After |
|-------|--------|-------|
| url_path (getting-started) | `/note/python/docs/getting-started/` | `/note/python/getting-started/` |
| url_path (api-overview) | `/note/python/reference/api-overview/` | `/note/python/api-overview/` |
| url_path (faq) | `/note/python/kb/faq/` | `/note/python/faq/` |
| url_path (announcement) | `/note/python/blog/announcement/` | `/note/python/announcement/` |
| cross_link (getting-started page) | `/note/python/reference/api-overview/` | `/note/python/api-overview/` |
| cross_link (faq page) | `/note/python/docs/getting-started/` | `/note/python/getting-started/` |

## Verification Results

### 1. JSON Validation

```
$ .venv/Scripts/python.exe -c "import json; json.load(open('specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json')); print('3D OK')"
3D OK

$ .venv/Scripts/python.exe -c "import json; json.load(open('specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json')); print('Note OK')"
Note OK
```

### 2. Section Name Pattern Search

```
$ grep -E '"url_path".*/(docs|kb|blog|reference|products)/' specs/pilots/*/expected_page_plan.json
# No output (as expected - no matches found)
```

## Summary of Changes

- **Total files modified:** 2
- **Total url_path fields fixed:** 8 (4 per file)
- **Total cross_links fixed:** 4 (2 per file)
- **Total edits:** 12

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| All url_path values in 3D pilot corrected | PASS |
| All url_path values in Note pilot corrected | PASS |
| No url_path contains section name (docs, kb, blog, reference, products) | PASS |
| JSON files remain valid after edits | PASS |
| cross_links also checked and fixed | PASS |
| Changes match spec 33 URL format | PASS |

## Spec Reference

Per specs/33_public_url_mapping.md lines 344-350:
- URL format: `/<family>/<platform>/<slug>/`
- Section (docs, kb, blog, reference, products) is encoded in the subdomain
- Example: `https://kb.aspose.org/3d/python/faq/` (section=kb is in subdomain)
