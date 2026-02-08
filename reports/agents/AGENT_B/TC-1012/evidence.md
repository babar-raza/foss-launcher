# TC-1012 Evidence: Fix expected_page_plan.json cross_links to ABSOLUTE URLs

## Date
2026-02-07

## Agent
Agent-B

## Summary
Updated both pilot expected_page_plan.json files to use absolute URLs in cross_links, matching W4 IAPlanner output after TC-1001.

## Files Changed
- `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json` -- Updated 3 cross_links to absolute
- `specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json` -- Updated 3 cross_links to absolute
- `plans/taskcards/TC-1012_fix_cross_links_absolute.md` -- Created taskcard

## Changes Detail

### pilot-aspose-3d-foss-python/expected_page_plan.json
| Page | Section | Old cross_link | New cross_link |
|------|---------|---------------|----------------|
| getting-started | docs | `/3d/python/api-overview/` | `https://reference.aspose.org/3d/python/api-overview/` |
| faq | kb | `/3d/python/getting-started/` | `https://docs.aspose.org/3d/python/getting-started/` |
| announcement | blog | `/3d/python/overview/` | `https://products.aspose.org/3d/python/overview/` |

### pilot-aspose-note-foss-python/expected_page_plan.json
| Page | Section | Old cross_link | New cross_link |
|------|---------|---------------|----------------|
| getting-started | docs | `/note/python/api-overview/` | `https://reference.aspose.org/note/python/api-overview/` |
| faq | kb | `/note/python/getting-started/` | `https://docs.aspose.org/note/python/getting-started/` |
| announcement | blog | `/note/python/overview/` | `https://products.aspose.org/note/python/overview/` |

## Cross-link Direction Mapping (from add_cross_links in W4)
- `docs` pages link to `reference` pages -> subdomain: reference.aspose.org
- `kb` pages link to `docs` pages -> subdomain: docs.aspose.org
- `blog` pages link to `products` pages -> subdomain: products.aspose.org

## Commands Run

### JSON validation
```
.venv/Scripts/python.exe -c "import json; json.load(open('specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json')); json.load(open('specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json')); print('Both JSON files valid')"
```
Output: Both JSON files valid

### Cross-link verification
```
.venv/Scripts/python.exe -c "import json; d3=json.load(open('specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json')); dn=json.load(open('specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json')); [print(f'3D {p[\"section\"]}/{p[\"slug\"]}: {p[\"cross_links\"]}') for p in d3['pages'] if p['cross_links']]; [print(f'Note {p[\"section\"]}/{p[\"slug\"]}: {p[\"cross_links\"]}') for p in dn['pages'] if p['cross_links']]"
```
Output:
```
3D docs/getting-started: ['https://reference.aspose.org/3d/python/api-overview/']
3D kb/faq: ['https://docs.aspose.org/3d/python/getting-started/']
3D blog/announcement: ['https://products.aspose.org/3d/python/overview/']
Note docs/getting-started: ['https://reference.aspose.org/note/python/api-overview/']
Note kb/faq: ['https://docs.aspose.org/note/python/getting-started/']
Note blog/announcement: ['https://products.aspose.org/note/python/overview/']
```

### Full test suite
```
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ -x
```
Result: 1916 passed, 12 skipped, 0 failures (96.55s)

## Deterministic Verification
- URLs exactly match build_absolute_public_url() output format: `https://{subdomain}/{product}/{platform}/{slug}/`
- All URLs have trailing slash (per _normalize_path())
- Subdomain mapping verified against public_urls.py subdomain_map dict
- No non-cross_links fields were modified in either file
