---
id: TC-701
title: "W4 IA Planner - Family-Aware Path Construction"
status: Done
owner: "PLANNER_AGENT"
updated: "2026-01-30"
depends_on:
  - TC-430
  - TC-700
allowed_paths:
  - tests/unit/workers/test_tc_701_w4_enumeration.py
  - reports/agents/**/TC-701/**
evidence_required:
  - reports/agents/<agent>/TC-701/report.md
  - reports/agents/<agent>/TC-701/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-701 — W4 IA Planner - Family-Aware Path Construction

## Objective
Fix W4 IA Planner to support family-aware path construction per V2 layout format. Update path generation logic to use `family` parameter instead of `product_slug` and implement correct subdomain routing with family segments.

## Required spec references
- specs/21_worker_contracts.md (W4)
- specs/06_page_planning.md
- specs/32_platform_aware_content_layout.md
- specs/18_site_repo_layout.md

## Scope
### In scope
- Update `compute_output_path()` to accept `family` parameter
- Add `subdomain_roots` parameter for V2 layout configuration
- Implement blog special case (no locale in path, bundle-style with index.md)
- Update `plan_pages_for_section()` to accept family/locale parameters
- Update `execute_ia_planner()` to extract family from run_config
- Create unit tests proving family-aware path construction

### Out of scope
- Template-driven enumeration (deferred to future work)
- Content generation (handled by W5+)
- Validation (handled by W7)

## Inputs
- `RUN_DIR/run_config.yaml` with `family` field
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/snippet_catalog.json`

## Outputs
- `RUN_DIR/artifacts/page_plan.json` with correct V2 paths

## Allowed paths
- tests/unit/workers/test_tc_701_w4_enumeration.py
- reports/agents/**/TC-701/**

## Implementation steps
1) **Update compute_output_path() function**:
   - Change signature to accept `family` parameter (replace `product_slug`)
   - Add `subdomain_roots` parameter for section → subdomain mapping
   - Implement V2 path format: `content/<subdomain>/<family>/<locale>/<platform>/<slug>.md`
   - Implement blog special case: `content/blog.aspose.org/<family>/<platform>/<slug>/index.md` (no locale)

2) **Update plan_pages_for_section() function**:
   - Add `family` parameter to signature
   - Add `subdomain_roots` parameter
   - Add `locale` parameter
   - Update all calls to `compute_output_path()` with new parameters
   - Update SEO keywords to use `family` instead of `product_slug`

3) **Update execute_ia_planner() function**:
   - Extract `family` from run_config (not `product_slug`)
   - Extract `locale` from run_config (default to "en")
   - Build `subdomain_roots` mapping for V2 layout
   - Pass new parameters to `plan_pages_for_section()`

4) **Create unit tests**:
   - Test family-aware path construction for all sections
   - Test blog special case (no locale segment)
   - Test V2 layout format compliance
   - Test different families produce different paths
   - Test no double slashes in any path

## Failure modes

### Failure mode 1: Double slashes in output paths
**Detection:** Unit tests check for "//" pattern in generated paths; manual inspection of page_plan.json shows malformed paths
**Resolution:** Remove trailing slashes from subdomain_roots mapping; ensure path join logic uses Path() or proper string concatenation without doubling separators; test with multiple section types
**Spec/Gate:** specs/18_site_repo_layout.md (path format requirements)

### Failure mode 2: Blog paths incorrectly include locale segment
**Detection:** Unit test checks blog paths don't contain locale segment; blog paths like `content/blog.aspose.org/3d/en/python/` instead of `content/blog.aspose.org/3d/python/`
**Resolution:** Add special case in compute_output_path() for section=="blog"; skip locale injection for blog section; verify blog uses bundle-style with index.md filename
**Spec/Gate:** specs/32_platform_aware_content_layout.md (blog layout special case)

### Failure mode 3: Missing family segment in output paths
**Detection:** Unit tests check all paths contain family segment; paths like `content/docs.aspose.org/en/python/` missing /3d/ family segment
**Resolution:** Ensure family parameter is passed to compute_output_path() from run_config; verify family is included in path template for all sections; test with different family values to confirm presence
**Spec/Gate:** specs/18_site_repo_layout.md (V2 layout requires family in all paths)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] All paths follow V2 layout format: `content/<subdomain>/<family>/<locale>/<platform>/`
- [ ] Blog paths follow special format: `content/blog.aspose.org/<family>/<platform>/` (no locale)
- [ ] No double slashes in any generated path
- [ ] Family segment present in all paths
- [ ] All TC-670 tests continue to pass (23/23)
- [ ] All new TC-701 tests pass (18/18)

## E2E verification
**Concrete command(s) to run:**
```bash
# Run unit tests
python -m pytest tests/unit/workers/test_tc_701_w4_enumeration.py -v

# Verify path format for products section
python -c "from launch.workers.w4_ia_planner.worker import compute_output_path; print(compute_output_path('products', 'overview', '3d', None, 'python', 'en'))"
# Expected: content/products.aspose.org/3d/en/python/overview.md

# Verify blog special case
python -c "from launch.workers.w4_ia_planner.worker import compute_output_path; print(compute_output_path('blog', 'announcement', 'note', None, 'python', 'en'))"
# Expected: content/blog.aspose.org/note/python/announcement/index.md
```

**Expected artifacts:**
- Modified src/launch/workers/w4_ia_planner/worker.py
- New tests/unit/workers/test_tc_701_w4_enumeration.py

**Success criteria:**
- [ ] All TC-670 tests pass (23/23)
- [ ] All TC-701 tests pass (18/18)
- [ ] No double slashes in generated paths
- [ ] Blog paths omit locale segment

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-700 (templates) → TC-701 (path enumeration)
- Downstream: TC-701 → TC-440 (W5 uses paths for content generation)
- Contracts: page_plan.json schema, V2 layout format

## Deliverables
- Code:
  - Modified src/launch/workers/w4_ia_planner/worker.py
  - New tests/unit/workers/test_tc_701_w4_enumeration.py
- Reports:
  - reports/agents/<agent>/TC-701/report.md
  - reports/agents/<agent>/TC-701/self_review.md

## Acceptance checks
- [ ] compute_output_path() accepts family parameter
- [ ] All paths include family segment
- [ ] Blog paths use bundle-style (no locale)
- [ ] No double slashes in any path
- [ ] All TC-670 tests pass (23/23)
- [ ] All TC-701 tests pass (18/18)
- [ ] page_plan.json validates against schema

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
