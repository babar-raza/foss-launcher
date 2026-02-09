---
id: TC-951
title: "Pilot Approval Gate Controlled Override"
status: Draft
priority: Critical
owner: "APPROVAL_GATE_FIXER"
updated: "2026-02-03"
tags: ["approval-gate", "ag-001", "vfv", "pilot", "w9", "pr-manager"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-951_pilot_approval_gate_controlled_override.md
  - scripts/run_pilot_vfv.py
  - tests/unit/workers/test_w9_approval_gate.py
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-951/**
evidence_required:
  - reports/agents/<agent>/TC-951/report.md
  - reports/agents/<agent>/TC-951/self_review.md
  - reports/agents/<agent>/TC-951/test_output.txt
  - reports/agents/<agent>/TC-951/vfv_approval_flag_diff.txt
spec_ref: "fe582540d14bb6648235fe9937d2197e4ed5cbac"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# TC-951: Pilot Approval Gate Controlled Override

## Objective
Add a controlled override mechanism to VFV (--approve-branch flag) that allows pilot validation runs to bypass AG-001 approval gate while preserving governance for production runs.

## Problem Statement
PRManager (W9) enforces AG-001 approval gate by checking for marker file at `runs\.git\AI_BRANCH_APPROVED`. Without this file, the pipeline fails with:
```
AG-001 approval gate violation: approval marker missing at runs\.git\AI_BRANCH_APPROVED
```

For pilot validation runs, we need a controlled way to satisfy AG-001 so the pipeline can complete and generate visible `.md` files, while preserving governance for production runs.

## Required spec references
- specs/30_approval_gates.md (AG-001 approval gate specification)
- specs/21_worker_contracts.md (W9 PRManager contract)
- specs/34_strict_compliance_guarantees.md (Governance requirements)

## Scope

### In scope
- Add `--approve-branch` CLI flag to scripts/run_pilot_vfv.py
- Create approval marker file (`runs/.git/AI_BRANCH_APPROVED`) when flag is set
- Populate marker file with `approval_source="vfv-pilot-validation"`
- Clean up marker file after VFV completes (in finally block)
- Add unit tests for both approval scenarios (with/without marker)
- Ensure AG-001 enforcement remains for production runs (flag not set)

### Out of scope
- Modifying W9 PRManager approval gate logic (PRManager is correct, VFV needs to provide marker)
- Changing approval gate policy or requirements
- Automatic approval for non-pilot runs
- Bypassing other validation gates

## Inputs
- Current scripts/run_pilot_vfv.py without approval marker creation
- W9 PRManager expecting approval marker at `runs/.git/AI_BRANCH_APPROVED`
- AG-001 gate enforcement error message from failed pilot runs

## Outputs
- Modified scripts/run_pilot_vfv.py with --approve-branch flag implementation
- Approval marker file created/cleaned up when flag is used
- Unit tests in tests/unit/workers/test_w9_approval_gate.py
- VFV runs completing successfully with --approve-branch flag
- AG-001 enforcement still active for production runs (without flag)

## Allowed paths

- `plans/taskcards/TC-951_pilot_approval_gate_controlled_override.md`
- `scripts/run_pilot_vfv.py`
- `tests/unit/workers/test_w9_approval_gate.py`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-951/**`## Implementation steps

### Step 1: Add CLI argument to VFV
Add to run_pilot_vfv.py argument parser:
```python
parser.add_argument(
    "--approve-branch",
    action="store_true",
    help="Automatically approve branch creation for pilot validation (bypasses AG-001)"
)
```

### Step 2: Create marker file before pilot runs
In run_pilot_vfv.py main() function, after argument parsing:
```python
if args.approve_branch:
    marker_path = repo_root / "runs" / ".git" / "AI_BRANCH_APPROVED"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("vfv-pilot-validation", encoding="utf-8")
    logger.info(f"Created approval marker for pilot validation: {marker_path}")
```

### Step 3: Clean up marker in finally block
Wrap VFV execution in try/finally:
```python
try:
    # Run pilot VFV logic
    ...
finally:
    if args.approve_branch and marker_path.exists():
        marker_path.unlink()
        logger.info("Cleaned up approval marker")
```

### Step 4: Add unit tests
Create tests/unit/workers/test_w9_approval_gate.py:
```python
def test_prmanager_with_approval_marker(mock_commit_service):
    """Test A: With approval marker present, PRManager proceeds"""
    marker_path = run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("vfv-pilot-validation")

    # Execute PRManager - should NOT raise
    result = execute_pr_manager(...)
    assert result["status"] == "success"

def test_prmanager_without_approval_marker(mock_commit_service):
    """Test B: Without approval marker, PRManager raises PRManagerError"""
    # Ensure marker does NOT exist
    marker_path = run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"
    if marker_path.exists():
        marker_path.unlink()

    # Execute PRManager - should raise AG-001 error
    with pytest.raises(PRManagerError, match="AG-001 approval gate violation"):
        execute_pr_manager(...)
```

### Step 5: Test with pilot VFV
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --approve-branch
```

## Task-specific review checklist
1. [ ] --approve-branch flag added to run_pilot_vfv.py argument parser
2. [ ] Marker file path is `runs/.git/AI_BRANCH_APPROVED` (matches W9 expectation)
3. [ ] Marker file content is "vfv-pilot-validation" (traceable source)
4. [ ] Marker file created BEFORE pilot runs execute (timing critical)
5. [ ] Marker file cleanup in finally block (executes even on error)
6. [ ] Unit test verifies PRManager proceeds with marker present
7. [ ] Unit test verifies PRManager raises PRManagerError without marker
8. [ ] Both unit tests mock commit_service to avoid real API calls
9. [ ] VFV runs complete successfully with --approve-branch flag
10. [ ] Production runs (without flag) still enforce AG-001 gate

## Failure modes

### Failure mode 1: Marker file created in wrong location
**Detection:** W9 PRManager still raises AG-001 error despite --approve-branch flag; logs show "approval marker missing at runs\.git\AI_BRANCH_APPROVED"
**Resolution:** Verify marker_path construction matches W9 expectation exactly: `run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"`; check that runs/.git directory is created before writing file; inspect actual filesystem to confirm marker exists
**Spec/Gate:** specs/30_approval_gates.md (AG-001 marker path specification)

### Failure mode 2: Marker file not cleaned up after VFV completes
**Detection:** Marker file persists in runs/.git/ after VFV execution; subsequent production runs bypass AG-001 unexpectedly
**Resolution:** Verify cleanup code is in finally block (not just at end of try); check that marker_path variable is accessible in finally block (define before try); test exception scenarios to ensure cleanup executes on error
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (Governance integrity)

### Failure mode 3: Unit tests pass but VFV integration fails
**Detection:** pytest shows 2/2 PASS for approval gate tests, but pilot VFV still fails with AG-001 error
**Resolution:** Verify unit test setup creates marker at exact same path as VFV implementation; check that test mocks match actual W9 PRManager behavior; run VFV with --verbose to see marker creation/cleanup logs; inspect runs/.git/ directory during VFV execution
**Spec/Gate:** Integration contract between VFV and W9 PRManager

## Deliverables
- Modified scripts/run_pilot_vfv.py with --approve-branch flag
- Unit tests in tests/unit/workers/test_w9_approval_gate.py
- reports/agents/<agent>/TC-951/vfv_approval_flag_diff.txt (git diff)
- reports/agents/<agent>/TC-951/test_output.txt (pytest output showing both tests pass)
- reports/agents/<agent>/TC-951/report.md
- reports/agents/<agent>/TC-951/self_review.md

## Acceptance checks
1. VFV accepts optional `--approve-branch` flag
2. When flag is set, VFV creates the approval marker file before running pilots
3. Marker file contains approval_source="vfv-pilot-validation"
4. Without the flag, AG-001 enforcement remains (manual approval required)
5. Unit test covers both scenarios:
   - With flag: PRManager proceeds successfully
   - Without flag: PRManager raises PRManagerError with AG-001 message
6. Unit tests pass: pytest tests/unit/workers/test_w9_approval_gate.py
7. VFV completes successfully with --approve-branch flag
8. git diff captured in evidence
9. validate_swarm_ready and pytest fully green
10. Report and self-review written

## E2E verification
Run VFV with --approve-branch flag:
```bash
.venv/Scripts/python.exe scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --approve-branch --verbose
```

Expected artifacts:
- VFV creates marker file at runs/.git/AI_BRANCH_APPROVED before pilot runs
- W9 PRManager proceeds successfully (no AG-001 error)
- Marker file is cleaned up after VFV completes
- Pilot runs generate .md files in content_preview
- VFV JSON report shows status=PASS

## Integration boundary proven
**Upstream:** VFV harness (run_pilot_vfv.py) receives --approve-branch flag from CLI; responsible for marker file lifecycle
**Downstream:** W9 PRManager reads approval marker at `runs/.git/AI_BRANCH_APPROVED`; proceeds with branch creation if marker exists
**Contract:** VFV must create marker before pilot runs execute; marker must exist at exact path W9 expects; marker must be cleaned up after VFV completes (even on error)

## Self-review
- [ ] --approve-branch flag added to VFV CLI argument parser
- [ ] Marker file creation logic added before pilot execution
- [ ] Marker file cleanup logic in finally block
- [ ] Unit tests cover both scenarios (with/without marker)
- [ ] All required sections present per taskcard contract
- [ ] Allowed paths cover all modified files
- [ ] Acceptance criteria are measurable and testable
- [ ] E2E verification includes concrete command and expected artifacts
- [ ] Integration boundary specifies upstream/downstream/contract
