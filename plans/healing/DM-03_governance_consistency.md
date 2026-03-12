---
id: DM-03
title: "Fix governance documentation consistency: CLAUDE.md AG range + specs/governance.md numbering gap"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-08"
tags: [healing, doc-maintenance, AG-019, governance]
depends_on: []
allowed_paths:
  - plans/healing/DM-03_governance_consistency.md
  - CLAUDE.md
  - specs/governance.md
evidence_required:
  - "grep 'AG-001 through AG-019' CLAUDE.md returns 1 match"
  - "grep 'AG-016\|AG-017\|AG-018' specs/governance.md returns matches (entries or explicit note)"
authorization_required: true
authorization_note: >
  CLAUDE.md and specs/governance.md are both protected files per .claude_code_rules.
  Explicit user authorization required before any edits. Do not proceed without it.
---

# Taskcard DM-03 — Fix Governance Documentation Consistency

## Gap linkage

- GR-04: `CLAUDE.md` references AG-001..AG-018 after AG-019 was added
- GR-08: `specs/governance.md` goes from AG-015 directly to AG-019; AG-016,
  AG-017, AG-018 are defined only in `.claude_code_rules` but have no entry
  in the human-readable governance spec

## Role

Senior engineer. Drop-in, production-ready.

## Authorization

**STOP**: Both target files (`CLAUDE.md`, `specs/governance.md`) are listed
in `.claude_code_rules` as protected files. You must obtain explicit user
authorization before writing either of them. Create this plan file, present
it to the user, and wait for "authenticated" or equivalent before editing.

## Scope

### Fix

#### 1. GR-04 — Update `CLAUDE.md`

Find and replace the governance reference line. Current text:

```
See `.claude_code_rules` for agent governance rules (AG-001 through AG-018).
```

Replace with:

```
See `.claude_code_rules` for agent governance rules (AG-001 through AG-019).
```

This is a one-line change. No other modifications to `CLAUDE.md`.

#### 2. GR-08 — Add AG-016, AG-017, AG-018 stubs to `specs/governance.md`

The file currently jumps from AG-015 to AG-019. Add brief entries for the
three rules that exist in `.claude_code_rules` but have no human-readable
counterpart. Insert them between AG-015 and AG-019 (before the AG-019 block
added in the original implementation).

**AG-016 entry** (root-cause fix policy):
```markdown
### AG-016: Root-Cause Fix Policy

Every defect must be traced to its root cause and fixed there. Surface-level
patches, workarounds, and symptom suppression are prohibited. If a gate
reports a failure, fix the generator that produced the failing output — do
not modify the gate to accept bad output.

See `.claude_code_rules` for the full enforcement specification.
```

**AG-017 entry** (plan mode for complex fixes):
```markdown
### AG-017: Plan Mode for Complex Multi-File Fixes

When a fix touches three or more files or requires architectural judgment,
the agent must enter plan mode, write a plan file, and obtain user approval
before executing. Single-file patches and trivial renames are exempt.

See `.claude_code_rules` for the full enforcement specification.
```

**AG-018 entry** (regression comparison):
```markdown
### AG-018: Pipeline Run Regression Review

After each pipeline run, the agent must produce a regression comparison
table showing the current run's D+F rate, A+B rate, and CRITICAL count
against the two prior runs. A regression (current run worse than both prior
runs on any tracked metric) blocks declaring the run successful.

See `.claude_code_rules` for the full metric list and outcome rules.
```

### Allowed paths

- `CLAUDE.md` (one-line text replacement)
- `specs/governance.md` (insertion of three AG entries before the existing AG-019 block)

### Forbidden

Any file outside the two allowed paths above (plus this plan file).

---

## Acceptance checks

### CLI

```bash
# Verify CLAUDE.md is updated
grep "AG-001 through AG-019" CLAUDE.md
# Expected: one match

# Verify AG-016 through AG-018 are now in governance.md
grep "AG-016\|AG-017\|AG-018" specs/governance.md
# Expected: 3 matches (one per rule heading)

# Verify AG-019 is still present and in correct order
grep -n "AG-01[5-9]" specs/governance.md
# Expected: AG-015, AG-016, AG-017, AG-018, AG-019 in ascending order
```

### UI/Web/API

N/A — documentation files only.

### Tests

No automated tests for governance prose. The CLI checks above are the
verification mechanism.

### Config respected end-to-end

After this change, all three governance documents (`.claude_code_rules`,
`CLAUDE.md`, `specs/governance.md`) must reference the same AG-001..AG-019
range without gaps or inconsistencies.

### No mock data in production paths

N/A.

---

## Deliverables

1. **One-line edit to `CLAUDE.md`**: update AG range reference from
   AG-001..AG-018 to AG-001..AG-019.

2. **Three-section insertion in `specs/governance.md`**: AG-016, AG-017,
   AG-018 entries added in sequence before the existing AG-019 block.

---

## Hard rules

- Only the explicitly named lines/sections are changed — no reformatting,
  no reordering, no cleanup of surrounding text
- AG-016, AG-017, AG-018 entries must reference `.claude_code_rules` for the
  full specification (don't duplicate the full rule text — it already exists
  there)
- Do not change the existing AG-019 entry added in the original implementation

---

## Review dimensions (what 5/5 means for DM-03)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Consistency | All governance docs reference AG-001..AG-019 with no gaps or mismatches |
| Minimality | CLAUDE.md: exactly 1 word changed; governance.md: exactly 3 new sections added |
| Correctness | AG-016..AG-018 descriptions accurately summarize `.claude_code_rules` definitions |
| Scope adherence | No other text in CLAUDE.md or governance.md is modified |
| Production grading | An agent reading governance.md gets a complete, non-confusing rule set |

---

## Now (runbook)

```bash
# PREREQUISITE: Obtain explicit user authorization before any edits.

# Step 1: Confirm current state
grep -n "AG-001" CLAUDE.md
# Expected: "...AG-001 through AG-018..."

grep -n "AG-01[5-9]" specs/governance.md
# Expected: only AG-015 and AG-019 (gap confirmed)

# Step 2: Edit CLAUDE.md — one-line replace
# Find: "AG-001 through AG-018"
# Replace: "AG-001 through AG-019"

# Step 3: Edit specs/governance.md
# Insert AG-016, AG-017, AG-018 sections immediately before the AG-019 block

# Step 4: Verify
grep "AG-001 through AG-019" CLAUDE.md       # must return 1 match
grep -n "AG-01[5-9]" specs/governance.md     # must return 5 matches in order
```
