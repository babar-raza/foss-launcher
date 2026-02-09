---
id: "TC-931"
title: "Fix taskcard structure, INDEX entries, and version locks (Gates A2/B/P/C)"
owner: "supervisor-agent"
status: "In-Progress"
created: "2026-02-02"
updated: "2026-02-03"
spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
evidence_required:
  - reports/agents/<agent>/TC-931/report.md
  - reports/agents/<agent>/TC-931/self_review.md
  - "validate_swarm_ready.py Gates A2/B/C/P PASS after fixes"
depends_on: []
allowed_paths:
  - "plans/taskcards/TC-931_fix_taskcards_index_and_version_locks.md"
  - "plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md"
  - "plans/taskcards/TC-703_pilot_vfv_harness.md"
  - "plans/taskcards/TC-930_fix_pilot1_3d_pinned_shas.md"
  - "plans/taskcards/INDEX.md"
  - "plans/taskcards/STATUS_BOARD.md"
  - "reports/agents/**/TC-931/**"
---

# Taskcard TC-931 — Fix taskcard structure, INDEX entries, and version locks

## Objective
Restore Gates A2, B, P, and C to PASS status by fixing taskcard frontmatter, adding missing required sections, updating INDEX.md with missing entries, and ensuring all taskcards have proper version lock fields. This resolves coupled failures across taskcard validation, plans validation, version locks, and status board generation.

## Context
Current baseline: 15/21 gates PASS, 6 gates FAIL. Four gates (A2, B, P, C) are failing due to incomplete taskcard structure:
- **Gate A2 (Plans validation):** TC-681 and TC-930 missing required sections; 6 taskcards missing from INDEX.md
- **Gate B (Taskcard validation):** TC-681, TC-703, TC-930 have missing YAML keys or vague E2E verification
- **Gate P (Version locks):** TC-681 and TC-930 missing ruleset_version/spec_ref/templates_version
- **Gate C (Status board):** Fails due to malformed taskcards upstream

These gates are coupled because they all validate taskcard completeness. Fixing the root causes (incomplete taskcards) will resolve all four gates simultaneously.

## Scope

### In scope
- Fix TC-930 frontmatter and add missing sections (A2/B/P requirements)
- Fix TC-681 frontmatter and add missing sections (A2/B/P requirements)
- Fix TC-703 E2E verification to be concrete (Gate B requirement)
- Add missing taskcard entries to INDEX.md (TC-681, TC-700, TC-701, TC-702, TC-703, TC-930, TC-931)
- Regenerate STATUS_BOARD.md via validation tools

### Out of scope
- Gate E (critical overlaps) - fixed in TC-932
- Gate R (subprocess wrapper) - fixed in TC-934
- Code changes to worker implementations
- VFV runs (done after all gates pass)

## Inputs
1. Current taskcards: TC-681, TC-703, TC-930
2. Validation output: runs/tc931_gate_restore_then_vfv_20260202_233815/logs/validate_before_tc931.txt
3. INDEX.md current state
4. Gate requirements from specs/09_validation_gates.md

## Outputs
1. Updated TC-930_fix_pilot1_3d_pinned_shas.md with:
   - Added YAML key: depends_on: []
   - Added sections: Required spec references, Allowed paths, Implementation steps, Deliverables, Acceptance checks, E2E verification, Integration boundary proven
   - spec_ref set to commit SHA (not a list)

2. Updated TC-681_w4_template_driven_page_enumeration_3d.md with:
   - Added YAML keys: allowed_paths, evidence_required, owner, ruleset_version, spec_ref, templates_version, updated, depends_on
   - Added sections: Objective, Scope, Inputs, Outputs, Self-review
   - Marked status as "superseded" with note pointing to TC-902
   - allowed_paths narrowed to only taskcard itself + reports (removing worker.py to avoid Gate E overlap)

3. Updated TC-703_pilot_vfv_harness.md with:
   - Concrete E2E verification command and expected artifacts (no vague language)

4. Updated INDEX.md with entries for: TC-681, TC-700, TC-701, TC-702, TC-703, TC-930, TC-931

5. Regenerated STATUS_BOARD.md (via validate_swarm_ready)

6. Evidence: runs/tc931_gate_restore_then_vfv_20260202_233815/logs/validate_after_tc931.txt

## Required spec references
- specs/09_validation_gates.md (Gate A2, B, P, C requirements)
- plans/_templates/taskcard.md (canonical taskcard template)

## Allowed paths

- `plans/taskcards/TC-931_fix_taskcards_index_and_version_locks.md`
- `plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md`
- `plans/taskcards/TC-703_pilot_vfv_harness.md`
- `plans/taskcards/TC-930_fix_pilot1_3d_pinned_shas.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-931/**`## Implementation steps

