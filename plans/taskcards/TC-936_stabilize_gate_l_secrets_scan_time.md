# TC-936: Stabilize Gate L (Secrets Hygiene) to Avoid Timeout

**Status:** ACTIVE
**Priority:** P1 (Blocks validate_swarm_ready reliability)
**Created:** 2026-02-03
**Agent:** tc935_w7_determinism_then_goldenize_20260203_090328

## Problem Statement

Gate L (Secrets hygiene) times out after 60 seconds when running validate_swarm_ready on repos with many runs/** bundles and archives. This is an environmental/performance issue, not a real security failure, but it prevents reliable autonomous validation.

**Evidence:**
- Previous run: Gate L timed out at 60s (20/21 gates PASS)
- Root cause: Likely scanning runs/** directory full of .tar.gz bundles and artifacts
- Impact: Cannot rely on validate_swarm_ready for autonomous CI/CD

## Objective

Make Gate L complete within 60 seconds consistently by excluding generated artifacts and archives from secrets scanning, without reducing coverage of tracked source files.

## Acceptance Criteria

1. ✓ Gate L completes within 60 seconds consistently on repo with runs/** full of bundles
2. ✓ No reduction in scanning of tracked source files (src/, specs/, tests/, etc.)
3. ✓ Excludes: runs/**, *.zip, *.tar.gz, *.7z, *.png, *.jpg, *.pdf, *.bin
4. ✓ validate_swarm_ready shows 21/21 gates PASS
5. ✓ Gate L duration is logged and under threshold

## Allowed File Modifications

- `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md` (this file)
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `tools/validate_swarm_ready.py` (Gate L implementation)
- `reports/agents/**/TC-936/**`

## Implementation Plan

### 1. Locate Gate L Implementation
Search for secrets scanning gate:
```bash
rg -n "gate.*L|secrets.*hygiene|secret.*scan" tools/validate_swarm_ready.py -S
```

### 2. Update Exclusion Patterns
Modify secrets scan to:
- Use `git ls-files` to scan only tracked files, OR
- Add explicit exclusion patterns:
  - `runs/**`
  - `*.zip`, `*.tar.gz`, `*.7z`
  - `*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.pdf`
  - `*.bin`, `*.exe`, `*.dll`
- Use ripgrep with `--glob` patterns for fast filtering

### 3. Example Implementation Pattern
```python
# Use git ls-files for tracked files only
tracked_files = subprocess.check_output(
    ["git", "ls-files"],
    text=True
).strip().split("\n")

# Filter out non-source files
source_files = [f for f in tracked_files if not f.startswith("runs/")]
```

OR

```python
# Use ripgrep with exclusions
result = subprocess.run(
    ["rg", "-i", "--glob", "!runs/**", "--glob", "!*.{zip,tar.gz,png,jpg}",
     "pattern", "."],
    capture_output=True
)
```

## Test Verification

```powershell
# Run validate_swarm_ready and check Gate L timing
.venv/Scripts/python.exe tools/validate_swarm_ready.py

# Verify all 21 gates PASS
# Verify Gate L duration < 60s
```

## Dependencies

- None (isolated validation gate change)

## Risk Assessment

**Low Risk:**
- Change only affects secrets scanning performance, not logic
- Excludes only generated/archive files, not source code
- Tracked source files remain fully scanned
- May actually improve security signal by reducing noise from artifacts

## Notes

- This is NOT reducing security coverage; we don't need to scan generated bundles
- Secrets should only exist in tracked source files, not artifacts
- Faster scans enable more frequent validation

## Evidence Location

`runs/tc935_w7_determinism_then_goldenize_20260203_090328/`
