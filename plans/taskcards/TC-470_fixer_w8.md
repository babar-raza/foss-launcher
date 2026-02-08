---
id: TC-470
title: "W8 Fixer (targeted one-issue fix loop)"
status: Done
owner: "W8_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-460
allowed_paths:
  - src/launch/workers/w8_fixer/**
  - src/launch/workers/_fix/**
  - tests/unit/workers/test_tc_470_fixer.py
  - reports/agents/**/TC-470/**
evidence_required:
  - reports/agents/<agent>/TC-470/report.md
  - reports/agents/<agent>/TC-470/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-470 — W8 Fixer (targeted one-issue fix loop)

## Objective
Implement **W8: Fixer** to apply the minimal change required to fix **exactly one** selected issue, without introducing new unsupported claims.

## Required spec references
- specs/21_worker_contracts.md (W8)
- specs/08_patch_engine.md
- specs/09_validation_gates.md
- specs/04_claims_compiler_truth_lock.md
- specs/schemas/issue.schema.json

## Scope
### In scope
- W8 entrypoint: `Fixer.run(issue_id, state, ctx)`
- Gate-specific fix rules per `specs/08_patch_engine.md`
- Strategy:
  - either modify relevant draft(s) and trigger W6 to produce a new PatchBundle
  - or produce a patch delta artifact if the architecture chooses (optional)
- Enforce single-issue rule:
  - must fail with blocker `FixNoOp` if no meaningful diff is produced

### Out of scope
- Running the full validator (orchestrator does that)

## Inputs
- `RUN_DIR/artifacts/validation_report.json`
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- site worktree (`RUN_DIR/work/site/`) writeable but constrained by allowed_paths

## Outputs
- Updated drafts under `RUN_DIR/drafts/<section>/...` and regenerated patch bundle via W6
  OR
- Optional `RUN_DIR/artifacts/patch_bundle.delta.json`
- Optional human note: `RUN_DIR/reports/fix_<issue_id>.md`

## Allowed paths
- src/launch/workers/w8_fixer/**
- src/launch/workers/_fix/**
- tests/unit/workers/test_tc_470_fixer.py
- reports/agents/**/TC-470/**
## Implementation steps
1) Load validation_report and locate the target issue_id.
2) Classify issue by gate/type and select an allowed fix strategy.
3) Apply minimal edit:
   - For content issues: modify draft(s) first (preferred), then rerun W6.
   - For link/frontmatter issues: fix frontmatter/draft formatting per contract.
4) Enforce TruthLock:
   - no new capability claims without evidence
5) Verify the fix produced a non-empty diff:
   - otherwise fail with blocker `FixNoOp`.
6) Emit events for fix start/finish and artifacts written.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w8_fixer --validation-report artifacts/validation_report.json --site-dir workdir/site
```

**Expected artifacts:**
- artifacts/fix_log.json
- artifacts/validation_report.json (updated)

**Success criteria:**
- [ ] Issue fixed or marked unfixable
- [ ] Re-validation runs

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-460 (validation_report with issues)
- Downstream: TC-460 (re-validation), TC-480 (PRManager)
- Contracts: specs/09_validation_gates.md fix loop rules

## Failure modes

### Failure mode 1: Generated content fails schema validation
**Detection:** Artifact schema validation fails; missing required fields; incorrect structure
**Resolution:** Validate artifact against schema before writing; ensure all required fields present
**Spec/Gate:** specs/09_validation_gates.md Gate C

### Failure mode 2: Non-deterministic output - content varies across identical runs
**Detection:** Generated drafts differ between runs; JSON artifact SHA256 mismatch
**Resolution:** Ensure template rendering is deterministic; sort all lists; remove timestamps; test with harness
**Spec/Gate:** specs/10_determinism_and_caching.md

### Failure mode 3: Content generation fails validation gates
**Detection:** Gate checks fail after generation; validation_report.json contains BLOCKER issues
**Resolution:** Review validation_report.json for failures; fix issues per gate requirements; re-run validation
**Spec/Gate:** specs/09_validation_gates.md, specs/21_worker_contracts.md


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
- Code: W8 implementation + fix strategy library
- Tests:
  - unit tests for "fix exactly one" enforcement
  - unit tests for FixNoOp
  - integration test: pick one synthetic issue and confirm a minimal diff is produced
- Reports:
  - reports/agents/<agent>/TC-470/report.md
  - reports/agents/<agent>/TC-470/self_review.md

## Acceptance checks
- [ ] Fixer refuses to fix multiple issues in one call
- [ ] Fixer produces a meaningful diff or raises FixNoOp blocker
- [ ] No new unsupported claims are introduced
- [ ] Determinism preserved (fix strategy is deterministic given the same issue + inputs)

## Self-review
Use `reports/templates/self_review_12d.md`.
