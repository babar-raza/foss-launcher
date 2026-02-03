# TC-951: Pilot Approval Gate Controlled Override

## Metadata
- **Status**: Ready
- **Owner**: APPROVAL_GATE_FIXER
- **Depends On**: -
- **Created**: 2026-02-03
- **Updated**: 2026-02-03

## Problem Statement
PRManager (W9) enforces AG-001 approval gate by checking for marker file at `runs\.git\AI_BRANCH_APPROVED`. Without this file, the pipeline fails with:
```
AG-001 approval gate violation: approval marker missing at runs\.git\AI_BRANCH_APPROVED
```

For pilot validation runs, we need a controlled way to satisfy AG-001 so the pipeline can complete and generate visible `.md` files, while preserving governance for production runs.

## Acceptance Criteria
1. VFV accepts optional `--approve-branch` flag
2. When flag is set, VFV creates the approval marker file before running pilots
3. Marker file contains approval_source="vfv-pilot-validation"
4. Without the flag, AG-001 enforcement remains (manual approval required)
5. Unit test covers both scenarios:
   - With flag: PRManager proceeds successfully
   - Without flag: PRManager raises PRManagerError with AG-001 message
6. Gate A2 (if applicable) passes after fix

## Allowed Paths
- plans/taskcards/TC-951_pilot_approval_gate_controlled_override.md
- scripts/run_pilot_vfv.py
- tests/unit/workers/test_w9_approval_gate.py (or similar test file)
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-951/**

## Evidence Requirements
- reports/agents/<agent>/TC-951/report.md
- reports/agents/<agent>/TC-951/self_review.md
- reports/agents/<agent>/TC-951/test_output.txt (pytest showing both scenarios)
- reports/agents/<agent>/TC-951/vfv_approval_flag_diff.txt (git diff)

## Implementation Notes

### Current Enforcement (src/launch/workers/w9_pr_manager/worker.py:503-544)
```python
approval_marker_path = run_layout.run_dir.parent / ".git" / "AI_BRANCH_APPROVED"

if approval_marker_path.exists():
    # Read approval marker and proceed
else:
    # AG-001 gate enforcement: Block branch creation without approval
    raise PRManagerError(error_msg)
```

### Proposed Solution: VFV Flag (Option A - Recommended)
Add `--approve-branch` flag to VFV:

**In run_pilot_vfv.py:**
1. Add CLI argument:
```python
parser.add_argument(
    "--approve-branch",
    action="store_true",
    help="Automatically approve branch creation for pilot validation (bypasses AG-001)"
)
```

2. Create marker file before running pilots:
```python
if args.approve_branch:
    marker_path = repo_root / "runs" / ".git" / "AI_BRANCH_APPROVED"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text("vfv-pilot-validation", encoding="utf-8")
    logger.info(f"Created approval marker for pilot validation: {marker_path}")
```

3. Clean up marker after both runs:
```python
finally:
    if args.approve_branch and marker_path.exists():
        marker_path.unlink()
```

### Alternative: Environment Variable (Option B)
If preferred, check env var in PRManager:
```python
if approval_marker_path.exists() or os.getenv("AI_BRANCH_APPROVED") == "1":
    # Proceed
else:
    # Block
```

**Decision:** Implement Option A (--approve-branch flag) for explicit control.

### Test Requirements
Add test in `tests/unit/workers/test_w9_approval_gate.py`:
1. Test A: With approval marker present, PRManager proceeds
2. Test B: Without approval marker, PRManager raises PRManagerError
3. Both tests mock the commit_service client to avoid real API calls

## Dependencies
None

## Related Issues
- VFV status truthfulness (TC-950)
- No visible .md files (TC-952)

## Definition of Done
- [ ] --approve-branch flag added to VFV CLI
- [ ] Marker file created when flag is set
- [ ] Marker file cleaned up after VFV completes
- [ ] Unit tests cover both approval scenarios
- [ ] Test output captured in evidence
- [ ] git diff captured
- [ ] validate_swarm_ready and pytest fully green
- [ ] Report and self-review written
