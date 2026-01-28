---
id: TC-450
title: "W6 LinkerAndPatcher (PatchBundle + apply to site worktree)"
status: Done
owner: "W6_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-440
allowed_paths:
  - src/launch/workers/w6_linker_and_patcher/**
  - src/launch/workers/_patch/**
  - tests/unit/workers/test_tc_450_linker_patcher.py
  - reports/agents/**/TC-450/**
evidence_required:
  - reports/agents/<agent>/TC-450/report.md
  - reports/agents/<agent>/TC-450/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-450 — W6 LinkerAndPatcher (PatchBundle + apply to site worktree)

## Objective
Implement **W6: LinkerAndPatcher** to convert drafts into a deterministic PatchBundle and apply it to the site repo worktree while enforcing allowed paths.

## Required spec references
- specs/21_worker_contracts.md (W6)
- specs/08_patch_engine.md
- specs/18_site_repo_layout.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/schemas/patch_bundle.schema.json
- specs/schemas/issue.schema.json

## Scope
### In scope
- Build `patch_bundle.json` from drafts and page_plan
- Deterministic application order:
  - by section order then by planned output_path
- Enforce `run_config.allowed_paths` (blocker `AllowedPathsViolation`)
- Frontmatter stability: formatting consistent with contract
- Write diff report to `RUN_DIR/reports/diff_report.md`

### Out of scope
- Validation gates (W7)
- Fixing issues (W8)

## Inputs
- `RUN_DIR/drafts/**`
- `RUN_DIR/artifacts/page_plan.json`
- site worktree under `RUN_DIR/work/site/` (writeable)
- templates/ruleset registry (read-only)

## Outputs
- `RUN_DIR/artifacts/patch_bundle.json`
- `RUN_DIR/reports/diff_report.md`

## Allowed paths
- src/launch/workers/w6_linker_and_patcher/**
- src/launch/workers/_patch/**
- tests/unit/workers/test_tc_450_linker_patcher.py
- reports/agents/**/TC-450/**
## Implementation steps
1) Load page_plan; enumerate expected output paths.
2) Map each draft to a site worktree target path.
3) Generate PatchBundle entries:
   - include target_path, op (create/update), sha256 before/after where possible
4) Enforce allowed_paths before writing anything.
5) Apply patches in deterministic order.
6) Generate `diff_report.md` with a stable ordering and stable headings.
7) Validate and write `patch_bundle.json` (schema + stable JSON) and emit events.

## E2E verification
**Concrete command(s) to run:**
```bash
python -m launch.workers.w6_linker_patcher --draft-dir artifacts/draft_sections --site-dir workdir/site
```

**Expected artifacts:**
- artifacts/patch_bundle.json
- workdir/site/content/**/*.md (patched files)

**Success criteria:**
- [ ] Patches apply cleanly
- [ ] No out-of-fence writes

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-440 (draft sections), TC-540 (path resolver)
- Downstream: TC-460 (Validator)
- Contracts: specs/08_patch_engine.md patch format

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
- Code: W6 implementation + patch application helpers
- Tests:
  - unit test: deterministic patch ordering
  - unit test: allowed_paths violation opens blocker
  - integration test: apply patches to a fixture site repo and assert expected files changed
- Reports:
  - reports/agents/<agent>/TC-450/report.md
  - reports/agents/<agent>/TC-450/self_review.md

## Acceptance checks
- [ ] `patch_bundle.json` validates against schema
- [ ] Only allowed paths are changed
- [ ] Re-run produces identical patch_bundle bytes for same drafts/plan
- [ ] diff_report generated and stable

## Self-review
Use `reports/templates/self_review_12d.md`.
