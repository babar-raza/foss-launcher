# TC-1002 Evidence: Document Absolute cross_links in Specs/Schemas

## Summary

Updated specs and schemas to document that `cross_links` contains absolute URLs rather than relative paths. This documents the change implemented in TC-1001.

## Files Modified

### 1. specs/schemas/page_plan.schema.json

**Change**: Updated `cross_links` definition with description and URI format.

**Before**:
```json
"cross_links": { "type": "array", "items": { "type": "string" } },
```

**After**:
```json
"cross_links": {
  "type": "array",
  "description": "Absolute URLs to related pages on other subdomains (e.g., https://docs.aspose.org/cells/python/overview/). Format: https://<subdomain>/<family>/<platform>/<slug>/",
  "items": { "type": "string", "format": "uri" }
},
```

**Rationale**: Adding `format: uri` enables JSON Schema validators to validate that cross_links values are proper URIs. The description explicitly documents the expected format.

### 2. specs/06_page_planning.md

**Change**: Added new "cross_links format (binding)" section after Path distinction.

**Content added**:
- Format specification: `https://<subdomain>/<family>/<platform>/<slug>/`
- Example: `https://docs.aspose.org/cells/python/overview/`
- List of supported subdomains (docs, kb, blog, products, reference)
- Rationale explaining why absolute URLs are necessary in subdomain architecture
- Schema reference pointer

**Location**: After line 22 (after "Path distinction" block)

### 3. specs/21_worker_contracts.md

**Change**: Added `cross_links` bullet point to W4 IAPlanner binding requirements.

**Content added**:
```markdown
- `cross_links`: array of **absolute URLs** to related pages across subdomains
  (e.g., `https://docs.aspose.org/cells/python/overview/`).
  Format: `https://<subdomain>/<family>/<platform>/<slug>/`.
  See `specs/06_page_planning.md` "cross_links format" section.
```

**Location**: In W4 IAPlanner "MUST define for each planned page" list

## Verification

### Schema Validation
```bash
.venv/Scripts/python.exe -c "import json; json.load(open('specs/schemas/page_plan.schema.json')); print('Schema valid')"
```

### Cross-Reference Consistency
All three files now consistently document:
1. cross_links contains absolute URLs
2. Format is `https://<subdomain>/<family>/<platform>/<slug>/`
3. Example: `https://docs.aspose.org/cells/python/overview/`

## Dependency Chain

- **Upstream**: TC-1001 (implements absolute cross_links in W4 code)
- **This taskcard**: TC-1002 (documents the format in specs/schemas)
- **Downstream**: Future consumers of page_plan.json understand cross_links format

## Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| Schema describes cross_links as absolute URLs | PASS |
| Specs document cross_links format with examples | PASS |
| W4 contract mentions absolute URL output | PASS |
| Format constraint added (`format: uri`) | PASS |
| Example URLs included | PASS |
| All cross-references consistent | PASS |

## Artifacts

- `specs/schemas/page_plan.schema.json` - cross_links with format: uri
- `specs/06_page_planning.md` - cross_links format section
- `specs/21_worker_contracts.md` - W4 outputs mention absolute URLs
