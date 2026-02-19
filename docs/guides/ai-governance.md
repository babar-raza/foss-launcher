# AI Governance Quick Reference

**For**: Developers and AI Coding Assistants (Claude Code, GitHub Copilot, etc.)
**Purpose**: Quick lookup of governance rules and approval workflows

---

## TL;DR - The One Rule You Must Know

🚨 **NEVER create git branches without explicit user approval via interactive choice/dialog**

Even if the user's prompt mentions a branch name, you MUST ask for confirmation first.

---

## Quick Gate Reference

| Gate | What | Severity | Approval Required |
|------|------|----------|-------------------|
| **AG-001** | Branch creation | 🔴 BLOCKER | ✅ Yes - Interactive |
| **AG-002** | Branch switching (dirty) | 🟠 ERROR | ✅ Yes |
| **AG-003** | Force push, hard reset | 🔴 BLOCKER | ✅ Yes |
| **AG-004** | Push new branch to remote | 🟡 WARNING | ✅ Recommended |
| **AG-005** | PR creation | 🟡 WARNING | ✅ Recommended |
| **AG-006** | Config file changes | 🟠 ERROR | ✅ Yes |
| **AG-007** | Dependency installation | 🟡 WARNING | ✅ Recommended |

---

## For AI Assistants: Branch Creation Workflow

### ❌ WRONG - Do NOT do this:

```
User: "Implement TC-910 on a new branch and create a PR"

AI: [silently creates branch feature/tc910]  ❌ VIOLATION!
```

### ✅ CORRECT - Always do this:

```
User: "Implement TC-910 on a new branch and create a PR"

AI: "I'll implement TC-910. First, let me confirm the branch details.

Should I create a new branch?

Options:
1. ✅ Create new branch (recommended)
2. Use current branch: feat/tc902_w4_impl_20260201
3. Cancel

Please select an option."

User: [selects option 1]

AI: "What should the branch be named?

Suggested: feature/tc910-taskcard-hygiene

[Approve] [Modify] [Cancel]"

User: [Approves]

AI: [Now creates branch using the approval flow]
```

### Implementation Steps for AI Assistants:

1. **Detect** branch creation need
2. **Ask** using `AskUserQuestion` tool:
   ```
   Question: "Should I create a new branch for this work?"
   Options: [Create new | Use current | Cancel]
   ```
3. **If approved**, confirm branch name:
   ```
   Question: "Branch name?"
   Suggested: feature/tc910-description
   ```
4. **Set approval marker**:
   ```bash
   touch .git/AI_BRANCH_APPROVED
   echo "interactive-dialog" > .git/AI_BRANCH_APPROVED
   ```
5. **Create branch**:
   ```bash
   git checkout -b feature/tc910-description
   ```
6. **Proceed** with implementation

---

## For Developers: Quick Commands

### Create Branch (Compliant Way)

```bash
# Use the helper script
./scripts/create-branch-with-approval.sh

# Or manually:
touch .git/AI_BRANCH_APPROVED
echo "manual-approval" > .git/AI_BRANCH_APPROVED
git checkout -b feature/your-branch
```

### Install Governance Hooks

```bash
./hooks/install.sh
```

### Check Governance Status

```bash
# View recent governance-compliant commits
git log --all --grep="AI-Governance" --oneline

# Check hook installation
ls -l .git/hooks/prepare-commit-msg
ls -l .git/hooks/pre-push

# View governance config
cat .claude_code_rules
```

### Emergency Bypass (Use Sparingly!)

```bash
# Disable enforcement temporarily
git config hooks.ai-governance.enforce false

# Re-enable
git config hooks.ai-governance.enforce true
```

---

## Common Scenarios

### Scenario 1: User Mentions Branch Name in Prompt

```
User: "Create feature/new-auth branch and implement OAuth"

❌ WRONG: Create branch immediately (just because they named it)
✅ CORRECT: Still ask for confirmation with suggested name
```

