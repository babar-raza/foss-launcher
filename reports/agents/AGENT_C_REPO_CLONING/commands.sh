#!/bin/bash
# Commands for Repository Cloning Gate Verification & Documentation
# Agent C (Tests & Verification + Docs)
# Date: 2026-02-02

set -e  # Exit on error

REPO_ROOT="c:/Users/prora/OneDrive/Documents/GitHub/foss-launcher"
cd "$REPO_ROOT"

echo "=========================================="
echo "Task C1: Verification Commands"
echo "=========================================="

# 1. Check validator file exists and size
echo -e "\n[1] Validator file verification:"
ls -lh "src/launch/workers/_git/repo_url_validator.py"
wc -l "src/launch/workers/_git/repo_url_validator.py"

# 2. Search for direct git clone calls (should find none in src/)
echo -e "\n[2] Search for direct git clone calls:"
grep -r "git clone" src/ --include="*.py" || echo "✅ No direct git clone calls found"

# 3. Search for subprocess git operations
echo -e "\n[3] Search for subprocess git operations:"
grep -r "subprocess.*git" src/ --include="*.py" || echo "✅ No subprocess git calls found"

# 4. Verify clone_and_resolve usage (should only be in clone.py)
echo -e "\n[4] Verify clone_and_resolve usage:"
grep -r "clone_and_resolve" src/ --include="*.py" | grep -v "def clone_and_resolve" | grep -v "clone_helpers.py"

# 5. Count validate_repo_url call sites in clone.py
echo -e "\n[5] Count validate_repo_url call sites:"
grep -c "validate_repo_url(" "src/launch/workers/w1_repo_scout/clone.py"
echo "✅ Expected: 3 (product, site, workflows)"

# 6. Check test file exists and size
echo -e "\n[6] Test file verification:"
ls -lh "tests/unit/workers/_git/test_repo_url_validator.py"
wc -l "tests/unit/workers/_git/test_repo_url_validator.py"

# 7. Count test classes
echo -e "\n[7] Count test classes:"
grep -c "^class Test" "tests/unit/workers/_git/test_repo_url_validator.py"

# 8. Count test methods
echo -e "\n[8] Count test methods:"
grep -c "def test_" "tests/unit/workers/_git/test_repo_url_validator.py"

# 9. Verify allowlist sizes
echo -e "\n[9] Verify allowlist sizes:"
echo "Families:"
grep -A 25 "ALLOWED_FAMILIES = frozenset" "src/launch/workers/_git/repo_url_validator.py" | grep '"' | wc -l
echo "Platforms:"
grep -A 20 "ALLOWED_PLATFORMS = frozenset" "src/launch/workers/_git/repo_url_validator.py" | grep '"' | wc -l

# 10. Run validator tests (if pytest available)
echo -e "\n[10] Run validator tests:"
if command -v pytest &> /dev/null; then
    python -m pytest tests/unit/workers/_git/test_repo_url_validator.py -v --tb=short
else
    echo "⚠️  pytest not installed - skipping test execution"
    echo "Install with: pip install pytest"
fi

# 11. Check test coverage (if pytest-cov available)
echo -e "\n[11] Check test coverage:"
if command -v pytest &> /dev/null && python -c "import pytest_cov" 2>/dev/null; then
    python -m pytest tests/unit/workers/_git/test_repo_url_validator.py \
        --cov=src/launch/workers/_git/repo_url_validator \
        --cov-report=term-missing \
        --cov-report=html:reports/agents/AGENT_C_REPO_CLONING/coverage
else
    echo "⚠️  pytest-cov not installed - skipping coverage"
    echo "Install with: pip install pytest-cov"
fi

echo -e "\n=========================================="
echo "Task C2: Documentation & Telemetry Commands"
echo "=========================================="

# 12. Verify specs/36 documentation exists
echo -e "\n[12] Verify specs/36 documentation:"
ls -lh "specs/36_repository_url_policy.md"

# 13. Check for Legacy FOSS Pattern documentation
echo -e "\n[13] Check for Legacy FOSS Pattern documentation:"
grep -A 10 "##### 4.2 Legacy FOSS Pattern" "specs/36_repository_url_policy.md" || echo "❌ Legacy FOSS Pattern section not found"

# 14. Count legacy pattern examples
echo -e "\n[14] Count legacy pattern examples:"
grep -c "Aspose.*-FOSS-for-" "specs/36_repository_url_policy.md"
echo "✅ Expected: At least 2 examples"

