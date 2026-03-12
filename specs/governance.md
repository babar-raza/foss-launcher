# Governance: Agent Rules

## Overview

These rules govern how AI agents (including Claude Code) interact with the
foss-launcher v2 codebase. They are non-negotiable and override convenience,
speed, and scope. The goal is to prevent unauthorized changes, ensure
traceability, and maintain publication-ready quality.

---

## Agent Governance Rules

### AG-001: Taskcard-First Workflow

Every code change requires a taskcard. No code is written, modified, or deleted
without an associated taskcard that describes the intent, scope, and acceptance
criteria. Taskcards are created before work begins, not retroactively.

### AG-002: No Unauthorized File Creation

Agents must not create files outside the established package structure. New files
require explicit approval or a taskcard that specifies file creation. This
prevents scope creep and orphan files.

### AG-003: No Spec Modification Without Approval

Spec files in `specs/` are the source of truth. Agents must not modify spec
files unless the taskcard explicitly authorizes spec changes. Schema files in
`specs/schemas/` are especially protected.

### AG-004: Schema Validation at Every Boundary

All data crossing worker boundaries must be validated against the relevant JSON
schema. Agents must not bypass validation, even temporarily. "We'll add
validation later" is prohibited.

### AG-005: No Hardcoded Product References

Pipeline code must not contain hardcoded product names, import paths, or API
surfaces (Rule 4). All product-specific data comes from configs or the
understanding bundle. Agents must parameterize, not hardcode.

### AG-006: Sandwich Model Compliance

Every LLM call must follow the sandwich model (Rule 5): engineering pre-
processing, LLM call, engineering post-processing. Agents must not make "raw"
LLM calls without pre/post validation.

### AG-007: No Downstream Patching

When a quality issue is found, the fix must address the root cause in the
responsible upstream worker (Rule 6). Agents must not add sanitizers, fixers,
or post-processors that paper over upstream defects.

### AG-008: Test Coverage Required

Every code change must include tests. Untested code is not mergeable. Tests
must run with `PYTHONHASHSEED=0` and pass deterministically.

### AG-009: Deterministic Output

Pipeline output must be deterministic for the same input. Agents must not
introduce non-determinism (random seeds, unordered collections, timestamp-
dependent logic in output).

### AG-010: Event Emission Required

All significant pipeline actions must emit events to the event stream. Workers
must emit `worker_started` and `worker_completed` events. LLM calls must emit
`llm_call_completed`. Gates must emit `gate_executed`.

### AG-011: Checkpoint Integrity

Checkpoints must be written atomically and validated on both write and read.
Agents must not write partial or unvalidated checkpoints.

### AG-012: No Silent Failures

Errors must be raised, not swallowed. If a function can fail, it must either
raise an exception or return a typed error result. `except: pass` and bare
`except Exception` without re-raise are prohibited.

### AG-013: Config-Driven Topology

Pipeline topology is defined in `pipeline.yaml` (Rule 9). Agents must not
hardcode worker ordering, skip logic, or re-run targets in Python code. All
topology decisions come from config.

### AG-014: Shared Library Ownership

Shared libraries (`io/`, `models/`, `llm/`) have designated owners (by taskcard
series). Changes to shared code require coordination. Agents must not modify
shared code as a side effect of feature work without a dedicated taskcard.

### AG-015: Publication-Ready Standard

All generated content must meet publication-ready standards. Content that would
embarrass the product in front of a paying customer is never acceptable. This
applies to every stage of the pipeline, not just the final output.

### AG-016: Root-Cause Fix Policy

Every defect must be traced to its root cause and fixed there. Surface-level
patches, workarounds, and symptom suppression are prohibited. If a quality
gate reports a failure, fix the worker that produced the failing output —
do not modify the gate to accept bad output. "We'll fix it properly later"
is not an acceptable resolution.

See `.claude_code_rules` for the full enforcement specification.

### AG-017: Plan Mode for Complex Multi-File Fixes