**Correct AI Response**:
```
"I'll implement OAuth authentication. Let me confirm the branch:

Branch name: feature/new-auth
Base branch: main
Purpose: Implement OAuth authentication

[Approve] [Modify] [Cancel]"
```

### Scenario 2: User Says "Use a New Branch"

```
User: "Fix the login bug. Use a new branch."

❌ WRONG: Infer branch name and create it
✅ CORRECT: Ask for branch name and details
```

**Correct AI Response**:
```
"I'll fix the login bug on a new branch.

Suggested branch name: fix/login-bug-20260201

[Approve] [Modify] [Cancel]"
```

### Scenario 3: User Says "Create Branch X"

```
User: "Create branch feature/tc910 and start working"

✅ This is explicit, but still good practice to confirm:
"Creating branch feature/tc910 based on main. Confirm?"
```

### Scenario 4: Working on Existing Branch

```
User: "Switch to feature/existing-branch and continue work"

This is NOT branch creation, so AG-001 doesn't apply.
Just check AG-002 (warn if working directory is dirty).
```

---

## Protected Files (AG-006)

**Never modify** these without explicit user instruction:

- `.github/workflows/*.yml`
- `Dockerfile`, `docker-compose.yml`
- `.claude_code_rules`
- `hooks/*`
- `specs/30_ai_agent_governance.md`
- Infrastructure: `*.tf`, `k8s/*.yaml`

**If user asks to modify these**: Proceed, but mention the change is to a protected file.

---

## Branch Naming Convention

**Pattern**: `<type>/tc<number>_<description>_YYYYMMDD`

**Types**:
- `feat/` - New feature
- `fix/` - Bug fix
- `chore/` - Maintenance
- `docs/` - Documentation
- `test/` - Tests
- `refactor/` - Refactoring

**Examples**:
- `feat/tc910_taskcard_hygiene_20260201`
- `fix/login_bug_20260201`
- `chore/update_dependencies_20260201`

---

## Troubleshooting

### "AG-001 violation" on commit

**Problem**: Branch was created without approval marker

**Solution**:
```bash
# Set approval marker and amend commit
touch .git/AI_BRANCH_APPROVED
echo "manual-approval" > .git/AI_BRANCH_APPROVED
git commit --amend --no-edit
```

### "AG-004 warning" on push

**Problem**: New branch, first push to remote

**Solution**:
```bash
# Approve the push
git config branch.$(git branch --show-current).push-approved true
git push
```

### Hook not running

**Problem**: Hooks not installed or not executable

**Solution**:
```bash
./hooks/install.sh
# Or manually:
chmod +x .git/hooks/prepare-commit-msg
chmod +x .git/hooks/pre-push
```

---

## Testing the Rules

### Test 1: Verify AG-001 Enforcement

```bash
# This should FAIL:
git checkout -b test-branch
touch test.txt
git add test.txt
git commit -m "Test"  # ❌ Should block with AG-001 error

# This should SUCCEED:
touch .git/AI_BRANCH_APPROVED
echo "test" > .git/AI_BRANCH_APPROVED
git commit -m "Test"  # ✅ Should succeed
```

### Test 2: Verify Protected Files (AG-006)

CI will warn if you modify:
- `.claude_code_rules`
- `.github/workflows/*.yml`
- Other protected files

---

## Documentation Links

- **Full Specification**: [specs/30_ai_agent_governance.md](../specs/30_ai_agent_governance.md)
- **Hooks README**: [hooks/README.md](../hooks/README.md)
- **Rules File**: [.claude_code_rules](../.claude_code_rules)
- **CI Workflow**: [.github/workflows/ai-governance-check.yml](../.github/workflows/ai-governance-check.yml)

---

## Remember

The goal is to prevent surprises:
- ✅ User always knows when branches are created
- ✅ User approves branch names explicitly
- ✅ User is in control of repository structure
- ✅ AI agents assist, but don't autonomously modify project structure

**When in doubt**: Ask the user first!

---

*This is a living document. Update as governance rules evolve.*
