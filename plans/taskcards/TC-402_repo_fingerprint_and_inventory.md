---
id: TC-402
title: "W1.2 Deterministic repo fingerprinting and inventory"
status: Done
owner: "W1_AGENT"
updated: "2026-01-28"
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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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

- `src/launch/workers/w1_repo_scout/fingerprint.py`
- `tests/unit/workers/test_tc_402_fingerprint.py`
- `reports/agents/**/TC-402/**`## Implementation steps
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

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w1_repo_scout.fingerprint --workdir workdir/repos/<sha>
```

**Expected artifacts:**
- artifacts/repo_inventory.json

**Success criteria:**
- [ ] Fingerprint is deterministic (run twice, compare hashes)
- [ ] Inventory sorted deterministically

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-401 (cloned repo)
- Downstream: TC-411 (facts extraction uses inventory)
- Contracts: repo_inventory.schema.json fields

## Failure modes

### Failure mode 1: File enumeration misses files due to .gitignore or symlinks
**Detection:** File count in repo_inventory.json significantly lower than expected; known files missing; symlinks not followed
**Resolution:** Review file walk logic; ensure .gitignore is NOT applied to inventory (inventory should include ALL files); handle symlinks according to specs/02_repo_ingestion.md; verify recursive directory traversal
**Spec/Gate:** specs/02_repo_ingestion.md (inventory completeness), specs/schemas/repo_inventory.schema.json

### Failure mode 2: File metadata is non-deterministic across runs
**Detection:** repo_inventory.json SHA256 differs between runs; file paths have different ordering; file hash calculations vary
**Resolution:** Ensure file list is sorted deterministically (lexicographic order); use stable hash algorithm (SHA256); exclude mtime/atime from inventory; verify specs/10_determinism_and_caching.md compliance
**Spec/Gate:** specs/10_determinism_and_caching.md (deterministic file enumeration)

### Failure mode 3: Large binary files cause memory exhaustion during hashing
**Detection:** OOM error during repo inventory; hash calculation times out on large files; process killed by OS
**Resolution:** Implement streaming hash calculation for files >100MB; set memory limits; skip hash for files exceeding size threshold (document in inventory with size_only flag); emit warning for skipped files
**Spec/Gate:** specs/02_repo_ingestion.md (binary file handling), specs/21_worker_contracts.md W1


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
