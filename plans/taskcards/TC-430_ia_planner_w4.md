---
id: TC-430
title: "W4 IAPlanner (page_plan.json)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-410
  - TC-420
allowed_paths:
  - src/launch/workers/w4_ia_planner/**
  - src/launch/workers/_planning/**
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/**/TC-430/**
evidence_required:
  - reports/agents/<agent>/TC-430/report.md
  - reports/agents/<agent>/TC-430/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-430 — W4 IAPlanner (page_plan.json)

## Objective
Implement **W4: IAPlanner** to produce a complete, deterministic **PagePlan** before any writing begins.

## Required spec references
- specs/21_worker_contracts.md (W4)
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/18_site_repo_layout.md
- specs/20_rulesets_and_templates_registry.md
- specs/22_navigation_and_existing_content_update.md
- specs/31_hugo_config_awareness.md
- specs/33_public_url_mapping.md (url_path computation)
- specs/schemas/page_plan.schema.json
- specs/schemas/hugo_facts.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- W4 implementation consuming facts, evidence, snippets, frontmatter contract, and site context
- Deterministic template selection from `specs/templates/**` per registry rules
- Deterministic output paths matching site repo layout
- Enforce `run_config.required_sections` and open blocker `PlanIncomplete` if unplannable
- Populate `url_path` for each page using the public URL resolver (specs/33_public_url_mapping.md)
- Fill per-page requirements:
  - output_path (content file path)
  - url_path (public canonical URL path via resolver)
  - template id + variant
  - required claim IDs
  - required snippet tags
  - internal link targets (using url_path, not output_path)

### Out of scope
- Draft writing (W5)
- Patching (W6)

## Inputs
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- `RUN_DIR/artifacts/frontmatter_contract.json`
- `RUN_DIR/artifacts/site_context.json`
- `RUN_DIR/artifacts/hugo_facts.json` (for url_path computation)
- run_config
- site worktree read-only (`RUN_DIR/work/site/`)

## Outputs
- `RUN_DIR/artifacts/page_plan.json`

## Allowed paths
- src/launch/workers/w4_ia_planner/**
- src/launch/workers/_planning/**
- tests/unit/workers/test_tc_430_ia_planner.py
- reports/agents/**/TC-430/**
## Implementation steps
1) Load and validate all prerequisite artifacts.
2) Determine supported `(subdomain, family)` build targets from `site_context.hugo.build_matrix`.
3) Determine required sections and page set from run_config and planning rules.
4) Select templates deterministically (registry rules, stable ordering).
5) Generate `pages[]` entries with deterministic ordering:
   - sort by section order, then by output_path
6) Validate the plan:
   - required sections present
   - output paths are inside valid content roots
   - all required claim_ids and snippet tags exist
   - if not, open blocker issues and stop.
7) Write and schema-validate `page_plan.json`; emit events.

## Failure modes

1. **Failure**: Required section cannot be planned (no suitable template or missing required claims/snippets)
   - **Detection**: `run_config.required_sections` includes a section type but no template matches; required claim_ids missing from `product_facts`; required snippet tags not in `snippet_catalog`
   - **Fix**: Emit BLOCKER issue `PLAN_INCOMPLETE_<SECTION>`; include missing claim_ids/snippet tags; require manual intervention (add evidence to repo, or relax required_sections); do NOT proceed to W5
   - **Spec/Gate**: specs/06_page_planning.md (planning requirements), specs/34_strict_compliance_guarantees.md (Guarantee B - no improvisation)

2. **Failure**: Template selection produces non-deterministic results (different templates chosen across runs)
   - **Detection**: Determinism test fails; `page_plan.json` sha256 differs; template_id fields vary across identical runs
   - **Fix**: Ensure template registry rules are stable and complete (no arbitrary tiebreakers); sort template candidates by template_id before applying selection rules; verify rulesets match `ruleset_version`
   - **Spec/Gate**: specs/20_rulesets_and_templates_registry.md (template selection), specs/10_determinism_and_caching.md (stable ordering)

3. **Failure**: Output paths violate site layout constraints (paths outside allowed content roots, wrong subdomain structure)
   - **Detection**: Schema validation fails; output_path does not match pattern in `site_context.allowed_content_roots`; Hugo build would fail on invalid path
   - **Fix**: Validate all output_path values against `site_context` before writing plan; emit BLOCKER with invalid paths; fix path generation logic to respect layout rules from specs/18 and specs/32
   - **Spec/Gate**: specs/18_site_repo_layout.md (content paths), specs/32_platform_aware_content_layout.md (V1/V2 layout), Gate B (schema validation)

4. **Failure**: url_path computation fails or produces incorrect canonical URLs
   - **Detection**: `url_path` field missing or malformed; URL does not match expected public URL format; cross_links use output_path instead of url_path
   - **Fix**: Ensure url_path resolver uses `hugo_facts` and site layout rules from specs/33; validate all url_path values follow canonical format; emit WARNING for ambiguous URL mappings
   - **Spec/Gate**: specs/33_public_url_mapping.md (URL resolution), specs/22_navigation_and_existing_content_update.md (cross-linking)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] page_plan.json determinism: run twice with same inputs, sha256 hashes must match
- [ ] All pages have both `output_path` (file system) and `url_path` (public URL) fields populated correctly
- [ ] Required sections enforcement tested: missing claim_ids/snippet tags produce BLOCKER issue, not empty plan
- [ ] Template selection is deterministic: registry rules produce same template_id given same input facts
- [ ] Output paths conform to site layout (V1 vs V2 layout rules from specs/32, allowed_content_roots from site_context)
- [ ] Cross-links (`cross_links[]` field) use `url_path` not `output_path` - verify linking strategy from specs/22
- [ ] Page ordering is stable: pages sorted by section order then output_path

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w4_ia_planner --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
```

**Expected artifacts:**
- artifacts/page_plan.json (schema: page_plan.schema.json)

**Success criteria:**
- [ ] page_plan.json validates
- [ ] All sections planned

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-410 (facts), TC-420 (snippets), TC-404 (site_context)
- Downstream: TC-440 (SectionWriter)
- Contracts: page_plan.schema.json

## Deliverables
- Code: W4 planner + template registry resolver
- Tests:
  - golden determinism test: identical page_plan bytes across 2 runs
  - tests that required_sections enforcement opens `PlanIncomplete`
  - tests that output paths conform to site layout rules
- Reports:
  - reports/agents/<agent>/TC-430/report.md
  - reports/agents/<agent>/TC-430/self_review.md

## Acceptance checks
- [ ] `page_plan.json` validates against schema
- [ ] plan ordering is stable and deterministic
- [ ] required sections enforced (blocker if missing)
- [ ] output paths are compatible with site layout and Hugo configs
- [ ] url_path populated for every page using resolver
- [ ] cross_links use url_path (not output_path)

## Self-review
Use `reports/templates/self_review_12d.md`.
