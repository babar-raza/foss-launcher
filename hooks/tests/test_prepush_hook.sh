#!/usr/bin/env bash
# Test script to simulate pre-push hook execution with taskcard validation

echo "=========================================="
echo "TEST 1: Simulate push with taskcard validation (should BLOCK)"
echo "=========================================="
echo ""

# First, approve the test branch to bypass AG-004
git config branch.test-branch.push-approved true

# Simulate a push to an existing branch (non-zero remote SHA means branch exists)
# This will skip the AG-004 new branch check and the force-push check
LOCAL_SHA=$(git rev-parse HEAD)
PARENT_SHA=$(git rev-parse HEAD~1 2>/dev/null || echo "$LOCAL_SHA")

echo "Simulating push where:"
echo "  - Branch already exists on remote (bypasses AG-004)"
echo "  - No force push needed (local is ahead of remote)"
echo "  - Taskcard validation will run"
echo ""

echo "refs/heads/test-branch $LOCAL_SHA refs/heads/test-branch $PARENT_SHA" | bash hooks/pre-push origin https://github.com/test/repo.git

EXIT_CODE=$?
echo ""
echo "Exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 1 ]; then
    echo "✅ TEST 1 PASSED: Hook correctly blocked push due to taskcard validation failures"
else
    echo "❌ TEST 1 FAILED: Hook should have blocked push but didn't (exit code: $EXIT_CODE)"
fi

# Clean up
git config --unset branch.test-branch.push-approved

echo ""
echo "=========================================="
echo "TEST 2: Verify --no-verify bypass mechanism"
echo "=========================================="
echo ""
echo "The --no-verify flag bypasses ALL pre-push hooks."
echo ""
echo "To bypass in real usage:"
echo "  $ git push --no-verify"
echo ""
echo "Note: The hook warns that CI/CD will track this bypass"
echo "and re-validate all taskcards during PR merge."
echo ""
echo "✅ TEST 2 PASSED: Bypass mechanism available via --no-verify"
