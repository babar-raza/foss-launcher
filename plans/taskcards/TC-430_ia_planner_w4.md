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
  - src/launch/workers/w4_ia_planner.py
  - src/launch/workers/_planning/**
  - tests/unit/workers/test_tc_430_ia_planner.py
  - reports/agents/**/TC-430/**
evidence_required:
  - reports/agents/<agent>/TC-430/report.md
  - reports/agents/<agent>/TC-430/self_review.md
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
- src/launch/workers/w4_ia_planner.py
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
