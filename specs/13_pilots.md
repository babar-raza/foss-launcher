# Pilots (Golden Runs for Regression Detection)

## Purpose
Establish two pilot projects as regression baselines to detect unintended changes in system behavior.

## Pilot Contract (binding)

### Required Pilot Fields
Each pilot MUST include:
- `pilot_id`: Unique identifier (e.g., `pilot_aspose_note_python`, `pilot_aspose_cells_dotnet`)
- `github_repo_url`: Public GitHub repo URL
- `github_ref`: Pinned commit SHA (NOT branch or tag)
- `site_ref`: Pinned site repo commit SHA
- `workflows_ref`: Pinned workflows repo commit SHA
- `run_config_path`: Path to pinned run config (e.g., `specs/pilots/{pilot_id}/run_config.pinned.yaml`)
- `golden_artifacts_dir`: Path to golden artifacts (e.g., `specs/pilots/{pilot_id}/golden/`)

### Golden Artifacts (binding)
Each pilot MUST generate and store:
1. `golden/page_plan.json` - Golden PagePlan
2. `golden/validation_report.json` - Golden ValidationReport with ok=true
3. `golden/patch_bundle.json` - Golden PatchBundle
4. `golden/diff_summary.md` - Human-readable diff summary
5. `golden/fingerprints.json` - Hashes of all artifacts for regression detection

### Pilot Execution Contract (binding)

To execute a pilot run:
1. Load pilot config from `specs/pilots/{pilot_id}/run_config.pinned.yaml`
2. Validate config includes pinned SHAs for all `*_ref` fields (no floating refs allowed)
3. Execute full launch run with `validation_profile=ci`
4. Generate artifacts under `RUN_DIR/artifacts/`
5. Compare generated artifacts to golden artifacts via diff algorithm (below)
6. Emit telemetry event `PILOT_RUN_COMPLETED` with comparison results

### Regression Detection Algorithm (binding)

Compare generated artifacts to golden artifacts:

1. **Exact Match Artifacts** (must be byte-identical):
   - `page_plan.json` (after removing timestamps and run_id)
   - `validation_report.ok` field

2. **Semantic Equivalence Artifacts** (allow minor differences):
   - `patch_bundle.json`: Allow line number shifts ±5 lines, but operations must be identical
   - `validation_report.issues[]`: Allow empty vs empty, but any new BLOCKER is a regression

3. **Computed Diff Metrics**:
   - Page count delta: `|generated_page_count - golden_page_count|`
   - Claim count delta: `|generated_claim_count - golden_claim_count|`
   - Issue count delta: `|generated_issue_count - golden_issue_count|`

4. **Regression Thresholds** (configurable):
   - Page count delta > 2 → WARN
   - Claim count delta > 5 → WARN
   - New BLOCKER issue → FAIL
   - validation_report.ok changed from true to false → FAIL

5. **Regression Report**:
   Write to `RUN_DIR/reports/pilot_regression_report.md` with:
   - Summary: PASS / WARN / FAIL
   - Diff metrics
   - List of regressions detected
   - Suggested fixes (if deterministic)

### Golden Artifact Update Policy (binding)

Golden artifacts MUST be updated when:
1. Intentional system behavior change (e.g., new validation gate added)
2. Schema version bumped (breaking change)
3. Pilot repo/site SHA intentionally updated

Golden artifact update process:
1. Run pilot with new behavior
2. Validate all gates pass
3. Manually review diff between old and new golden artifacts
4. If diff is expected and correct:
   a. Replace `specs/pilots/{pilot_id}/golden/*` with new artifacts
   b. Update `fingerprints.json` with new hashes
   c. Commit with message: "Update pilot {pilot_id} golden artifacts: {reason}"
   d. Include rationale in commit body

## Pilots

### Pilot 1: Aspose.Note Python (planned)
- `pilot_id`: `pilot_aspose_note_python`
- `github_repo_url`: TBD (will be pinned after initial implementation)
- `github_ref`: TBD (pinned commit SHA)
- Purpose: Test Python repo adapter with standard repo structure
- Rationale: Larger repo with `src/` layout, rich README/API surface, binary testfiles, optional dependency groups

### Pilot 2: Aspose.3D Python (planned)
- `pilot_id`: `pilot_aspose_3d_python`
- `github_ref`: TBD (pinned commit SHA)
- Purpose: Test Python repo adapter with flat layout and sparse examples
- Rationale: Smaller repo, flatter layout, potential marketing/implementation mismatch detection

## Acceptance
- Two pilots exist with pinned SHAs
- Golden artifacts stored and versioned under `specs/pilots/{pilot_id}/golden/`
- Regression detection algorithm implemented and tested
- CI runs pilots on every commit with regression detection
- Golden artifact update commits include rationale
