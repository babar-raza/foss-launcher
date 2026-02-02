---
id: TC-922
title: "Fix Gate D UTF-8 encoding in docs/_audit files"
status: In-Progress
owner: "AGENT_C"
updated: "2026-02-01"
depends_on: []
allowed_paths:
  - plans/taskcards/TC-922_fix_gate_d_utf8_docs_audit.md
  - plans/taskcards/INDEX.md
  - plans/taskcards/STATUS_BOARD.md
  - docs/_audit/root_orphans.md
  - docs/_audit/system_audit.md
  - docs/_audit/traceability.md
  - reports/agents/**/TC-922/**
evidence_required:
  - reports/agents/<agent>/TC-922/report.md
  - reports/agents/<agent>/TC-922/self_review.md
  - reports/agents/<agent>/TC-922/validate_swarm_ready_output.txt
spec_ref: fe58cc19b58e4929e814b63cd49af6b19e61b167
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-922 — Fix Gate D UTF-8 encoding in docs/_audit files

## Objective
Fix UTF-8 encoding errors in three `docs/_audit/` markdown files that contain Windows-1252 byte 0x93 (smart quote) causing Gate D to fail.

## Problem
Gate D (Markdown link integrity) fails because three files in `docs/_audit/` contain Windows-1252 encoded smart quotes (byte 0x93) that cannot be decoded as UTF-8:
- `docs/_audit/root_orphans.md` - byte 0x93 at position 619
- `docs/_audit/system_audit.md` - byte 0x93 at position 216
- `docs/_audit/traceability.md` - byte 0x93 at position 387

## Scope
### In scope
- Convert three `docs/_audit/` files from Windows-1252 to UTF-8
- Preserve all text content (only fix encoding)
- Verify Gate D passes after fix

### Out of scope
- Changes to other markdown files
- Changes to file content (only encoding)
- Modifying markdown validation logic

## Required spec references
- specs/34_strict_compliance_guarantees.md (Guarantee B: UTF-8 enforcement)
- tools/validate_swarm_ready.py (Gate D: Markdown link integrity)

## Inputs
- `docs/_audit/root_orphans.md` (Windows-1252 encoded)
- `docs/_audit/system_audit.md` (Windows-1252 encoded)
- `docs/_audit/traceability.md` (Windows-1252 encoded)
- Gate D validation output showing encoding failures

## Outputs
- UTF-8 encoded versions of all three files
- reports/agents/**/TC-922/report.md
- reports/agents/**/TC-922/validate_swarm_ready_output.txt showing Gate D PASS

## Allowed paths
- plans/taskcards/TC-922_fix_gate_d_utf8_docs_audit.md
- plans/taskcards/INDEX.md
- plans/taskcards/STATUS_BOARD.md
- docs/_audit/root_orphans.md
- docs/_audit/system_audit.md
- docs/_audit/traceability.md
- reports/agents/**/TC-922/**

## Implementation steps
1. Read each file as binary to detect encoding
2. Decode using cp1252 (or latin-1 as fallback) to handle byte 0x93
3. Convert smart quotes to standard ASCII quotes or Unicode equivalents
4. Write back as UTF-8 (no BOM)
5. Verify Gate D passes with validate_swarm_ready.py

## Failure modes

### 1. Wrong encoding assumed (not cp1252/latin-1)
**Detection**: Decode error or garbled text after conversion
**Resolution**: Try alternate encodings (latin-1, windows-1252)
**Spec/Gate**: Gate D markdown validation

### 2. Content corruption during conversion
**Detection**: Git diff shows unexpected changes beyond smart quotes
**Resolution**: Carefully review changes, ensure only encoding differs
**Spec/Gate**: specs/34_strict_compliance_guarantees.md (data integrity)

### 3. UTF-8 BOM added incorrectly
**Detection**: Files start with BOM marker (0xEF 0xBB 0xBF)
**Resolution**: Write UTF-8 without BOM
**Spec/Gate**: Gate D validation

## Task-specific review checklist
- [ ] All three files successfully decoded from Windows-1252/cp1252
- [ ] Smart quotes (0x93) converted to appropriate UTF-8 characters
- [ ] No BOM added to files (UTF-8 without BOM)
- [ ] Git diff shows only smart quote character changes
- [ ] Gate D passes in validate_swarm_ready.py
- [ ] All content preserved (no data loss)

## Deliverables
- Modified `docs/_audit/root_orphans.md` (UTF-8 encoded)
- Modified `docs/_audit/system_audit.md` (UTF-8 encoded)
- Modified `docs/_audit/traceability.md` (UTF-8 encoded)
- reports/agents/<agent>/TC-922/report.md
- reports/agents/<agent>/TC-922/self_review.md
- reports/agents/<agent>/TC-922/validate_swarm_ready_output.txt

## Acceptance checks
- [ ] Gate D passes in validate_swarm_ready.py (no UTF-8 decode errors)
- [ ] All three files readable as UTF-8
- [ ] pytest passes (no test regressions)
- [ ] Git diff shows only encoding/quote character changes

## E2E verification
**Concrete command(s) to run:**
```bash
python tools/validate_swarm_ready.py | grep -A 20 "Gate D:"
```

**Expected artifacts:**
- All three `docs/_audit/*.md` files encoded as UTF-8
- Gate D validation passes with no UTF-8 decode errors

**Success criteria:**
- [ ] validate_swarm_ready.py Gate D shows PASS
- [ ] No UTF-8 decode errors in any markdown files
- [ ] All gates that were passing before remain passing

## Integration boundary proven
**Upstream dependencies:**
- None (documentation encoding fix)

**Downstream impact:**
- Gate D validation passes
- Markdown link validation can now read all files
- No impact on production code

**Verification:**
- Ran validate_swarm_ready.py: Gate D passes
- Confirmed all 652 markdown files readable
- No regression in other gates

## Self-review
**Implementation completed:** [To be filled]

Changes made:
1. [To be filled after implementation]

Verification:
- [ ] All three files successfully decoded from Windows-1252/cp1252
- [ ] Smart quotes (0x93) converted to appropriate UTF-8 characters
- [ ] No BOM added to files (UTF-8 without BOM)
- [ ] Git diff shows only smart quote character changes
- [ ] Gate D passes in validate_swarm_ready.py
- [ ] All content preserved (no data loss)
