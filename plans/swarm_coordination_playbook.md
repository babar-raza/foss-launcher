# Swarm Coordination Playbook

This playbook defines **enforceable rules** for parallel agent execution to prevent merge conflicts, ensure deterministic outcomes, and enable safe concurrent implementation.

**Status**: BINDING for all implementation agents
**Last updated**: 2026-01-22

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Module Ownership Rules](#module-ownership-rules)
3. [Taskcard Selection Protocol](#taskcard-selection-protocol)
4. [Branch Naming Convention](#branch-naming-convention)
5. [Write Fence Enforcement](#write-fence-enforcement)
6. [Cross-Module Changes](#cross-module-changes)
7. [Conflict Resolution](#conflict-resolution)
8. [Stop Conditions](#stop-conditions)
9. [PR Boundaries](#pr-boundaries)

---

## Core Principles

1. **Single-writer per module**: Only ONE taskcard may modify shared libraries at a time
2. **Write fence isolation**: Each agent MUST only modify files listed in their taskcard's `allowed_paths`
3. **Deterministic artifacts**: All generated artifacts must be stable and reproducible
4. **Evidence-driven**: All decisions must cite spec references or be recorded as blockers
5. **Fail-safe defaults**: When uncertain, STOP and write a blocker issue

### Critical Clarifications

**allowed_paths means WRITE fence only**:
- `allowed_paths` lists define which files a taskcard may **MODIFY/CREATE**
- Reading, importing, and using existing code is **ALWAYS allowed** for all taskcards
- Do NOT include shared libraries in `allowed_paths` just because you need to import/use them
- Example: If TC-401 needs to use `src/launch/io/write_json()`, it does NOT include `src/launch/io/**` in its `allowed_paths`

**Shared libs = owners only (zero tolerance)**:
- After Phase 4 hardening, repo enforces **zero shared-library write violations**
- Tooling (`validate_taskcards.py`, `validate_swarm_ready.py`) rejects violations
- No "acceptable overlap" exceptions - violations must be fixed before proceeding

**Preflight validation (mandatory)**:
- Before starting ANY taskcard implementation, run: `python tools/validate_swarm_ready.py`
- All gates must pass (Gate A1 may fail due to jsonschema - this will be fixed by TC-100)
- If Gate E fails (shared lib violations), repo is not ready for implementation

---

## Module Ownership Rules

### Shared Libraries (Single-Writer Enforcement)

The following directories contain **foundational shared code** and require **single-writer governance**:

- `src/launch/io/**` - Core IO utilities (atomic writes, schema validation, YAML parsing)
- `src/launch/util/**` - Shared utilities (logging, errors, run_id generation)
- `src/launch/models/**` - Shared data models
- `src/launch/clients/**` - External API clients (LLM, Git, Telemetry)

**Rule**: Only taskcards explicitly marked as owners may modify these directories.

**Current owner taskcard**: TC-200 (Schemas and IO foundations) owns initial implementation.

**To request shared lib changes**:
1. Write a blocker issue documenting the required change
2. Reference the blocker in your taskcard report
3. Do NOT modify shared libs directly
4. Coordinate via STATUS_BOARD or create a micro-taskcard for the specific change

### Worker-Specific Modules (Parallel-Safe)

Each worker has exclusive ownership of its implementation directory:

- `src/launch/workers/w1_repo_scout/**` - TC-400 series
- `src/launch/workers/w2_facts_builder/**` - TC-410 series
- `src/launch/workers/w3_snippet_curator/**` - TC-420 series
- `src/launch/workers/w4_ia_planner/**` - TC-430
- `src/launch/workers/w5_section_writer/**` - TC-440
- `src/launch/workers/w6_linker_patcher/**` - TC-450
- `src/launch/workers/w7_validator/**` - TC-460
- `src/launch/workers/w8_fixer/**` - TC-470
- `src/launch/workers/w9_pr_manager/**` - TC-480

Workers in different directories may be implemented **in parallel** without conflicts.

### Test Ownership

Each taskcard owns its own test files:

- `tests/unit/<module>/**` - Owned by the taskcard implementing `src/launch/<module>`
- `tests/integration/**` - Cross-module tests require coordination (see below)

---

## Taskcard Selection Protocol

### For Human Orchestrators

1. Review [STATUS_BOARD.md](taskcards/STATUS_BOARD.md)
2. Select taskcards with `status: Ready` and no `Blocked` dependencies
3. Verify no conflicting `allowed_paths` with in-progress taskcards
4. Assign by updating `owner` field and setting `status: In-Progress`
5. Re-generate STATUS_BOARD: `python tools/generate_status_board.py`

### For Agent Self-Selection

1. Read `plans/taskcards/STATUS_BOARD.md`
2. Filter taskcards where:
   - `status == "Ready"`
   - All `depends_on` taskcards have `status == "Done"`
   - No overlap in `allowed_paths` with any `In-Progress` taskcards
3. Claim taskcard by updating YAML frontmatter:
   - Set `owner: "<agent_id>"`
   - Set `status: "In-Progress"`
   - Update `updated: "YYYY-MM-DD"`
4. Commit frontmatter change with message: `claim: <taskcard_id> by <agent_id>`
5. Re-generate and commit STATUS_BOARD

---

## Branch Naming Convention

### Per-Taskcard Branches

All work MUST be done on feature branches:

```
feat/<taskcard-id>-<slug>
```

Examples:
- `feat/TC-100-bootstrap-repo`
- `feat/TC-401-clone-and-resolve-shas`
- `feat/TC-200-schemas-and-io`

### Multi-Taskcard Epics (Optional)

For coordinated delivery of related taskcards:

```
epic/<epic-name>-<tc-range>
```

Example:
- `epic/repo-scout-w1-TC-401-404`

### Branch Lifecycle

1. Create branch from `main` when claiming taskcard
2. Work exclusively on that branch
3. Push regularly to enable evidence collection
4. Open PR when all acceptance checks pass
5. Delete branch after merge

---

## Write Fence Enforcement

### Allowed Paths

Each taskcard YAML frontmatter includes `allowed_paths` - a list of glob patterns defining **exactly** what the agent may modify.

**Example**:
```yaml
allowed_paths:
  - src/launch/workers/w1_repo_scout/**
  - tests/unit/workers/test_w1_*.py
  - reports/agents/<agent>/TC-401/**
```

### Enforcement

1. **Pre-commit check** (recommended): Use `tools/validate_write_fence.py` (to be created if needed)
2. **PR review**: Reviewer MUST verify no files outside `allowed_paths` are modified
3. **Self-review**: Agent MUST confirm write fence compliance in self-review report

### Violations

If a taskcard requires changes outside its `allowed_paths`:

1. **STOP** implementation immediately
2. Write a blocker issue documenting the required change
3. Record in `OPEN_QUESTIONS.md`
4. Wait for coordination or taskcard update

---

## Cross-Module Changes

### When Shared Lib Changes Are Needed

If your taskcard requires changes to shared libraries (`src/launch/io/**`, `src/launch/util/**`, etc.):

#### Option 1: Blocker Issue (Preferred)
1. Write a detailed blocker issue JSON file
2. Document the required interface/function
3. Continue with stub/mock if possible
4. Mark taskcard as `Blocked` with reference to issue

#### Option 2: Micro-Taskcard Creation
1. Create a new taskcard `TC-2XX_<shared-lib-change>.md`
2. Set `allowed_paths` to only the shared lib path
3. Add dependency in your original taskcard
4. Mark original taskcard as `Blocked` waiting for new taskcard

#### Option 3: Coordination via Issue Tracker
1. Open a coordination issue in repo (if using issue tracker)
2. Tag the owner of the shared lib taskcard
3. Negotiate the change
4. Update both taskcards' dependencies

### Integration Tests

Integration tests in `tests/integration/**` touch multiple modules:

- **Prefer unit tests** in worker-specific directories
- For true integration tests, create a separate taskcard:
  - `TC-5XX_integration_<feature>.md`
  - Set `depends_on` to all relevant worker taskcards
  - Wait for dependencies to be `Done` before starting

---

## Conflict Resolution

### Merge Conflicts

If merge conflicts occur despite coordination:

1. **Identify root cause**: overlapping `allowed_paths` or missing dependency?
2. **Update taskcards**: tighten `allowed_paths` or add `depends_on`
3. **Rebase/merge**: resolve conflict following standard Git workflow
4. **Document**: record in swarm audit report

### Taskcard Ambiguity Conflicts

If two agents interpret a spec differently:

1. **Pause both implementations**
2. **Write blocker issues** documenting the ambiguity
3. **Update `OPEN_QUESTIONS.md`** with the conflict
4. **Human review**: requires stakeholder decision
5. **Update spec/taskcard** to resolve ambiguity for future

### Dependency Deadlocks

If circular dependencies are discovered:

1. **Identify the cycle**: list all taskcards involved
2. **Break the cycle**: refactor one taskcard to remove dependency
3. **Create micro-taskcard**: extract shared concern into new taskcard
4. **Update dependency graph**: regenerate STATUS_BOARD

---

## Stop Conditions

Agents MUST stop work and write a blocker if ANY of these occur:

### Spec Ambiguity
- Required detail is missing from specs
- Conflicting requirements in specs
- Unclear acceptance criteria

### Write Fence Violation
- Need to modify files outside `allowed_paths`
- Shared lib change required
- Cross-module dependency discovered

### Test Failures
- Existing tests fail after changes
- Cannot write deterministic test
- Test requires external service not in specs

### Blocked Dependencies
- Depends-on taskcard is `Blocked` or `In-Progress`
- Required artifact not yet available
- Shared resource locked by another agent

### Determinism Violation
- Cannot eliminate timestamp/random behavior
- Output differs across runs
- Environment-dependent behavior unavoidable

---

## PR Boundaries

### One PR Per Taskcard (Default)

Each taskcard generates **one pull request**:

- **Branch**: `feat/<taskcard-id>-<slug>`
- **Title**: `[<taskcard-id>] <taskcard-title>`
- **Description**: Link to taskcard, list deliverables, attach evidence
- **Reviewers**: Assigned per team policy

### Epic PRs (Exception)

For tightly coupled micro-taskcards (e.g., TC-401..TC-404):

- **Allowed**: Combine into single PR if `allowed_paths` are non-overlapping
- **Required**: Each taskcard's evidence must be individually verifiable
- **Branch**: `epic/<name>-TC-###-###`

### PR Checklist

Every PR MUST include:

- [ ] All taskcard acceptance checks passed
- [ ] Tests added and passing (or explicitly waived with rationale)
- [ ] Self-review 12D report included in `reports/`
- [ ] No files modified outside `allowed_paths`
- [ ] Agent report with commands and outputs
- [ ] Determinism verification performed
- [ ] Dependencies satisfied (all `depends_on` taskcards are `Done`)

### Review Process

1. **Automated checks**: CI runs tests, link checks, taskcard validation
2. **Human review**: Verify write fence, spec compliance, determinism
3. **Approval**: Requires 1+ approvers (per repo policy)
4. **Merge**: Squash or merge commit (per repo policy)
5. **Post-merge**: Update taskcard `status: Done`, regenerate STATUS_BOARD

---

## Coordination Tools

### Status Visibility

- **Primary**: [STATUS_BOARD.md](taskcards/STATUS_BOARD.md) - regenerate after every taskcard update
- **Secondary**: Git branch list (`git branch -a`)
- **Audit**: `reports/swarm_allowed_paths_audit.md`

### Communication Channels

- **Blocker issues**: `reports/agents/<agent>/<taskcard>/blockers/*.issue.json`
- **Open questions**: `OPEN_QUESTIONS.md`
- **Agent reports**: `reports/agents/<agent>/<taskcard>/report.md`

### Regeneration Commands

After updating any taskcard frontmatter:

```bash
# Validate all taskcards
python tools/validate_taskcards.py

# Regenerate STATUS_BOARD
python tools/generate_status_board.py

# Commit changes
git add plans/taskcards/*.md
git commit -m "update: taskcard status changes"
```

---

## Emergency Procedures

### Halt All Work

If critical issue discovered (security, data loss, spec invalidation):

1. **Broadcast**: Update all `In-Progress` taskcards to `Blocked`
2. **Document**: Create `reports/incidents/<timestamp>_<slug>.md`
3. **Notify**: Alert all agents via coordination channel
4. **Resolve**: Fix root cause, update specs/taskcards
5. **Resume**: Update taskcards back to `Ready` or `In-Progress`

### Rollback

If merged taskcard causes critical failure:

1. **Revert PR**: Create revert commit
2. **Update taskcard**: Set `status: Blocked` with revert reason
3. **Root cause**: Write incident report
4. **Fix forward**: Create new taskcard to address issue
5. **Re-implement**: Resume with corrected approach

---

## Appendix: Quick Reference

### Taskcard Lifecycle States

| State | Meaning | Who Can Transition |
|---|---|---|
| Draft | Under development | Taskcard author |
| Ready | Ready for implementation | Orchestrator |
| In-Progress | Actively being implemented | Agent (on claim) |
| Blocked | Cannot proceed | Agent (on blocker) |
| Done | Implementation complete and merged | Reviewer (on merge) |

### Shared Library Ownership

| Directory | Current Owner | Change Protocol |
|---|---|---|
| `src/launch/io/**` | TC-200 | Blocker issue required |
| `src/launch/util/**` | TC-200 | Blocker issue required |
| `src/launch/models/**` | TC-200 | Blocker issue required |
| `src/launch/clients/**` | TC-500 | Blocker issue required |

### Parallel-Safe Worker Modules

Workers TC-400, TC-410, TC-420, TC-430, TC-440, TC-450, TC-460, TC-470, TC-480 may run **concurrently** as long as their `allowed_paths` do not overlap (which they should not by design).

---

**Version**: 1.0
**Effective**: 2026-01-22
**Review cycle**: After every 5 completed taskcards or on conflict discovery
