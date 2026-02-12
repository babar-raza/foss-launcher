# AI Agent Governance Rules

**Document ID**: SPEC-030
**Status**: Active
**Last Updated**: 2026-02-09
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

### 2.4 Principle of Defense in Depth
Enforcement mechanisms MUST use multiple independent layers to prevent policy violations. No single layer failure should compromise enforcement.

**Rationale**:
- Local hooks can be bypassed (e.g., `--no-verify`)
- CI/CD provides unbypassable final gate
- Multiple layers reduce single points of failure
- Early detection (creation-time) prevents issues from propagating
- Monitoring ensures accountability even when bypasses occur

**Implementation Pattern**:
1. **Prevention**: Validate at creation time (delete invalid artifacts)
2. **Detection**: Validate at commit/push time (block early)
3. **Enforcement**: Validate in CI/CD (unbypassable gate)
4. **Monitoring**: Track bypass usage (accountability and compliance)

### 2.5 Principle of Acceptance Criteria Completeness

**Rule Statement**:
> An AI agent MUST NOT mark a taskcard status as "Done" if any acceptance criterion remains pending, deferred, unchecked, or unverified through end-to-end testing.

**Context**: This principle was added in response to TC-1401 and TC-1402, where agents marked taskcards as "Done" despite having pending acceptance criteria (⏳), causing 99% claim loss in pilot verification and 8+ hours of wasted downstream work.

**Definition: "Acceptance Checks Satisfied"**

For purposes of the taskcard contract (00_TASKCARD_CONTRACT.md §11), an acceptance check is "satisfied" if and only if ALL of the following conditions hold:

1. **Checkbox State**: The acceptance item is marked with `[x]` or ✅ (not `[ ]`, `⏳`, or unchecked)
2. **Evidence Exists**: Referenced evidence files exist at the documented paths
3. **Evidence Complete**: Evidence files contain concrete results (logs, outputs, metrics) proving the criterion was met
4. **No Pending Markers**: Evidence does NOT contain words: "Pending", "Deferred", "TODO", "Not executed", "⏳", "📋"
5. **E2E Verification**: For integration taskcards (W2/W4/W5/W5.5), pilot runs or equivalent E2E tests executed with passing results

**Prohibited Rationalizations**:

Agents MUST NOT use the following excuses to bypass acceptance criteria:

1. ❌ "Unit tests validate integration" (unit tests cannot prove E2E behavior)
2. ❌ "Pilot runs take too long" (14 minutes << 8 hours of downstream debugging)
3. ❌ "Will verify in TC-XXXX later" (verification is taskcard-local requirement)
4. ❌ "Evidence section exists" (section existence ≠ criterion satisfaction)
5. ❌ "Deferred to reduce execution time" (acceptance criteria are NOT optional)

**Mandatory Gates for Critical Workers**:

Taskcards modifying these workers MUST include pilot verification as acceptance criterion:

- **W2 (FactsBuilder)**: Pilot must verify claim counts within expected range (±30%)
- **W4 (IAPlanner)**: Pilot must verify page plan completeness (all mandatory pages present)
- **W5 (SectionWriter)**: Pilot must verify generated content passes W7 validation
- **W5.5 (ContentReviewer)**: Pilot must verify dimension scores meet baseline thresholds
- **W7 (Validator)**: Pilot must verify zero false-positive validation errors

**Enforcement Mechanisms**:

1. **Validation Tool** (`tools/validate_taskcards.py --check-evidence`):
   - Parse acceptance checks section
   - Verify all items are checked `[x]`
   - Detect pending markers (`⏳`, `📋`, "Pending", "Deferred")
   - Exit 1 if status="Done" with incomplete acceptance

2. **Pre-Push Hook**:
   - Block push if any taskcard has `status: Done` with unchecked acceptance items
   - Block push if evidence files referenced in frontmatter don't exist
   - Emit warning for taskcards with "Deferred" in evidence files

3. **CI/CD Gate** (GitHub Actions):
   - Validate all taskcards in PR
   - Fail PR if status="Done" with pending acceptance
   - Comment on PR with list of incomplete taskcards

**Consequences of Violation**:

If an agent marks a taskcard "Done" with incomplete acceptance criteria:

1. **Immediate**: Status rolled back to "In-Progress"
2. **Documentation**: Violation documented in taskcard frontmatter (`rollback_reason`)
3. **Accountability**: Agent ID and timestamp logged for audit
4. **Corrective Action**: Taskcard cannot be re-marked "Done" until:
   - All acceptance criteria satisfied with evidence
   - Pilot runs executed with passing results
   - Evidence files updated with concrete proof

**Example: Valid "Done" Status**

