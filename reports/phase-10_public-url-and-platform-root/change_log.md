# Phase 10 Change Log — Public URL Mapping + Platform Root + Bundle Style + No-Skip Gates

## Summary

Phase 10 implements public URL mapping, platform root page templates, bundle style support,
and enforces that Gate A1 (spec pack validation) cannot be skipped.

## Changes by Work Item

### WORK ITEM A: Public URL Mapping Spec + Hugo Config Updates

**New files:**
- `specs/33_public_url_mapping.md` — Binding contract for URL path resolution from content paths

**Modified files:**
- `specs/31_hugo_config_awareness.md` — Added URL mapping section with `default_language_in_subdir` field
- `specs/schemas/hugo_facts.schema.json` — Added `default_language_in_subdir` as required boolean field

### WORK ITEM B: Add url_path to page_plan.json Schema

**Modified files:**
- `specs/schemas/page_plan.schema.json` — Added `url_path` as required field in pages array
- `specs/06_page_planning.md` — Added url_path field documentation
- `specs/21_worker_contracts.md` — Updated W4 contract to include url_path population requirement

### WORK ITEM C: Public URL Resolver Implementation

**New files:**
- `src/launch/resolvers/__init__.py` — Package init
- `src/launch/resolvers/public_urls.py` — Public URL resolver implementation
- `tests/unit/resolvers/__init__.py` — Test package init
- `tests/unit/resolvers/test_public_urls.py` — Comprehensive test suite (20+ test cases)

### WORK ITEM D: Bundle Style Support in TC-540

**Modified files:**
- `plans/taskcards/TC-540_content_path_resolver.md` — Added page_style support (flat_md, bundle_index)
- `specs/22_navigation_and_existing_content_update.md` — Added page style detection rules

### WORK ITEM E: Platform Root Templates

**New files:**
- `specs/templates/products.aspose.org/cells/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/docs.aspose.org/cells/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/kb.aspose.org/cells/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/reference.aspose.org/cells/__LOCALE__/__PLATFORM__/_index.md`

**Modified files:**
- `specs/20_rulesets_and_templates_registry.md` — Added platform root template documentation

### WORK ITEM F: Fix Templates Path in specs/29

**Modified files:**
- `specs/29_project_repo_structure.md` — Updated templates tree section with V1 and V2 layout paths

### WORK ITEM G: No A1 Skip Enforcement

**New files:**
- `tools/validate_phase_report_integrity.py` — Validator ensuring phase reports have gate_outputs with A1 output

**Modified files:**
- `tools/validate_swarm_ready.py` — Added `_ensure_user_site_packages()` and `_check_required_dependencies()` functions
- `scripts/validate_spec_pack.py` — Added user site-packages path fix for Windows environments

### Taskcard Updates

**Modified files:**
- `plans/taskcards/TC-430_ia_planner_w4.md` — Added specs/33 reference, url_path population requirement
- `plans/taskcards/TC-540_content_path_resolver.md` — Added specs/33 reference, page_style support
- `plans/taskcards/TC-550_hugo_config_awareness_ext.md` — Added specs/33 reference, default_language_in_subdir requirement

## Gate Status

All 9 gates pass:
- [PASS] Gate A1: Spec pack validation
- [PASS] Gate A2: Plans validation (zero warnings)
- [PASS] Gate B: Taskcard validation + path enforcement
- [PASS] Gate C: Status board generation
- [PASS] Gate D: Markdown link integrity
- [PASS] Gate E: Allowed paths audit (zero violations + zero critical overlaps)
- [PASS] Gate F: Platform layout consistency (V2)
- [PASS] Gate G: Pilots contract (canonical path consistency)
- [PASS] Gate H: MCP contract (quickstart tools in specs)

## Additional Fixes

- Fixed Python user site-packages handling for Windows environments where `site.ENABLE_USER_SITE` is False
- Added proper `.pth` file processing for editable installs in user site-packages
