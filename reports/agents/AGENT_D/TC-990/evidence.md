# TC-990 Evidence: Specs & Schemas -- Template Structure Ground Truth

**Agent**: Agent-D (Docs & Specs)
**Taskcard**: TC-990
**Date**: 2026-02-05
**spec_ref**: fad128dc63faba72bad582ddbc15c19a4c29d684

## Files Changed

### 1. `specs/07_section_templates.md`

**Lines 167-178 (V2 template root)**:
- Removed: Blog V2 path was `specs/templates/blog.aspose.org/<family>/<platform>/...` (incorrectly included `__PLATFORM__`)
- Added: Corrected Blog V2 path to `specs/templates/blog.aspose.org/<family>/__POST_SLUG__/...` (NO platform, NO locale)
- Added: Explicit "Blog exception (binding)" note stating blog does NOT use `__PLATFORM__` or `__LOCALE__`

**Lines 566-608 (Template Discovery and Filtering)**:
- Removed: Blog "correct" structure showing `__PLATFORM__/__POST_SLUG__/...` path
- Added: Corrected blog structure using only `__POST_SLUG__/index.variant-*.md`
- Added: Blog filtering rule #1 now explicitly excludes `__PLATFORM__` in path (was only excluding `__LOCALE__`)
- Added: Obsolete structure examples showing both `__PLATFORM__` and `__LOCALE__` as WRONG for blog
- Updated: Related fixes section to include TC-990

**Lines 610-678 (NEW: Target V2 Template File Structure)**:
- Added: Complete ground truth tables for all 5 subdomains (DOCS, PRODUCTS, KB, BLOG, REFERENCE)
- Added: Each table shows template path, content type, Hugo type, and notes
- Added: Blog constraints (binding) -- MUST NOT contain `__PLATFORM__` or `__LOCALE__`
- Added: Obsolete Patterns section explicitly deprecating `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__`

**Line 444 (KB Template Location)**:
- Removed: `__TOPIC_SLUG__.variant-feature-showcase.md`
- Added: `howto.variant-*.md` (matches ground truth KB template naming)

### 2. `specs/21_worker_contracts.md`

**Lines 198-208 (W4 IAPlanner binding requirements)**:
- Added: New binding requirement for page_role derivation from template filename prefix
- Rules: `_index*` -> context-dependent (toc/landing/comprehensive_guide), `index*` (blog) -> landing, `feature*` -> workflow_page, `howto*` -> feature_showcase, `reference*` -> api_reference, `installation*`/`license*`/`getting-started*` -> workflow_page
- Cross-reference to `specs/07_section_templates.md` ground truth

### 3. `specs/schemas/page_plan.schema.json`

**No changes needed**: The `page_role` enum already contains all 7 required values:
`landing`, `toc`, `comprehensive_guide`, `workflow_page`, `feature_showcase`, `troubleshooting`, `api_reference`

### 4. `specs/06_page_planning.md`

**No changes needed**: No references to `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__`, or incorrect blog+platform patterns found.

## Grep Verification

### Stale placeholders in spec files (non-template):

```
grep __CONVERTER_SLUG__|__FORMAT_SLUG__|__SECTION_PATH__ specs/07_section_templates.md
  -> Only in "Obsolete Patterns" deprecation section (correct)

grep __CONVERTER_SLUG__|__FORMAT_SLUG__|__SECTION_PATH__ specs/21_worker_contracts.md
  -> No matches (correct)

grep __CONVERTER_SLUG__|__FORMAT_SLUG__|__SECTION_PATH__ specs/06_page_planning.md
  -> No matches (correct)

grep __CONVERTER_SLUG__|__FORMAT_SLUG__|__SECTION_PATH__ specs/schemas/page_plan.schema.json
  -> No matches (correct)
```

### Blog + __PLATFORM__ in spec files:

```
grep "blog.*__PLATFORM__|__PLATFORM__.*blog" specs/07_section_templates.md
  -> Only in "WRONG" examples and exclusion rules (correct)

grep "blog.*__PLATFORM__|__PLATFORM__.*blog" specs/06_page_planning.md
  -> No matches (correct)
```

## What Was NOT Changed (per TC-990 scope)

- Template files under `specs/templates/` (TC-991/TC-992 scope)
- W4/W5 code under `src/launch/workers/` (TC-993/TC-994 scope)
- `specs/rulesets/ruleset.v1.yaml` (already correct)
- Template README files under `specs/templates/*/README.md` (legacy documentation for existing template sets)

## Acceptance Criteria Met

1. V2 template root section corrected: Blog no longer claims `__PLATFORM__`
2. Template Discovery section corrected: Blog exclusion now covers both `__PLATFORM__` and `__LOCALE__`
3. Ground truth tables added: All 5 subdomains documented with binding template hierarchies
4. Obsolete patterns documented: `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__` explicitly deprecated
5. W4 page_role derivation rules added to worker contract
6. page_plan.schema.json verified: all required page_role values present
7. KB template location updated from `__TOPIC_SLUG__` to `howto.variant-*`
