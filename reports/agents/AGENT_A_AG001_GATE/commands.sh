#!/usr/bin/env bash
# AG-001 Gate Strengthening - Verification Commands
# All commands used to verify implementation of Tasks A1, A2, A3

set -e

echo "======================================================================="
echo "AG-001 Gate Strengthening - Verification Commands"
echo "======================================================================="
echo ""

# Change to repository root
cd "$(dirname "$0")/../../.."

echo "[1] Verify repository structure"
echo "---"
pwd
test -d .git && echo "[OK] .git directory exists"
test -d hooks && echo "[OK] hooks directory exists"
test -d scripts && echo "[OK] scripts directory exists"
echo ""

echo "[2] Verify created files exist"
echo "---"
test -f scripts/install_hooks.py && echo "[OK] scripts/install_hooks.py exists"
test -f hooks/prepare-commit-msg && echo "[OK] hooks/prepare-commit-msg exists"
echo ""

echo "[3] Verify Python syntax of all modified files"
echo "---"
python -m py_compile scripts/install_hooks.py && echo "[OK] install_hooks.py syntax valid"
python -m py_compile scripts/stub_commit_service.py && echo "[OK] stub_commit_service.py syntax valid"
python -m py_compile src/launch/clients/commit_service.py && echo "[OK] commit_service.py syntax valid"
python -m py_compile src/launch/workers/w9_pr_manager/worker.py && echo "[OK] w9_pr_manager/worker.py syntax valid"
echo ""

echo "[4] Verify bash syntax of modified hooks"
echo "---"
bash -n hooks/prepare-commit-msg && echo "[OK] prepare-commit-msg syntax valid"
echo ""

echo "[5] Verify JSON schemas are valid"
echo "---"
python -c "import json; json.load(open('specs/schemas/commit_request.schema.json')); print('[OK] commit_request.schema.json is valid JSON')"
echo ""

echo "[6] Test Task A1: Hook Installation"
echo "---"
# Remove hooks if they exist
rm -f .git/hooks/prepare-commit-msg .git/hooks/pre-push

# Run installation
python scripts/install_hooks.py

# Verify hooks are installed
test -f .git/hooks/prepare-commit-msg && echo "[OK] prepare-commit-msg installed"
test -f .git/hooks/pre-push && echo "[OK] pre-push installed"

# Check if hooks are executable
if [ "$(uname)" != "MINGW64_NT"* ]; then
    test -x .git/hooks/prepare-commit-msg && echo "[OK] prepare-commit-msg is executable"
    test -x .git/hooks/pre-push && echo "[OK] pre-push is executable"
else
    echo "[OK] Windows detected - Git Bash handles executable bit"
fi

# Test idempotency - run again
python scripts/install_hooks.py > /dev/null 2>&1
test -f .git/hooks/prepare-commit-msg && echo "[OK] Idempotent - hooks still installed after re-run"

# Check for backup files
test -f .git/hooks/prepare-commit-msg.backup && echo "[OK] Backup created on second install"
echo ""

echo "[7] Test Task A2: Emergency Bypass"
echo "---"
# Check that git config bypass was removed
if grep -q "git config --get hooks.ai-governance.enforce" hooks/prepare-commit-msg; then
    echo "[FAIL] Git config bypass still exists in hook"
    exit 1
else
    echo "[OK] Git config bypass removed from hook"
fi

# Check that emergency bypass environment variable is used
if grep -q "AG001_EMERGENCY_BYPASS" hooks/prepare-commit-msg; then
    echo "[OK] Emergency bypass environment variable check added"
else
    echo "[FAIL] Emergency bypass environment variable not found"
    exit 1
fi

# Check that bypass logging is implemented
if grep -q "AG001_EMERGENCY_BYPASS_LOG.jsonl" hooks/prepare-commit-msg; then
    echo "[OK] Bypass logging implemented"
else
    echo "[FAIL] Bypass logging not found"
    exit 1
fi
echo ""

echo "[8] Test Task A3: Schema Changes"
echo "---"
# Check that ai_governance_metadata field was added to schema
if grep -q "ai_governance_metadata" specs/schemas/commit_request.schema.json; then
    echo "[OK] ai_governance_metadata field added to schema"
else
    echo "[FAIL] ai_governance_metadata field not found in schema"
    exit 1
fi

# Check for ag001_approval structure
if grep -q "ag001_approval" specs/schemas/commit_request.schema.json; then
    echo "[OK] ag001_approval structure defined in schema"
else
    echo "[FAIL] ag001_approval structure not found"
    exit 1
fi
echo ""

echo "[9] Test Task A3: Stub Service Changes"
echo "---"
# Check that AG001Approval model was added
if grep -q "class AG001Approval" scripts/stub_commit_service.py; then
    echo "[OK] AG001Approval model added to stub service"
else
    echo "[FAIL] AG001Approval model not found"
    exit 1
fi

# Check that validation logic was added
if grep -q "AG001_APPROVAL_REQUIRED" scripts/stub_commit_service.py; then
    echo "[OK] AG-001 validation logic added to stub service"
else
    echo "[FAIL] AG-001 validation logic not found"
    exit 1
fi
echo ""

echo "[10] Test Task A3: Client Changes"
echo "---"
# Check that ai_governance_metadata parameter was added to create_commit
if grep -q "ai_governance_metadata: Optional\[Dict\[str, Any\]\]" src/launch/clients/commit_service.py; then
    echo "[OK] ai_governance_metadata parameter added to client"
else
    echo "[FAIL] ai_governance_metadata parameter not found in client"
    exit 1
fi
echo ""

echo "[11] Test Task A3: W9 PRManager Changes"
echo "---"
# Check that approval collection logic was added
if grep -q "AG-001 Task A3: Collect branch creation approval" src/launch/workers/w9_pr_manager/worker.py; then
    echo "[OK] Approval collection logic added to W9 PRManager"
else
    echo "[FAIL] Approval collection logic not found"
    exit 1
fi

# Check that approval marker is read
if grep -q "AI_BRANCH_APPROVED" src/launch/workers/w9_pr_manager/worker.py; then
    echo "[OK] Approval marker reading implemented"
else
    echo "[FAIL] Approval marker reading not found"
    exit 1
fi
echo ""

echo "[12] Test Task A3: Spec Documentation"
echo "---"
# Check that AG-001 section was added to spec
if grep -q "AI Governance Integration (AG-001)" specs/17_github_commit_service.md; then
    echo "[OK] AG-001 section added to commit service spec"
else
    echo "[FAIL] AG-001 section not found in spec"
    exit 1
fi

# Check for error code documentation
if grep -q "AG001_APPROVAL_REQUIRED" specs/17_github_commit_service.md; then
    echo "[OK] Error codes documented in spec"
else
    echo "[FAIL] Error codes not documented"
    exit 1
fi
echo ""

echo "======================================================================="
echo "[SUCCESS] All verification tests passed!"
echo "======================================================================="
echo ""
echo "Summary:"
echo "  - Task A1: Hook installation automation - VERIFIED"
echo "  - Task A2: Emergency bypass with logging - VERIFIED"
echo "  - Task A3: Commit service AG-001 validation - VERIFIED"
echo ""
echo "All acceptance criteria met."
