---
id: TC-401
title: "W1.1 Clone inputs and resolve SHAs deterministically"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/workers/w1_repo_scout/clone.py
  - src/launch/workers/_git/clone_helpers.py
  - tests/unit/workers/test_tc_401_clone.py
  - reports/agents/**/TC-401/**
evidence_required:
  - reports/agents/<agent>/TC-401/report.md
  - reports/agents/<agent>/TC-401/self_review.md
---

# Taskcard TC-401 — W1.1 Clone inputs and resolve SHAs deterministically

## Objective
Implement deterministic cloning/checkout for product, site, and workflows repos and record **resolved SHAs** in artifacts/events.

## Required spec references
- specs/02_repo_ingestion.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/21_worker_contracts.md (W1)
- specs/30_site_and_workflow_repos.md
- specs/schemas/site_context.schema.json
- specs/schemas/repo_inventory.schema.json

## Scope
### In scope
- Clone repos into `RUN_DIR/work/{repo,site,workflows}`
- Deterministic resolution of `default_branch` to a specific commit SHA
- Recording resolved SHAs in:
  - repo_inventory (or a dedicated artifact field per schema)
  - events.ndjson (ARTIFACT_WRITTEN + provenance)
- Safe behavior when network is unavailable (fail as external dependency with clear error)

### Out of scope
- Repo fingerprinting (TC-402)
- Frontmatter contract discovery (TC-403)
- Hugo build matrix inference (TC-404)

## Inputs
- `RUN_DIR/run_config.yaml` (validated) providing:
  - github_repo_url + github_ref
  - site_repo_url + site_ref
  - workflows_repo_url + workflows_ref
- Git installed in environment

## Outputs
- `RUN_DIR/work/repo/` checked out at resolved SHA
- `RUN_DIR/work/site/` checked out at resolved SHA
- `RUN_DIR/work/workflows/` checked out at resolved SHA
- Artifact fields recording resolved SHAs (per schema) and event trail

## Allowed paths
- src/launch/workers/w1_repo_scout/clone.py
- src/launch/workers/_git/clone_helpers.py
- tests/unit/workers/test_tc_401_clone.py
- reports/agents/**/TC-401/**
## Implementation steps
1) Implement clone utility:
   - fetch shallow or full clone as allowed by spec; behavior must be deterministic
   - checkout exact ref
2) Resolve `default_branch`:
   - query remote default branch name
   - resolve to commit SHA
   - record the resolved SHA as authoritative provenance
3) Write minimal provenance into repo_inventory fields and emit events.
4) Tests:
   - mock git remote resolution and ensure stable outputs
   - integration test (optional) behind marker that clones a small public repo

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout.clone --repo https://github.com/aspose-3d/Aspose.3D-for-Python-via-.NET --ref main --dry-run
```

**Expected artifacts:**
- workdir/repos/<sha>/ (cloned repo)
- artifacts/resolved_refs.json

**Success criteria:**
- [ ] Clone completes
- [ ] SHA deterministically resolved

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (RunConfig with github_repo_url)
- Downstream: TC-402 (fingerprint), TC-403 (frontmatter), TC-404 (Hugo scan)
- Contracts: specs/02_repo_ingestion.md clone contract

## Deliverables
- Code:
  - clone + sha resolution utilities
- Tests:
  - unit tests for default_branch resolution logic
- Reports (required):
  - reports/agents/<agent>/TC-401/report.md
  - reports/agents/<agent>/TC-401/self_review.md

## Acceptance checks
- [ ] `default_branch` resolves to a concrete SHA and is recorded
- [ ] Work dirs are created exactly under RUN_DIR/work/*
- [ ] Event trail includes clone + checkout + artifact provenance
- [ ] Tests passing

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
