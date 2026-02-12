# Taskcards Contract (binding for plans)

Taskcards are the **only** implementation instructions agents may follow. Agents MUST NOT guess missing details.

## Core rules
1) **Single responsibility:** a taskcard MUST cover one cohesive outcome. If it feels "multi-feature", split it into multiple taskcards.
2) **No improvisation:** if any required detail is missing or ambiguous, write a **blocker** issue artifact (see below) and stop that path.
3) **Write fence:** the taskcard MUST enumerate Allowed paths. Agents MAY ONLY modify files under Allowed paths.
4) **Evidence-driven:** decisions must cite the specific spec sections or schema fields that justify them.
5) **Determinism-first:** no timestamps, random IDs, nondeterministic ordering, or environment-dependent outputs unless explicitly allowed by specs.
6) **No manual content edits:** agents MUST NOT "massage" content files to make validators pass. All content changes must be explained by evidence and produced through the designed pipeline (W4–W6 and/or fix-loop W8). See `plans/policies/no_manual_content_edits.md`.
7) **Strict compliance guarantees (A-L):** All taskcards MUST comply with guarantees defined in [specs/34_strict_compliance_guarantees.md](../../specs/34_strict_compliance_guarantees.md). This includes: no floating refs, hermetic execution, supply-chain pinning, network allowlists, secret hygiene, budgets, change budgets, CI parity, non-flaky tests, no untrusted code execution, version locking, and rollback contracts.

### Critical clarifications

**allowed_paths = write fence only**:
- `allowed_paths` lists define which files a taskcard may **MODIFY or CREATE**
- Reading, importing, and using existing code is **ALWAYS allowed** for all taskcards
- Do NOT include shared libraries in `allowed_paths` just because you need to import/use them
- Example: If TC-401 needs to use `src/launch/io/write_json()`, it does NOT include `src/launch/io/**` in its `allowed_paths`

**Shared libraries = owners only (zero tolerance)**:
- After Phase 4 hardening, the repository enforces **zero shared-library write violations**
- Shared libraries and their designated owners:
  - `src/launch/io/**` → TC-200
  - `src/launch/util/**` → TC-200
  - `src/launch/models/**` → TC-250
  - `src/launch/clients/**` → TC-500
- Only the owner taskcard may include these paths in their `allowed_paths`
- Validation tooling (`validate_taskcards.py`, `validate_swarm_ready.py`) rejects violations
- No "acceptable overlap" exceptions permitted

**Frontmatter and body consistency (binding rule)**:
- The frontmatter `allowed_paths` list is the **single source of truth**
- The body section `## Allowed paths` MUST be an exact mirror of frontmatter (same entries, same order)
- The body section may include a subsection `### Allowed paths rationale` with explanations, but NOT additional paths
- A taskcard with mismatched frontmatter and body is invalid
- Validation tooling enforces this rule at preflight

**Preflight validation (mandatory)**:
- Before starting ANY taskcard implementation, run: `make install` (or pip editable install) to install dependencies
- Then run: `python tools/validate_swarm_ready.py`
- All gates must pass before proceeding. No exceptions.
- If Gate E fails (shared-lib violations), the repository is not ready for implementation work
- Gate failures indicate planning/specification issues that must be fixed first

**Version locking (Guarantee K, binding)**:
- Every taskcard MUST include version lock fields in YAML frontmatter:
  - `spec_ref`: Commit SHA of the spec pack (obtain via `git rev-parse HEAD`)
  - `ruleset_version`: Ruleset version (canonical: `ruleset.v1`)
  - `templates_version`: Templates version (canonical: `templates.v1`)
- These fields are REQUIRED and will be validated by Gate B (taskcard validation)
- Taskcards without version locks will FAIL preflight validation
- See [specs/34_strict_compliance_guarantees.md](../../specs/34_strict_compliance_guarantees.md) Guarantee K for rationale

## Mandatory taskcard sections
Every taskcard MUST contain these top-level sections:

