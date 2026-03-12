---
id: GS-04
title: "Add post-edit documentation verification protocol to agents.md"
status: Done
priority: Medium
owner: "agent"
updated: "2026-03-08"
tags: [healing, process, agents, documentation]
depends_on: []
allowed_paths:
  - plans/healing/GS-04_doc_edit_verification_protocol.md
  - agents.md
evidence_required:
  - "grep 'Re-read' agents.md returns the post-edit protocol heading"
  - "grep 'section membership' agents.md returns a match"
---

# Taskcard GS-04 — Add Post-Edit Documentation Verification Protocol to `agents.md`

## Gap linkage

- GS-04: No post-edit verification protocol for documentation changes exists
  in `agents.md`. The DM-03 structural bug (AG-016..AG-019 outside their
  section) would have been caught immediately if the agent had re-read the
  modified document section before marking Done. The protocol must be
  codified so future documentation edits are verified at the right level
  of detail.

## Role

Senior engineer. Drop-in, production-ready.

## Scope

### Fix

In `agents.md`, add a sub-section to **Section 14** (Documentation Maintenance,
AG-019) titled `### Verifying Documentation Edits Before Done`.

Insert after the existing "If the check reports a stale spec but you are certain
no behavioral change occurred..." paragraph and before the final standards
reference line.

**New sub-section content**:

```markdown
### Verifying Documentation Edits Before Done

A documentation edit is NOT verified by a grep for the content you inserted.
It is verified by reading the output *as a whole* and confirming structural
coherence. Before setting any documentation taskcard to Done, run this
three-step check:

**Step 1 — Section membership check**

For Markdown files with `##` section headers, confirm that every `###`
heading you added belongs to the correct `##` parent:

```bash
# Show all ## and ### headings with line numbers
grep -n "^##\|^###" <file>
# Confirm: every new ### is preceded by the correct ## parent
```

**Step 2 — Full re-read of modified section**

Read back the entire `##` section you modified — not just the lines you
inserted. Verify that:
- No heading is now "orphaned" (a `###` with no parent `##`)
- No `---` separator breaks the section prematurely
- The document reads coherently from the modified section to the next
  `##` heading

**Step 3 — Section-scoped grep**

Use `awk` to extract only the section you edited and verify your additions
are inside it:

```bash
# Verify addition is inside the target section
awk '/^## Target Section Name/,/^---/' <file> | grep "your-added-content"
# Expected: the content you added, confirming section membership
```

**Verification shorthand for governance.md specifically**:

```bash
# All AG rules inside ## Agent Governance Rules
awk '/## Agent Governance Rules/,/^---/' specs/governance.md | grep "^### AG-"

# No orphaned AG rules after other sections
awk '/## Taskcard Lifecycle/,0' specs/governance.md | grep "^### AG-"
# Expected: empty
```

These three steps take less than 30 seconds and prevent the class of error
where correct content is placed in the wrong structural position.
```

### Allowed paths

- `agents.md` (targeted insertion in Section 14)

### Forbidden

Any file outside `agents.md` and this plan file.

---

## Acceptance checks

### CLI

```bash
# New sub-section is present
grep -n "Verifying Documentation Edits Before Done" agents.md
# Expected: 1 match with a line number inside Section 14

# Section membership check command is documented
grep "section membership" agents.md
# Expected: 1 match

# awk verification pattern is present
grep "awk.*Agent Governance Rules" agents.md
# Expected: 1 match (the governance.md shorthand)

# Step count is correct
grep -c "Step 1\|Step 2\|Step 3" agents.md
# Expected: >= 3 (the 3 verification steps)
```

### UI/Web/API

N/A — agents.md is a guidance document.

### Tests

No automated tests. CLI checks above are the verification mechanism.

### Config respected end-to-end

After this taskcard, the verification commands for documentation edits are
documented in the same file that agents read before pipeline runs and code
changes. Protocol is discoverable without reading the runbook.

### No mock data in production paths

N/A.

---

## Deliverables

1. **Targeted insertion in `agents.md` Section 14**: new `### Verifying
   Documentation Edits Before Done` sub-section with the three-step check
   and the governance.md verification shorthand.

---

## Hard rules

- Insertion point is inside **Section 14** (Documentation Maintenance) — not
  in Section 13 (Common Mistakes) and not as a new top-level section
- The three verification steps must include concrete bash commands, not
  just prose instructions
- The governance.md shorthand commands must be present verbatim (they are
  the specific commands that would have caught the GS-01 bug)
- No other sections of agents.md are modified

---

## Review dimensions (what 5/5 means for GS-04)

| Dimension | 5/5 criterion |
|-----------|---------------|
| Thoroughness | All three verification steps documented with concrete commands |
| Correctness | The `awk` commands actually catch orphaned headings (tested) |
| Actionability | An agent reading Section 14 can execute the check in < 30s |
| Minimality | Only Section 14 extended; no other agents.md text modified |
| Defect prevention | Following the protocol would have prevented the GS-01 DM-03 bug |

---

## Now (runbook)

```bash
# Step 1: Read the end of agents.md Section 14 to find insertion point
grep -n "Section 14\|## 14\|Documentation Maintenance" agents.md

# Step 2: Read the current Section 14 content to find the exact insertion point
# (after the "no behavioral change" paragraph, before the skills.md reference line)

# Step 3: Insert the new sub-section using Edit tool

# Step 4: Verify
grep -n "Verifying Documentation Edits Before Done" agents.md
# Expected: 1 match

grep "section membership\|awk.*Agent Governance" agents.md
# Expected: both present
```
