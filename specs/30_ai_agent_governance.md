# AI Agent Governance Rules

**Document ID**: SPEC-030
**Status**: Active
**Last Updated**: 2026-02-01
**Scope**: All AI coding assistants (Claude Code, GitHub Copilot, Codex, etc.)

---

## 1. Purpose

This specification establishes governance rules and gates to control AI agent behavior when working on the FOSS Launcher project. These rules ensure that autonomous actions requiring project-level decisions always receive explicit human approval.

## 2. Governing Principles

### 2.1 Principle of Explicit Consent
AI agents MUST NOT execute actions that create persistent project artifacts (branches, PRs, releases, deployments) without explicit user approval through interactive mechanisms.

### 2.2 Principle of Least Surprise
AI agents MUST NOT perform actions that would surprise a developer returning to the project (e.g., finding unexpected branches, commits on wrong branches, or altered CI/CD configurations).

### 2.3 Principle of Reversibility
Before executing irreversible or difficult-to-reverse operations, AI agents MUST obtain approval and provide clear rollback instructions.

---

## 3. Mandatory Gates

### 3.1 Branch Creation Gate

**Rule ID**: `AG-001`
**Severity**: BLOCKER

**Rule Statement**:
> AI agents MUST NOT create new git branches without explicit user approval obtained through an interactive choice mechanism (selection dialog, form input, or explicit command).

**Rationale**:
- Branch creation affects repository structure visible to all collaborators
- Branch naming conventions may have team-specific policies
- Accidental branch proliferation creates repository clutter
- Branch creation often implies intent to push/share work

**Enforcement**:
1. **Static Rule**: Declared in `.claude_code_rules` and read by AI agents
2. **Pre-commit Hook**: Detects branch creation and validates approval marker
3. **Interactive Approval**: AI agents must use `AskUserQuestion` tool or equivalent before branch operations

**Approval Mechanisms** (in order of preference):
1. **Interactive Selection Dialog**:
   ```
   AI: "I need to create a new branch. Please select the branch name:"
   User: [selects from options or provides custom name]
   ```

2. **Explicit Command**:
   ```
   User: "Create a branch named feature/tc910-implementation"
   AI: [proceeds with branch creation]
   ```

3. **Approval Form**:
   ```
   AI presents form:
   - Branch name: ___________
   - Base branch: [main|develop|current]
   - Purpose: ___________
   [ Approve ] [ Cancel ]
   ```

**Prohibited Patterns**:
- ❌ Inferring branch creation from task description
- ❌ Creating branches mentioned in prompt without explicit approval
- ❌ Auto-creating branches based on ticket/task card numbers
- ❌ Creating branches "for convenience" during implementation

**Allowed Patterns**:
- ✅ User explicitly requests: "create a branch called X"
- ✅ AI asks via dialog and receives selection/confirmation
- ✅ User approves branch creation via form/choice mechanism

**Example Violation**:
```
User: "Implement TC-910 and create a PR"
AI: [creates branch feature/tc910 without asking] ❌ VIOLATION
```

**Correct Behavior**:
```
User: "Implement TC-910 and create a PR"
AI: "I'll implement TC-910. First, should I create a new branch?"
    Options:
    - Create new branch (recommended)
    - Work on current branch
    - Cancel
User: [selects "Create new branch"]
AI: "What should I name the branch?"
    Suggested: feature/tc910-taskcard-hygiene
User: [approves or provides alternative]
AI: [proceeds with branch creation]
```

---

### 3.2 LLM Claim Enrichment Approval Gate

**Rule ID**: `AG-002`
**Severity**: BLOCKER
**Scope**: W2 FactsBuilder semantic claim enrichment (TC-1045, TC-1046)

**Rule Statement**:
> AI agents and automated systems MUST NOT use LLM-based claim enrichment in production without explicit approval demonstrating cost controls, caching effectiveness, offline mode functionality, and determinism.