- `## Objective`
- `## Required spec references`
- `## Scope` (with `### In scope` and `### Out of scope`)
- `## Inputs`
- `## Outputs`
- `## Allowed paths`
- `## Implementation steps`
- `## Failure modes` (minimum 3 failure modes with detection signal, resolution steps, and spec/gate link)
- `## Task-specific review checklist` (minimum 6 task-specific items beyond standard acceptance checks)
- `## Deliverables` (must include reports)
- `## Acceptance checks`
- `## Self-review`

Recommended (strongly) sections:
- `## Preconditions / dependencies`
- `## Test plan`

## Mandatory per-task evidence
Every task execution MUST produce:

- `reports/agents/<agent>/<task_id>/report.md`
- `reports/agents/<agent>/<task_id>/self_review.md` (use `reports/templates/self_review_12d.md`)

The agent report MUST include:
- files changed/added
- commands run (copy/paste)
- test results
- deterministic verification performed (what was compared)

## Blockers (how to stop safely)
If a required spec detail is missing or ambiguous, the agent MUST write a blocker issue:

- `reports/agents/<agent>/<task_id>/blockers/<timestamp>_<slug>.issue.json`

This file MUST validate against:
- `specs/schemas/issue.schema.json`

Minimum required fields:
- `schema_version`
- `issue_id`
- `severity` (BLOCKER)
- `component`
- `description`
- `repro_steps` (if applicable)
- `proposed_resolution` (what spec/taskcard must be clarified)

## Definition of done for a taskcard

A task is "done" only when ALL of the following conditions are met:

### 1. Acceptance Checks Satisfied

**All** acceptance check items must be **explicitly satisfied** with concrete evidence:

- **Checkbox state**: Every acceptance item marked `[x]` or ✅ (not `[ ]`, `⏳`, or blank)
- **Evidence files exist**: All evidence files referenced in frontmatter `evidence_required` list exist on disk
- **Evidence complete**: Evidence files are ≥100 bytes and contain concrete results (not "TODO", "Pending", "Not executed")
- **No pending markers**: Evidence files do NOT contain: `⏳`, `📋 Pending`, `Deferred`, `Will verify in TC-XXX`

**Invalid "Done" examples**:
```markdown
# VIOLATION 1: Unchecked acceptance item
- [x] Tests pass
- [ ] Pilots complete  ← CANNOT mark status: Done

# VIOLATION 2: Pending marker in evidence
- [x] Pilots complete ⏳ PENDING (see TC-1408)  ← CANNOT mark status: Done

# VIOLATION 3: Evidence file missing
evidence_required:
  - reports/agents/agent_b/TC-XXX/evidence.md  ← file doesn't exist = CANNOT mark Done
```

### 2. Tests Passing (or Waived)

**Unit tests**:
- All existing tests pass (zero failures)
- New tests added for new functionality (minimum 3 tests per new module)
- Test output captured in evidence files

**Integration tests** (if applicable):
- Full test suite passes: `pytest tests/ -x`
- Test count documented in evidence (e.g., "3008 passed, 9 skipped")

**Pilot runs** (MANDATORY for W2/W4/W5/W5.5 changes):
- Both pilots executed: pilot-aspose-3d-foss-python, pilot-aspose-note-foss-python
- Pilot output directories captured in evidence
- Key metrics documented:
  - Claim counts (W2 changes)
  - Page counts (W4 changes)
  - W5.5 dimension scores (W5/W5.5 changes)
  - Validation status (all changes)
- Exit codes documented (must be 0 for PASS)

**Test waiver** (if no tests added):
- Must include explicit rationale in evidence.md
- Rationale must specify why testing is infeasible (not just "takes too long")
- Approved waivers: documentation-only changes, spec updates, governance updates

### 3. Self-Review Complete

**12D self-review**:
- All 12 dimensions scored (1-5 scale)
- No dimension <4 without documented fix plan
- Known gaps section completed (empty = "None" explicitly stated)
- Self-review file exists at path in `evidence_required`

