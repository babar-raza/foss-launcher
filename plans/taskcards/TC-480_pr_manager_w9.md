---
id: TC-480
title: "W9 PRManager (commit service → PR)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on:
  - TC-470
allowed_paths:
  - src/launch/workers/w9_pr_manager.py
  - tests/unit/workers/test_tc_480_pr_manager.py
  - reports/agents/**/TC-480/**
evidence_required:
  - reports/agents/<agent>/TC-480/report.md
  - reports/agents/<agent>/TC-480/self_review.md
---

# Taskcard TC-480 — W9 PRManager (commit service → PR)

## Objective
Implement **W9: PRManager** to open a PR via the commit service with deterministic branch naming and a deterministic PR body.

## Required spec references
- specs/21_worker_contracts.md (W9)
- specs/12_pr_and_release.md
- specs/17_github_commit_service.md
- specs/16_local_telemetry_api.md
- specs/10_determinism_and_caching.md

## Scope
### In scope
- W9 worker implementation
- Deterministic branch name and PR title/body templates
- Commit service client calls in production mode
- Persist optional `RUN_DIR/artifacts/pr.json` with PR URL and commit SHA
- Associate commit SHA to telemetry outbox/client

### Out of scope
- Implementing commit service itself (client only)

## Inputs
- site worktree diff
- `RUN_DIR/reports/diff_report.md`
- `RUN_DIR/artifacts/validation_report.json`
- run_config commit templates

## Outputs
- `RUN_DIR/artifacts/pr.json` (optional but recommended)

## Allowed paths
- src/launch/workers/w9_pr_manager.py
- tests/unit/workers/test_tc_480_pr_manager.py
- reports/agents/**/TC-480/**
## Implementation steps
1) Determine deterministic branch name from run_id + product_slug (per spec).
2) Build PR body:
   - gates summary
   - pages created/updated
   - TruthLock/evidence summary
   - include resolved SHAs for repo/site/workflows
3) Call commit service to:
   - create branch
   - commit changes
   - open PR
4) Write `pr.json` and emit events.
5) Emit telemetry association event/outbox record.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w9_pr_manager --site-dir workdir/site --config specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml --dry-run
```

**Expected artifacts:**
- artifacts/pr_request.json

**Success criteria:**
- [ ] PR payload generated
- [ ] Commit message follows template

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-460 (validation_report.ok=true)
- Downstream: Commit service (external)
- Contracts: specs/12_pr_and_release.md, specs/17_github_commit_service.md

## Deliverables
- Code: W9 implementation + commit-service + telemetry client usage
- Tests:
  - unit test: deterministic branch naming
  - unit test: PR body rendering stable given same inputs
  - integration test: commit client stub receives expected payload
- Reports:
  - reports/agents/<agent>/TC-480/report.md
  - reports/agents/<agent>/TC-480/self_review.md

## Acceptance checks
- [ ] PR payload is deterministic given same run_dir artifacts
- [ ] `pr.json` (if produced) validates against its schema (if schema exists) or internal model
- [ ] Telemetry association of commit SHA recorded

## Self-review
Use `reports/templates/self_review_12d.md`.