**Approval Required**: YES (for production use)

**Conditions**:
- LLM calls MUST be deterministic (temperature=0.0)
- Caching MUST be implemented (target: 80%+ hit rate on second run)
- Cost controls MUST be active (hard limit 1000 claims/repo, budget alert at $0.15/repo)
- Offline mode MUST work (heuristic fallbacks MUST produce valid metadata)
- Prompts MUST be versioned (included in cache key)

**Approval Process**:
1. Submit evidence of cost controls working (budget alerts, hard limits enforced)
2. Submit evidence of caching effectiveness (cache hit rate >= 80% on second run)
3. Submit evidence of offline mode working (pilot runs without LLM produce valid output)
4. Demonstrate determinism (same input → same output across multiple runs)

**Offline Mode Exemption**:
- Pilots MAY run in offline mode without AG-002 approval
- Offline mode uses heuristic fallbacks (no LLM calls)
- Quality lower but acceptable for testing and development
- Emit telemetry event `CLAIM_ENRICHMENT_OFFLINE_MODE`

**Cost Control Mechanisms**:
- **Batch processing**: 20 claims per LLM call (reduces API overhead)
- **Hard limit**: Maximum 1000 claims per repo (prevents cost spirals)
- **Budget alert**: Emit telemetry warning if estimated cost > $0.15 per repo
- **Skip enrichment**: For repos with < 10 claims (not cost-effective)
- **Caching**: Cache enriched claims by `sha256(repo_url + repo_sha + prompt_hash + llm_model + schema_version)`
- **Target cache hit rate**: 80%+ on second run with same repo SHA

**Offline Fallback Heuristics**:
- `audience_level`: Keyword-based (e.g., "install" → "beginner", "optimize" → "advanced")
- `complexity`: Text length-based (< 50 chars → "simple", > 150 chars → "complex")
- `prerequisites`: Empty array (no dependency analysis without LLM)
- `use_cases`: Empty array (no scenario generation without LLM)
- `target_persona`: `"{product_name} developers"` (generic fallback)

**References**:
- Specification: `specs/08_semantic_claim_enrichment.md`
- Schema: `specs/schemas/evidence_map.schema.json` (enrichment fields)
- Implementation: TC-1045 (W2 enrichment), TC-1046 (testing)

---

### 3.3 Taskcard Completeness Gate

**Rule ID**: `AG-003`
**Severity**: BLOCKER

**Rule Statement**:
> AI agents MUST NOT commit taskcard files that are missing required sections per `plans/taskcards/00_TASKCARD_CONTRACT.md`.

**Rationale**:
- Incomplete taskcards create ambiguity for implementation agents
- Missing sections (Failure modes, Review checklists) reduce quality
- Prevention system ensures all 14 mandatory sections exist

**Enforcement**:
1. **Pre-commit Hook**: `hooks/pre-commit` validates staged taskcards
2. **CI Validation**: `tools/validate_taskcards.py` runs in CI
3. **Developer Tools**: Templates and creation scripts prevent omissions

**Required Sections** (14 total):
1. Objective
2. Required spec references
3. Scope (In scope / Out of scope)
4. Inputs
5. Outputs
6. Allowed paths
7. Implementation steps
8. Failure modes (minimum 3)
9. Task-specific review checklist (minimum 6 items)
10. Deliverables
11. Acceptance checks
12. Self-review
13. E2E verification
14. Integration boundary proven

**Bypass**:
- `git commit --no-verify` (not recommended)
- Only use for emergency fixes documented in commit message

---

### 3.4 Branch Switching Gate

**Rule ID**: `AG-004`
**Severity**: ERROR

**Rule Statement**:
> AI agents MUST warn before switching branches if there are uncommitted changes.

**Enforcement**:
- Check `git status --porcelain` before `git checkout/switch`
- Require explicit approval if working directory is dirty

---

### 3.5 Destructive Git Operations Gate

