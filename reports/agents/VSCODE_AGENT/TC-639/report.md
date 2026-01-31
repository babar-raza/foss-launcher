# TC-639 Report: Capture Goldens for pilot-aspose-3d-foss-python

**Agent**: VSCODE_AGENT
**Taskcard**: TC-639
**Date**: 2026-01-30
**Status**: COMPLETE

## Summary

Captured golden expected_page_plan.json for pilot-aspose-3d-foss-python after TC-638 fixed W4 IAPlanner.

## Actions Taken

1. Copied page_plan.json from successful E2E run to expected_page_plan.json
2. Updated notes.md with run details, SHAs, and checksums
3. Verified determinism with two consecutive runs

## Commands Run

```bash
# Compute checksums
sha256sum runs/r_20260129T200943Z_3d-python_5c8d85a_f04c8553/artifacts/page_plan.json
sha256sum runs/r_20260129T201052Z_3d-python_5c8d85a_f04c8553/artifacts/page_plan.json

# Copy golden
cp runs/r_20260129T201052Z_3d-python_5c8d85a_f04c8553/artifacts/page_plan.json specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
```

## Evidence

### Run IDs
- Run 1: r_20260129T200943Z_3d-python_5c8d85a_f04c8553
- Run 2: r_20260129T201052Z_3d-python_5c8d85a_f04c8553

### Pinned SHAs
- github_ref: 5c8d85a914989458e4170a8f603dba530e88e45a
- site_ref: 8d8661ad55a1c00fcf52ddc0c8af59b1899873be
- workflows_ref: f4f8f86ef4967d5a2f200dbe25d1ade363068488

### Environment Variables
- OFFLINE_MODE=1
- LAUNCH_GIT_SHALLOW=1
- LAUNCH_GIT_RETRIES=3
- LAUNCH_GIT_LFS_SKIP_SMUDGE=1

### Checksums
- expected_page_plan.json SHA256: d9e07042fe02c9a0d9f8f0b24bcc13791745e54de33bd983b5a22b4c855cf978

### Determinism Proof
- Run 1 SHA256: d9e07042fe02c9a0d9f8f0b24bcc13791745e54de33bd983b5a22b4c855cf978
- Run 2 SHA256: d9e07042fe02c9a0d9f8f0b24bcc13791745e54de33bd983b5a22b4c855cf978
- Status: PASS (identical)

## Acceptance Criteria Checklist

| ID | Criterion | Status |
|----|-----------|--------|
| A | expected_page_plan.json contains actual W4 output | PASS |
| B | notes.md updated with run details | PASS |
| C | Determinism verified | PASS |
| D | validate_swarm_ready 21/21 PASS | PASS |

## Files Changed
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json (golden)
- specs/pilots/pilot-aspose-3d-foss-python/notes.md (updated)
- plans/taskcards/TC-639_capture_goldens_pilot1_3d.md (new taskcard)
- plans/taskcards/INDEX.md (updated)

## Notes
- expected_validation_report.json remains placeholder (W7 not reached yet due to W5+ blockers)
- page_plan shows launch_tier=minimal (CI absent in repo)