When a fix touches three or more files or requires architectural judgment,
the agent must enter plan mode, write a plan file, and obtain user approval
before executing. Single-file patches and trivial renames are exempt. Plan
mode ensures complex changes are reviewed before irreversible edits are made.

See `.claude_code_rules` for the full enforcement specification.

### AG-018: Pipeline Run Regression Review

After each pipeline run, the agent must produce a regression comparison
table showing the current run's D+F rate, A+B rate, and CRITICAL count
against the two prior runs. A regression — where the current run is worse
than both prior runs on any tracked metric — blocks declaring the run
successful. If no prior runs exist, note this and record current metrics
for future comparison.

See `.claude_code_rules` for the full metric list and outcome rules.

### AG-019: Documentation Maintenance Policy

Agents must keep source-code documentation and specification files in sync
with code changes. When a taskcard modifies a worker, shared module, schema,
or CLI command, the agent must review and update the governing spec within
the same taskcard — not deferred. Documentation debt is not permitted to
accumulate.

**Triggers** — an agent MUST update docs when:
- A new public function, class, or worker phase is added to `src/launcher/**`
- An existing function's signature, behavior, or error contract changes
- A worker's phase logic changes (update `specs/worker_*.md`)
- A JSON schema property is added, removed, or renamed
- A CLI command is added or its flags change (update `agents.md`)
- A new governance rule is added

**Docs layer (`docs/guides/` and `docs/usage/`):** In addition to `specs/`, agents
must update the relevant guide when a trigger event from the ownership map in
`docs/README.md` applies. The `check_doc_freshness.py` script detects guide drift
alongside spec drift — the same exit-1 investigation applies.

**Verification**: Run before marking any taskcard Done:
```bash
python scripts/check_doc_freshness.py --since HEAD~N
```
Exit 1 means a spec is potentially stale. Investigate and update, or document
"no behavioral change" explicitly in the taskcard Self-review section.

**Standards**: See `skills.md` under `## TECHNICAL DOCUMENTATION STANDARDS`
for docstring, spec file, and schema annotation requirements.

### AG-020: Self-Review After Every Task

After completing any task — code, docs, config, plans, or analysis — the agent
must run the three-phase self-review protocol:

1. **Self-Review**: Score the output on 14 dimensions. Be honest and critical.
2. **Healing Plan**: Convert every gap/blocker identified into a taskcard written
   to `plans/healing/`. No orphaned gaps.
3. **Execute**: Run the highest-priority healing taskcards immediately in the
   same session.

There are no exceptions. Even "trivial" single-file tasks get a self-review.
Self-review is not optional overhead — it is the primary quality control
mechanism for agent-generated work.

**Runbook**: `.claude/runbooks/self-review.md`

---

## Review Requirements

### Code Review

- All changes are committed to the `v2` branch.
- Changes must pass CI (lint, typecheck, unit tests, integration tests, schema
  validation) before merge.
- Shared library changes require review of downstream impact.

### Content Review

- Pilot runs produce evaluation reports with A-F grades per page.
- GO criteria: A+B rate >= 50%, D+F rate <= 30%.
- NO_GO triggers root-cause diagnosis and re-generation (Rule 6).
- NEEDS_HUMAN_REVIEW requires manual inspection before publishing.

### Spec Review

- Spec changes are reviewed for consistency with the plan file and existing
  schemas.
- Schema changes require migration consideration for existing checkpoints.

---

## Taskcard Lifecycle

1. **Created**: Taskcard is written with intent, scope, and acceptance criteria.
2. **In Progress**: Agent is actively working on the taskcard.
3. **Testing**: Code is written, tests pass, CI is green.
4. **Done**: Acceptance criteria met, changes committed.

Taskcards are referenced by ID (e.g., `TC-3773`) in commit messages and code
comments.

---

## Escalation

When an agent encounters a situation not covered by these rules:
- Stop and ask for human guidance.
- Do not guess or improvise architectural decisions.
- Document the gap for future rule updates.
