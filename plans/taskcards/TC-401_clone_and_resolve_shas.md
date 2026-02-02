---
id: TC-401
title: "W1.1 Clone inputs and resolve SHAs deterministically"
status: Done
owner: "W1_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-200
  - TC-300
allowed_paths:
  - src/launch/workers/w1_repo_scout/clone.py
  - tests/unit/workers/test_tc_401_clone.py
  - reports/agents/**/TC-401/**
evidence_required:
  - reports/agents/<agent>/TC-401/report.md
  - reports/agents/<agent>/TC-401/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

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
