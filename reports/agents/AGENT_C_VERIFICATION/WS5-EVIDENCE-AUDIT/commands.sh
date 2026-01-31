#!/bin/bash
# Commands for WS5-EVIDENCE-AUDIT Audit Script Testing

## Setup
cd "c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher"

## 1. Run Unit Tests
echo "=== Test 1: Unit Tests ==="
.venv/Scripts/python.exe -m pytest tests/unit/tools/test_audit_taskcard_evidence.py -v
echo "Exit code: $?"

## 2. Full Audit of All Done Taskcards
echo ""
echo "=== Test 2: Full Audit ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py
echo "Exit code: $?"

## 3. Audit Specific Taskcard (TC-500)
echo ""
echo "=== Test 3: Specific Taskcard ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --taskcard TC-500
echo "Exit code: $?"

## 4. JSON Output Format
echo ""
echo "=== Test 4: JSON Output ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --taskcard TC-500 --json
echo "Exit code: $?"

## 5. Detailed Report with Full Paths
echo ""
echo "=== Test 5: Detailed Report ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --taskcard TC-100 --detailed
echo "Exit code: $?"

## 6. Ignore Orphaned Evidence
echo ""
echo "=== Test 6: Ignore Orphaned Evidence ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --ignore-orphaned
echo "Exit code: $?"

## 7. Help Message
echo ""
echo "=== Test 7: Help Message ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --help
echo "Exit code: $?"

## 8. Multiple Options Combined
echo ""
echo "=== Test 8: Combined Options ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --detailed --taskcard TC-500 --ignore-orphaned
echo "Exit code: $?"

## 9. JSON with Detailed Output
echo ""
echo "=== Test 9: JSON + Detailed ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --json --taskcard TC-200 --detailed | head -30
echo "Exit code: $?"

## 10. Check Compliance Rate
echo ""
echo "=== Test 10: Compliance Statistics ==="
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py 2>&1 | grep -A 5 "Summary"
echo "Exit code: $?"

## Expected Results Summary

# Test 1: Unit Tests
# Expected: All 24 tests pass, exit code 0

# Test 2: Full Audit
# Expected:
#   - 46 total Done taskcards
#   - 36 complete (78.3%)
#   - 10 incomplete
#   - 11 orphaned evidence dirs
#   - Exit code 1 (due to incomplete/orphaned)

# Test 3: Specific Taskcard (TC-500)
# Expected:
#   - TC-500: [OK] Complete
#   - Complete evidence for CLIENTS_AGENT
#   - Exit code 1 (due to orphaned evidence shown)

# Test 4: JSON Output
# Expected:
#   - Valid JSON structure
#   - audit_summary, evidence_results, orphaned_evidence keys
#   - TC-500 marked as complete
#   - Exit code 0 with --ignore-orphaned

# Test 5: Detailed Report (TC-100)
# Expected:
#   - Full paths shown
#   - Missing items listed
#   - Framework section visible
#   - Exit code 1 (TC-100 has missing evidence)

# Test 6: Ignore Orphaned
# Expected:
#   - No "Orphaned Evidence" section
#   - Still shows incomplete evidence
#   - Exit code 1 (due to incomplete evidence)

# Test 7: Help Message
# Expected:
#   - Usage information displayed
#   - All options documented
#   - Examples provided
#   - Exit code 0

# Test 8: Combined Options
# Expected:
#   - Shows only TC-500 (specific filter)
#   - Detailed paths shown
#   - No orphaned section (--ignore-orphaned)
#   - Exit code 0 (TC-500 is complete)

# Test 9: JSON with Detailed
# Expected:
#   - Valid JSON output
#   - Full paths included in evidence_path
#   - Detailed information available
#   - Exit code varies based on evidence

# Test 10: Compliance Statistics
# Expected:
#   - Shows summary section
#   - Reports total Done, complete, incomplete, orphaned counts
#   - Compliance rate visible
#   - Exit code 1 (due to issues found)

## Verification Commands (Optional)

# Count total Done taskcards in plans
grep -r "status: Done" plans/taskcards/ | wc -l
# Expected: 46

# Count evidence directories
find reports/agents -type d -name "TC-*" | wc -l
# Expected: > 46 (due to TC-521 and VSCODE_AGENT orphans)

# List incomplete taskcards
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py 2>&1 | grep "\[FAIL\]"
# Expected: 10 incomplete taskcards listed

# Verify orphaned count
find reports/agents -type d -name "TC-*" -printf '%P\n' | sort | uniq > /tmp/evidence_dirs.txt
grep "status: Done" plans/taskcards/*.md | sed 's/.*\/TC-//;s/:.*//;s/.md:.*//;s/_.*//' | sort | uniq > /tmp/taskcard_ids.txt
# Shows evidence dirs with no matching Done taskcard

## Performance Testing

# Measure execution time
time .venv/Scripts/python.exe tools/audit_taskcard_evidence.py > /dev/null 2>&1
# Expected: < 1 second

# Check memory usage
.venv/Scripts/python.exe -c "import sys; from tools.audit_taskcard_evidence import audit_taskcards; from pathlib import Path; exit_code, _, _, _ = audit_taskcards(Path('.')); print(f'Exit: {exit_code}')"
# Expected: Memory usage minimal

## CI/CD Integration Examples

# Use exit code for gate enforcement
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py
if [ $? -eq 0 ]; then
    echo "All evidence complete - pass gate"
else
    echo "Evidence missing or orphaned - fail gate"
fi

# Generate JSON report for dashboard
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --json > audit_report.json

# Audit before merging
.venv/Scripts/python.exe tools/audit_taskcard_evidence.py --ignore-orphaned
if [ $? -eq 1 ]; then
    echo "FAIL: Missing evidence for Done taskcards"
    exit 1
fi
