---
id: TC-404
title: "W1.4 Hugo config scan and site_context build matrix inference"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/workers/w1_repo_scout/hugo_scan.py
  - tests/unit/workers/test_tc_404_hugo_scan.py
  - reports/agents/**/TC-404/**
evidence_required:
  - reports/agents/<agent>/TC-404/report.md
  - reports/agents/<agent>/TC-404/self_review.md
---

# Taskcard TC-404 — W1.4 Hugo config scan and site_context build matrix inference

## Objective
Produce `site_context.json` capturing Hugo config constraints and a build matrix sufficient for downstream planners/validators to avoid generating unsupported paths.

**Platform-aware**: For V2 layout, the site context MUST include platform root detection and resolved `layout_mode` per section (see specs/32_platform_aware_content_layout.md).

## Required spec references
- specs/31_hugo_config_awareness.md
- specs/18_site_repo_layout.md
- specs/32_platform_aware_content_layout.md (V2 auto-detection algorithm)
- specs/30_site_and_workflow_repos.md
- specs/10_determinism_and_caching.md
- specs/schemas/site_context.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Deterministic scan of `RUN_DIR/work/site/configs/**`
- Extraction of:
  - enabled subdomains/sections
  - language mode per section (dir vs filename)
  - any explicit disables/allowlists affecting content output
- Emitting Issues when required config coverage is missing
- Artifact write + schema validation

### Out of scope
- Running Hugo build (validator gate)
- Modifying site configs

## Inputs
- Site repo checked out under `RUN_DIR/work/site`
- `run_config.site_layout` and required_sections
- `run_config.target_platform` (for V2 platform root detection)
- `run_config.layout_mode` (auto/v1/v2)

## Outputs
- `RUN_DIR/artifacts/site_context.json` (schema-valid)
- Includes `layout_mode_resolved_by_section` (auto-detection results)
- Includes `detected_platforms_per_family` (list of platforms found per family for V2)
- Issues for missing/invalid config patterns relevant to required sections

## Allowed paths
- src/launch/workers/w1_repo_scout/hugo_scan.py
- tests/unit/workers/test_tc_404_hugo_scan.py
- reports/agents/**/TC-404/**
## Implementation steps
1) Enumerate config files deterministically (sorted paths).
2) Parse Hugo configs (TOML/YAML/JSON) safely; record parse failures as Issues.
3) Infer build matrix fields per schema:
   - sections enabled per (subdomain,family)
   - localization rules per section
4) **Platform root detection** (V2):
   - For each required section, apply auto-detection algorithm from specs/32_platform_aware_content_layout.md
   - Check if platform directories exist at expected depth
   - Record `layout_mode_resolved_by_section`
   - Detect and record list of platforms per family (if V2)
5) Validate and write site_context.json; emit events.
6) Tests:
   - stable enumeration and parsing (mock files)
   - missing config coverage emits blocker Issue (as specified)
   - V2 auto-detection tests (platform directories present/absent)

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout.hugo_scan --site-dir workdir/site
```

**Expected artifacts:**
- artifacts/site_context.json (schema: site_context.schema.json)
- artifacts/build_matrix.json

**Success criteria:**
- [ ] Hugo config parsed
- [ ] Layout mode detected per section

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-401 (site repo cloned)
- Downstream: TC-540 (path resolver), TC-550 (Hugo awareness)
- Contracts: specs/31_hugo_config_awareness.md detection rules

## Deliverables
- Code:
  - config scanner + build matrix inference
- Tests:
  - enumeration determinism + issue emission tests
- Reports (required):
  - reports/agents/<agent>/TC-404/report.md
  - reports/agents/<agent>/TC-404/self_review.md

## Acceptance checks
- [ ] site_context validates against schema
- [ ] build_matrix has deterministic ordering and stable serialization
- [ ] V2 auto-detection: `layout_mode_resolved_by_section` recorded
- [ ] V2 auto-detection: detected platforms per family recorded
- [ ] V2 auto-detection follows specs/32 deterministic algorithm
- [ ] missing required coverage yields explicit Issues
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
