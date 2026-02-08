# VFV-004 Execution Plan

**Agent**: Agent E (Observability & Ops)
**Workstream**: VFV-004 - IAPlanner VFV Readiness
**Run ID**: run_20260204_114709
**Date**: 2026-02-04

## Objectives

1. Verify VFV script has TC-950 exit code check implementation
2. Run VFV on pilot-aspose-3d-foss-python
3. Run VFV on pilot-aspose-note-foss-python
4. Analyze page_plan.json for spec compliance (TC-957, TC-958, TC-959)
5. Collect comprehensive evidence
6. Complete self-review

## Execution Steps

### Step 1: Verify VFV Script (TC-950)
- File: `scripts/run_pilot_vfv.py`
- Lines: 492-506
- Check: Exit code verification before determinism check

### Step 2: Run VFV on pilot-aspose-3d-foss-python
- Command: `.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --output reports\vfv_3d.json`
- Capture: exit code, JSON report, stdout/stderr, execution time

### Step 3: Run VFV on pilot-aspose-note-foss-python
- Command: `.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-note-foss-python --output reports\vfv_note.json`
- Capture: exit code, JSON report, stdout/stderr, execution time

### Step 4: Analyze page_plan.json Artifacts
- Verify URL path format: `/{family}/{platform}/{slug}/`
- Verify template paths: no `__LOCALE__` for blog
- Verify index pages: no duplicates per section

### Step 5: Document Evidence
- Create evidence.md with all findings
- Store artifacts in artifacts/ subfolder
- Document all commands in commands.sh

### Step 6: Self-Review
- Score all 12 dimensions
- Verify all criteria met
- Document any gaps

## Safety Protocols

- All artifacts in run_20260204_114709 folder
- No file overwrites
- Read-before-write for any existing files
- Windows path format used throughout
