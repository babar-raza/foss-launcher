---
id: TC-681
title: W4 Template-Driven Page Enumeration for family=3d
status: Ready
priority: P0
agent: VSCODE_AGENT
created: 2026-01-30
depends_on: []
version_lock:
  w4_ia_planner: "1.0.0"
  page_planning_spec: "06_page_planning.md @ d420b76"
---

## Problem Statement
W4 IA Planner is generating only 5 pages (1 per section) for Pilot-1 (family=3d), and paths are malformed:
- **Missing family segment**: `content/docs.aspose.org//en/python/` instead of `content/docs.aspose.org/3d/en/python/`
- **Double slash**: Path construction error when family is missing
- **Only 5 pages**: Hardcoded count instead of template-driven enumeration
- **Expected**: 42+ pages based on template inventory (7 products, 8 docs, 5 reference, 12 kb, 10 blog)

Evidence: runs/r_20260129T201052Z_3d-python_5c8d85a_f04c8553/artifacts/page_plan.json

## Root Cause
W4 planner (`src/launch/workers/w4_ia_planner/worker.py`) is not:
1. Using `run_config.family` in output path construction
2. Enumerating pages from templates in `specs/templates/<subdomain>/<family>/`
3. Respecting template hierarchy and variants

## Required spec references
- specs/06_page_planning.md (page planning contract)
- specs/07_section_templates.md (template enumeration requirements)
- specs/20_rulesets_and_templates_registry.md (template selection)
- specs/32_platform_aware_content_layout.md (V2 layout paths with platform)
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml (family=3d, target_platform=python)

## Implementation steps
1. **Locate W4 path construction logic** in `src/launch/workers/w4_ia_planner/worker.py`
   - Find where `output_path` and `url_path` are built
   - Confirm it's NOT using `run_config.family` from context

2. **Fix path construction** to include family segment:
   - Change: `content/{subdomain_root}//en/{platform}/`
   - To: `content/{subdomain_root}/{family}/en/{platform}/`
   - Ensure no double slashes when joining path segments

3. **Implement template-driven enumeration**:
   - Read templates from `specs/templates/<subdomain>/<family>/`
   - If family-specific templates don't exist, use fallback (e.g., cells)
   - Enumerate ALL template variants (not just 1 per section)
   - Generate one page per template variant found

4. **Verify deterministic ordering**:
   - Sort pages by section, then by slug
   - Ensure consistent ordering across runs

5. **Add unit test** `tests/unit/workers/test_tc_681_w4_template_enumeration.py`:
   - Test: W4 generates expected page count for fixture templates
   - Test: Output paths include family segment correctly
   - Test: No double slashes in paths
   - Test: Pages enumerated from templates, not hardcoded

## Deliverables
- [ ] Modified: src/launch/workers/w4_ia_planner/worker.py
- [ ] Added: tests/unit/workers/test_tc_681_w4_template_enumeration.py
- [ ] Test passing: `.venv/Scripts/python.exe -m pytest tests/unit/workers/test_tc_681_w4_template_enumeration.py -q`
- [ ] Swarm-ready: validate_swarm_ready 21/21 PASS
- [ ] Pytest suite: No regressions

## Acceptance checks
- [ ] W4 generates pages from templates for family=3d (not hardcoded 5)
- [ ] Page count per section >= expected template count from TEMPLATE_AUDIT.md:
  - products: >= 7 pages
  - docs: >= 8 pages
  - reference: >= 5 pages
  - kb: >= 12 pages
  - blog: >= 10 pages
- [ ] Output paths conform to: `content/{subdomain_root}/{family}/en/{platform}/...`
- [ ] No double slashes in any output_path or url_path
- [ ] Deterministic ordering (same order across runs)

## E2E verification
After implementation:
1. Run: `$env:OFFLINE_MODE="1"; .venv/Scripts/python.exe scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python`
2. Verify: artifacts/page_plan.json has 42+ pages
3. Verify: All paths include `/3d/` segment
4. Verify: No paths contain `//`

## Integration boundary proven
- **Input**: run_config with family=3d, target_platform=python
- **Output**: page_plan.json with template-driven page enumeration and correct paths
- **Contract**: Paths must match site_layout subdomain_roots + family + locale + platform

## Allowed paths
- plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md
- src/launch/workers/w4_ia_planner/worker.py
- tests/unit/workers/test_tc_681_w4_template_enumeration.py
- reports/agents/**/TC-681/**
