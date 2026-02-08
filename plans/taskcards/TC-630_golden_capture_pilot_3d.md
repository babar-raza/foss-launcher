---
id: TC-630
title: "Golden capture for pilot-aspose-3d-foss-python"
status: In-Progress
owner: "PILOT_E2E_AGENT"
updated: "2026-01-29"
depends_on: []
allowed_paths:
  - specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
  - specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json
  - specs/pilots/pilot-aspose-3d-foss-python/notes.md
  - reports/agents/**/TC-630/**
evidence_required:
  - reports/agents/<agent>/TC-630/report.md
  - reports/agents/<agent>/TC-630/self_review.md
  - "Golden files populated with real run outputs"
  - "Determinism proof: checksums match across two runs"
spec_ref: d420b76f215ff3073a6cd1762e40fa4510cebea3
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-630 — Golden capture for pilot-aspose-3d-foss-python

## Objective
Capture golden (expected) outputs from a successful end-to-end run of the pilot-aspose-3d-foss-python pilot and establish determinism proof by verifying that two independent runs produce identical artifacts.

## Required spec references
- specs/10_determinism_and_caching.md
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
- specs/13_pilots.md

## Scope
### In scope
- Run pilot-aspose-3d-foss-python E2E successfully
- Capture actual outputs: page_plan.json and validation_report.json
- Copy outputs as golden files into specs/pilots/pilot-aspose-3d-foss-python/
- Update notes.md with run metadata (run_id, SHAs, environment)
- Prove determinism: run twice and verify checksums match

### Out of scope
- Modifying pilot logic or worker implementations
- Changing run_config.pinned.yaml (handled by TC-632)
- Offline PR manager implementation (handled by TC-631)

## Inputs
- Working pilot-aspose-3d-foss-python configuration (TC-632)
- Functional offline-safe PR manager (TC-631)
- Running telemetry and commit service stubs

## Outputs
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json (real data, not placeholder)
- specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json (real data, not placeholder)
- specs/pilots/pilot-aspose-3d-foss-python/notes.md (updated with run metadata)
- Determinism proof with checksums in run report

## Allowed paths
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
- specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json
- specs/pilots/pilot-aspose-3d-foss-python/notes.md
- reports/agents/**/TC-630/**

## Implementation steps
1) **Prerequisites check**: Verify TC-632 (valid config) and TC-631 (offline PR manager) are complete
2) **First E2E run**: Execute `scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python` with OFFLINE_MODE=1
3) **Capture artifacts**: Copy artifacts/page_plan.json and artifacts/validation_report.json to expected_*.json
4) **Update notes**: Record run_id, commit SHAs used, offline mode setting, LLM endpoint (no secrets)
5) **Second E2E run**: Execute pilot E2E again (fresh run directory)
6) **Determinism proof**: Compute SHA256 checksums of canonical JSON outputs from both runs and verify match
7) **Verification**: Re-run pilot E2E to confirm expected-vs-actual comparison passes

## E2E verification
**Concrete command(s) to run:**
```bash
# PowerShell: set OFFLINE_MODE=1
$env:OFFLINE_MODE="1"

# Run pilot E2E
.venv\Scripts\python.exe scripts/run_pilot_e2e.py --pilot pilot-aspose-3d-foss-python --output artifacts\pilot_e2e_cli_report.json

# Verify golden files exist and are not placeholders
powershell -Command "Get-Content specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json | Select-String -Pattern 'PLACEHOLDER' -CaseSensitive"
# Should return no matches

# Check notes.md is updated
powershell -Command "Get-Content specs/pilots/pilot-aspose-3d-foss-python/notes.md | Select-String -Pattern 'run_id|github_ref'"
# Should show real values
```

**Expected artifacts:**
- specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json (non-placeholder)
- specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json (non-placeholder)
- specs/pilots/pilot-aspose-3d-foss-python/notes.md (with run metadata)
- reports/agents/<agent>/TC-630/report.md
- reports/agents/<agent>/TC-630/self_review.md

**Success criteria:**
- [ ] First E2E run completes successfully
- [ ] Golden files captured (expected_page_plan.json, expected_validation_report.json)
- [ ] Golden files contain real data (no PLACEHOLDER strings)
- [ ] notes.md updated with run metadata
- [ ] Second E2E run completes successfully
- [ ] Checksums from both runs match (determinism proof)
- [ ] Re-run with golden files in place: expected-vs-actual comparison passes

## Failure modes

### Failure mode 1: Golden files captured with PLACEHOLDER values instead of real data
**Detection:** expected_page_plan.json or expected_validation_report.json contains "PLACEHOLDER", "TODO", or "FIXME" strings; grep shows unresolved placeholders; subsequent pilot runs fail expected-vs-actual comparison with cryptic diffs
**Resolution:** Review goldenization process; ensure pilot E2E run completes successfully BEFORE capturing artifacts; verify artifacts/page_plan.json and artifacts/validation_report.json exist and validate against schemas; check that pilot run didn't abort early leaving partial outputs; re-run E2E and recapture goldens with --goldenize flag
**Spec/Gate:** specs/13_pilots.md (golden artifact requirements), Gate C (schema validation)

### Failure mode 2: Determinism check fails due to timestamp or run_id embedded in captured golden
**Detection:** Second E2E run produces different SHA256 checksum for page_plan.json or validation_report.json; diff shows timestamp or run_id differences; determinism_report.json shows artifacts_match=false
**Resolution:** Review artifact normalization; ensure timestamps removed or normalized before goldenization; verify run_id field excluded from golden comparison or normalized to canonical value; check that TC-935 path normalization applied; apply canonical JSON serialization (sorted keys, stable ordering) before capturing golden
**Spec/Gate:** specs/10_determinism_and_caching.md (canonical JSON), TC-935 (validation report normalization), Gate H (determinism)

### Failure mode 3: notes.md updated with secrets or sensitive environment data
**Detection:** Gate L (secrets scan) fails on notes.md; API tokens, credentials, or internal URLs found; security audit flags leaked data
**Resolution:** Review notes.md content before commit; ensure no LLM API keys, GitHub PATs, or internal endpoints included; verify only public metadata captured (run_id, commit SHAs, OFFLINE_MODE boolean, LLM provider name not token); apply TC-590 redaction to notes.md if needed; document notes.md content guidelines
**Spec/Gate:** specs/09_validation_gates.md (Gate L secrets), TC-590 (secret redaction), specs/34_strict_compliance_guarantees.md (Guarantee J)

### Failure mode 4: Golden overwrite loses previous baseline without backup
**Detection:** Previous golden artifacts deleted; git diff shows large changes; no backup created; unable to compare current vs previous golden behavior
**Resolution:** Add backup step to goldenization script; create timestamped backup (e.g., expected_page_plan.json.backup.20260203) before overwrite; require explicit --force flag for golden updates; document golden update procedure with git commit message template; commit golden changes separately from code changes for easy revert
**Spec/Gate:** specs/13_pilots.md (golden artifact management), specs/10_determinism_and_caching.md (regression baseline)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] expected_page_plan.json contains real page data with valid slugs, paths, and frontmatter (no PLACEHOLDER strings)
- [ ] expected_validation_report.json shows ok=true and contains actual gate results (not stub data)
- [ ] notes.md includes run_id, commit SHAs (specs, content repo), OFFLINE_MODE setting, LLM provider (no secrets)
- [ ] Determinism verified: two independent E2E runs produce identical SHA256 checksums for both golden files
- [ ] Re-running pilot with goldens in place produces PASS for expected-vs-actual comparison
- [ ] Golden files committed to git under specs/pilots/pilot-aspose-3d-foss-python/ with descriptive commit message
- [ ] No secrets or sensitive data in notes.md or golden artifacts (Gate L passes)
- [ ] Evidence bundle includes both run outputs, checksum verification, and diff comparison

## Acceptance criteria
1. expected_*.json files are NOT placeholders and match actual run artifacts
2. notes.md is updated with factual run metadata: run_id, SHAs, environment details
3. Determinism proof: SHA256 checksums of canonical JSON outputs match across two independent runs
4. Evidence bundle includes both run outputs and checksum verification

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

## Dependencies
- TC-632: Pilot config must have valid, reachable refs
- TC-631: PR manager must support offline mode to avoid network dependency
