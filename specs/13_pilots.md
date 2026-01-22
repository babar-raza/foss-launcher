# Pilots and Golden Runs

## Goal
Use two pilot projects to harden determinism and universality.

## Pilot set (current)
1) `pilot-aspose-3d-foss-python` — smaller repo, flatter layout, sparse examples, potential marketing/implementation mismatch
2) `pilot-aspose-note-foss-python` — larger repo, `src/` layout, rich README/API surface, binary testfiles, optional dependency groups

## For each pilot, define
- pilot_id
- github_repo_url + pinned SHA
- site_repo_url + pinned SHA
- launch_config pinned
- expected PagePlan hash
- expected ValidationReport ok=true

## Golden artifacts
Store in:
- `specs/pilots/<pilot_id>/expected_page_plan.json`
- `specs/pilots/<pilot_id>/expected_validation_report.json`
- `specs/pilots/<pilot_id>/notes.md`
- `specs/pilots/<pilot_id>/run_config.pinned.yaml`

## Regression criteria
- PagePlan must match expected hash.
- PatchBundle must match expected structure.
- ValidationReport must be ok and issue_count stable.

## Autopilot readiness
A pilot is "mature" when:
- 3 consecutive identical PagePlan runs
- 3 consecutive gate-pass runs
- zero uncited claims
- minimal diffs