```markdown
## Acceptance checks
- [x] All tests pass (3008/3008) - see reports/test_results.txt
- [x] Pilot 3D: claim count 2455 → 2485 (+30) - see runs/pilot-3d/product_facts.json
- [x] Pilot Note: claim count 6551 → 6571 (+20) - see runs/pilot-note/product_facts.json
- [x] W5.5 scores: CQ≥5, TA≥5, U≥5 - see runs/pilot-3d/review_report.json
- [x] No regressions: validation report status=PASS - see runs/pilot-3d/validation_report.json
```

**Example: Invalid "Done" Status (VIOLATION)**

```markdown
## Acceptance checks
- [x] All tests pass (102/102)
- [ ] Pilot 3D: claim count increase 10-30 ⏳ PENDING (pilot runs required)  ← VIOLATION
- [x] Self-review complete (12D scores 5/5)
```

This violates §2.5 because criterion #2 is unchecked and marked PENDING.

**Related Rules**:
- See AG-003 (Taskcard Validation Gate)
- See 00_TASKCARD_CONTRACT.md §11 (Definition of Done)
- See .claude/runbooks/taskcards.md §6 (Completion Checklist)

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

### 3.3 Taskcard Validation Gate (Multi-Layered)

**Rule ID**: `AG-003`
**Severity**: BLOCKER

**Rule Statement**:
> AI agents MUST NOT create, commit, or merge taskcard files that violate format requirements per `plans/taskcards/00_TASKCARD_CONTRACT.md`.

**Rationale**:
- Incomplete/invalid taskcards create ambiguity for implementation agents
- Missing sections (Failure modes, Review checklists) reduce quality
- Format violations (invalid status, incorrect YAML types) break automation
- Multi-layered enforcement prevents invalid taskcards from entering repository

**Enforcement Architecture** (Defense in Depth):

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Creation   │ --> │ Pre-Commit  │ --> │  Pre-Push   │ --> │   CI/CD     │
│   Script    │     │   (Staged)  │     │    (ALL)    │     │ (BLOCKING)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      ↓                    ↓                    ↓                    ↓
  Deletes invalid    Validates staged    Validates ALL      UNBYPASSABLE
  Exit code 1        Bypassable          Bypassable         Final Gate ⛔
```

**Layer 1: Creation Script** (`scripts/create_taskcard.py`)
- Validates newly created taskcards immediately
- **DELETES** invalid taskcards (prevents "create and forget")
- Exits with code 1 on validation failure
- 60-second validation timeout

**Layer 2: Pre-Commit Hook** (`hooks/pre-commit`)
- Validates STAGED taskcard files only
- Blocks commit if validation fails
- Bypassable with `git commit --no-verify` (tracked by CI/CD)
- Enforces at commit time

**Layer 3: Pre-Push Hook** (`hooks/pre-push`)
- Validates ALL 144+ taskcards in repository
- Blocks push if ANY taskcard is invalid
- Bypassable with `git push --no-verify` (tracked by CI/CD)
- Provides comprehensive error messages with fix instructions
- Warns that bypasses are tracked

**Layer 4: CI/CD Blocking Gate** (`.github/workflows/ai-governance-check.yml`)
- **UNBYPASSABLE** final enforcement layer
- Validates ALL taskcards on every PR
- Detects bypass attempts via commit message scanning
- **BLOCKS PR MERGE** if validation fails (exit 1 fails workflow)
- Runs on ubuntu-latest with `./.venv/bin/python tools/validate_taskcards.py`

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

**Required Frontmatter Format**:
- `status`: Must be `Draft`, `In-Progress`, or `Done` (NOT "Complete")
- `evidence_required`: Must be list of paths (NOT boolean true/false)
- `updated`: Must be quoted string "YYYY-MM-DD" (NOT date object)
- `allowed_paths`: Must match body `## Allowed paths` section exactly

**Bypass Policy**:
- Local bypasses (`--no-verify`) permitted for emergency fixes ONLY
- Bypass usage tracked and monitored via `scripts/monitor_bypass_usage.py`
- CI/CD detects bypasses via commit message patterns: `no.verify`, `no-verify`, `skip.*hook`, `bypass.*hook`
- CI/CD re-validates ALL taskcards regardless of local bypass
- **High bypass rate (>10%) triggers review of enforcement effectiveness**

**Monitoring**:
```bash
# Track bypass frequency
python scripts/monitor_bypass_usage.py --max-count 100

# Generate detailed report
python scripts/monitor_bypass_usage.py --detailed --output bypass_report.md
```

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
**Pre-Commit Hook** (`hooks/pre-commit`):
- Validates STAGED files only (fast, focused)
- Checks approval markers for gated operations (AG-001, AG-005)
- Validates taskcard completeness (AG-003 Layer 2)
- Bypassable with `--no-verify` (emergency use only)