### Step 1: Fix TC-930 (add missing sections and keys)
Read current TC-930, then update:
- Add to YAML: `depends_on: []`
- Rename "## Objective" → keep as-is
- Rename "## Implementation Steps" → "## Implementation steps"
- Add "## Required spec references" with bullet list of specs/22_pilot_contracts.md, specs/21_determinism_and_reproducibility.md
- Rename existing content sections to match required names
- Add "## Deliverables" section listing tangible outputs
- Rename "## Acceptance Criteria" → "## Acceptance checks"
- Rename "## Integration & Verification" → split into "## E2E verification" and "## Integration boundary proven"
- Ensure spec_ref is commit SHA (35fb9356...), not a list

### Step 2: Fix TC-681 (add missing keys and sections, narrow paths)
Read current TC-681, then update:
- Add to YAML:
  ```yaml
  owner: "w4-agent"
  status: "superseded"
  created: "2026-01-30"
  updated: "2026-02-02"
  spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
  ruleset_version: "ruleset.v1"
  templates_version: "templates.v1"
  evidence_required: false
  depends_on: []
  allowed_paths:
    - "plans/taskcards/TC-681_w4_template_driven_page_enumeration_3d.md"
    - "reports/agents/**/TC-681/**"
  ```
- Add H1 title matching ID
- Add sections: ## Objective, ## Scope, ## Inputs, ## Outputs, ## Required spec references, ## Allowed paths, ## Implementation steps, ## Deliverables, ## Acceptance checks, ## Self-review
- In Objective, note: "Superseded by TC-902 for worker.py edits. Retained for historical reference."
- In allowed_paths body section, list only the two paths above (NOT worker.py)

### Step 3: Fix TC-703 (concrete E2E verification)
Read current TC-703, check if E2E verification is vague. If so, replace with:
```markdown
## E2E verification
Run VFV for Pilot-1 (3D):
```powershell
$env:OFFLINE_MODE="1"
.venv\Scripts\python.exe scripts\run_pilot_vfv.py --pilot pilot-aspose-3d-foss-python --goldenize --verbose
```

Expected artifacts:
- Run-1 directory: page_plan.json, validation_report.json
- Run-2 directory: page_plan.json, validation_report.json
- VFV report JSON with determinism check PASS
- Golden files updated: expected_page_plan.json, expected_validation_report.json
```

### Step 4: Update INDEX.md
Read current INDEX.md to understand format, then add missing entries in numerical order:
- TC-681 — W4 template-driven page enumeration (3D pilot)
- TC-700 — Template packs for 3D and NOTE families
- TC-701 — W4 family-aware path construction
- TC-702 — Validation report determinism
- TC-703 — Pilot VFV harness (determinism + goldenize)
- TC-930 — Fix Pilot-1 (3D) placeholder SHAs with real pinned refs
- TC-931 — Fix taskcard structure, INDEX entries, and version locks (Gates A2/B/P/C)

