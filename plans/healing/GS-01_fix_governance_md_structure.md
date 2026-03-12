---
id: GS-01
title: "Fix specs/governance.md: move AG-016..AG-019 inside ## Agent Governance Rules section"
status: Done
priority: High
owner: "agent"
updated: "2026-03-08"
tags: [healing, governance, structure, AG-019]
depends_on: []
allowed_paths:
  - plans/healing/GS-01_fix_governance_md_structure.md
  - specs/governance.md
evidence_required:
  - "awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep '### AG-01[5-9]' shows all 5 rules"
  - "grep -n '## Agent Governance Rules' specs/governance.md shows exactly 1 match"
  - "grep -n '^### AG-' specs/governance.md shows AG-001..AG-019 in consecutive order"
authorization_required: true
authorization_note: "specs/governance.md is a protected file per .claude_code_rules. Require explicit user authorization."
---

# Taskcard GS-01 — Fix `specs/governance.md` Section Structure

## Gap linkage

- GS-01: AG-016..AG-019 are outside `## Agent Governance Rules` — dangling `###`
  headings with no `##` parent section. Future agents doing section-based parsing
  will not find AG-016..AG-019 when reading `## Agent Governance Rules`.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

Restructure `specs/governance.md` so that AG-001..AG-019 are all inside the
`## Agent Governance Rules` section. The current layout is:

```
## Agent Governance Rules
  ### AG-001..AG-015
---
## Review Requirements
---
## Taskcard Lifecycle
---
### AG-016..AG-019   ← WRONG: no parent ## section
---
## Escalation
```

Target layout:

```
## Agent Governance Rules
  ### AG-001..AG-015
  ### AG-016..AG-019   ← moved inside
---
## Review Requirements
---
## Taskcard Lifecycle
---
## Escalation
```

**Concrete edit steps** (in order):

1. Remove the `---` separator that currently appears immediately after AG-015
   (between AG-015 and `## Review Requirements` in the original — this is the
   separator that closes the `## Agent Governance Rules` section too early).

2. The AG-016..AG-019 block currently sits after `## Taskcard Lifecycle`. Move
   it to immediately after AG-015, before `## Review Requirements`.

3. After moving, ensure a single `---` separator appears after AG-019 to close
   the `## Agent Governance Rules` section before `## Review Requirements`.

4. Remove the now-orphaned `---` separator that was before AG-016 in the old
   location (the one between `## Taskcard Lifecycle` and `### AG-016`).

**Net result**: The only change to document content is the position of the
AG-016..AG-019 block. No rule text is modified.

### Allowed paths

- `specs/governance.md` (surgical restructuring — no text content changes)

### Forbidden

Any file outside `specs/governance.md` and this plan file.

---

## Acceptance checks

### CLI

```bash
# All AG rules are now inside ## Agent Governance Rules
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-"
# Expected: all rules from AG-001 to AG-019, in order

# Exactly one ## Agent Governance Rules heading
grep -c "## Agent Governance Rules" specs/governance.md
# Expected: 1

# All AG-### headings appear before ## Review Requirements
grep -n "^### AG-\|^## Review Requirements" specs/governance.md
# Expected: all ### AG- lines have lower line numbers than ## Review Requirements

# No orphaned ### AG- headings after ## Taskcard Lifecycle
awk '/## Taskcard Lifecycle/,0' specs/governance.md | grep "^### AG-"
# Expected: no output (empty)
```

### UI/Web/API

N/A — documentation file only.

### Tests

No automated tests for governance prose structure. CLI checks above are the
verification mechanism. Run all four before marking Done.

### Config respected end-to-end

The moved AG-016..AG-019 rule text must be byte-identical to what was written
by DM-03. This is a position change only — zero content changes.

### No mock data in production paths

N/A.

---

## Deliverables

1. **Full replacement of `specs/governance.md`** with the AG-016..AG-019 block
   repositioned inside `## Agent Governance Rules`. All other content identical
   to the current file.

---

## Hard rules

- Rule text for AG-016..AG-019 must not be modified — position change only
- The `## Review Requirements`, `## Taskcard Lifecycle`, `## Escalation` sections
  must remain intact and in their current order
- No new rules added in this taskcard (AG-020 is GS-02's scope)
- No reformatting of existing rule text

---

## Review dimensions (what 5/5 means for GS-01)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Correctness | `awk '/## Agent Governance Rules/,/^---/'` captures AG-001..AG-019 |
| Minimality | Zero content changes; only the block's position in the file changes |
| Consistency | Document now has a single zone for governance rules |
| Integration fit | Future `### AG-020+` entries have an unambiguous insertion point |
| Scope adherence | Only `specs/governance.md` modified |

---

## Now (runbook)

```bash
# PREREQUISITE: Explicit user authorization required.

# Step 1: Read the current full file to identify exact line numbers
# (line numbers shifted from DM-03 additions)
grep -n "^##\|^### AG-\|^---" specs/governance.md

# Step 2: Identify the block to move
# Find: ### AG-016 start, ### AG-019 end (including its "---" paragraph)

# Step 3: Write the full replacement of specs/governance.md
# Correct section order:
#   ## Agent Governance Rules
#     AG-001..AG-015 (existing)
#     AG-016..AG-019 (moved here from end of file)
#   ---
#   ## Review Requirements (unchanged)
#   ---
#   ## Taskcard Lifecycle (unchanged)
#   ---
#   ## Escalation (unchanged)

# Step 4: Verify
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-"
# Expected: ### AG-001 through ### AG-019 in order

awk '/## Taskcard Lifecycle/,0' specs/governance.md | grep "^### AG-"
# Expected: empty (no orphaned rules after Taskcard Lifecycle)
```
