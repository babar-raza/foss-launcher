---
id: TC-400
title: "W1 RepoScout (clone + fingerprint + Hugo/site discovery)"
status: Done
owner: "W1_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-401
  - TC-402
  - TC-403
  - TC-404
allowed_paths:
  - src/launch/workers/w1_repo_scout/__init__.py
  - src/launch/workers/w1_repo_scout/__main__.py
  - src/launch/workers/_git/__init__.py
  - tests/integration/test_tc_400_w1_integration.py
  - reports/agents/**/TC-400/**
evidence_required:
  - reports/agents/<agent>/TC-400/report.md
  - reports/agents/<agent>/TC-400/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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
- Deterministic `repo_inventory` construction including `adapter_id`
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
- src/launch/workers/w1_repo_scout/__main__.py
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

## Failure modes

1. **Failure**: Git clone fails due to network timeout or invalid credentials
   - **Detection**: `subprocess.CalledProcessError` during `git clone`; timeout after 60s; non-zero exit code
   - **Fix**: Retry with exponential backoff (max 3 attempts); emit BLOCKER issue with error code `GIT_CLONE_FAILED`; check network allowlist (Gate N) includes GitHub
   - **Spec/Gate**: specs/02_repo_ingestion.md (clone contract), specs/34_strict_compliance_guarantees.md (Guarantee D - network allowlist)

2. **Failure**: Frontmatter contract discovery finds inconsistent or malformed frontmatter patterns
   - **Detection**: YAML parse errors in sampled `.md` files; conflicting field types across samples; required fields missing
   - **Fix**: Emit BLOCKER issue with exact file paths + parse errors; require manual config override via `run_config.frontmatter_override`; fail fast (do not guess)
   - **Spec/Gate**: specs/examples/frontmatter_models.md (sampling algorithm), Gate B (taskcard validation enforces no-guess policy)

3. **Failure**: Determinism violation - artifact bytes differ across identical runs
   - **Detection**: Integration test compares sha256 of `repo_inventory.json` + `site_context.json` across 2 runs; hash mismatch indicates non-deterministic ordering or timestamps
   - **Fix**: Check for unsorted file lists; check for time-based serialization; ensure stable JSON serialization (sorted keys); run determinism harness (TC-560)
   - **Spec/Gate**: specs/10_determinism_and_caching.md (stable ordering requirement), Gate B (taskcard validation)

4. **Failure**: Hugo config contains invalid YAML or references non-existent modules
   - **Detection**: YAML parse exception during `site_context` construction; `hugo.build_matrix` field missing or malformed
   - **Fix**: Emit WARNING (not blocker) if Hugo config cannot be parsed; populate `site_context.hugo` with minimal safe defaults; record issue for human review
   - **Spec/Gate**: specs/31_hugo_config_awareness.md (Hugo scan contract), Gate H (MCP contract validation)

## Task-specific review checklist

Beyond the standard acceptance checks, verify:
- [ ] All 3 output artifacts (`repo_inventory.json`, `frontmatter_contract.json`, `site_context.json`) validate against their schemas
- [ ] Determinism test passes: run worker twice with same inputs, compare artifact sha256 hashes (must be identical)
- [ ] Git clone uses pinned commit SHAs (no floating branches/tags in prod configs) - verified by Gate J
- [ ] Frontmatter sampling uses deterministic file selection (sorted paths, fixed sample size)
- [ ] Hugo config scan handles missing/malformed configs gracefully (emits warning, uses safe defaults)
- [ ] Network requests (git clone) respect network allowlist (Gate N) - GitHub must be in `config/network_allowlist.yaml`

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run
```

**Expected artifacts:**
- artifacts/repo_inventory.json (schema: repo_inventory.schema.json)
- artifacts/site_context.json

**Success criteria:**
- [ ] repo_inventory.json validates
- [ ] site_context.json validates

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-300 (orchestrator dispatches W1)
- Downstream: TC-410 (W2 FactsBuilder), TC-420 (W3 Snippets)
- Contracts: repo_inventory.schema.json, site_context.schema.json

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
