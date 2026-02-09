---
id: "TC-930"
title: "Fix Pilot-1 (3D) placeholder SHAs with real pinned refs"
owner: "supervisor-agent"
status: "In-Progress"
created: "2026-02-02"
updated: "2026-02-03"
spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
evidence_required:
  - reports/agents/<agent>/TC-930/report.md
  - reports/agents/<agent>/TC-930/self_review.md
  - "validate_swarm_ready.py Gate J PASS after SHA pinning"
depends_on: []
allowed_paths:
  - "plans/taskcards/TC-930_fix_pilot1_3d_pinned_shas.md"
  - "plans/taskcards/INDEX.md"
  - "plans/taskcards/STATUS_BOARD.md"
  - "specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml"
  - "specs/pilots/pilot-aspose-3d-foss-python/notes.md"
  - "reports/agents/**/TC-930/**"
---

# Taskcard TC-930 — Fix Pilot-1 (3D) placeholder SHAs with real pinned refs

## Objective
Replace placeholder SHA values in Pilot-1 (3D) run_config.pinned.yaml with real, validated 40-hex commit SHAs to enable VFV golden runs and ensure deterministic reproducibility.

## Context
Pilot-1 (aspose-3d-foss-python) currently has placeholder SHAs ("0000...") for github_ref, site_ref, and workflows_ref in its pinned config. These placeholders pass schema validation but block real VFV runs because they cannot be cloned. Per specs/13_pilots.md, pinned pilot configs MUST reference specific, validated commit SHAs for full reproducibility (Guarantee A: no floating branches/tags).

## Scope

### In scope
- Resolve real commit SHAs for all three repos using git ls-remote HEAD
- Update run_config.pinned.yaml lines 14, 17, 21 with 40-hex SHAs
- Validate each SHA exists and is reachable via git ls-remote <repo_url> <sha>
- Document resolution facts in notes.md with timestamps and repo URLs

### Out of scope
- Changes to any other pilot configs
- Changes to Pilot-2 (NOTE) config (already has real SHAs)
- Modifications to site layout or allowed_paths sections
- Re-running VFV (will be done after TC-931 completes)

## Inputs
1. Current config: specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
2. Repo URLs from config:
   - github_repo_url: https://github.com/Aspose/aspose-3d-foss-python
   - site_repo_url: https://github.com/Aspose/aspose.org
   - workflows_repo_url: https://github.com/Aspose/aspose.org-workflows

## Outputs
1. Updated run_config.pinned.yaml with real SHAs at lines 14, 17, 21
2. Updated notes.md documenting:
   - Repo URLs
   - Resolved SHAs
   - Timestamp of resolution
   - Validation commands used
3. Evidence log: runs/tc930_fix_pilots_and_vfv_20260202_230459/logs/ls_remote_tc930.txt

## Required spec references
- specs/13_pilots.md (pilot config requirements, pinned refs)
- specs/10_determinism_and_caching.md (determinism guarantees)

## Allowed paths

