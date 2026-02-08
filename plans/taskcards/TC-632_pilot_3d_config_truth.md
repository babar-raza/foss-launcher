---
id: TC-632
title: "Pilot 3D config truth verification"
status: In-Progress
owner: "PILOT_E2E_AGENT"
updated: "2026-01-29"
depends_on: []
allowed_paths:
  - specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
  - reports/agents/**/TC-632/**
evidence_required:
  - reports/agents/<agent>/TC-632/report.md
  - reports/agents/<agent>/TC-632/self_review.md
  - "git ls-remote proof for all refs in run_config.pinned.yaml"
  - "All refs are 40-character hex SHAs (no all-zeros, no tags/branches)"
spec_ref: d420b76f215ff3073a6cd1762e40fa4510cebea3
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-632 — Pilot 3D config truth verification

## Objective
Verify that pilot-aspose-3d-foss-python run_config.pinned.yaml contains valid, reachable git refs (not placeholders, all-zeros, or floating tags/branches). Ensure all referenced repositories are accessible and all commit SHAs exist.

This ensures the pilot can run end-to-end without ref resolution failures.

## Required spec references
- specs/10_determinism_and_caching.md (Determinism and pinned refs)
- specs/34_strict_compliance_guarantees.md (Guarantee A: no floating branches/tags)
- specs/13_pilots.md (Pilot configuration)
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml

## Scope
### In scope
- Verify github_ref, site_ref, workflows_ref are 40-character hex SHAs
- Run `git ls-remote` on each repo to verify refs exist
- Update run_config.pinned.yaml if any refs are invalid
- Document verification in report

### Out of scope
- Modifying pilot logic or worker implementations
- Changing pilot expected outputs (handled by TC-630)
- Implementing offline PR manager (handled by TC-631)

## Inputs
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml

## Outputs
- Verified run_config.pinned.yaml with valid refs
- Git ls-remote proof logs saved to RUN_DIR/logs/
- Documentation of any ref updates in DECISIONS.md

## Allowed paths
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml
- reports/agents/**/TC-632/**

## Implementation steps

### 1. Read current run_config.pinned.yaml

Extract the following fields:
- github.repo_url
- github.ref (github_ref)
- site.repo_url
- site.ref (site_ref)
- workflows.repo_url (aspose.org-workflows)
- workflows.ref (workflows_ref)

### 2. Validate ref format

For each ref (github_ref, site_ref, workflows_ref):
- Verify it is exactly 40 characters long
- Verify it contains only hexadecimal characters [0-9a-f]
- Verify it is not all zeros (0000000000000000000000000000000000000000)

If any validation fails, flag for update.

### 3. Verify refs exist in remote repos

For each repo and ref pair, run:
```bash
git ls-remote <repo_url> <ref>
```

Expected output: `<ref> refs/...` or `<ref>` alone (for commit SHAs)

Save outputs to:
- RUN_DIR/logs/ls_remote_github.txt
- RUN_DIR/logs/ls_remote_site.txt
- RUN_DIR/logs/ls_remote_workflows.txt

### 4. Handle missing or invalid refs

If any ref does not exist:

**Option 1: Use current HEAD of default branch**
```bash
git ls-remote <repo_url> HEAD
```
Extract the SHA and update run_config.pinned.yaml.

**Option 2: Use a known-good ref from repo**
Query recent commits and select a stable one.

Document the change in DECISIONS.md:
```markdown
### D00X: Updated <ref_name> in pilot 3D config
- **Date:** 2026-01-29
- **Context:** Original ref <old_sha> not found in <repo_url>
- **Decision:** Updated to <new_sha> (HEAD of main branch)
- **Rationale:** Ensures pilot can run with reachable refs
- **Verification:** git ls-remote confirmed <new_sha> exists
```

### 5. Update run_config.pinned.yaml if needed

If any refs were updated, write the changes to run_config.pinned.yaml.

Preserve all other fields and formatting.

### 6. Re-verify all refs

After any updates, re-run git ls-remote for all refs to confirm they are valid.

## E2E verification
**Concrete command(s) to run:**
```bash
# Read config
powershell -Command "Get-Content specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml"

# Verify refs are 40-hex (not all-zeros)
powershell -Command "Get-Content specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml | Select-String -Pattern 'ref:' | Select-String -Pattern '[0-9a-f]{40}'"

# Verify github_ref exists
git ls-remote https://github.com/aspose-3d/Aspose.3D-API-References <github_ref>

# Verify site_ref exists
git ls-remote https://github.com/Aspose/aspose.org <site_ref>

# Verify workflows_ref exists
git ls-remote https://github.com/Aspose/aspose.org-workflows <workflows_ref>
```

**Expected artifacts:**
- specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml (verified or updated)
- RUN_DIR/logs/ls_remote_github.txt
- RUN_DIR/logs/ls_remote_site.txt
- RUN_DIR/logs/ls_remote_workflows.txt
- reports/agents/<agent>/TC-632/report.md
- reports/agents/<agent>/TC-632/self_review.md

**Success criteria:**
- [ ] All refs (github_ref, site_ref, workflows_ref) are 40-character hex SHAs
- [ ] No all-zeros refs
- [ ] git ls-remote confirms all refs exist in their respective repos
- [ ] Any updated refs documented in DECISIONS.md
- [ ] run_config.pinned.yaml is valid and runnable

## Acceptance criteria
1. github_ref, site_ref, workflows_ref are real 40-hex SHAs (no all-zeros)
2. Repo URLs point to real repositories (surrogate allowed)
3. git ls-remote proof captured for all refs
4. If refs were updated, changes are documented with rationale

## Deliverables
- Code: None (verification task)
- Tests: None (git ls-remote proofs are the validation)
- Docs/specs/plans:
  - specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml (verified or updated with valid refs)
- Reports (required):
  - reports/agents/<agent>/TC-632/report.md
  - reports/agents/<agent>/TC-632/self_review.md
  - RUN_DIR/logs/ls_remote_*.txt (git ls-remote proofs)

## Acceptance checks
- [ ] All refs (github_ref, site_ref, workflows_ref) are exactly 40-character hexadecimal SHAs
- [ ] No refs are all-zeros (0000000000000000000000000000000000000000)
- [ ] git ls-remote confirms all refs exist in their respective remote repositories
- [ ] If any refs were updated, changes are documented in DECISIONS.md with rationale
- [ ] run_config.pinned.yaml is valid and ready for pilot E2E execution
- [ ] validate_swarm_ready.py passes all gates
- [ ] Agent report.md and self_review.md completed per templates

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: run_config.pinned.yaml is the binding input for pilot E2E script
- Downstream: Validated refs are used by W1 (repo cloning) and ensure no ref resolution failures during E2E
- Contracts: Gate J (Pinned refs policy) validates ref format; git ls-remote validates ref existence

## Failure modes

### Failure mode 1: Git ls-remote fails due to network or auth issues
**Detection:** git ls-remote command exits non-zero or returns empty output; cannot verify refs exist
**Resolution:** Check network connectivity to github.com; verify repo URLs are accessible (public repos or valid credentials); try alternative refs (main vs master branch); if repo unavailable, document in DECISIONS.md and use surrogate repo with known-good SHA
**Spec/Gate:** specs/10_determinism_and_caching.md (pinned refs requirement)

### Failure mode 2: Ref format validation passes but refs don't exist in remote
**Detection:** Refs are 40-char hex SHAs (not all-zeros) but git ls-remote returns no match
**Resolution:** Query recent commits using `git ls-remote <repo_url> HEAD` to get current HEAD SHA; update run_config.pinned.yaml with reachable ref; document ref change in DECISIONS.md with rationale and timestamp
**Spec/Gate:** specs/34_strict_compliance_guarantees.md (Guarantee A - no floating branches), Gate J

### Failure mode 3: Updated refs break pilot E2E due to incompatible changes
**Detection:** Pilot E2E runs successfully with new refs but produces different artifacts than expected; validation fails
**Resolution:** Review commit history between old and new refs for breaking changes; if new ref incompatible, find intermediate SHA that maintains compatibility; update expected outputs if changes are intentional; document compatibility considerations in specs/pilots/<pilot>/notes.md
**Spec/Gate:** specs/13_pilots.md (pilot configuration stability)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All three refs (github_ref, site_ref, workflows_ref) are exactly 40 hexadecimal characters
- [ ] No refs are all-zeros (0000000000000000000000000000000000000000)
- [ ] Git ls-remote proofs captured for all refs and saved to logs/
- [ ] If any refs were updated, DECISIONS.md includes entry with old/new SHAs and rationale
- [ ] Run_config.pinned.yaml is valid YAML and passes schema validation
- [ ] Repo URLs point to accessible repositories (public or with valid surrogate)

## Self-review
Use `reports/templates/self_review_12d.md`. Evidence: git ls-remote proof logs, ref format validation commands, any DECISIONS.md entries if refs were updated.

## Dependencies
None (this is a prerequisite for TC-630)
