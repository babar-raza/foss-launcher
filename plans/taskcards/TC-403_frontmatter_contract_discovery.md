---
id: TC-403
title: "W1.3 Frontmatter contract discovery (deterministic)"
status: Done
owner: "W1_AGENT"
updated: "2026-01-28"
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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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

- `src/launch/workers/w1_repo_scout/frontmatter.py`
- `tests/unit/workers/test_tc_403_frontmatter.py`
- `reports/agents/**/TC-403/**`## Implementation steps
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

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout.frontmatter --site-dir workdir/site
```

**Expected artifacts:**
- artifacts/frontmatter_contracts.json

**Success criteria:**
- [ ] Frontmatter patterns discovered
- [ ] Output deterministic

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-401 (site repo cloned)
- Downstream: TC-440 (SectionWriter uses frontmatter contracts)
- Contracts: specs/examples/frontmatter_models.md patterns

## Failure modes

### Failure mode 1: Inconsistent frontmatter formats across sampled files
**Detection:** YAML parse errors in some .md files; field types conflict between samples (string vs int); required fields missing in subset
**Resolution:** Emit BLOCKER issue with exact file paths + parse errors; require manual override via run_config.frontmatter_override; do NOT guess schema; fail fast per no-guess policy
**Spec/Gate:** specs/examples/frontmatter_models.md (sampling algorithm), specs/09_validation_gates.md Gate B

### Failure mode 2: Sampling algorithm is non-deterministic
**Detection:** Different files sampled across runs; frontmatter_contract.json changes without code changes; Gate H determinism fails
**Resolution:** Ensure sample selection uses deterministic seed; sort file paths before sampling; use fixed sample size from specs; verify sampling produces stable output
**Spec/Gate:** specs/10_determinism_and_caching.md (deterministic sampling), specs/examples/frontmatter_models.md

### Failure mode 3: Discovered frontmatter schema conflicts with expected template
**Detection:** Frontmatter fields do not match section template requirements; missing mandatory fields like family or platform; validation fails downstream
**Resolution:** Cross-validate discovered schema against specs/07_section_templates.md requirements; emit BLOCKER if incompatible; suggest manual frontmatter_override with required fields
**Spec/Gate:** specs/07_section_templates.md (template requirements), specs/06_page_planning.md


## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Worker emits required events per specs/21_worker_contracts.md
- [ ] Worker outputs validate against declared schemas
- [ ] Worker handles missing/malformed inputs gracefully with blocker artifacts
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

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
