---
id: TC-1111
title: "Verify Track 3.1 Fix"
status: In-Progress
owner: "Agent E"
updated: "2026-02-10"
depends_on:
  - TC-1110
allowed_paths:
  - scripts/run_pilot.py
  - specs/pilots/pilot-aspose-note-foss-python/**
  - runs/track3_1_verification/**
  - reports/agents/agent_e/TC-1111_verify_track3_1/**
evidence_required:
  - reports/agents/agent_e/TC-1111_verify_track3_1/evidence.md
  - reports/agents/agent_e/TC-1111_verify_track3_1/self_review.md
spec_ref: bb0df68a8cc573a27e7fb3a8006e8a820385f194
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-1111 — Verify Track 3.1 Fix

## Objective
Verify that TC-1110 fix eliminated the TC-1106 regression and achieved Track 3.1 targets: errors ≤6, status NEEDS_CHANGES or better, pages passed ≥83%.

## Required spec references
- C:\Users\prora\.claude\plans\enchanted-drifting-naur.md (Track 3.1 section, lines 636-955)
- specs/21_worker_contracts.md (W7 ContentReviewer contract)
- specs/schemas/review_report.schema.json

## Scope
### In scope
- Verify TC-1110 commit exists in git log
- Run Track 3.1 pilot with TC-1110 fix
- Extract and compare metrics: Track 2 vs Track 3 vs Track 3.1
- Verify all bullet points <200 chars (no 1.6MB bullet points)
- Analyze remaining issues (if any)
- Production-readiness assessment
- Create evidence package with comparison tables and metrics
- 12D self-review with ≥4/5 on all dimensions

### Out of scope
- Implementation changes (TC-1110 responsibility)
- W5 SectionWriter modifications beyond verification
- W7 ContentReviewer modifications
- Track 4 or subsequent improvements
- Root cause analysis of non-regression issues

## Inputs
- TC-1110 commit SHA from git log
- Track 2 baseline: runs/r_20260210T095028Z_launch_pilot-aspose-note-foss-python_ec274a7_default_a2b79983/artifacts/review_report.json
- Track 3 baseline: runs/r_20260210T111338Z_launch_pilot-aspose-note-foss-python_ec274a7_default_a2b79983/artifacts/review_report.json
- Track 3.1 pilot run: runs/track3_1_verification/artifacts/review_report.json
- Track 3.1 developer-guide.md: runs/track3_1_verification/drafts/docs/developer-guide.md

## Outputs
- Verification summary (pass/fail on each metric)
- Comparison table (Track 2 vs Track 3 vs Track 3.1)
- Bullet point length analysis
- Remaining issues analysis (if errors >6)
- Production-readiness assessment with decision + rationale
- Evidence package in reports/agents/agent_e/TC-1111_verify_track3_1/
- 12D self-review

## Allowed paths
- scripts/run_pilot.py
- specs/pilots/pilot-aspose-note-foss-python/**
- runs/track3_1_verification/**
- reports/agents/agent_e/TC-1111_verify_track3_1/**

### Allowed paths rationale
All paths are read-only except reports/agents/agent_e/TC-1111_verify_track3_1/** (write). Verification task reads pilot configs and scripts, writes evidence package, and creates pilot run output.

## Preconditions / dependencies
- TC-1110 (Fix TC-1106 Regression) must be complete with git commit
- Track 2 baseline run artifacts must exist
- Track 3 baseline run artifacts must exist
- Python environment must be installed (.venv)
- PYTHONHASHSEED=0 for deterministic pilot runs

## Implementation steps

1. **Create evidence directory structure**:
   - Create reports/agents/agent_e/TC-1111_verify_track3_1/
   - Prepare evidence.md for findings

2. **Verify TC-1110 Complete (TASK 2)**:
   ```bash
   git log --oneline --since="2 hours ago" --grep="TC-1110" -1
   ```
   - Expected: 1 commit with Co-Authored-By tag
   - Document commit SHA in evidence.md

3. **Run Track 3.1 Pilot (TASK 3)**:
   ```bash
   set PYTHONHASHSEED=0
   .venv\Scripts\python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/track3_1_verification
   ```
   - Expected runtime: 7-8 minutes
   - Expected artifacts: review_report.json, developer-guide.md

4. **Extract and Compare Metrics (TASK 4)**:
   - Read Track 2 baseline: runs/r_20260210T095028Z_.../artifacts/review_report.json
   - Read Track 3 baseline: runs/r_20260210T111338Z_.../artifacts/review_report.json
   - Read Track 3.1 results: runs/track3_1_verification/artifacts/review_report.json
   - Create comparison table with columns: Metric, Track 2, Track 3, Track 3.1, Delta (3→3.1), Status
   - Metrics: Errors, Warnings, Pages Passed (%), Overall Status

5. **Verify Bullet Point Lengths (TASK 5)**:
   ```bash
   python -c "
   with open('runs/track3_1_verification/drafts/docs/developer-guide.md', 'r', encoding='utf-8') as f:
       lines = f.readlines()
       bullets = [l for l in lines if l.strip().startswith('- ')]
       long_bullets = [l for l in bullets if len(l) > 200]
       print(f'Total bullets: {len(bullets)}')
       print(f'Long bullets (>200 chars): {len(long_bullets)}')
       if bullets:
           print(f'Longest bullet: {max(len(l) for l in bullets)} chars')
   "
   ```
   - Expected: Long bullets = 0, longest <200 chars

6. **Analyze Remaining Issues (TASK 6)**:
   - If errors > 6:
     - Extract top 3-5 remaining error types from review_report.json
     - Categorize as: legitimate, false positive, or configuration issue
     - Document in evidence.md

7. **Production-Readiness Assessment (TASK 7)**:
   - Decision criteria:
     - ✅ Production-Ready: Errors ≤6, status NEEDS_CHANGES/PASS, pages ≥83%
     - ⚠️ Needs Follow-Up: Errors 7-10, substantial improvement but targets missed
     - ❌ Requires Investigation: Errors >10 or regressions detected
   - Document decision and rationale in evidence.md

8. **Create Evidence Package (TASK 8)**:
   - evidence.md sections:
     1. Verification Summary (pass/fail on each metric)
     2. Comparison Table (Track 2 vs 3 vs 3.1)
     3. Bullet Point Analysis
     4. Remaining Issues (if any)
     5. Production-Readiness Assessment
     6. Artifacts (pilot run path, review report path, TC-1110 commit SHA)

9. **12D Self-Review (TASK 9)**:
   - Create self_review.md using reports/templates/self_review_12d.md
   - Target: ≥4/5 on ALL 12 dimensions (≥48/60 total)

10. **Update Taskcard (TASK 10)**:
    - Update TC-1111 status to "Done"
    - Add final completion summary to evidence.md Section 10

## Test plan
- Verification test: TC-1110 commit exists in git log
- Regression test: Track 3.1 errors ≤ Track 2 errors (no regression)
- Quality test: All bullet points <200 chars
- Gate test: Track 3.1 status = NEEDS_CHANGES or PASS (not REJECT)
- Metrics test: Pages passed ≥83% (maintain Track 3 improvement)

## E2E verification
**Concrete command(s) to run:**
```bash
cd c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

# Verify TC-1110 commit
git log --oneline --since="2 hours ago" --grep="TC-1110" -1

# Run Track 3.1 pilot
set PYTHONHASHSEED=0
.venv\Scripts\python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/track3_1_verification

# Verify bullet point lengths
python -c "with open('runs/track3_1_verification/drafts/docs/developer-guide.md', 'r', encoding='utf-8') as f: lines = f.readlines(); bullets = [l for l in lines if l.strip().startswith('- ')]; long_bullets = [l for l in bullets if len(l) > 200]; print(f'Total bullets: {len(bullets)}'); print(f'Long bullets (>200 chars): {len(long_bullets)}'); print(f'Longest bullet: {max(len(l) for l in bullets)} chars' if bullets else 'No bullets')"
```

**Expected artifacts:**
- TC-1110 commit SHA in git log
- runs/track3_1_verification/artifacts/review_report.json
- runs/track3_1_verification/drafts/docs/developer-guide.md
- Evidence package: reports/agents/agent_e/TC-1111_verify_track3_1/evidence.md
- Self-review: reports/agents/agent_e/TC-1111_verify_track3_1/self_review.md

**Success criteria:**
- [ ] TC-1110 commit verified in git log with Co-Authored-By tag
- [ ] Pilot completes successfully with review_report.json generated
- [ ] Errors ≤6 (eliminate 29+ regression errors from Track 3)
- [ ] Long bullets (>200 chars) = 0
- [ ] Pages passed ≥83% (maintain Track 3 improvement)
- [ ] Production-readiness: YES or NEEDS_FOLLOW_UP (not REQUIRES_INVESTIGATION)
- [ ] Evidence package complete with all sections
- [ ] 12D self-review ≥48/60 (≥4/5 on all dimensions)

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-1110 (W5 SectionWriter bullet point truncation/filtering fix)
- Upstream: TC-1106 (W5 Limitations section generation)
- Downstream: W7 ContentReviewer (review_report.json validation)
- Contracts: specs/21_worker_contracts.md (W5 contract, W7 contract)
- Verification: Track 3.1 achieves ≤6 errors, eliminating TC-1106 regression

## Failure modes

### Failure mode 1: TC-1110 commit not found
**Detection:** git log returns no results; TC-1110 not in commit history
**Resolution:** Wait for Agent B to complete TC-1110; verify Agent B taskcard status is "Done"; check recent commits for alternate naming; escalate if Agent B reports completion but no commit exists
**Spec/Gate:** Git history verification, taskcard status check

### Failure mode 2: Pilot run fails
**Detection:** scripts/run_pilot.py exits with non-zero code; no review_report.json generated; Python exceptions in output
**Resolution:** Check pilot configuration in specs/pilots/pilot-aspose-note-foss-python/; verify .venv is installed correctly; check PYTHONHASHSEED=0 is set; review error logs in runs/track3_1_verification/
**Spec/Gate:** specs/pilots/ (pilot config), CI/CD gate (pilot success requirement)

### Failure mode 3: Errors still >6 (regression not eliminated)
**Detection:** review_report.json shows severity_counts.error >6; Track 3.1 errors ≥ Track 3 errors
**Resolution:** Investigate remaining bullet point errors in review_report.json; check if TC-1110 fix was incomplete; verify developer-guide.md has truncated bullets; escalate to Agent B if TC-1110 fix didn't work; document in evidence.md as "Requires Investigation"
**Spec/Gate:** Track 3.1 spec (errors ≤6 target), production-readiness criteria

### Failure mode 4: New regressions introduced
**Detection:** Track 3.1 warnings > Track 3 warnings; Track 3.1 pages passed < Track 3 pages passed; new error types not in Track 2 or Track 3
**Resolution:** Analyze new issues in review_report.json; check if TC-1110 fix broke other functionality; run git diff on TC-1110 commit to review changes; escalate if unintended side effects detected; document in evidence.md
**Spec/Gate:** Regression prevention policy, taskcard contract (no unintended changes)

### Failure mode 5: Bullet point verification fails
**Detection:** Longest bullet >200 chars; long_bullets >0; Python script errors on malformed markdown
**Resolution:** Inspect developer-guide.md manually for long bullets; check if TC-1110 truncation logic applied; verify MAX_CLAIM_TEXT_LENGTH=200 in W5 code; escalate to Agent B if truncation not working; check for edge cases (e.g., list items vs paragraphs)
**Spec/Gate:** Track 3.1 spec (bullet points <200 chars requirement), W5 contract

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] TC-1110 commit SHA documented in evidence.md
- [ ] Comparison table shows all 4 metrics (Errors, Warnings, Pages Passed, Status)
- [ ] Delta column shows Track 3 → Track 3.1 change (negative for errors/warnings = improvement)
- [ ] Bullet point analysis confirms 0 long bullets and longest <200 chars
- [ ] Production-readiness assessment uses decision matrix criteria
- [ ] Remaining issues (if any) are categorized correctly
- [ ] Evidence package cites specific artifact paths (review_report.json, developer-guide.md)
- [ ] Self-review addresses verification thoroughness and metric accuracy
- [ ] No manual edits to generated content (read-only verification)
- [ ] All commands copy/pasted into evidence.md for reproducibility

## Deliverables
- Reports (required):
  - reports/agents/agent_e/TC-1111_verify_track3_1/evidence.md
  - reports/agents/agent_e/TC-1111_verify_track3_1/self_review.md
- Artifacts:
  - runs/track3_1_verification/ (pilot run output)
  - runs/track3_1_verification/artifacts/review_report.json
  - runs/track3_1_verification/drafts/docs/developer-guide.md

## Acceptance checks
- [ ] TC-1110 commit verified in git log
- [ ] Track 3.1 pilot run completed successfully
- [ ] Comparison table created with all metrics (Errors, Warnings, Pages Passed, Status)
- [ ] Errors ≤6 (Gate 4: eliminate 29+ regression errors)
- [ ] Long bullets = 0 (all <200 chars)
- [ ] Production-readiness assessment completed with decision
- [ ] Evidence package complete with all 6 sections
- [ ] Self-review scores ≥4/5 on all 12 dimensions (≥48/60 total, Gate 5)
- [ ] Taskcard status updated to "Done"
- [ ] No regressions introduced (warnings ≤205, pages ≥83%)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
