---
id: "TC-932"
title: "Fix Gate E critical path overlaps"
owner: "supervisor-agent"
status: "In-Progress"
created: "2026-02-03"
updated: "2026-02-03"
spec_ref: "35fb9356c1e277ff05be2fbf60d59111ca2dece6"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
evidence_required:
  - reports/agents/<agent>/TC-932/report.md
  - reports/agents/<agent>/TC-932/self_review.md
  - "validate_swarm_ready.py Gate E PASS after overlap resolution"
depends_on: []
allowed_paths:
  - "plans/taskcards/TC-932_fix_gate_e_overlaps.md"
  - "plans/taskcards/TC-401_clone_and_resolve_shas.md"
  - "plans/taskcards/TC-701_w4_family_aware_paths.md"
  - "plans/taskcards/TC-921_fix_tc401_clone_sha_used_by_pilots.md"
  - "plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md"
  - "plans/taskcards/TC-926_fix_w4_path_construction_blog_and_subdomains.md"
  - "plans/taskcards/INDEX.md"
  - "plans/taskcards/STATUS_BOARD.md"
  - "reports/agents/**/TC-932/**"
---

# Taskcard TC-932 — Fix Gate E critical path overlaps

## Objective
Resolve critical path overlaps reported by Gate E by establishing canonical ownership for src/** files. This prevents multiple taskcards from claiming authority over the same implementation files.

## Context
Gate E reports 2 critical overlaps:
- `src/launch/workers/_git/clone_helpers.py`: claimed by TC-401 and TC-921
- `src/launch/workers/w4_ia_planner/worker.py`: claimed by TC-701, TC-902, TC-925, TC-926

Per specs/09_validation_gates.md Gate E, critical path files (src/** or repo-root) must have exactly ONE canonical owner to prevent conflicting changes.

## Scope
**In scope:**
- Remove `src/launch/workers/_git/clone_helpers.py` from TC-401 allowed_paths
- Remove `src/launch/workers/w4_ia_planner/worker.py` from TC-701, TC-925, TC-926 allowed_paths
- Keep canonical ownership: TC-921 for clone_helpers.py, TC-902 for worker.py
- Update INDEX.md to add TC-932 entry if missing

**Out of scope:**
- Code changes to worker implementations
- Non-critical overlaps (reports/**, tests/**)
- Changes to shared library policies

## Inputs
1. Gate E validation report showing critical overlaps
2. Current allowed_paths in affected taskcards
3. specs/09_validation_gates.md (Gate E requirements)

## Outputs
1. Updated TC-401 with clone_helpers.py removed from allowed_paths
2. Updated TC-701 with worker.py removed from allowed_paths
3. Updated TC-925 with worker.py removed from allowed_paths
4. Updated TC-926 with worker.py removed from allowed_paths
5. Gate E validation passing with zero critical overlaps

## Required spec references
- specs/09_validation_gates.md (Gate E: critical path overlap prevention)
- plans/taskcards/00_TASKCARD_CONTRACT.md (allowed_paths requirements)

## Allowed paths
- plans/taskcards/TC-932_fix_gate_e_overlaps.md
- plans/taskcards/TC-401_clone_and_resolve_shas.md
- plans/taskcards/TC-701_w4_family_aware_paths.md
- plans/taskcards/TC-921_fix_tc401_clone_sha_used_by_pilots.md
- plans/taskcards/TC-925_fix_w4_load_and_validate_run_config_signature.md
- plans/taskcards/TC-926_fix_w4_path_construction_blog_and_subdomains.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- reports/agents/**/TC-932/**

## Implementation steps

### Step 1: Remove clone_helpers.py from TC-401
Edit TC-401 frontmatter and body to remove:
- `src/launch/workers/_git/clone_helpers.py`

Note: TC-921 remains the canonical owner for clone_helpers.py fixes.

### Step 2: Remove worker.py from TC-701
Edit TC-701 frontmatter and body to remove:
- `src/launch/workers/w4_ia_planner/worker.py`

Note: TC-902 remains the canonical owner for W4 worker implementation.

### Step 3: Remove worker.py from TC-925
Edit TC-925 frontmatter and body to remove:
- `src/launch/workers/w4_ia_planner/worker.py`

Note: TC-925 should be a narrow fix taskcard that doesn't modify worker.py directly.

### Step 4: Remove worker.py from TC-926
Edit TC-926 frontmatter and body to remove:
- `src/launch/workers/w4_ia_planner/worker.py`

Note: TC-926 should be a narrow fix taskcard that doesn't modify worker.py directly.

### Step 5: Verify Gate E passes
Run validation:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Save output to: runs/tc931_a2bc_then_er_then_vfv_20260203_000521/logs/validate_after_tc932.txt

Expected:
- Gate E: PASS (zero critical overlaps)
- No new gate failures introduced

## Deliverables
1. TC-401 with clone_helpers.py removed from allowed_paths
2. TC-701 with worker.py removed from allowed_paths
3. TC-925 with worker.py removed from allowed_paths
4. TC-926 with worker.py removed from allowed_paths
5. Validation log showing Gate E PASS

## Acceptance checks
- [ ] TC-401 allowed_paths does NOT include src/launch/workers/_git/clone_helpers.py
- [ ] TC-701 allowed_paths does NOT include src/launch/workers/w4_ia_planner/worker.py
- [ ] TC-925 allowed_paths does NOT include src/launch/workers/w4_ia_planner/worker.py
- [ ] TC-926 allowed_paths does NOT include src/launch/workers/w4_ia_planner/worker.py
- [ ] TC-921 still owns clone_helpers.py
- [ ] TC-902 still owns worker.py
- [ ] Gate E PASS (zero critical overlaps)
- [ ] No new gate failures introduced

## E2E verification
After implementing all fixes, run:
```bash
.venv\Scripts\python.exe tools\validate_swarm_ready.py
```

Expected artifacts:
- Updated TC-401, TC-701, TC-925, TC-926 with removed paths
- Validation log showing Gate E PASS

Expected outcome:
- Gate E transitions from FAIL → PASS
- Critical overlaps count: 0
- 20/21 gates PASS (only Gate R still failing)

## Integration boundary proven
**Upstream:** TC-931 (structural fixes) → TC-932 (overlap resolution)
**Downstream:** TC-932 → TC-934 (subprocess policy) → VFV runs
**Proven by:** validate_swarm_ready showing Gate E PASS after TC-932 implementation

## Risk Assessment
- **Low risk:** Only modifies taskcard metadata (allowed_paths), no code changes
- **Validation:** Each fix is tested via validate_swarm_ready Gate E check
- **Rollback:** Git revert TC-932 commit if gates regress

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
