---
id: TC-DOCS-GOV
title: "Extend AG-019 to cover docs/guides/ layer"
status: Done
priority: Normal
owner: "agent"
updated: "2026-03-08"
tags: [governance, documentation, ag-019]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-DOCS-GOV_docs-governance-extension.md
  - specs/governance.md
  - .claude_code_rules
evidence_required:
  - reports/TC-DOCS-GOV/evidence.md
---

# Taskcard TC-DOCS-GOV — Extend AG-019 to cover docs/guides/ layer

## Objective

Extend the AG-019 documentation maintenance rule in `specs/governance.md` to
explicitly cover the new `docs/guides/` layer, and update the `[self_review]`
dimensions count in `.claude_code_rules` from 13 to 14 to reflect the new
"Documentation completeness" dimension added to the self-review runbook.

## Required spec references

- `specs/governance.md` (AG-019 — Documentation Maintenance Policy)
- `.claude_code_rules` (`[self_review]` block, `dimensions` field)

## Scope

### In scope
- One paragraph addition to AG-019 in `specs/governance.md`
- One integer change in `.claude_code_rules` (`dimensions = 13` → `dimensions = 14`)
- Optionally: add `docs_layer_ref = "docs/README.md"` under `[documentation]` in `.claude_code_rules`

### Out of scope
- Any other AG rule changes
- Modifying `docs/guides/` files (already done outside this taskcard)
- Modifying `scripts/check_doc_freshness.py` (already done outside this taskcard)

## Inputs

- Approved plan: `C:\Users\prora\.claude\plans\silly-moseying-meerkat.md`
- Current `specs/governance.md` AG-019 section
- Current `.claude_code_rules` `[self_review]` block

## Outputs

- `specs/governance.md` — AG-019 extended with one paragraph on docs/ layer
- `.claude_code_rules` — `dimensions = 14`

## Allowed paths

- plans/taskcards/TC-DOCS-GOV_docs-governance-extension.md
- specs/governance.md
- .claude_code_rules

### Allowed paths rationale

`specs/governance.md` is under `specs/**` which is a protected path. `.claude_code_rules`
is never-edit-without-explicit-user-instruction. Both require explicit authorization
before modification. This taskcard provides that authorization once approved.

## Implementation steps

### Step 1: Update AG-019 in specs/governance.md

Find the AG-019 section. After the existing "Triggers" list, add:

```markdown
**Docs layer (`docs/guides/`):** In addition to `specs/`, agents must update
the relevant guide when a trigger event from the ownership map in `docs/README.md`
applies. The `check_doc_freshness.py` script detects guide drift alongside spec
drift — the same exit-1 investigation applies.
```

### Step 2: Update .claude_code_rules

In the `[self_review]` block, change:
```
dimensions = 13
```
to:
```
dimensions = 14
```

Optionally add under `[documentation]`:
```
docs_layer_ref = "docs/README.md"
```

### Step 3: Capture evidence

```bash
grep -A 5 "Docs layer" specs/governance.md
grep "dimensions" .claude_code_rules
```

Copy output to `reports/TC-DOCS-GOV/evidence.md`.

## Failure modes

### Failure mode 1: AG-019 section not found at expected location

**Detection**: `grep -n "AG-019" specs/governance.md` returns no results.
**Resolution**: Read the full file, locate the AG-019 heading, and apply the edit.
**Gate**: Manual review of the edit result.

### Failure mode 2: .claude_code_rules has different syntax for dimensions

**Detection**: `grep "dimensions" .claude_code_rules` returns unexpected format.
**Resolution**: Read the full block, match the existing syntax exactly.
**Gate**: Manual verification after edit.

### Failure mode 3: Edit breaks other AG rules due to proximity

**Detection**: Read the full AG-019 section after edit and confirm only the
intended paragraph was added.
**Resolution**: Revert and re-apply the edit with a smaller, more targeted context string.
**Gate**: Manual review.

## Task-specific review checklist

1. [ ] AG-019 paragraph added immediately after existing Triggers list
2. [ ] No other AG rules modified
3. [ ] `.claude_code_rules` dimensions updated to 14
4. [ ] Paragraph text matches approved plan exactly
5. [ ] `specs/governance.md` is still valid Markdown (no broken headings)
6. [ ] `.claude_code_rules` syntax is unchanged except for the integer value
7. [ ] Docstrings updated for all new/changed public functions — N/A (no code)
8. [ ] Spec file updated if worker behavior changed — this IS the spec update
9. [ ] Schema `"description"` fields present for all new/changed properties — N/A
10. [ ] Checked `docs/README.md` ownership map — no code changed, N/A
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated — N/A

## Deliverables

1. `specs/governance.md` with extended AG-019
2. `.claude_code_rules` with `dimensions = 14`
3. `reports/TC-DOCS-GOV/evidence.md` with grep output confirming both changes

## Acceptance checks

1. [ ] `grep -A 5 "Docs layer" specs/governance.md` outputs the new paragraph
2. [ ] `grep "dimensions" .claude_code_rules` outputs `dimensions = 14`
3. [ ] `python scripts/check_doc_freshness.py --since HEAD~1` exits 0

## Self-review

### Verification results
- [ ] Tests: N/A (no code changed)
- [ ] Validation: manual Markdown review PASS
- [ ] Evidence captured: reports/TC-DOCS-GOV/evidence.md
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` — clean

## E2E verification

```bash
grep -A 8 "Docs layer" specs/governance.md
grep "dimensions" .claude_code_rules
python scripts/check_doc_freshness.py --since HEAD~1
```

**Expected results**:
- AG-019 shows the new docs/ paragraph
- `.claude_code_rules` shows `dimensions = 14`
- Freshness script exits 0

## Integration boundary proven

**Upstream**: `docs/README.md` (ownership map) + `.claude/runbooks/self-review.md` (dimension 14 already added)
**Downstream**: Every future taskcard's checklist items 10+11; every self-review's dimension 14
**Contract**: AG-019 now formally covers both `specs/` and `docs/guides/`; `.claude_code_rules` enforces 14-dimension self-review
