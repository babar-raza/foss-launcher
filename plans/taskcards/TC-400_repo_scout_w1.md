---
id: TC-400
title: "W1 RepoScout (clone + fingerprint + Hugo/site discovery)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-401
  - TC-402
  - TC-403
  - TC-404
allowed_paths:
  - src/launch/workers/w1_repo_scout/__init__.py
  - src/launch/workers/_git/__init__.py
  - tests/integration/test_tc_400_w1_integration.py
  - reports/agents/**/TC-400/**
evidence_required:
  - reports/agents/<agent>/TC-400/report.md
  - reports/agents/<agent>/TC-400/self_review.md
---

# Taskcard TC-400 — W1 RepoScout (clone + fingerprint + Hugo/site discovery)

## Objective
Implement **W1: RepoScout** exactly per binding specs so the system can deterministically:
- clone and resolve SHAs for the GitHub product repo, site repo, and workflows repo
- fingerprint the repos with stable ordering + stable hashing
- discover the site **frontmatter contract**
- infer Hugo config/build matrix constraints into `site_context.json`
- emit required events and write all artifacts atomically

## Required spec references
- specs/21_worker_contracts.md (W1)
- specs/02_repo_ingestion.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/18_site_repo_layout.md
- specs/26_repo_adapters_and_variability.md
- specs/30_site_and_workflow_repos.md
- specs/31_hugo_config_awareness.md
- specs/examples/frontmatter_models.md
- specs/schemas/repo_inventory.schema.json
- specs/schemas/frontmatter_contract.schema.json
- specs/schemas/site_context.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- W1 worker entrypoint and helpers
- Git clone/checkout into `RUN_DIR/work/{repo,site,workflows}`
- SHA resolution and recording in artifacts
- Deterministic file-tree fingerprinting
- Deterministic `repo_profile` construction including `adapter_id`
- Frontmatter contract discovery (deterministic sampling)
- Hugo config scan + build matrix inference
- Schema validation for outputs

### Out of scope
- Facts/claims extraction (W2)
- Snippet extraction (W3)
- Planning/writing/patching (W4–W9)

## Inputs
- `RUN_DIR/run_config.yaml` validated against `specs/schemas/run_config.schema.json`

## Outputs
- `RUN_DIR/artifacts/repo_inventory.json`
- `RUN_DIR/artifacts/frontmatter_contract.json`
- `RUN_DIR/artifacts/site_context.json`

## Allowed paths
- src/launch/workers/w1_repo_scout/__init__.py
- src/launch/workers/_git/__init__.py
- tests/integration/test_tc_400_w1_integration.py
- reports/agents/**/TC-400/**
## Implementation steps
1) **Prepare run folders**: ensure `RUN_DIR/work/`, `RUN_DIR/artifacts/`, `RUN_DIR/logs/` exist.
2) **Clone + resolve SHAs**:
   - Support `default_branch` resolution deterministically.
   - Record resolved SHAs for repo/site/workflows.
3) **Fingerprint repos**:
   - Walk paths in sorted order; hash file bytes (sha256).
   - Record summary + selected fingerprints as per schema.
4) **Repo profile + adapter_id**:
   - Derive language/platform hints deterministically.
   - Detect docs/examples/tests/src roots deterministically.
   - Select `adapter_id` per `specs/26_*` and record.
5) **Frontmatter contract**:
   - Follow `specs/examples/frontmatter_models.md` algorithm.
   - Deterministic sampling (sorted candidates, fixed N).
6) **Hugo config awareness**:
   - Scan `RUN_DIR/work/site/configs/**`.
   - Populate `site_context.hugo.build_matrix` and any derived constraints.
7) **Write artifacts**:
   - Validate against schemas.
   - Write stable JSON with atomic rename.
   - Emit required events (`WORK_ITEM_*`, `ARTIFACT_WRITTEN`).

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run
```

**Expected artifacts:**
- artifacts/repo_profile.json (schema: repo_profile.schema.json)
- artifacts/site_context.json

**Success criteria:**
- [ ] repo_profile.json validates
- [ ] site_context.json validates

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (orchestrator dispatches W1)
- Downstream: TC-410 (W2 FactsBuilder), TC-420 (W3 Snippets)
- Contracts: repo_profile.schema.json, site_context.schema.json

## Deliverables
- Code:
  - W1 worker and helper modules
- Tests:
  - Unit tests for deterministic sampling and tree hashing
  - Integration test proving same inputs => identical artifact bytes across 2 runs
- Reports:
  - reports/agents/<agent>/TC-400/report.md
  - reports/agents/<agent>/TC-400/self_review.md

## Acceptance checks
- [ ] All 3 artifacts validate against schemas
- [ ] Resolved SHAs are present for repo/site/workflows
- [ ] Determinism test passes (byte-for-byte identical artifacts)
- [ ] `site_context.hugo.build_matrix` is present (can be minimal but non-empty structure)
- [ ] Events include WORK_ITEM_STARTED/FINISHED and ARTIFACT_WRITTEN per artifact

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
