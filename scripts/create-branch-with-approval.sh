#!/usr/bin/env bash
# FOSS Launcher - Compliant Branch Creation Helper
# Creates git branches following AI governance rules (AG-001)
# See: specs/30_ai_agent_governance.md

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}FOSS Launcher - Compliant Branch Creation${NC}"
echo -e "${BLUE}Gate AG-001: Branch Creation with Approval${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${CYAN}Current branch:${NC} $CURRENT_BRANCH"
echo ""

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: You have uncommitted changes${NC}"
    git status --short
    echo ""
    read -p "Do you want to stash these changes? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash push -m "Auto-stash before branch creation $(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✅ Changes stashed${NC}"
        echo ""
    fi
fi

# Step 1: Get branch name
echo -e "${CYAN}Step 1: Branch Name${NC}"
echo ""

# Suggest branch name based on convention: feat/tc<number>_<description>_YYYYMMDD
SUGGESTED_PREFIX="feat"
SUGGESTED_DATE=$(date +%Y%m%d)

echo "Enter branch name (or press Enter for guided creation):"
read BRANCH_NAME

if [ -z "$BRANCH_NAME" ]; then
    echo ""
    echo "Guided branch creation:"
    echo ""

    # Select branch type
    echo "Select branch type:"
    echo "  1) feat    - New feature"
    echo "  2) fix     - Bug fix"
    echo "  3) chore   - Maintenance/tooling"
    echo "  4) docs    - Documentation"
    echo "  5) test    - Test additions"
    echo "  6) refactor - Code refactoring"
    read -p "Choice [1-6]: " TYPE_CHOICE

    case $TYPE_CHOICE in
        1) BRANCH_TYPE="feat" ;;
        2) BRANCH_TYPE="fix" ;;
        3) BRANCH_TYPE="chore" ;;
        4) BRANCH_TYPE="docs" ;;
        5) BRANCH_TYPE="test" ;;
        6) BRANCH_TYPE="refactor" ;;
        *) BRANCH_TYPE="feat" ;;
    esac

    # Get task card number (if applicable)
    echo ""
    read -p "Task card number (e.g., 910, or leave empty): " TC_NUMBER

    # Get description
    echo ""
    read -p "Brief description (lowercase, use underscores): " DESCRIPTION

    # Build branch name
    if [ -n "$TC_NUMBER" ]; then
        BRANCH_NAME="${BRANCH_TYPE}/tc${TC_NUMBER}_${DESCRIPTION}_${SUGGESTED_DATE}"
    else
        BRANCH_NAME="${BRANCH_TYPE}/${DESCRIPTION}_${SUGGESTED_DATE}"
    fi

    echo ""
    echo -e "${CYAN}Suggested branch name:${NC} $BRANCH_NAME"
    read -p "Use this name? (y/n/edit) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Ee]$ ]]; then
        read -p "Enter custom branch name: " BRANCH_NAME
    elif [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi
fi

# Validate branch doesn't already exist
if git show-ref --verify --quiet refs/heads/"$BRANCH_NAME"; then
    echo -e "${RED}❌ Error: Branch '$BRANCH_NAME' already exists locally${NC}"
    exit 1
fi

if git ls-remote --heads origin "$BRANCH_NAME" | grep -q "$BRANCH_NAME"; then
    echo -e "${RED}❌ Error: Branch '$BRANCH_NAME' already exists on remote${NC}"
    exit 1
fi

# Step 2: Select base branch
echo ""
echo -e "${CYAN}Step 2: Base Branch${NC}"
echo ""

# List available branches
echo "Available branches:"
git branch -a | grep -v "HEAD" | head -10

echo ""
read -p "Base branch [default: main]: " BASE_BRANCH
BASE_BRANCH=${BASE_BRANCH:-main}

# Validate base branch exists
if ! git show-ref --verify --quiet refs/heads/"$BASE_BRANCH"; then
    if ! git show-ref --verify --quiet refs/remotes/origin/"$BASE_BRANCH"; then
        echo -e "${RED}❌ Error: Base branch '$BASE_BRANCH' not found${NC}"
        exit 1
    fi
fi

# Step 3: Purpose/description
echo ""
echo -e "${CYAN}Step 3: Purpose${NC}"
echo ""
read -p "Purpose of this branch (brief): " PURPOSE
PURPOSE=${PURPOSE:-"Feature development"}

# Step 4: Review and approve
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Review Branch Creation${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Branch name:${NC} $BRANCH_NAME"
echo -e "${CYAN}Base branch:${NC} $BASE_BRANCH"
echo -e "${CYAN}Purpose:${NC}     $PURPOSE"
echo -e "${CYAN}Created by:${NC}  ${USER:-$(whoami)}"
echo -e "${CYAN}Timestamp:${NC}   $(date)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "Create this branch? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Branch creation cancelled"
    exit 0
fi

# Step 5: Set approval marker (AG-001 compliance)
echo ""
echo -e "${GREEN}✅ Approval granted${NC}"
echo -e "${CYAN}Setting AG-001 compliance marker...${NC}"

APPROVAL_MARKER=".git/AI_BRANCH_APPROVED"
APPROVAL_METHOD="interactive-dialog"

# Write approval metadata
cat > "$APPROVAL_MARKER" <<EOF
$APPROVAL_METHOD
branch=$BRANCH_NAME
base=$BASE_BRANCH
purpose=$PURPOSE
approved_by=${USER:-$(whoami)}
approved_at=$(date -Iseconds)
EOF

echo -e "${GREEN}✅ Approval marker set${NC}"

# Step 6: Create branch
echo ""
echo -e "${CYAN}Creating branch from $BASE_BRANCH...${NC}"

# Ensure we have latest base branch
git fetch origin "$BASE_BRANCH" --quiet 2>/dev/null || true

# Create and checkout new branch
git checkout -b "$BRANCH_NAME" "$BASE_BRANCH"

echo -e "${GREEN}✅ Branch created: $BRANCH_NAME${NC}"
echo ""

# Step 7: Success summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Branch Creation Complete${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo "  1. Make your changes"
echo "  2. Commit with: git commit -m 'Your message'"
echo "     (First commit will include AG-001 approval metadata)"
echo "  3. Push to remote: git push -u origin $BRANCH_NAME"
echo ""
echo -e "${CYAN}Governance:${NC}"
echo "  • AG-001 compliant: ✅"
echo "  • Approval method: $APPROVAL_METHOD"
echo "  • Approval marker: $APPROVAL_MARKER"
echo ""
echo "Your first commit will automatically include governance metadata:"
echo "  AI-Governance: AG-001-approved"
echo "  Branch-Approval: $APPROVAL_METHOD"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