- `plans/taskcards/TC-930_fix_pilot1_3d_pinned_shas.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
- `specs/pilots/pilot-aspose-3d-foss-python/notes.md`
- `reports/agents/**/TC-930/**`## Implementation steps

### Step 1: Resolve SHAs
Run git ls-remote for each repo to get HEAD commit SHAs:

```bash
git ls-remote https://github.com/Aspose/aspose-3d-foss-python HEAD
git ls-remote https://github.com/Aspose/aspose.org HEAD
git ls-remote https://github.com/Aspose/aspose.org-workflows HEAD
```

Save outputs to: runs/tc930_fix_pilots_and_vfv_20260202_230459/logs/ls_remote_tc930.txt

### Step 2: Validate SHAs
For each resolved SHA, validate it exists in the repo:

```bash
git ls-remote <repo_url> <sha>
```

Confirm non-empty output (SHA exists and is reachable).

### Step 3: Update run_config.pinned.yaml
Replace placeholder values with real SHAs:
- Line 14: github_ref: "<40-hex-sha>"
- Line 17: site_ref: "<40-hex-sha>"
- Line 21: workflows_ref: "<40-hex-sha>"

Preserve all other fields unchanged (comment on line 3 can remain as-is or be updated to reflect "production-ready").

### Step 4: Update notes.md
Create or update specs/pilots/pilot-aspose-3d-foss-python/notes.md with:

```markdown
## Pinned SHA Resolution (TC-930)
- **Date:** 2026-02-02 23:04 UTC
- **Repos:**
  - GitHub: https://github.com/Aspose/aspose-3d-foss-python
  - Site: https://github.com/Aspose/aspose.org
  - Workflows: https://github.com/Aspose/aspose.org-workflows
- **Resolved SHAs:**
  - github_ref: <sha>
  - site_ref: <sha>
  - workflows_ref: <sha>
- **Validation:** All SHAs validated via `git ls-remote <url> <sha>` (non-empty output)
```

### Step 5: Verify Gate Pass
Run validation to confirm pinned refs policy gate passes:

```bash
.venv\Scripts\python.exe tools/validate_swarm_ready.py
```

Save output to: runs/tc930_fix_pilots_and_vfv_20260202_230459/logs/validate_after_tc930.txt

Expected: Gate J (Pinned refs policy) remains PASS, no new gate failures introduced.

## Deliverables
1. Updated run_config.pinned.yaml with real 40-hex SHAs (github_ref, site_ref, workflows_ref)
2. Updated notes.md with resolution facts, timestamps, and repo URLs
3. Evidence log: runs/tc930_fix_pilots_and_vfv_20260202_230459/logs/ls_remote_tc930.txt
4. Validation log: runs/tc930_fix_pilots_and_vfv_20260202_230459/logs/validate_after_tc930.txt
5. Corrected github_repo_url to https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python

## Acceptance checks
- [ ] github_ref is a valid 40-hex SHA (not "0000...")
- [ ] site_ref is a valid 40-hex SHA (not "0000...")
- [ ] workflows_ref is a valid 40-hex SHA (not "0000...")
- [ ] Each SHA validated via `git ls-remote <url> <sha>` (non-empty output)
- [ ] notes.md updated with resolution facts and timestamp
- [ ] validate_swarm_ready runs without introducing new gate failures
- [ ] No changes to Pilot-2 (NOTE) config
- [ ] All changes within allowed_paths for TC-930

## E2E verification
After TC-931 completes and all gates pass, run:

```bash
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize --verbose
```

Expected:
- Run completes without clone errors
- Two run directories created (Run-1, Run-2)
- Determinism check PASS for page_plan.json and validation_report.json
- Golden files updated with real artifact hashes

## Integration boundary proven
- **Upstream:** None (fixes blocking issue for VFV)
- **Downstream:** Enables TC-931 and VFV Stage 3 to proceed
- **Dependencies:** None (can execute immediately)
- **Proven by:** VFV run for Pilot-1 completing successfully without clone errors

## Risk Assessment
- **Low risk:** Only updates config values, no code changes
- **Validation:** Each SHA verified before update
- **Rollback:** Git revert if SHAs are incorrect (unlikely given ls-remote validation)

## Task-specific review checklist
1. [ ] github_ref resolved to valid 40-hex SHA using git ls-remote for github_repo_url
2. [ ] site_ref resolved to valid 40-hex SHA using git ls-remote for site_repo_url
3. [ ] workflows_ref resolved to valid 40-hex SHA using git ls-remote for workflows_repo_url
4. [ ] Each SHA validated as reachable via git ls-remote <url> <sha> (non-empty output)
5. [ ] All three SHAs are different from placeholder "0000...0000"
6. [ ] run_config.pinned.yaml updated at lines 14, 17, 21 with real SHAs
7. [ ] notes.md created/updated with resolution timestamp (2026-02-03)
8. [ ] notes.md documents all three repo URLs and their resolved SHAs
9. [ ] validate_swarm_ready runs without new gate failures (Gate J remains PASS)
10. [ ] No changes made to Pilot-2 (NOTE) config files

## Failure modes

### Failure mode 1: git ls-remote fails to resolve HEAD SHA
**Detection:** Command `git ls-remote <url> HEAD` returns empty output or network error
**Resolution:** Verify repository URLs are correct and accessible; check network connectivity; try alternative refs like refs/heads/main or refs/heads/master; ensure authentication not required for public repos
**Spec/Gate:** specs/13_pilots.md (Pilot repo requirements), specs/02_repo_ingestion.md (Git operations)

### Failure mode 2: Resolved SHA is not reachable or does not exist
**Detection:** Validation command `git ls-remote <url> <sha>` returns empty output after SHA resolution
**Resolution:** Verify SHA was copied correctly (40 hex characters, no typos); check that repo history contains this commit; try resolving HEAD SHA again as it may have changed between resolution and validation; use specific branch ref instead of HEAD
**Spec/Gate:** specs/13_pilots.md (Pinned refs must be valid and reachable), Gate J (Pinned refs policy)

### Failure mode 3: VFV still fails after SHA pinning
**Detection:** Pilot VFV run fails with clone errors like "remote branch <sha> not found" despite real SHAs in config
**Resolution:** Check that TC-921 (SHA clone fix) has been implemented in clone_helpers.py; verify run_config.pinned.yaml was saved correctly; ensure pilot selection in VFV command matches updated config; clear any cached git clones
**Spec/Gate:** TC-921 (SHA clone implementation), specs/02_repo_ingestion.md (Clone operations)

## Self-review
- [ ] Taskcard follows required structure (Objective, Scope, Inputs, Outputs, Self-review)
- [ ] allowed_paths covers all files to be modified
- [ ] Acceptance criteria are concrete and testable
- [ ] E2E verification includes specific command and expected artifacts
- [ ] YAML frontmatter complete (all required keys present)
- [ ] Spec references accurate (22_pilot_contracts.md, 21_determinism_and_reproducibility.md)
- [ ] Integration boundary specifies downstream impact (enables VFV)
