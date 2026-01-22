---
id: TC-570
title: "Validation Gates (schema, links, Hugo smoke, policy)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-460
  - TC-550
allowed_paths:
  - src/launch/tools/validate.py
  - src/launch/tools/frontmatter_validate.py
  - src/launch/tools/linkcheck.py
  - src/launch/tools/hugo_smoke.py
  - tests/unit/tools/test_tc_570_validation.py
  - reports/agents/**/TC-570/**
evidence_required:
  - reports/agents/<agent>/TC-570/report.md
  - reports/agents/<agent>/TC-570/self_review.md
---

# Taskcard TC-570 — Validation Gates (schema, links, Hugo smoke, policy)

## Objective
Implement the full validation gates runner that blocks merges unless artifacts and content pass required checks.

## Required spec references
- specs/09_validation_gates.md
- specs/18_site_repo_layout.md
- specs/31_hugo_config_awareness.md
- specs/10_determinism_and_caching.md
- specs/12_pr_and_release.md

## Scope
### In scope
- Implement `launch_validate` tool/CLI that runs:
  - schema validation (run_config, artifacts, patches)
  - markdown/frontmatter validation against discovered contract
  - **content_layout_platform gate**: V2 platform path structure validation (NEW)
  - link checks for relative links and internal anchors (best-effort)
  - Hugo build smoke test (best-effort; skip with recorded reason if unavailable)
  - policy check: no manual edits (plans/policies/no_manual_content_edits.md)
- Produce machine-readable and human-readable reports
- Exit non-zero on required gate failure

### Out of scope
- Deep content quality scoring (W7/W8)
- PR creation (W9)

## Inputs
- `RUN_DIR` (artifacts, patches, updated content files)
- `site_context.json` and `hugo_facts.json` (if present)

## Outputs
- `RUN_DIR/reports/validate.json`
- `RUN_DIR/reports/validate.md`
- Event: `VALIDATION_COMPLETED`

## Allowed paths
- src/launch/tools/validate.py
- src/launch/tools/frontmatter_validate.py
- src/launch/tools/linkcheck.py
- src/launch/tools/hugo_smoke.py
- tests/unit/tools/test_tc_570_validation.py
- reports/agents/**/TC-570/**
## Implementation steps
1) Implement a gate registry with structured results.
2) Schema gate: validate all artifacts via JSON Schema.
3) Frontmatter gate:
   - use discovered contract when available
   - fallback to warnings when contract missing
4) **Platform layout gate** (content_layout_platform):
   - Read resolved `layout_mode` per section from artifacts
   - When V2 detected:
     - Verify non-blog paths contain `/{locale}/{platform}/`
     - Verify blog paths contain `/{platform}/`
     - Verify products use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
     - Check all writes are within `allowed_paths`
     - Lint for unresolved `__PLATFORM__` tokens in generated content
   - Emit BLOCKER issues on violations
   - See specs/32_platform_aware_content_layout.md
5) Link gate:
   - resolve relative links within repo
   - anchor checks best-effort
6) Hugo smoke:
   - use config locations from TC-550 artifact
   - capture logs under RUN_DIR/logs/
7) Policy gate:
   - fail on unexplained file edits
8) Write reports and exit accordingly.
9) Add fixtures/tests for pass and fail (including V2 path validation tests).

## Deliverables
- Code + tests
- Report and self review under repo-root reports/

## Acceptance checks
- [ ] Exits non-zero on required gate failure
- [ ] Writes both JSON and MD reports
- [ ] Platform layout gate enforces V2 path structure when layout_mode=v2
- [ ] Platform layout gate verifies products use /{locale}/{platform}/
- [ ] Platform layout gate fails on unresolved __PLATFORM__ tokens
- [ ] Hugo smoke records skip reason when unavailable
- [ ] Policy gate prevents unexplained manual edits

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