**Rule ID**: `AG-005`
**Severity**: BLOCKER

**Rule Statement**:
> AI agents MUST obtain explicit approval before executing destructive git operations: `reset --hard`, `clean -fd`, `push --force`, `branch -D`, `rebase`, `cherry-pick`.

**Approval Required For**:
- Force push to any branch
- Hard reset that discards commits
- Deleting local or remote branches
- Interactive rebase
- Any operation that rewrites history

---

### 3.6 Remote Push Gate

**Rule ID**: `AG-006`
**Severity**: WARNING

**Rule Statement**:
> AI agents SHOULD confirm before first push to remote, especially for new branches.

**Enforcement**:
- Detect if branch has no upstream tracking
- Ask: "This branch hasn't been pushed. Push to remote?"

---

### 3.7 PR Creation Gate

**Rule ID**: `AG-007`
**Severity**: WARNING

**Rule Statement**:
> AI agents SHOULD present PR title, body, and target branch for approval before creating pull requests.

**Required Approval Elements**:
- PR title
- PR description/body
- Base branch (target for merge)
- Draft vs. ready status
- Labels/assignees

---

### 3.8 Configuration Change Gate

**Rule ID**: `AG-008`
**Severity**: ERROR

**Rule Statement**:
> AI agents MUST NOT modify CI/CD configurations, git hooks, or deployment scripts without explicit instruction.

**Protected Files**:
- `.github/workflows/*.yml`
- `.git/hooks/*`
- `Dockerfile`, `docker-compose.yml`
- Deployment manifests (k8s, terraform)
- `.claude_code_rules`, `.ai_governance`

**Exception**: User explicitly requests changes to these files

---

### 3.9 Dependency Installation Gate

**Rule ID**: `AG-009`
**Severity**: WARNING

**Rule Statement**:
> AI agents SHOULD confirm before installing new dependencies or running package managers with install/add commands.

**Rationale**:
- Supply chain security
- Lockfile changes affect all developers
- May have licensing implications

---

## 4. Implementation Requirements

### 4.1 For AI Agents (Claude Code, Copilot, etc.)

AI agents operating on this repository MUST:

1. **Parse Governance Files**: Read and respect `.claude_code_rules` in repository root
2. **Use Interactive Tools**: Leverage `AskUserQuestion` or equivalent for approvals
3. **Log Gate Checks**: Record when gates are triggered and outcomes
4. **Fail Safe**: If unable to obtain approval, ABORT the gated operation
5. **Provide Context**: When requesting approval, explain WHY the operation is needed

### 4.2 For Repository Maintainers

Repository maintainers SHOULD:

1. **Enforce via Hooks**: Install git hooks that validate gate compliance
2. **CI Validation**: Run governance checks in GitHub Actions
3. **Audit Logs**: Review AI agent actions periodically
4. **Update Rules**: Evolve governance rules based on incidents/learnings

---

## 5. Enforcement Mechanisms

### 5.1 Static Enforcement (`.claude_code_rules`)
- Declarative rules read by AI agents at session start
- Used by Claude Code to configure automatic behaviors

### 5.2 Dynamic Enforcement (Git Hooks)
- `pre-commit`: Check for approval markers before allowing commits
- `pre-push`: Validate branch creation followed proper approval flow
- `prepare-commit-msg`: Inject governance metadata into commit messages

### 5.3 CI Enforcement (GitHub Actions)
- Workflow that checks for governance violations in PR
- Validates branch naming conventions
- Ensures PR creation followed approval protocol

---

## 6. Approval Flow Examples

### Example 1: Branch Creation for New Feature

