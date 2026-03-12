---
id: GS-02
title: "Propagate AG-020 to specs/governance.md and .claude_code_rules"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, governance, AG-020, self-review]
depends_on: [GS-01]
allowed_paths:
  - plans/healing/GS-02_add_ag020_to_governance.md
  - specs/governance.md
  - .claude_code_rules
evidence_required:
  - "grep 'AG-020' specs/governance.md returns the rule heading"
  - "grep 'AG-020' .claude_code_rules returns a rule block"
  - "grep 'AG-001 through AG-020' CLAUDE.md returns 1 match (pre-existing)"
  - "grep -c '## Agent Governance Rules' specs/governance.md returns 1"
authorization_required: true
authorization_note: "specs/governance.md and .claude_code_rules are both protected files. Require explicit user authorization."
---

# Taskcard GS-02 — Propagate AG-020 to `specs/governance.md` and `.claude_code_rules`

## Gap linkage

- GS-02: AG-020 (Self-Review After Every Task) was added to `CLAUDE.md` by the
  user on 2026-03-08 but is absent from:
  - `specs/governance.md` — the human-readable governance spec
  - `.claude_code_rules` — the machine-readable governance config

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

#### 1. `specs/governance.md` — Add AG-020 entry

After GS-01 completes, AG-001..AG-019 are all inside `## Agent Governance Rules`.
Append AG-020 as the final rule in that section, immediately after AG-019 and
before the closing `---` separator.

```markdown
### AG-020: Self-Review After Every Task

After completing any task — code, docs, config, plans, or analysis — the agent
must run the three-phase self-review protocol:

1. **Self-Review**: Score the output on 13 dimensions. Be honest and critical.
2. **Healing Plan**: Convert every gap/blocker identified into a taskcard written
   to `plans/healing/`. No orphaned gaps.
3. **Execute**: Run the highest-priority healing taskcards immediately in the
   same session.

There are no exceptions. Even "trivial" single-file tasks get a self-review.
Self-review is not optional overhead — it is the primary quality control
mechanism for agent-generated work.

**Runbook**: `.claude/runbooks/self-review.md`
```

#### 2. `.claude_code_rules` — Add AG-020 machine-readable block

Append after the existing `[documentation]` block (added in DM-01..DM-03 series):

```toml
# =============================================================================
# SELF-REVIEW PROTOCOL (AG-020)
# =============================================================================
# After completing any task, the agent must run the three-phase self-review
# protocol:
#   Phase 1 — Self-Review: Score output on 13 dimensions (thoroughness,
#             consistency, production grading, systematic approach, correctness,
#             scope adherence, maintainability, testability, robustness,
#             performance, integration fit, observability, minimality).
#   Phase 2 — Healing Plan: Convert every gap/blocker into a taskcard in
#             plans/healing/. No gap may remain without a taskcard.
#   Phase 3 — Execute: Run highest-priority healing taskcards immediately.
#
# EXCEPTIONS: None. All tasks require self-review, including "trivial" changes.
#
# RUNBOOK: .claude/runbooks/self-review.md

[self_review]
self_review_policy = "AG-020"
runbook = ".claude/runbooks/self-review.md"
phases = ["self_review", "healing_plan", "execute"]
no_exceptions = true
healing_output_dir = "plans/healing/"
```

#### 3. `CLAUDE.md` — Update AG range reference

`CLAUDE.md` currently reads `AG-001 through AG-019` on the governance line.
Update to `AG-001 through AG-020`.

### Allowed paths

- `specs/governance.md` (append AG-020 entry inside `## Agent Governance Rules`)
- `.claude_code_rules` (append `[self_review]` block)
- `CLAUDE.md` (one-word change: AG-019 → AG-020 in governance reference line)

### Forbidden

Any file outside the three allowed paths and this plan file.

---

## Acceptance checks

### CLI

```bash
# AG-020 in governance.md inside correct section
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "AG-020"
# Expected: ### AG-020: Self-Review After Every Task

# AG-020 in .claude_code_rules
grep -A 3 "AG-020" .claude_code_rules
# Expected: comment block + [self_review] section

# CLAUDE.md range updated
grep "AG-001 through AG-020" CLAUDE.md
# Expected: 1 match

# All 20 rules in governance.md, in order, inside the right section
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-" | wc -l
# Expected: 20
```

### UI/Web/API

N/A — governance and config files only.

### Tests

No automated tests. CLI checks above are the verification mechanism. Run all
four commands before marking Done.

### Config respected end-to-end

After this change, all three authoritative governance documents reference AG-020:
`CLAUDE.md` (rule text + range), `specs/governance.md` (human-readable entry),
`.claude_code_rules` (machine-readable config).

### No mock data in production paths

N/A.

---

## Deliverables

1. **Targeted edit to `specs/governance.md`**: AG-020 entry appended inside
   `## Agent Governance Rules`, after AG-019, before the closing `---`.

2. **Targeted edit to `.claude_code_rules`**: `[self_review]` TOML block
   appended after the `[documentation]` block.

3. **One-word edit to `CLAUDE.md`**: governance reference line updated from
   `AG-001 through AG-019` to `AG-001 through AG-020`.

---

## Hard rules

- AG-020 rule text in `specs/governance.md` must match the substance of the
  text already in `CLAUDE.md` — do not introduce inconsistencies
- `.claude_code_rules` TOML must be valid TOML syntax (no unquoted strings with
  special characters, no unclosed brackets)
- `CLAUDE.md` change is exactly 1 word: "AG-019" → "AG-020" in the reference line
- Do not modify any other existing rule text

---

## Review dimensions (what 5/5 means for GS-02)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Consistency | AG-020 present in all 3 governance files; no document references a different rule range |
| Correctness | AG-020 text in governance.md matches the authoritative CLAUDE.md definition |
| Minimality | Only the new AG-020 block + one-word CLAUDE.md change; zero other edits |
| Integration fit | AG-020 positioned after AG-019 inside `## Agent Governance Rules` (GS-01 must be Done first) |
| Config validity | .claude_code_rules TOML parses cleanly: `python -c "import tomllib; tomllib.load(open('.claude_code_rules','rb'))"` |

---

## Now (runbook)

```bash
# PREREQUISITE: GS-01 must be Done. Explicit user authorization required.

# Step 1: Confirm AG-019 is last rule inside ## Agent Governance Rules
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-" | tail -1
# Expected: ### AG-019: Documentation Maintenance Policy

# Step 2: Edit specs/governance.md
# Insert AG-020 entry after AG-019, before the closing --- of ## Agent Governance Rules

# Step 3: Edit .claude_code_rules
# Append [self_review] block after [documentation] block

# Step 4: Edit CLAUDE.md
# Change "AG-001 through AG-019" to "AG-001 through AG-020"

# Step 5: Verify all three
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-" | wc -l
# Expected: 20

grep "AG-020" .claude_code_rules | head -1
# Expected: # SELF-REVIEW PROTOCOL (AG-020)

grep "AG-001 through AG-020" CLAUDE.md
# Expected: 1 match
```
