---
id: TC-403
title: "W1.3 Frontmatter contract discovery (deterministic)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/workers/w1_repo_scout/frontmatter.py
  - tests/unit/workers/test_tc_403_frontmatter.py
  - reports/agents/**/TC-403/**
evidence_required:
  - reports/agents/<agent>/TC-403/report.md
  - reports/agents/<agent>/TC-403/self_review.md
---

# Taskcard TC-403 — W1.3 Frontmatter contract discovery (deterministic)

## Objective
Generate `frontmatter_contract.json` by deterministically sampling existing content and inferring required/optional keys and types per the authoritative algorithm.

**Platform-aware**: For V2 layout, discovery MUST occur within platform-specific roots (see specs/32_platform_aware_content_layout.md).

## Required spec references
- specs/examples/frontmatter_models.md
- specs/18_site_repo_layout.md
- specs/32_platform_aware_content_layout.md (V2 platform roots)
- specs/31_hugo_config_awareness.md
- specs/10_determinism_and_caching.md
- specs/schemas/frontmatter_contract.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic sampling of existing .md files per section roots
- Frontmatter parsing (YAML/TOML/JSON) with robust error handling:
  - parse failures become Issues (not silent)
- Key inference:
  - required_keys, optional_keys, type inference rules per spec
- Artifact serialization and schema validation

### Out of scope
- Hugo config build matrix (TC-404)
- Writing new content (W5)

## Inputs
- Site repo checked out under `RUN_DIR/work/site`
- Section roots derived from run_config + site_layout
- Resolved `layout_mode` per section from site_context.json (to locate correct roots)
- `target_platform` from run_config (for V2 platform root resolution)
- Sampling parameters pinned (N, exclude globs) per spec

## Outputs
- `RUN_DIR/artifacts/frontmatter_contract.json` (schema-valid)
- Includes `layout_mode_resolved` per section
- Includes `platform_roots_detected` (list of platforms found) for V2 sections
- Issues for any frontmatter parse failures

## Allowed paths
- src/launch/workers/w1_repo_scout/frontmatter.py
- tests/unit/workers/test_tc_403_frontmatter.py
- reports/agents/**/TC-403/**
## Implementation steps
1) Resolve section roots per layout_mode:
   - V1: `content/<subdomain>/<family>/<locale>/`
   - V2: `content/<subdomain>/<family>/<locale>/<platform>/` for non-blog
   - V2: `content/<subdomain>/<family>/<platform>/` for blog
2) Enumerate candidate .md files under resolved section roots; apply exclusions and sort.
3) Select first N deterministically; parse frontmatter.
4) Infer required/optional keys and types; mark unknown on mixed types.
5) Record resolved `layout_mode` and detected platform roots in artifact.
6) Emit Issues for parse failures (continue processing).
7) Validate and write artifact atomically; emit events.
8) Tests:
   - deterministic sampling test (V1 and V2 layouts)
   - frontmatter parse failure => Issue test
   - V2 platform root detection test

## Deliverables
- Code:
  - frontmatter contract builder
- Tests:
  - sampling determinism + error-to-issue tests
- Reports (required):
  - reports/agents/<agent>/TC-403/report.md
  - reports/agents/<agent>/TC-403/self_review.md

## Acceptance checks
- [ ] Artifact validates against schema
- [ ] Sampling is deterministic (stable input set)
- [ ] V2 layout: discovery occurs within platform-specific roots
- [ ] V2 layout: artifact records `layout_mode_resolved` per section
- [ ] V2 layout: artifact records detected platform roots
- [ ] Parse failures become Issues and do not crash the run
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