```
User: "Implement TC-910 taskcard hygiene improvements"

AI (Internal Check):
  - Task mentions implementation
  - Likely requires branch creation
  - Gate AG-001 triggered
  - Must obtain approval

AI: "To implement TC-910, I'll need to create a new branch.
     Please approve the branch details:"

     Branch Name: feature/tc910-taskcard-hygiene
     Base Branch: main
     Purpose: Implement taskcard hygiene rules per TC-910

     [ Approve ] [ Modify ] [ Cancel ]

User: [Approves]

AI: [Creates branch, proceeds with implementation]
    "Created branch feature/tc910-taskcard-hygiene from main"
```

### Example 2: Implicit Branch Reference (Should Block)

```
User: "Fix the bug on feature/hotfix-123 and push"

AI (Internal Check):
  - User mentions existing branch
  - Needs to switch, not create
  - Gate AG-002 applies (branch switch warning if dirty)
  - Gate AG-001 does NOT apply (not creating new branch)

AI: "I'll switch to feature/hotfix-123 and fix the bug.
     Note: You have uncommitted changes on current branch.

     Should I:
     1. Stash changes and switch
     2. Commit current changes first
     3. Cancel
     "

User: [selects option 2]

AI: [Commits, switches, fixes bug, commits fix]
```

### Example 3: Mentioned Branch Name (Requires Approval)

```
User: "Create a PR from feature/new-auth to main"

AI (Internal Check):
  - Branch "feature/new-auth" mentioned
  - Check if branch exists locally: NO
  - Check if branch exists remotely: NO
  - Gate AG-001 triggered (would need to create)

AI: "The branch feature/new-auth doesn't exist.
     Should I create it first?

     [ Yes, create branch ] [ No, use different branch ] [ Cancel ]
     "

User: [selects "Yes, create branch"]

AI: [Creates feature/new-auth, asks about PR details, proceeds]
```

---

## 7. Incident Response

If a gate violation occurs:

1. **Detect**: Git hook or CI detects violation
2. **Block**: Prevent the operation from completing
3. **Alert**: Notify user of violation and gate rule
4. **Remediate**: Provide rollback instructions
5. **Log**: Record incident for governance audit

---

## 8. Governance Metadata

All commits created via AI agent assistance SHOULD include:

```
Co-Authored-By: Claude Code <noreply@anthropic.com>
AI-Governance: AG-001-approved
Branch-Approval: interactive-dialog
```

---

## 9. Version History

| Version | Date       | Changes                          |
|---------|------------|----------------------------------|
| 1.0     | 2026-02-01 | Initial governance specification |

---

## 10. References

- Git Best Practices: https://git-scm.com/book/en/v2/Git-Branching-Branching-Workflows
- FOSS Launcher Worker Contracts: `specs/21_worker_contracts.md`
- Security Guarantees: `specs/06_security_guarantees.md`

---

## Appendix A: Gate Summary Table

| Rule ID | Gate Name                       | Severity | Requires Approval |
|---------|---------------------------------|----------|-------------------|
| AG-001  | Branch Creation                 | BLOCKER  | Yes (interactive) |
| AG-002  | LLM Claim Enrichment            | BLOCKER  | Yes (production)  |
| AG-003  | Taskcard Completeness           | BLOCKER  | Auto (validator)  |
| AG-004  | Branch Switching (dirty WD)     | ERROR    | Yes               |
| AG-005  | Destructive Git Operations      | BLOCKER  | Yes               |
| AG-006  | Remote Push (new branch)        | WARNING  | Recommended       |
| AG-007  | PR Creation                     | WARNING  | Recommended       |
| AG-008  | Configuration Changes           | ERROR    | Yes               |
| AG-009  | Dependency Installation         | WARNING  | Recommended       |

---

## Appendix B: Implementation Checklist

- [ ] Create `.claude_code_rules` in repository root
- [ ] Install git hooks (`hooks/pre-commit`, `hooks/pre-push`)
- [ ] Add GitHub Actions workflow for governance validation
- [ ] Document governance in team onboarding
- [ ] Train developers on approval workflows
- [ ] Establish incident response process
- [ ] Schedule quarterly governance review
