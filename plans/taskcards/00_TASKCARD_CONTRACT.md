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
A task is “done” only when:
- All Acceptance checks are satisfied,
- Tests are added and passing (or explicitly waived with rationale in the agent report),
- The self-review is written and no dimension is <4 without a fix plan.

## Maintaining the plan set
When updating taskcards:
- Keep `plans/taskcards/INDEX.md` accurate.
- Prefer adding micro taskcards over enlarging existing ones.
- Treat taskcards as versioned contracts: changes should be deliberate and documented in the orchestrator master review.
