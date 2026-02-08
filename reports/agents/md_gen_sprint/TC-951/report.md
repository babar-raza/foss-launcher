# TC-951 Implementation Report

## Agent: md_gen_sprint
## Taskcard: TC-951 - Pilot Approval Gate Controlled Override
## Date: 2026-02-03

## Summary
Implemented `--approve-branch` flag for VFV harness to bypass AG-001 approval gate during pilot validation runs. When enabled, VFV creates the approval marker file that PRManager (W9) requires, allowing the pipeline to complete and generate visible `.md` files. Flag is optional, preserving governance for production runs.

## Changes Implemented

### 1. VFV CLI Flag (scripts/run_pilot_vfv.py:638-641)
Added `--approve-branch` argument:
```python
parser.add_argument(
    "--approve-branch",
    action="store_true",
    help="Automatically approve branch creation for pilot validation (bypasses AG-001)"
)
```

### 2. Function Signature Update (scripts/run_pilot_vfv.py:317)
Added `approve_branch` parameter to `run_pilot_vfv()`:
```python
def run_pilot_vfv(
    pilot_id: str,
    goldenize_flag: bool,
    allow_placeholders: bool,
    output_path: Path,
    approve_branch: bool = False  # NEW
) -> Dict[str, Any]:
```

### 3. Marker File Creation (scripts/run_pilot_vfv.py:343-354)
Create approval marker before running pilots:
```python
# TC-951: Create approval marker if requested
marker_path = repo_root / "runs" / ".git" / "AI_BRANCH_APPROVED"
marker_created = False

if approve_branch:
    try:
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text("vfv-pilot-validation", encoding="utf-8")
        marker_created = True
        print(f"\nCreated approval marker for pilot validation: {marker_path}")
    except Exception as e:
        print(f"\nWARNING: Failed to create approval marker: {e}")
```

**Marker Content**: `"vfv-pilot-validation"` (identifier for approval source)
**Marker Location**: `runs/.git/AI_BRANCH_APPROVED` (PRManager checks this path)

### 4. Try-Finally Wrapper (scripts/run_pilot_vfv.py:356, 609-615)
Wrapped main execution in try-finally to ensure cleanup:
```python
try:
    # All VFV execution (preflight, runs, determinism, goldenize)
    ...
finally:
    # TC-951: Clean up approval marker if we created it
    if marker_created and marker_path.exists():
        try:
            marker_path.unlink()
            print(f"\nCleaned up approval marker: {marker_path}")
        except Exception as e:
            print(f"\nWARNING: Failed to clean up approval marker: {e}")
```

## Files Modified
1. `scripts/run_pilot_vfv.py` - Added flag, marker creation/cleanup (48 lines changed)

## Behavior

### Without --approve-branch Flag
```bash
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output vfv.json
```
- No approval marker created
- PRManager will fail with AG-001 error (as expected for production)
- Governance preserved

### With --approve-branch Flag
```bash
python scripts/run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output vfv.json --approve-branch
```
- Approval marker created at `runs/.git/AI_BRANCH_APPROVED`
- PRManager sees marker and proceeds (AG-001 satisfied)
- Pipeline completes, generates .md files
- Marker cleaned up after VFV completes

## Acceptance Criteria Met
- [x] VFV accepts optional `--approve-branch` flag
- [x] When flag is set, VFV creates the approval marker file before running pilots
- [x] Marker file contains approval_source="vfv-pilot-validation"
- [x] Without the flag, AG-001 enforcement remains (manual approval required)
- [x] Marker file cleaned up after VFV completes (finally block)
- [x] Git diff captured in evidence

## Testing Status
- Manual testing required (will occur during pilot VFV runs)
- Integration test: Run VFV with --approve-branch and verify PRManager proceeds
- Unit test for marker creation/cleanup would require extensive mocking

## Related Components
- **PRManager (W9)**: Checks for marker at [src/launch/workers/w9_pr_manager/worker.py:503-544](src/launch/workers/w9_pr_manager/worker.py#L503-L544)
- **Approval Source**: Marker content "vfv-pilot-validation" recognized by PRManager metadata builder

## Impact
- **Pilots**: Can now complete full pipeline including PR step
- **Content Generation**: Patches will be applied, .md files visible
- **Governance**: Manual approval still required for non-pilot runs
- **Determinism**: Marker creation/cleanup is deterministic (no timestamps)

## Next Steps
1. Test with actual pilot run (TC-952 must be implemented first for content visibility)
2. Verify PRManager accepts marker and proceeds
3. Confirm marker cleanup occurs even on VFV failure

## Security Considerations
- Flag is opt-in (explicit consent required)
- Marker clearly identifies source as "vfv-pilot-validation"
- Production workflows remain protected (no flag = no bypass)
- Marker is ephemeral (cleaned up after each run)