**Pre-Push Hook** (`hooks/pre-push`):
- Validates ALL taskcards in repository (comprehensive)
- Blocks force pushes without approval (AG-005)
- Confirms new branch pushes (AG-006)
- Taskcard validation gate (AG-003 Layer 3)
- Bypassable with `--no-verify` (tracked by CI/CD)

**Prepare-Commit-Msg Hook**:
- Injects governance metadata into commit messages
- Adds Co-Authored-By for AI agent commits

### 5.3 CI Enforcement (GitHub Actions)
**AI Governance Check Workflow** (`.github/workflows/ai-governance-check.yml`):
- **Unbypassable final enforcement gate**
- Validates branch naming conventions
- Detects hook bypass attempts via commit message scanning
- **Blocking taskcard validation** (AG-003 Layer 4)
  - Validates ALL taskcards on every PR
  - Exit code 1 BLOCKS PR merge
  - Provides clear error messages with fix instructions
- Ensures PR creation followed approval protocol
- Runs on all pull requests and pushes to main

**Bypass Detection**:
```yaml
- name: Detect --no-verify bypass in commits
  run: |
    BYPASS=$(git log origin/${{ github.base_ref }}..${{ github.head_ref }} --format=%B \
      | grep -i "no.verify\|no-verify\|skip.*hook\|bypass.*hook" || true)

    if [ -n "$BYPASS" ]; then
      echo "⚠️ WARNING: Commit messages mention hook bypass"
      echo "All taskcards will be re-validated in CI/CD."
    fi
```

### 5.4 Creation-Time Enforcement
**Taskcard Creation Script** (`scripts/create_taskcard.py`):
- Validates taskcards immediately after creation (AG-003 Layer 1)
- **Deletes invalid taskcards** to prevent commit
- Exit code 1 on validation failure
- 60-second validation timeout
- Prevents "create and forget" anti-pattern

### 5.5 Monitoring and Compliance
**Bypass Usage Monitor** (`scripts/monitor_bypass_usage.py`):
- Analyzes git history for bypass indicators
- Tracks bypass frequency by author, date, and pattern
- Generates detailed compliance reports
- Exit code 2 if bypass rate exceeds 10%
- Helps identify enforcement gaps

**Usage**:
```bash
# Monitor last 100 commits
python scripts/monitor_bypass_usage.py

# Analyze date range
python scripts/monitor_bypass_usage.py --since "2026-02-01" --until "2026-02-09"

# Generate report
python scripts/monitor_bypass_usage.py --detailed --output bypass_report.md
```

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

| Version | Date       | Changes                                                                 |
|---------|------------|-------------------------------------------------------------------------|
| 1.0     | 2026-02-01 | Initial governance specification                                        |
| 1.1     | 2026-02-09 | Added multi-layered taskcard validation enforcement (AG-003)            |
|         |            | Documented 4-layer defense-in-depth architecture                        |
|         |            | Added bypass monitoring and compliance tracking tools                   |
|         |            | Enhanced enforcement mechanisms section with CI/CD blocking gate        |
|         |            | Documented creation-time validation and deletion of invalid taskcards   |

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

### Core Infrastructure
- [x] Create `.claude_code_rules` in repository root
- [x] Install git hooks (`hooks/pre-commit`, `hooks/pre-push`)
- [x] Add GitHub Actions workflow for governance validation
- [x] Create taskcard validation tool (`tools/validate_taskcards.py`)
- [x] Create taskcard creation script (`scripts/create_taskcard.py`)

### Multi-Layered Enforcement (AG-003)
- [x] **Layer 1**: Creation script validates and deletes invalid taskcards
- [x] **Layer 2**: Pre-commit hook validates staged taskcards
- [x] **Layer 3**: Pre-push hook validates ALL taskcards
- [x] **Layer 4**: CI/CD blocking gate (unbypassable)
- [x] Bypass detection in CI/CD workflow
- [x] Bypass monitoring script (`scripts/monitor_bypass_usage.py`)

### Documentation and Training
- [x] Document governance in team onboarding
- [x] Document 4-layer enforcement architecture
- [x] Create bypass usage monitoring guide
- [ ] Train developers on approval workflows
- [ ] Establish incident response process
- [ ] Schedule quarterly governance review

### Monitoring and Compliance
- [x] Bypass tracking implementation
- [x] Automated report generation
- [ ] Set up bypass rate alerts (>10% threshold)
- [ ] Quarterly compliance audit schedule
