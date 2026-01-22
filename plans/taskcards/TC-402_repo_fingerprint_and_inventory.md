---
id: TC-402
title: "W1.2 Deterministic repo fingerprinting and inventory"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/workers/w1_repo_scout/fingerprint.py
  - tests/unit/workers/test_tc_402_fingerprint.py
  - reports/agents/**/TC-402/**
evidence_required:
  - reports/agents/<agent>/TC-402/report.md
  - reports/agents/<agent>/TC-402/self_review.md
---

# Taskcard TC-402 — W1.2 Deterministic repo fingerprinting and inventory

## Objective
Produce `repo_inventory.json` with deterministic file enumeration and hashing for product/site/workflows repos.

## Required spec references
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/21_worker_contracts.md (W1)
- specs/schemas/repo_inventory.schema.json
- specs/26_repo_adapters_and_variability.md
- specs/27_universal_repo_handling.md

## Scope
### In scope
- Deterministic tree walk and hashing (sha256 of bytes)
- Stable ordering of paths
- Emitting repo inventory summary required by schema
- Recording adapter hints (but not selecting adapter — that is separate contract logic)

### Out of scope
- Frontmatter contract discovery (TC-403)
- Hugo config scan (TC-404)

## Inputs
- Checked out repos under `RUN_DIR/work/{repo,site,workflows}` (from TC-401)
- Exclusion rules for vendor/build folders per specs

## Outputs
- `RUN_DIR/artifacts/repo_inventory.json` validated against schema
- Corresponding ARTIFACT_WRITTEN event entries

## Allowed paths
- src/launch/workers/w1_repo_scout/fingerprint.py
- tests/unit/workers/test_tc_402_fingerprint.py
- reports/agents/**/TC-402/**
## Implementation steps
1) Implement deterministic file walker:
   - exclude patterns per spec
   - sort lexicographically
2) Hashing:
   - hash file bytes using sha256
   - store per-file hash and roll-up summary per schema
3) Serialize artifact using stable JSON writer (TC-200).
4) Tests:
   - unit test: given a temp tree, output ordering and hashes are stable
   - determinism test: run twice and compare artifact bytes

## Deliverables
- Code:
  - deterministic fingerprinting utilities
- Tests:
  - ordering + bytes determinism tests
- Reports (required):
  - reports/agents/<agent>/TC-402/report.md
  - reports/agents/<agent>/TC-402/self_review.md

## Acceptance checks
- [ ] repo_inventory validates against schema
- [ ] path ordering is stable and documented
- [ ] artifact bytes identical across two runs on same input
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