### Step 5: Verify Gates A2/B/P/C
Run validation:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```
Save output to: runs/tc931_gate_restore_then_vfv_20260202_233815/logs/validate_after_tc931.txt

Expected:
- Gate A2: PASS (no missing sections, no missing INDEX entries)
- Gate B: PASS (all taskcards valid)
- Gate P: PASS (all version locks present)
- Gate C: PASS (STATUS_BOARD generation succeeds)
- Gates E, R still FAIL (fixed in later stages)

## Deliverables
1. TC-930 with complete frontmatter and all required sections
2. TC-681 with complete frontmatter, sections, and narrow allowed_paths (no worker.py)
3. TC-703 with concrete E2E verification
4. INDEX.md with 7 new entries
5. STATUS_BOARD.md regenerated
6. Validation log showing Gates A2/B/P/C now PASS

## Acceptance checks
- [ ] TC-930 has depends_on key in YAML
- [ ] TC-930 has all required sections with proper names
- [ ] TC-930 spec_ref is a 40-hex commit SHA (not a list)
- [ ] TC-681 has all required YAML keys (owner, spec_ref, ruleset_version, templates_version, allowed_paths, etc.)
- [ ] TC-681 has all required sections
- [ ] TC-681 allowed_paths does NOT include src/launch/workers/w4_ia_planner/worker.py
- [ ] TC-703 E2E verification includes concrete command and expected artifacts
- [ ] INDEX.md contains entries for TC-681, TC-700, TC-701, TC-702, TC-703, TC-930, TC-931
- [ ] Gate A2 PASS
- [ ] Gate B PASS
- [ ] Gate P PASS
- [ ] Gate C PASS
- [ ] Gates E and R still FAIL (expected until TC-932/TC-934)

## E2E verification
After implementing all fixes, run:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Expected:
- Gates A2, B, P, C transition from FAIL → PASS
- 19/21 gates PASS (E and R still failing)
- No errors related to missing sections, missing INDEX entries, or missing version locks

## Integration boundary proven
**Upstream:** Depends on TC-930 (created but incomplete)
**Downstream:** Unblocks TC-932 (Gate E) and TC-934 (Gate R), which require clean taskcard baseline
**Proven by:** validate_swarm_ready showing Gates A2/B/P/C PASS after TC-931 implementation

## Risk Assessment
- **Low risk:** Only modifies taskcard metadata and structure, no code changes
- **Validation:** Each fix is tested via validate_swarm_ready gate checks
- **Rollback:** Git revert TC-931 commit if gates regress

## Task-specific review checklist
1. [ ] TC-930 YAML frontmatter has depends_on key added
2. [ ] TC-930 has all required sections renamed/added (Required spec references, Allowed paths, Implementation steps, Deliverables, Acceptance checks, E2E verification, Integration boundary proven)
3. [ ] TC-930 spec_ref is 40-hex commit SHA (not a list or dict)
4. [ ] TC-681 YAML frontmatter has all 8+ required keys (owner, status, created, updated, spec_ref, ruleset_version, templates_version, depends_on, allowed_paths, evidence_required)
5. [ ] TC-681 allowed_paths does NOT include src/launch/workers/w4_ia_planner/worker.py (narrowed to avoid Gate E overlap)
6. [ ] TC-681 has all required sections added (Objective, Scope, Inputs, Outputs, Required spec references, etc.)
7. [ ] TC-703 E2E verification includes concrete PowerShell command with expected artifacts list
8. [ ] INDEX.md has 7 new entries added in numerical order (TC-681, TC-700, TC-701, TC-702, TC-703, TC-930, TC-931)
9. [ ] validate_swarm_ready Gate A2 transitions from FAIL to PASS
10. [ ] validate_swarm_ready Gate B transitions from FAIL to PASS
11. [ ] validate_swarm_ready Gate P transitions from FAIL to PASS
12. [ ] validate_swarm_ready Gate C transitions from FAIL to PASS

## Failure modes

### Failure mode 1: Gate A2 still fails due to missing sections in updated taskcards
**Detection:** validate_swarm_ready output shows "Missing required section: X" for TC-930, TC-681, or TC-703
**Resolution:** Cross-reference updated taskcards against plans/taskcards/00_TASKCARD_CONTRACT.md required sections list; ensure section headers match exactly (case-sensitive, no extra spaces); verify all 14+ mandatory sections are present
**Spec/Gate:** Gate A2 (Plans validation), plans/taskcards/00_TASKCARD_CONTRACT.md

### Failure mode 2: Gate P still fails due to missing or malformed version lock fields
**Detection:** validate_swarm_ready shows "Missing ruleset_version" or "spec_ref must be commit SHA" for TC-681 or TC-930
**Resolution:** Verify YAML frontmatter has all three version fields: spec_ref (40-hex SHA string), ruleset_version ("ruleset.v1"), templates_version ("templates.v1"); ensure spec_ref is not a list or dict, just a plain string; get current SHA using git rev-parse HEAD
**Spec/Gate:** Gate P (Version locks validation), specs/10_determinism_and_caching.md

### Failure mode 3: Gate E (critical overlaps) fails due to TC-681 allowed_paths still including worker.py
**Detection:** validate_swarm_ready shows Gate E failure with "TC-681 and TC-902 both modify same file"
**Resolution:** Verify TC-681 allowed_paths contains ONLY plans/taskcards/TC-681_*.md and reports/agents/**/TC-681/**; remove any src/launch/workers/w4_ia_planner/worker.py entries; document in TC-681 Objective that worker changes are superseded by TC-902
**Spec/Gate:** Gate E (Critical path overlaps), specs/28_taskcard_allowed_paths.md

## Self-review
- [ ] Taskcard follows required structure (all required sections present)
- [ ] allowed_paths covers all files to be modified
- [ ] Acceptance criteria are concrete and testable
- [ ] E2E verification includes specific command and expected outcome
- [ ] YAML frontmatter complete (all required keys present, spec_ref is commit SHA)
- [ ] Spec references accurate and exist in repo
- [ ] Integration boundary specifies upstream/downstream dependencies explicitly
- [ ] Implementation steps are concrete and executable
- [ ] Deliverables list tangible outputs