**Evidence files**:
- `plan.md` - Implementation approach and design decisions
- `changes.md` - File-by-file change summary with line numbers
- `evidence.md` - Test results, pilot outputs, verification commands
- `self_review.md` - 12D assessment with scores and known gaps

### 4. E2E Verification Executed (Critical Workers Only)

For taskcards modifying W2, W4, W5, W5.5, W7:

**Pilot verification checklist**:
- [x] Both pilots executed with pinned configs
- [x] Pilot run directories captured in evidence
- [x] Key metrics documented (claim counts, page counts, scores)
- [x] Exit codes = 0 (PASS status)
- [x] No regressions vs baseline (claim count ±30%, scores maintained)
- [x] Validation reports included (validation_report.json, review_report.json if applicable)

**Example evidence documentation**:
```markdown
## E2E Verification Results

### 3D Pilot
**Command**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-3d-foss-python --output runs/tc-XXX-3d`
**Exit code**: 0 ✅
**Runtime**: 3m 42s
**Artifacts**: runs/tc-XXX-3d/
**Metrics**:
- Claim count: 2455 → 2485 (+30) ✅
- Pages generated: 18 ✅
- Validation status: PASS ✅
- W5.5 scores: CQ=5, TA=5, U=5 ✅

### Note Pilot
**Command**: `PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/run_pilot.py --pilot pilot-aspose-note-foss-python --output runs/tc-XXX-note`
**Exit code**: 0 ✅
**Runtime**: 7m 18s
**Artifacts**: runs/tc-XXX-note/
**Metrics**:
- Claim count: 6551 → 6571 (+20) ✅
- Pages generated: 24 ✅
- Validation status: PASS ✅
- W5.5 scores: CQ=5, TA=4, U=4 ✅
```

### 5. Status Change Authorization

Before updating `status: In-Progress` → `status: Done`:

1. **Self-verify**: Review all acceptance checks are ✅ with evidence
2. **Run validation**: `python tools/validate_taskcards.py plans/taskcards/TC-XXX.md --check-evidence`
3. **Check evidence files**: Ensure all files in `evidence_required` exist and are complete
4. **Document completion**: Update frontmatter `updated` field to current date
5. **Commit**: Create commit with message format: `feat(tc-XXX): mark complete with pilot verification`

### Rollback Conditions

Status will be rolled back from "Done" to "In-Progress" if:

1. Acceptance checks found unchecked or pending during audit
2. Evidence files missing or contain "Pending"/"TODO"
3. Pilot verification not executed for W2/W4/W5/W5.5 changes
4. Downstream taskcard (like TC-1408) discovers integration failure

Rollback process:
1. Update frontmatter: `status: Done` → `status: In-Progress`
2. Add frontmatter field: `rollback_reason: "[explanation]"`
3. Document in taskcard body: `## Rollback History` section
4. Create BLOCKER issue documenting the false completion

### Summary Checklist

Before marking `status: Done`, verify:

- [ ] All acceptance items marked `[x]` (not `[ ]` or `⏳`)
- [ ] All evidence files exist and are ≥100 bytes
- [ ] No "Pending", "Deferred", "TODO" in evidence files
- [ ] Tests pass: `pytest tests/ -x` shows 0 failures
- [ ] Pilots executed (for W2/W4/W5/W5.5): both 3D and Note, exit code 0
- [ ] Self-review complete: 12D scored, no dimension <4 without fix plan
- [ ] Validation passes: `tools/validate_taskcards.py` exits 0
- [ ] Evidence files committed: all paths in `evidence_required` are in git

If ANY checkbox is unchecked, status MUST remain "In-Progress".

## Maintaining the plan set
When updating taskcards:
- Keep `plans/taskcards/INDEX.md` accurate.
- Prefer adding micro taskcards over enlarging existing ones.
- Treat taskcards as versioned contracts: changes should be deliberate and documented in the orchestrator master review.
