---
id: "TC-681"
title: "W4 Template-Driven Page Enumeration for family=3d"
owner: "w4-agent"
status: "Done"
created: "2026-01-30"
updated: "2026-02-03"
spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
evidence_required:
  - "Superseded by TC-902; no evidence required for this historical taskcard"
depends_on: []
allowed_paths:
  - "plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md"
  - "reports/agents/**/TC-681/**"
---

# Taskcard TC-681 — W4 Template-Driven Page Enumeration for family=3d

## Objective
Enable W4 IA Planner to generate correct page counts and paths for Pilot-1 (family=3d) using template-driven enumeration. **Note: This taskcard is superseded by TC-902 for worker.py implementation. Retained for historical reference and traceability.**

## Scope

### In scope
- Document the original problem (missing family segment, double slashes, hardcoded page count)
- Define expected behavior (template-driven enumeration, correct path construction)
- Specify acceptance criteria for W4 family-aware paths

### Out of scope
- Actual implementation of worker.py changes (owned by TC-902)
- Code changes to W4 planner
- Unit tests for W4 (owned by TC-902)

## Inputs
1. run_config with family=3d, target_platform=python
2. Templates in specs/templates/<subdomain>/<family>/
3. Current W4 implementation (before fix)

## Outputs
1. Problem statement documenting W4 path construction bugs
2. Required spec references for template-driven enumeration
3. Acceptance criteria for correct W4 behavior
4. Note: Actual code changes delivered by TC-902

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
```powershell
$env:OFFLINE_MODE="1"
.venv/Scripts/python.exe scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python
```

Expected artifacts:
- artifacts/page_plan.json with 42+ pages
- All paths include `/3d/` segment
- No paths contain `//`

## Integration boundary proven
- **Upstream**: TC-700 (template packs) → TC-681 (template enumeration requirements)
- **Downstream**: TC-681 (problem definition) → TC-902 (implementation)
- **Input**: run_config with family=3d, target_platform=python
- **Output**: page_plan.json with template-driven page enumeration and correct paths
- **Contract**: Paths must match site_layout subdomain_roots + family + locale + platform

## Allowed paths

- `plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md`
- `reports/agents/**/TC-681/**`## Failure modes

### Failure mode 1: Template enumeration logic misses template variants
**Detection:** Page count lower than expected template inventory; missing pages in page_plan.json for known template files
**Resolution:** Verify template discovery scans all subdirectories; check file extension filter includes all .md files; ensure variant detection logic handles all template naming patterns (.variant-minimal.md, etc.); cross-reference with TEMPLATE_AUDIT.md
**Spec/Gate:** specs/07_section_templates.md (template enumeration), specs/20_rulesets_and_templates_registry.md

### Failure mode 2: Output paths still contain double slashes or missing family segment
**Detection:** page_plan.json inspection shows paths like `content/docs.aspose.org//en/python/` or `content/docs.aspose.org/en/python/` (missing /3d/)
**Resolution:** Review path construction in compute_output_path(); ensure subdomain_roots don't have trailing slashes; verify family parameter is included in path template; test with different family values to confirm segment presence
**Spec/Gate:** specs/32_platform_aware_content_layout.md (V2 layout format), specs/18_site_repo_layout.md

### Failure mode 3: Page enumeration non-deterministic across runs
**Detection:** Running pilot E2E twice produces different page ordering or count in page_plan.json
**Resolution:** Add stable sorting by (section, slug) before writing page_plan.json; ensure template discovery uses sorted() on file paths; remove any randomness in template selection (e.g., set iteration order)
**Spec/Gate:** specs/10_determinism_and_caching.md (reproducibility requirement)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Problem statement accurately documents W4 path construction bugs (double slash, missing family)
- [ ] Expected page count matches template inventory from TEMPLATE_AUDIT.md (42+ pages for 3D pilot)
- [ ] Acceptance criteria specify concrete numbers (products >= 7, docs >= 8, reference >= 5, kb >= 12, blog >= 10)
- [ ] All spec references exist and are accurate
- [ ] TC-902 ownership clearly documented (this is problem definition, not implementation)
- [ ] No implementation code changes in allowed_paths (only taskcard and reports)

## Self-review
- [x] Taskcard follows required structure (all required sections present)
- [x] allowed_paths covers only this taskcard and reports (no worker.py)
- [x] Acceptance criteria are concrete and testable
- [x] E2E verification includes specific command and expected outcome
- [x] YAML frontmatter complete (all required keys present, spec_ref is commit SHA)
- [x] Spec references accurate and exist in repo
- [x] Integration boundary specifies superseded status and canonical owner (TC-902)
- [x] Status marked as "superseded" with clear note about TC-902 ownership
