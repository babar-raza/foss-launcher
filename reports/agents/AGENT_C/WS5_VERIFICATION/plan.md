# Verification Plan - WS5: Verification & Testing

**Agent:** Agent C (Tests & Verification)
**Workstream:** WS5 - Verification & Testing
**Date:** 2026-02-03
**Status:** Complete

---

## Objective

Run comprehensive verification tests (V1, V2, V3) to validate all layers of the Taskcard Validation Prevention System and create a final evidence bundle proving the system works end-to-end.

---

## Test Cases

### V1: Enhanced Validator - All Taskcards

**Purpose:** Verify validator checks all 14 mandatory sections

**Test Command:**
```bash
.venv/Scripts/python.exe tools/validate_taskcards.py
```

**Expected Results:**
- All 82 taskcards validated
- TC-935 and TC-936 PASS (recently fixed)
- Report shows specific missing sections for incomplete taskcards
- Execution time <5 seconds

**Evidence to Capture:**
- Full validator output
- Count of passing vs failing taskcards
- Examples of error messages
- Performance timing

---

### V2: Incomplete Taskcard Detection

**Purpose:** Verify validator correctly identifies missing sections

**Test Procedure:**
```bash
# Create intentionally incomplete test taskcard
cat > plans/taskcards/TC-999_test.md <<'EOF'
---
id: TC-999
title: "Test"
status: Draft
owner: "test"
updated: "2026-02-03"
depends_on: []
allowed_paths: ["test"]
evidence_required: ["test"]
spec_ref: "abc123"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---
## Objective
Test taskcard
EOF

# Run validator
.venv/Scripts/python.exe tools/validate_taskcards.py | grep TC-999

# Clean up
rm plans/taskcards/TC-999_test.md
```

**Expected Results:**
- Validator reports multiple "Missing required section" errors
- Should report missing: Required spec references, Scope, Inputs, Outputs, Implementation steps, Failure modes, Task-specific review checklist, Deliverables, Acceptance checks, Self-review, E2E verification, Integration boundary proven
- Error messages are clear and actionable

---

### V3: Pre-Commit Hook Blocking

**Purpose:** Verify hook blocks incomplete taskcards before commit

**Test Procedure:**
```bash
# Create incomplete taskcard
echo "---
id: TC-999
title: Test
status: Draft
owner: test
updated: 2026-02-03
depends_on: []
allowed_paths: [\"test\"]
evidence_required: [\"test\"]
spec_ref: abc123
ruleset_version: ruleset.v1
templates_version: templates.v1
---
## Objective
Test" > plans/taskcards/TC-999_test.md

# Stage the file
git add plans/taskcards/TC-999_test.md

# Try to commit (should BLOCK)
git commit -m "test: incomplete taskcard"

# Clean up
git reset HEAD plans/taskcards/TC-999_test.md
rm plans/taskcards/TC-999_test.md
```

**Expected Results:**
- Hook executes and runs validation
- Hook BLOCKS commit (exit 1)
- Clear error message showing all missing sections
- Guidance on how to fix or bypass
- Execution time <5 seconds

---

### V4: Performance Measurement

**Purpose:** Verify performance meets targets

**Test Cases:**
```bash
# Test 1: Single taskcard
time .venv/Scripts/python.exe tools/validate_taskcards.py --staged-only
# (with 1 taskcard staged)

# Test 2: All 82 taskcards
time .venv/Scripts/python.exe tools/validate_taskcards.py

# Test 3: Pre-commit hook performance
time git commit -m "test" --allow-empty
```

**Targets:**
- Single taskcard: <2 seconds
- All 82 taskcards: <5 seconds
- Pre-commit hook: <5 seconds

---

## Evidence Requirements

All verification evidence captured at:
```
runs/tc_prevent_incomplete_20260203/
├── V1_validator_output.txt
├── V2_incomplete_detection.txt
├── V3_hook_blocking.txt
├── performance_metrics.txt
├── validation_summary.md
└── VERIFICATION_REPORT.md
```

Agent documentation at:
```
reports/agents/AGENT_C/WS5_VERIFICATION/
├── plan.md (this file)
├── evidence.md
├── self_review.md
└── commands.sh
```

---

## Acceptance Criteria

- [ ] V1 verification complete (enhanced validator tested on all taskcards)
- [ ] V2 verification complete (incomplete taskcard detected with clear errors)
- [ ] V3 verification complete (pre-commit hook blocks incomplete taskcards)
- [ ] Performance measured and documented (<5s for all tests)
- [ ] Evidence bundle created at runs/tc_prevent_incomplete_20260203/
- [ ] Agent documentation complete
- [ ] Self-review performed (12D)

---

## Success Metrics

- V1, V2, V3 all PASS ✅
- Performance under budget (<5s) ✅
- Evidence bundle complete ✅
- Clear verification report ✅
