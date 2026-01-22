# Pilots (golden runs)

This folder contains pinned “golden runs” used to harden determinism and universality.

Each pilot folder MUST contain:
- `run_config.pinned.yaml` — pinned inputs (repo SHAs, versions, allowed_paths)
- `expected_page_plan.json` — the expected PagePlan (or its hash + version)
- `expected_validation_report.json` — the expected ValidationReport (must have ok=true)
- `notes.md` — known quirks, repo structure notes, and any manual assumptions

Recommended additional files:
- `expected_snippet_catalog.json` (or hash)
- `expected_evidence_map.json` (or hash)
- `known_issues.md` (if a repo contains unavoidable limitations)

## Folder layout (binding)
- `specs/pilots/<pilot_id>/run_config.pinned.yaml`
- `specs/pilots/<pilot_id>/expected_page_plan.json`
- `specs/pilots/<pilot_id>/expected_validation_report.json`
- `specs/pilots/<pilot_id>/notes.md`

## Pilot IDs (current)
See `specs/13_pilots.md` for the current pilot set and maturity criteria.
