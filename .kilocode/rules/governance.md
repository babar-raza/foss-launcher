# Governance Rules for Kilo Code

This file summarizes the governance rules most relevant when working in this
repository with Kilo Code. The full rules are in `.claude_code_rules` and
`specs/governance.md` (AG-001 through AG-020).

---

## Taskcard-First Workflow (AG-002) — BLOCKING RULE

**You MUST NOT write, edit, or create any file under these paths without an
approved, In-Progress taskcard:**

- `src/launcher/**`
- `configs/**`
- `specs/schemas/**`

There are zero exceptions. Not for "small fixes". Not for "obvious changes".
Not for "one-line patches".

### Required sequence before touching protected paths

1. Check `plans/taskcards/` for an existing taskcard covering this work.
2. If none exists, create one from the template:
   `plans/taskcards/TC-000_TEMPLATE.md`
3. Fill all 14 mandatory sections (Objective, Scope, Inputs, Outputs, Allowed
   paths, Implementation steps, Failure modes ×3, Review checklist ×6,
   Deliverables, Acceptance checks, Self-review, E2E verification, Integration
   boundary proven).
4. Set status to `In-Progress` — `Draft` does NOT authorize writes.
5. Reference the taskcard ID in all commit messages.
6. Mark Done only when ALL acceptance checks are checked and tests pass.

### Files that do NOT require a taskcard

Docs, plans, specs (non-schema), configs outside the protected set,
`skills/`, `tests/`, `tools/`, and root-level .md files are freely editable.

---

## Root-Cause Fix Policy (AG-016)

Never apply surface-level patches, workarounds, or symptom suppression.

**Prohibited approaches:**
- Adding try/except to swallow errors instead of fixing what produces them
- String-replace hacks to clean up malformed output
- Disabling or weakening gates/checks to make failures go away
- Post-hoc fixup passes instead of fixing the producing worker

**Required approach:**
1. Identify the root cause (which worker/module produces the defect).
2. Fix the producing code so it generates correct output from the start.
3. Confirm the fix eliminates the defect class, not just the symptom.
4. Add a regression test that fails without the root-cause fix.

---

## Self-Review After Every Task (AG-020)

After completing any task — code, docs, config, plans, or analysis — run
the three-phase self-review before declaring Done:

1. **Self-Review** — Score output on 14 dimensions (1–5 each).
2. **Healing Plan** — Convert every gap into a taskcard in `plans/healing/`.
3. **Execute** — Run the highest-priority healing taskcards.

Runbook: `.claude/runbooks/self-review.md`

---

## Content Quality Standards

For content work, see:
- `.kilocode/rules/content-quality.md` — GENERATION STANDARDS, EVALUATION
  CRITERIA, ANTI-PATTERNS (AP-1..AP-10)
- `.kilocode/rules/human-review.md` — HUMAN REVIEW: Content Quality + SEO

Source of truth for both is `skills.md`. Operator skill prompts are in
`skills/prompts/` (SKL-201..SKL-210). Skill catalog is in `skills_catalog.md`.

---

## Branch Creation (AG-001)

Never create a git branch without explicit user approval. Present the proposed
branch name, base branch, and purpose — then wait for confirmation.

---

## Key references

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Primary governance enforcement (read first) |
| `.claude_code_rules` | Full AG-001..AG-020 rule set |
| `specs/governance.md` | Authoritative source for all governance rules |
| `agents.md` | Operational guide: commands, entry points, LLM config |
| `plans/taskcards/TC-000_TEMPLATE.md` | Taskcard template |
| `.claude/runbooks/taskcards.md` | Taskcard workflow runbook |
| `.claude/runbooks/self-review.md` | Self-review protocol runbook |
