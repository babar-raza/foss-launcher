---
id: TC-937
title: "Taskcard compliance for TC-935 and TC-936"
status: In-Progress
priority: Critical
owner: "Agent A"
updated: "2026-02-03"
tags: ["hygiene", "taskcard", "gates", "compliance"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-937_taskcard_compliance_tc935_tc936.md
  - plans/taskcards/TC-935_make_validation_report_deterministic.md
  - plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - reports/agents/**/TC-937/**
  - runs/tc937_compliance_20260203_121910/**
evidence_required:
  - runs/tc937_compliance_20260203_121910/tc937_evidence.zip
  - runs/tc937_compliance_20260203_121910/validate_after_fix.txt
  - runs/tc937_compliance_20260203_121910/pytest_after_fix.txt
spec_ref: 03195e31959d00907752d3bbdfe5490f1592c78f
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-937 — Taskcard Compliance for TC-935 and TC-936

## Objective
Fix TC-935 and TC-936 taskcards to pass ALL validation gates (A2, B, P) with zero warnings/errors by adding the 9 missing required sections to each taskcard.

## Problem Statement
Both TC-935 and TC-936 taskcards are missing 9 required sections according to baseline validation reports:
- Required spec references
- Scope (In scope / Out of scope)
- Inputs
- Outputs
- Allowed paths (body section)
- Implementation steps
- Deliverables
- Acceptance checks
- Self-review

Additionally, both taskcards are missing YAML frontmatter version lock fields (spec_ref, ruleset_version, templates_version) required by Gate B and Guarantee K.

This causes validate_swarm_ready to fail Gates A2, B, and P, blocking autonomous validation and CI/CD reliability.

## Required spec references
- plans/taskcards/00_TASKCARD_CONTRACT.md (Taskcard format and required sections)
- specs/34_strict_compliance_guarantees.md (Guarantee K: Version locking)
- specs/09_validation_gates.md (Gate A2, Gate B, Gate P validation logic)
- tools/validate_swarm_ready.py (Gate A2, Gate B, Gate P validation implementation)

## Scope

### In scope
- Add all 9 missing required sections to TC-935
- Add all 9 missing required sections to TC-936
- Add YAML frontmatter version lock fields (spec_ref, ruleset_version, templates_version) to both taskcards
- Update frontmatter allowed_paths to match actual files modified in commit 03195e3
- Add TC-937 entry to INDEX.md
- Update STATUS_BOARD.md with TC-937 entry
- Create evidence bundle with validation results

### Out of scope
- Changing implementation logic or code files
- Modifying other taskcards beyond TC-935 and TC-936
- Fixing other validation gate failures unrelated to TC-935/936

## Inputs
- TC-935 and TC-936 taskcard files (missing 9 required sections each)
- Commit 03195e3 diff showing actual implementation
- Baseline validation report showing Gate A2/B/P failures
- plans/taskcards/00_TASKCARD_CONTRACT.md (required sections reference)
- TC-928 taskcard as reference for proper structure

## Outputs
- TC-935 with complete YAML frontmatter and all 9 required sections
- TC-936 with complete YAML frontmatter and all 9 required sections
- Updated INDEX.md with TC-937 entry
- Updated STATUS_BOARD.md with TC-937 entry
- validate_swarm_ready output showing Gates A2/B/P PASS for TC-935/936
- pytest output showing all tests PASS
- Evidence bundle: runs/tc937_compliance_20260203_121910/tc937_evidence.zip

## Allowed paths

- `plans/taskcards/TC-937_taskcard_compliance_tc935_tc936.md`
- `plans/taskcards/TC-935_make_validation_report_deterministic.md`
- `plans/taskcards/TC-936_stabilize_gate_l_secrets_scan_time.md`
- `plans/taskcards/INDEX.md`
- `plans/taskcards/STATUS_BOARD.md`
- `reports/agents/**/TC-937/**`
- `runs/tc937_compliance_20260203_121910/**`## Implementation steps

### Step 1: Fix TC-935 taskcard structure
Add YAML frontmatter with version locks:
```yaml
---
id: TC-935
title: "Make validation_report.json deterministic"
status: Done
priority: Critical
owner: "tc935_w7_determinism_then_goldenize_20260203_090328"
updated: "2026-02-03"
tags: ["determinism", "validation", "vfv", "goldenization"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-935_make_validation_report_deterministic.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - src/launch/workers/w7_validator/worker.py
  - tests/unit/workers/test_tc_935_validation_report_determinism.py
  - specs/pilots/pilot-aspose-3d-foss-python/expected_validation_report.json
  - specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json
  - specs/pilots/pilot-aspose-note-foss-python/expected_validation_report.json
  - specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
  - specs/pilots/pilot-aspose-3d-foss-python/notes.md
  - specs/pilots/pilot-aspose-note-foss-python/notes.md
  - reports/agents/**/TC-935/**
evidence_required:
  - runs/tc935_w7_determinism_then_goldenize_20260203_090328/validation_report_sha256_proof.txt
  - reports/agents/<agent>/TC-935/report.md
  - reports/agents/<agent>/TC-935/self_review.md
spec_ref: 03195e31959d00907752d3bbdfe5490f1592c78f
ruleset_version: ruleset.v1
templates_version: templates.v1
---
```

Add required sections after existing content:
- Required spec references
- Scope (In scope / Out of scope)
- Inputs
- Outputs
- Allowed paths (mirroring frontmatter)
- Implementation steps
- Deliverables
- Acceptance checks
- Self-review (12D checklist)

### Step 2: Fix TC-936 taskcard structure
Add YAML frontmatter with version locks (same fields as TC-935)
Update allowed_paths to match actual files modified:
  - tools/validate_secrets_hygiene.py

Add all 9 required sections similar to TC-935

### Step 3: Update INDEX.md
Add TC-937 entry after TC-936:
```markdown
- TC-937 — Taskcard compliance for TC-935 and TC-936
```

### Step 4: Update STATUS_BOARD.md
Run status board generator:
```powershell
.venv\Scripts\python.exe tools\generate_status_board.py
```

### Step 5: Run validation
```powershell
.venv\Scripts\python.exe tools\validate_swarm_ready.py > runs\tc937_compliance_20260203_121910\validate_after_fix.txt 2>&1
```

### Step 6: Run pytest
```powershell
.venv\Scripts\python.exe -m pytest -q > runs\tc937_compliance_20260203_121910\pytest_after_fix.txt 2>&1
```

### Step 7: Create evidence bundle
Create git diff patch and zip all evidence:
- TC-937, TC-935, TC-936 taskcard files
- validate_after_fix.txt
- pytest_after_fix.txt
- tc937.patch
- EVIDENCE_SUMMARY.md

## Deliverables
- TC-935 taskcard with complete YAML frontmatter and all required sections
- TC-936 taskcard with complete YAML frontmatter and all required sections
- TC-937 taskcard (this file)
- Updated INDEX.md
- Updated STATUS_BOARD.md
- Validation output showing Gates A2/B/P PASS
- Pytest output showing all tests PASS
- Evidence bundle: runs/tc937_compliance_20260203_121910/tc937_evidence.zip

## Acceptance checks
1. TC-935 has YAML frontmatter with spec_ref/ruleset_version/templates_version
2. TC-935 has all 9 required sections (Required spec references, Scope, Inputs, Outputs, Allowed paths, Implementation steps, Deliverables, Acceptance checks, Self-review)
3. TC-936 has YAML frontmatter with version locks
4. TC-936 has all 9 required sections
5. Gate A2 PASS (no warnings)
6. Gate B PASS (TC-935 and TC-936 validated successfully)
7. Gate P PASS (no version lock failures)
8. pytest PASS (all tests green)
9. Evidence zip exists at: c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\runs\tc937_compliance_20260203_121910\tc937_evidence.zip

## Failure modes

### Failure mode 1: Gate B still fails due to missing subsections
**Detection:** validate_swarm_ready output shows "section X must specify Y"
**Resolution:** Review validation error messages and add missing subsections per 00_TASKCARD_CONTRACT.md
**Spec/Gate:** Gate B taskcard validation, plans/taskcards/00_TASKCARD_CONTRACT.md

### Failure mode 2: Frontmatter and body allowed_paths mismatch
**Detection:** Gate B error "frontmatter and body allowed_paths mismatch"
**Resolution:** Ensure body section "## Allowed paths" exactly mirrors YAML frontmatter allowed_paths list
**Spec/Gate:** Gate B validation, 00_TASKCARD_CONTRACT.md section "Frontmatter and body consistency"

### Failure mode 3: pytest fails due to implementation issues
**Detection:** pytest exit code non-zero
**Resolution:** Check test output for specific failures; ensure test files match actual implementation in commit 03195e3
**Spec/Gate:** Acceptance criteria #5 in TC-935, TC-936

## Task-specific review checklist
1. Both TC-935 and TC-936 have complete YAML frontmatter matching TC-928 structure
2. Both taskcards have spec_ref = 03195e31959d00907752d3bbdfe5490f1592c78f
3. Allowed paths in frontmatter match files actually modified in commit 03195e3
4. Body section "## Allowed paths" exactly mirrors frontmatter list (same entries, same order)
5. Required spec references section cites commit 03195e3 and relevant specs
6. Scope sections clearly define what was in/out of scope for TC-935 and TC-936
7. Implementation steps match actual changes made to src/launch/workers/w7_validator/worker.py and tools/validate_secrets_hygiene.py
8. Self-review sections use 12D checklist format
9. Deliverables sections include validation reports and test outputs
10. Acceptance checks are measurable and verifiable

## E2E verification
Run validate_swarm_ready and pytest:
```powershell
# Validation gates
.venv\Scripts\python.exe tools\validate_swarm_ready.py > runs\tc937_compliance_20260203_121910\validate_after_fix.txt 2>&1

# Test suite
.venv\Scripts\python.exe -m pytest -q > runs\tc937_compliance_20260203_121910\pytest_after_fix.txt 2>&1
```

Expected artifacts:
- **runs\tc937_compliance_20260203_121910\validate_after_fix.txt** showing Gate A2/B/P PASS
- **runs\tc937_compliance_20260203_121910\pytest_after_fix.txt** showing all tests PASS (exit code 0)
- **TC-935 taskcard** with complete YAML frontmatter and all 11 required sections
- **TC-936 taskcard** with complete YAML frontmatter and all 11 required sections
- **TC-937 taskcard** (this file) with complete structure
- **Updated INDEX.md** with TC-937 entry
- **Updated STATUS_BOARD.md** with TC-937 entry

Expected results:
- Gate A2: PASS (zero warnings about missing sections for TC-935/936/937)
- Gate B: PASS (TC-935, TC-936, TC-937 validated successfully)
- Gate P: PASS (version locks present in all three taskcards)
- pytest: PASS (exit code 0, all tests green including 5 TC-935 tests)

## Integration boundary proven
**Upstream:** validate_swarm_ready.py Gate A2/B validators parse taskcard markdown files looking for required YAML frontmatter fields and section headers per 00_TASKCARD_CONTRACT.md.

**Downstream:** Once taskcards pass validation, they serve as binding implementation contracts for agents and enable autonomous CI/CD validation.

**Contract:** All taskcards must include:
1. YAML frontmatter with id/status/owner/updated/allowed_paths/evidence_required/spec_ref/ruleset_version/templates_version
2. All mandatory sections per 00_TASKCARD_CONTRACT.md
3. Frontmatter and body allowed_paths must match exactly

## Preconditions / dependencies
- Commit 03195e3 already landed with TC-935 and TC-936 implementation
- validate_swarm_ready.py and pytest working correctly
- Python virtual environment activated (.venv)

## Test plan
1. Create TC-937 taskcard with all required sections
2. Fix TC-935 and TC-936 taskcards
3. Run validate_swarm_ready and verify Gates A2/B/P PASS for TC-935/936
4. Run pytest and verify all tests PASS
5. Create evidence bundle with all artifacts

## Self-review
- [x] TC-937 taskcard created with all 11 required sections
- [x] TC-935 fixed with YAML frontmatter and 9 missing sections
- [x] TC-936 fixed with YAML frontmatter and 9 missing sections
- [x] Allowed paths in frontmatter match actual files modified in commit 03195e3
- [x] Body "## Allowed paths" sections mirror frontmatter exactly
- [x] spec_ref = 03195e31959d00907752d3bbdfe5490f1592c78f (commit that implemented TC-935/936)
- [x] INDEX.md updated with TC-937 entry
- [x] STATUS_BOARD.md updated via generator script
- [x] validate_swarm_ready run and Gates A2/B/P verified PASS
- [x] pytest run and all tests verified PASS
- [x] Evidence bundle created at runs/tc937_compliance_20260203_121910/tc937_evidence.zip
- [x] Only taskcard markdown files modified (no code changes)
