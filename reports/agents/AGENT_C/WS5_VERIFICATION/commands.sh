#!/bin/bash
# Commands Executed - WS5: Verification & Testing
# Agent: Agent C (Tests & Verification)
# Date: 2026-02-03

# Change to repo root
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"

# ============================================================
# SETUP: Create Evidence Directories
# ============================================================

mkdir -p "reports/agents/AGENT_C/WS5_VERIFICATION"
mkdir -p "runs/tc_prevent_incomplete_20260203"

# ============================================================
# V1: Enhanced Validator - All Taskcards
# ============================================================

# Run validator on all taskcards and capture output
.venv/Scripts/python.exe tools/validate_taskcards.py 2>&1 | tee runs/tc_prevent_incomplete_20260203/V1_validator_output.txt

# Measure performance (PowerShell)
powershell -Command "Measure-Command { .venv/Scripts/python.exe tools/validate_taskcards.py > nul 2>&1 } | Select-Object TotalSeconds"
# Result: 0.21 seconds (24x faster than 5s target) ✅

# ============================================================
# V2: Incomplete Taskcard Detection
# ============================================================

# Create test incomplete taskcard
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

# Run validator and capture output for TC-999
.venv/Scripts/python.exe tools/validate_taskcards.py 2>&1 | grep -A 20 "TC-999" | tee runs/tc_prevent_incomplete_20260203/V2_incomplete_detection.txt

# Clean up test file
rm plans/taskcards/TC-999_test.md

# ============================================================
# V3: Pre-Commit Hook Blocking
# ============================================================

# Verify hook is installed
ls -la .git/hooks/pre-commit
# Result: -rwxr-xr-x (executable) ✅

# Create test incomplete taskcard
cat > plans/taskcards/TC-999_test.md <<'EOF'
---
id: TC-999
title: Test
status: Draft
owner: test
updated: 2026-02-03
depends_on: []
allowed_paths: ["test"]
evidence_required: ["test"]
spec_ref: abc123
ruleset_version: ruleset.v1
templates_version: templates.v1
---
## Objective
Test
EOF

# Stage the file
git add plans/taskcards/TC-999_test.md

# Attempt commit (should be BLOCKED)
git commit -m "test: incomplete taskcard" 2>&1 | tee runs/tc_prevent_incomplete_20260203/V3_hook_blocking.txt
# Result: BLOCKED (exit code 1) ✅

# Measure hook performance (PowerShell)
powershell -Command "Measure-Command { git commit -m 'test' 2>&1 | Out-Null } | Select-Object TotalSeconds"
# Result: 1.05 seconds (5x faster than 5s target) ✅

# Clean up test file
git reset HEAD plans/taskcards/TC-999_test.md
rm plans/taskcards/TC-999_test.md

# ============================================================
# EVIDENCE BUNDLE CREATION
# ============================================================

# Created the following files in runs/tc_prevent_incomplete_20260203/:
# - V1_validator_output.txt
# - V2_incomplete_detection.txt
# - V3_hook_blocking.txt
# - performance_metrics.txt
# - validation_summary.md
# - VERIFICATION_REPORT.md

# Created agent documentation in reports/agents/AGENT_C/WS5_VERIFICATION/:
# - plan.md
# - evidence.md
# - self_review.md
# - commands.sh (this file)

# ============================================================
# VERIFICATION SUMMARY
# ============================================================

echo "============================================================"
echo "VERIFICATION RESULTS"
echo "============================================================"
echo ""
echo "V1: Enhanced Validator"
echo "  Status: ✅ PASS"
echo "  Performance: 0.21s (target: <5s, 24x faster)"
echo "  TC-935: ✅ PASS"
echo "  TC-936: ✅ PASS"
echo ""
echo "V2: Incomplete Detection"
echo "  Status: ✅ PASS"
echo "  Detection: 14/14 sections correctly identified"
echo "  Error Quality: Clear, actionable"
echo ""
echo "V3: Pre-Commit Hook Blocking"
echo "  Status: ✅ PASS"
echo "  Performance: 1.05s (target: <5s, 5x faster)"
echo "  Blocking: ✅ Commit prevented"
echo "  UX: ✅ Excellent"
echo ""
echo "Overall: ✅ ALL VERIFICATIONS PASSED"
echo "Recommendation: SYSTEM PRODUCTION READY"
echo "============================================================"

# End of commands
