---
id: TC-633
title: "Taskcard hygiene for TC-630/631/632 (Gate A2/B fixes)"
status: Done
owner: "VSCODE_AGENT"
updated: "2026-01-29"
depends_on: []
allowed_paths:
  - plans/taskcards/TC-630_golden_capture_pilot_3d.md
  - plans/taskcards/TC-631_offline_safe_pr_manager.md
  - plans/taskcards/TC-632_pilot_3d_config_truth.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-633/**
evidence_required:
  - reports/agents/<agent>/TC-633/report.md
  - reports/agents/<agent>/TC-633/self_review.md
  - "validate_swarm_ready.py 21/21 PASS after fixes"
spec_ref: 795ef77041401410c85fdb995e381e70879570e2
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-633 — Taskcard hygiene for TC-630/631/632 (Gate A2/B fixes)

## Objective
Fix Gate A2 and Gate B validation failures in TC-630, TC-631, and TC-632 to achieve 21/21 gates PASS in validate_swarm_ready.py.

## Required spec references
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard required sections and format)
- specs/09_validation_gates.md (Gate definitions)
- tools/validate_swarm_ready.py (Gate A2 and B implementation)

## Scope
### In scope
- Fix status enum: "In Progress" → "In-Progress" in TC-630/631/632
- Add missing required sections to TC-630/631/632:
  - ## Deliverables
  - ## Acceptance checks
  - ## Integration boundary proven
  - ## Self-review
- Fix broken spec references in TC-630/631:
  - specs/27_pilot_execution_model.md → specs/13_pilots.md
- Add TC-630/631/632/633 entries to INDEX.md
- Regenerate STATUS_BOARD.md via Gate C

### Out of scope
- Changing taskcard objectives or implementation steps
- Modifying spec files or other taskcards
- Implementing the actual functionality described in TC-630/631/632

## Non-negotiables (binding for this task)
- **No improvisation:** Only fix validation failures; do not alter taskcard content beyond what is required to pass gates.
- **Write fence:** ONLY change files under **Allowed paths** below.
- **Determinism:** Changes must be reproducible and verifiable via validate_swarm_ready.py.
- **Evidence:** Document all changes with before/after excerpts in report.md.

## Preconditions / dependencies
- Repository is on branch feat/pilot-e2e-golden-3d-20260129
- validate_swarm_ready.py baseline shows 2/21 gates failed (A2 and B)
- TC-630, TC-631, TC-632 taskcard files exist

## Inputs
- plans/taskcards/TC-630_golden_capture_pilot_3d.md (current state with validation failures)
- plans/taskcards/TC-631_offline_safe_pr_manager.md (current state with validation failures)
- plans/taskcards/TC-632_pilot_3d_config_truth.md (current state with validation failures)
- plans/taskcards/INDEX.md (missing entries for TC-630/631/632)
- tools/validate_swarm_ready.py (Gate A2 and B validators)

## Outputs
- Fixed plans/taskcards/TC-630_golden_capture_pilot_3d.md
- Fixed plans/taskcards/TC-631_offline_safe_pr_manager.md
- Fixed plans/taskcards/TC-632_pilot_3d_config_truth.md
- Updated plans/taskcards/INDEX.md
- Regenerated plans/taskcards/STATUS_BOARD.md
- reports/agents/VSCODE_AGENT/TC-633/report.md
- reports/agents/VSCODE_AGENT/TC-633/self_review.md

## Allowed paths

- `plans/taskcards/TC-630_golden_capture_pilot_3d.md`
- `plans/taskcards/TC-631_offline_safe_pr_manager.md`
- `plans/taskcards/TC-632_pilot_3d_config_truth.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-633/**`## Implementation steps

### 1. Fix status enum in all three taskcards
In TC-630, TC-631, TC-632, change frontmatter:
```yaml
status: In Progress
```
To:
```yaml
status: In-Progress
```

### 2. Fix broken spec references in TC-630 and TC-631
In TC-630_golden_capture_pilot_3d.md, line 31:
- Change: `- specs/27_pilot_execution_model.md`
- To: `- specs/13_pilots.md`

In TC-631_offline_safe_pr_manager.md, line 34:
- Change: `- specs/27_pilot_execution_model.md`
- To: `- specs/13_pilots.md`

Note: specs/21_worker_contracts.md:322-344 reference in TC-631 is correct (lines 322-344 exist and contain W9 contract).

### 3. Add missing required sections to TC-630

Add before "## Dependencies" section:

```markdown
## Deliverables
- Code: None (golden capture is artifact-based)
- Tests: None (E2E verification is the test)
- Docs/specs/plans:
  - specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json (populated with real data)
  - specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json (populated with real data)
  - specs/pilots/pilot-aspose-3d-foss-python/notes.md (updated with run metadata)
- Reports (required):
  - reports/agents/<agent>/TC-630/report.md
  - reports/agents/<agent>/TC-630/self_review.md

## Acceptance checks
- [ ] Golden files (expected_page_plan.json, expected_validation_report.json) are populated with real data (no PLACEHOLDER strings)
- [ ] notes.md contains factual run metadata: run_id, commit SHAs, OFFLINE_MODE setting, LLM endpoint (no secrets)
- [ ] Determinism proof: SHA256 checksums match across two independent E2E runs
- [ ] Re-running pilot E2E with goldens in place produces PASS for expected-vs-actual comparison
- [ ] validate_swarm_ready.py passes all gates
- [ ] Agent report.md and self_review.md completed per templates

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: Pilot E2E script (scripts/run_pilot_e2e.py) receives pilot name and run_config.pinned.yaml
- Downstream: Golden files are consumed by future E2E runs for regression detection
- Contracts: artifacts/page_plan.json and artifacts/validation_report.json schemas validated during E2E run

## Self-review
Use `reports/templates/self_review_12d.md`. Evidence: determinism proof (checksums), golden files non-placeholder check, E2E logs showing successful runs.
```

### 4. Add missing required sections to TC-631

Add before "## Dependencies" section:

```markdown
## Deliverables
- Code:
  - src/launch/workers/w9_pr_manager/worker.py (modified to support offline mode and client construction)
- Tests:
  - tests/unit/workers/test_tc_480_pr_manager.py (extended with offline mode and client construction tests)
- Docs/specs/plans: None
- Reports (required):
  - reports/agents/<agent>/TC-631/report.md
  - reports/agents/<agent>/TC-631/self_review.md

## Acceptance checks
- [ ] execute_pr_manager constructs CommitServiceClient from run_config when commit_client is None
- [ ] OFFLINE_MODE=1 environment variable skips network calls and writes pr_payload.json to RUN_DIR/offline_bundles/
- [ ] Unit tests cover: (a) commit_client injected, (b) commit_client None/constructed, (c) OFFLINE_MODE path
- [ ] All existing PR manager tests still pass
- [ ] Pilot E2E runs successfully in offline mode (integration test)
- [ ] validate_swarm_ready.py passes all gates
- [ ] Agent report.md and self_review.md completed per templates

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: W9 receives commit_client (may be None) and run_config from orchestrator
- Downstream: In online mode, commit_client.create_commit() and commit_client.open_pr() are called; in offline mode, offline bundle written to RUN_DIR/offline_bundles/pr_payload.json
- Contracts: CommitServiceClient interface (specs/17_github_commit_service.md) validated; offline bundle is JSON file with deterministic structure

## Self-review
Use `reports/templates/self_review_12d.md`. Evidence: unit test outputs, offline bundle example, E2E pilot run with OFFLINE_MODE=1.
```

### 5. Add missing required sections to TC-632

Add before "## Dependencies" section:

```markdown
## Deliverables
- Code: None (verification task)
- Tests: None (git ls-remote proofs are the validation)
- Docs/specs/plans:
  - specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml (verified or updated with valid refs)
- Reports (required):
  - reports/agents/<agent>/TC-632/report.md
  - reports/agents/<agent>/TC-632/self_review.md
  - RUN_DIR/logs/ls_remote_*.txt (git ls-remote proofs)

## Acceptance checks
- [ ] All refs (github_ref, site_ref, workflows_ref) are exactly 40-character hexadecimal SHAs
- [ ] No refs are all-zeros (0000000000000000000000000000000000000000)
- [ ] git ls-remote confirms all refs exist in their respective remote repositories
- [ ] If any refs were updated, changes are documented in DECISIONS.md with rationale
- [ ] run_config.pinned.yaml is valid and ready for pilot E2E execution
- [ ] validate_swarm_ready.py passes all gates
- [ ] Agent report.md and self_review.md completed per templates

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: run_config.pinned.yaml is the binding input for pilot E2E script
- Downstream: Validated refs are used by W1 (repo cloning) and ensure no ref resolution failures during E2E
- Contracts: Gate J (Pinned refs policy) validates ref format; git ls-remote validates ref existence

## Self-review
Use `reports/templates/self_review_12d.md`. Evidence: git ls-remote proof logs, ref format validation commands, any DECISIONS.md entries if refs were updated.
```

### 6. Add TC-630/631/632/633 to INDEX.md

Read plans/taskcards/INDEX.md to understand the current format/ordering.

Add entries in the appropriate location (likely sorted by TC number):

```markdown
| TC-630 | Golden capture for pilot-aspose-3d-foss-python | In-Progress | PILOT_E2E_AGENT |
| TC-631 | Offline-safe PR manager (W9) | In-Progress | PILOT_E2E_AGENT |
| TC-632 | Pilot 3D config truth verification | In-Progress | PILOT_E2E_AGENT |
| TC-633 | Taskcard hygiene for TC-630/631/632 (Gate A2/B fixes) | In-Progress | VSCODE_AGENT |
```

(Adjust format to match existing INDEX.md style.)

### 7. Verify fixes

Run:
```bash
.venv\Scripts\python.exe tools/validate_swarm_ready.py
```

Expected: 21/21 gates PASS.

If any gates still fail, review the error messages and iterate on the fixes.

## Test plan
- Unit tests to add: None (this is a documentation hygiene task)
- Integration tests to add: None
- Determinism proof: validate_swarm_ready.py output is deterministic (same fixes produce same validation results)

## Failure modes

### Failure mode 1: STATUS_BOARD.md regeneration fails or contains stale data
**Detection:** Gate C fails with regeneration errors, or STATUS_BOARD.md doesn't reflect latest taskcard frontmatter changes
**Resolution:** STATUS_BOARD.md is auto-generated by Gate C; never manually edit; if regeneration fails, check file permissions and verify STATUS_BOARD.md is not locked; re-run validate_swarm_ready.py to force regeneration
**Spec/Gate:** specs/09_validation_gates.md (Gate C - status board generation)

### Failure mode 2: Spec reference still broken after attempted fix
**Detection:** Gate A2 continues reporting broken spec reference errors after correction
**Resolution:** Double-check the corrected spec path exists using `ls specs/<path>` or file explorer; verify path is relative (not absolute); check for typos in spec filename; ensure spec file not renamed or moved
**Spec/Gate:** specs/09_validation_gates.md (Gate A2 - plans validation zero warnings)

### Failure mode 3: Added sections do not satisfy validator requirements
**Detection:** Gate A2 or B still reports missing section errors after adding sections
**Resolution:** Review plans/taskcards/00_TASKCARD_CONTRACT.md for exact section heading requirements; verify case-sensitive match (e.g., "## Deliverables" not "## deliverables"); ensure markdown heading level correct (## not # or ###); check section has required content (not empty stub)
**Spec/Gate:** specs/09_validation_gates.md (Gate A2, Gate B - taskcard validation)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] Status enum is exactly "In-Progress" (not "In Progress", "in-progress", etc.)
- [ ] All four required sections added to each taskcard (Deliverables, Acceptance checks, Integration boundary proven, Self-review)
- [ ] Broken spec references replaced with correct, existing paths
- [ ] INDEX.md entries follow the same format as existing entries
- [ ] validate_swarm_ready.py output shows 21/21 PASS
- [ ] No duplicate section headings in any fixed taskcard

## E2E verification
**Concrete command(s) to run:**
```bash
# Run validation before fixes (baseline)
.venv\Scripts\python.exe tools/validate_swarm_ready.py > baseline_before.txt 2>&1

# Apply fixes (manual edits to taskcards + INDEX.md)

# Run validation after fixes
.venv\Scripts\python.exe tools/validate_swarm_ready.py > baseline_after.txt 2>&1

# Verify 21/21 PASS
powershell -Command "Get-Content baseline_after.txt | Select-String -Pattern '21/21|PASS.*gates|gates.*PASS'"
```

**Expected artifacts:**
- plans/taskcards/TC-630_golden_capture_pilot_3d.md (fixed)
- plans/taskcards/TC-631_offline_safe_pr_manager.md (fixed)
- plans/taskcards/TC-632_pilot_3d_config_truth.md (fixed)
- plans/taskcards/INDEX.md (with TC-630/631/632/633 entries)
- plans/taskcards/STATUS_BOARD.md (regenerated)
- reports/agents/VSCODE_AGENT/TC-633/report.md
- reports/agents/VSCODE_AGENT/TC-633/self_review.md

**Success criteria:**
- [ ] validate_swarm_ready.py exits with 21/21 gates PASS
- [ ] Gate A2 (Plans validation) shows zero warnings
- [ ] Gate B (Taskcard validation) shows zero failures
- [ ] All expected artifacts exist and are valid
- [ ] No unintended changes to other files

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: validate_swarm_ready.py reads taskcard frontmatter and content
- Downstream: Clean taskcards enable subsequent phases (pilot E2E execution in TC-630)
- Contracts: Taskcard contract (plans/taskcards/00_TASKCARD_CONTRACT.md) validated; Gate A2/B schema validation

## Deliverables
- Code: None
- Tests: None
- Docs/specs/plans:
  - plans/taskcards/TC-630_golden_capture_pilot_3d.md (fixed)
  - plans/taskcards/TC-631_offline_safe_pr_manager.md (fixed)
  - plans/taskcards/TC-632_pilot_3d_config_truth.md (fixed)
  - plans/taskcards/INDEX.md (updated)
  - plans/taskcards/STATUS_BOARD.md (regenerated)
- Reports (required):
  - reports/agents/VSCODE_AGENT/TC-633/report.md
  - reports/agents/VSCODE_AGENT/TC-633/self_review.md

## Acceptance checks
- [ ] All acceptance criteria in this taskcard are met
- [ ] validate_swarm_ready.py reports 21/21 gates PASS
- [ ] Gate A2 and Gate B validation errors are resolved
- [ ] No new validation errors introduced
- [ ] Reports are written and include before/after excerpts
- [ ] Self-review 12D written; any dimension <4 includes a concrete fix plan

## Self-review
Use `reports/templates/self_review_12d.md`.
