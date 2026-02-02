# AI Governance Git Hooks

This directory contains git hooks that enforce AI agent governance rules for the FOSS Launcher project.

## Overview

These hooks implement automated gates to ensure AI coding assistants (Claude Code, GitHub Copilot, etc.) follow proper approval workflows before executing sensitive operations.

See **[specs/30_ai_agent_governance.md](../specs/30_ai_agent_governance.md)** for the complete specification.

## Available Hooks

### 1. `prepare-commit-msg` (Gate AG-001)

**Purpose**: Validates branch creation followed proper approval flow

**What it does**:
- Detects when a commit is being made on a newly created branch
- Checks for AI approval marker (`.git/AI_BRANCH_APPROVED`)
- Blocks commits on unapproved branches
- Adds governance metadata to approved commits

**Example workflow**:
```bash
# ❌ Without approval (will be blocked)
git checkout -b feature/new-feature
git commit -m "Add feature"
# ERROR: AG-001 violation - branch created without approval

# ✅ With approval (correct flow)
# 1. AI agent asks for approval via interactive dialog
# 2. User approves
# 3. AI sets approval marker:
touch .git/AI_BRANCH_APPROVED
echo "interactive-dialog" > .git/AI_BRANCH_APPROVED
# 4. Create branch and commit
git checkout -b feature/new-feature
git commit -m "Add feature"
# SUCCESS: Commit includes governance metadata
```

### 2. `pre-push` (Gates AG-003, AG-004)

**Purpose**: Validates remote push operations and prevents force push

**What it does**:
- Warns before pushing new branches to remote (AG-004)
- Blocks force push operations (AG-003)
- Requires explicit approval for destructive operations

**Example workflow**:
```bash
# Push new branch (requires confirmation)
git push -u origin feature/new-feature
# WARNING: AG-004 - first push of new branch
# To approve: git config branch.feature/new-feature.push-approved true

# Force push (blocked)
git push --force
# ERROR: AG-003 - force push detected and blocked
```

## Installation

### Quick Install

From repository root:
```bash
./hooks/install.sh
```

### Manual Install

```bash
cp hooks/prepare-commit-msg .git/hooks/prepare-commit-msg
cp hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/prepare-commit-msg
chmod +x .git/hooks/pre-push
```

## Configuration

### Enable/Disable Enforcement

```bash
# Disable enforcement (not recommended)
git config hooks.ai-governance.enforce false

# Re-enable enforcement
git config hooks.ai-governance.enforce true

# Disable push checks only
git config hooks.ai-governance.push-check false
```

### Approve Existing Branch

If you created a branch before installing hooks:
```bash
# Mark branch as approved
git config branch.your-branch-name.ai-approved true
touch .git/AI_BRANCH_APPROVED
echo "manual-approval" > .git/AI_BRANCH_APPROVED

# Then commit
git commit --amend --no-edit
```

## For AI Coding Assistants

If you're an AI assistant (Claude Code, Copilot, etc.) working on this repository:

### Branch Creation Workflow

**REQUIRED**: Always follow this flow when creating branches:

1. **Detect need for branch creation**
   ```
   User requests implementation that requires new branch
   ```

2. **Request approval via interactive dialog**
   ```
   Use AskUserQuestion tool or equivalent:
   "Should I create a new branch for this work?"
   Options:
   - Yes, create branch (recommended)
   - No, use current branch
   - Cancel
   ```

3. **If approved, confirm branch name**
   ```
   Suggest: feature/tc910-description
   Allow user to modify
   ```

4. **Set approval marker BEFORE creating branch**
   ```bash
   touch .git/AI_BRANCH_APPROVED
   echo "interactive-dialog" > .git/AI_BRANCH_APPROVED
   ```

5. **Create branch and proceed**
   ```bash
   git checkout -b feature/tc910-description
   # Marker will be consumed on first commit
   ```

### Prohibited Patterns

❌ **Never** do this:
```
User: "Implement TC-910 on a new branch"
AI: *creates branch without asking*
```

✅ **Always** do this:
```
User: "Implement TC-910 on a new branch"
AI: "I'll create a branch for TC-910. Suggested name: feature/tc910-taskcard-hygiene"
    [presents interactive choice]
User: [approves]
AI: *sets marker, creates branch, proceeds*
```

## Testing the Hooks

### Test 1: Unapproved Branch Creation (Should Fail)

```bash
# Create new branch without approval
git checkout -b test-unapproved-branch

# Try to commit
touch test.txt
git add test.txt
git commit -m "Test commit"

# Expected: ❌ BLOCKED with AG-001 violation message
```

### Test 2: Approved Branch Creation (Should Succeed)

```bash
# Set approval marker first
touch .git/AI_BRANCH_APPROVED
echo "manual-test" > .git/AI_BRANCH_APPROVED

# Create branch
git checkout -b test-approved-branch

# Commit
touch test.txt
git add test.txt
git commit -m "Test commit"

# Expected: ✅ SUCCESS with governance metadata in commit
```

### Test 3: Force Push Protection (Should Block)

```bash
# Make conflicting change
git commit --amend -m "Modified commit"

# Try to force push
git push --force

# Expected: ❌ BLOCKED with AG-003 violation message
```

## Troubleshooting

### Hook not running

```bash
# Check if hook is installed
ls -l .git/hooks/prepare-commit-msg

# Check if executable
chmod +x .git/hooks/prepare-commit-msg
```

### False positive on existing branch

```bash
# Mark branch as approved
git config branch.$(git branch --show-current).ai-approved true
```

### Bypass for emergency (use with caution)

```bash
# Temporarily disable enforcement
git config hooks.ai-governance.enforce false

# Make your commit
git commit -m "Emergency fix"

# Re-enable
git config hooks.ai-governance.enforce true
```

## Integration with CI/CD

These hooks are complemented by GitHub Actions workflow:
- **`.github/workflows/ai-governance-check.yml`**
- Validates governance rules on every PR
- Posts validation report as PR comment
- Checks for approval metadata, protected file changes, etc.

## Maintenance

### Updating Hooks

When hooks are updated in the repository:

```bash
# Re-run installation
./hooks/install.sh
```

### Auditing Governance Compliance

```bash
# Check recent commits for governance metadata
git log --all --grep="AI-Governance" --oneline

# Check which branches have approval markers
git config --get-regexp "branch.*ai-approved"

# View governance log (if enabled)
cat .ai_governance_log.jsonl
```

## Support

- **Specification**: [specs/30_ai_agent_governance.md](../specs/30_ai_agent_governance.md)
- **Issues**: Report hook problems as GitHub issues with `ai-governance` label
- **Questions**: See project documentation or ask maintainers

---

**Remember**: These hooks exist to prevent surprises and ensure AI assistants get explicit approval before making project-level changes. They protect both the codebase and the development workflow.