# 15. Check for telemetry event emission
echo -e "\n[15] Check for REPO_URL_VALIDATED event emission:"
grep -c "emit_validation_event" "src/launch/workers/w1_repo_scout/clone.py"
echo "✅ Expected: 3 (product, site, workflows)"

# 16. Verify event type definition
echo -e "\n[16] Verify REPO_URL_VALIDATED event type:"
grep "REPO_URL_VALIDATED" "src/launch/workers/w1_repo_scout/clone.py" | head -1

# 17. Check event payload structure
echo -e "\n[17] Check event payload structure:"
grep -A 2 "payload.*url.*repo_type" "src/launch/workers/w1_repo_scout/clone.py"

# 18. Verify imports for event emission
echo -e "\n[18] Verify imports for event emission:"
grep "import datetime" "src/launch/workers/w1_repo_scout/clone.py"
grep "import uuid" "src/launch/workers/w1_repo_scout/clone.py"
grep "from.*Event" "src/launch/workers/w1_repo_scout/clone.py"

echo -e "\n=========================================="
echo "Integration Tests (Manual - requires test run)"
echo "=========================================="

# 19. Simulate test run (conceptual - not executed)
echo -e "\n[19] To test telemetry events in a real run:"
echo "1. Create a test run_config.yaml with valid product repository"
echo "2. Run: python -m launch.workers.w1_repo_scout.clone <run_dir>"
echo "3. Check events.ndjson for REPO_URL_VALIDATED events:"
echo "   grep REPO_URL_VALIDATED <run_dir>/events.ndjson | jq ."

# 20. Event verification command
echo -e "\n[20] To verify event structure:"
echo "   cat <run_dir>/events.ndjson | grep REPO_URL_VALIDATED | jq '.payload'"

echo -e "\n=========================================="
echo "Code Quality Checks"
echo "=========================================="

# 21. Check for TODO/FIXME markers
echo -e "\n[21] Check for unresolved TODOs:"
grep -n "TODO\|FIXME" "src/launch/workers/_git/repo_url_validator.py" || echo "✅ No TODOs found"
grep -n "TODO\|FIXME" "src/launch/workers/w1_repo_scout/clone.py" | grep -v "# TODO: Open BLOCKER" || echo "✅ No new TODOs added"

# 22. Check Python syntax
echo -e "\n[22] Check Python syntax:"
python -m py_compile "src/launch/workers/_git/repo_url_validator.py"
python -m py_compile "src/launch/workers/w1_repo_scout/clone.py"
echo "✅ Python syntax valid"

# 23. Check for type hints
echo -e "\n[23] Verify type hints in new code:"
grep "def emit_validation_event" "src/launch/workers/w1_repo_scout/clone.py" -A 2

# 24. Check documentation formatting
echo -e "\n[24] Check markdown formatting:"
if command -v markdownlint &> /dev/null; then
    markdownlint "specs/36_repository_url_policy.md"
else
    echo "⚠️  markdownlint not installed - skipping"
fi

echo -e "\n=========================================="
echo "Security Checks"
echo "=========================================="

# 25. Verify no hardcoded secrets
echo -e "\n[25] Check for hardcoded secrets:"
grep -iE "(password|secret|token|api[_-]?key)" "src/launch/workers/w1_repo_scout/clone.py" | grep -v "# " | grep -v "docstring" || echo "✅ No hardcoded secrets found"

# 26. Verify HTTPS enforcement
echo -e "\n[26] Verify HTTPS enforcement in validator:"
grep "https://" "src/launch/workers/_git/repo_url_validator.py" | head -3

# 27. Check for SQL injection vectors (none expected)
echo -e "\n[27] Check for SQL injection vectors:"
grep -iE "execute|query.*\+|cursor" "src/launch/workers/w1_repo_scout/clone.py" || echo "✅ No SQL operations found"

# 28. Verify no shell command injection
echo -e "\n[28] Check for shell command injection:"
grep "shell=True" "src/launch/workers/w1_repo_scout/clone.py" || echo "✅ No shell=True found"

echo -e "\n=========================================="
echo "Verification Complete"
echo "=========================================="

echo -e "\n✅ Task C1: Verification commands executed"
echo "✅ Task C2: Documentation and telemetry commands executed"
echo -e "\nNext steps:"
echo "1. Review verification_report.md for findings"
echo "2. Review changes.md for implementation details"
echo "3. Review evidence.md for detailed evidence"
echo "4. Complete self_review.md for quality assessment"
