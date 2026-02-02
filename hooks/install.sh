#!/usr/bin/env bash
# FOSS Launcher - AI Governance Hooks Installer
# Installs git hooks to enforce AI agent governance rules

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}FOSS Launcher - AI Governance Hooks Installation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not in a git repository root${NC}"
    echo "Please run this script from the repository root directory"
    exit 1
fi

# Check if hooks directory exists
if [ ! -d "hooks" ]; then
    echo -e "${RED}❌ Error: hooks/ directory not found${NC}"
    echo "Expected to find hooks/ in current directory"
    exit 1
fi

echo "Installing AI governance hooks..."
echo ""

# Install prepare-commit-msg hook
if [ -f ".git/hooks/prepare-commit-msg" ]; then
    echo -e "${YELLOW}⚠️  Existing prepare-commit-msg hook found${NC}"
    echo "Backing up to prepare-commit-msg.backup"
    cp .git/hooks/prepare-commit-msg .git/hooks/prepare-commit-msg.backup
fi

echo -e "${GREEN}➜${NC} Installing prepare-commit-msg hook (Gate AG-001)"
cp hooks/prepare-commit-msg .git/hooks/prepare-commit-msg
chmod +x .git/hooks/prepare-commit-msg

# Install pre-push hook
if [ -f ".git/hooks/pre-push" ]; then
    echo -e "${YELLOW}⚠️  Existing pre-push hook found${NC}"
    echo "Backing up to pre-push.backup"
    cp .git/hooks/pre-push .git/hooks/pre-push.backup
fi

echo -e "${GREEN}➜${NC} Installing pre-push hook (Gates AG-003, AG-004)"
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push

echo ""
echo -e "${GREEN}✅ Hooks installed successfully!${NC}"
echo ""
echo -e "${BLUE}Installed hooks:${NC}"
echo "  • prepare-commit-msg - Branch creation approval validation (AG-001)"
echo "  • pre-push           - Remote push & force push protection (AG-003, AG-004)"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Enforcement:  ${GREEN}ENABLED${NC}"
echo "  Specification: specs/30_ai_agent_governance.md"
echo "  Rules File:    .claude_code_rules"
echo ""
echo -e "${BLUE}To disable enforcement (not recommended):${NC}"
echo "  $ git config hooks.ai-governance.enforce false"
echo ""
echo -e "${BLUE}To test the hooks:${NC}"
echo "  1. Try creating a new branch without approval:"
echo "     $ git checkout -b test-branch"
echo "     $ touch test.txt"
echo "     $ git add test.txt"
echo "     $ git commit -m \"Test commit\""
echo "     ${YELLOW}(Should be blocked by AG-001)${NC}"
echo ""
echo "  2. Approve and retry:"
echo "     $ touch .git/AI_BRANCH_APPROVED"
echo "     $ echo 'interactive-dialog' > .git/AI_BRANCH_APPROVED"
echo "     $ git commit -m \"Test commit\""
echo "     ${GREEN}(Should succeed with governance metadata)${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Installation complete!${NC} AI governance enforcement is now active."
echo ""
