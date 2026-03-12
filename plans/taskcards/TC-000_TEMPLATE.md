---
id: TC-NNNN
title: "[Brief descriptive title]"
status: Draft
priority: Normal
owner: "[agent or human]"
updated: "YYYY-MM-DD"
tags: []
depends_on: []
allowed_paths:
  - plans/taskcards/TC-NNNN_slug.md
evidence_required:
  - reports/TC-NNNN/evidence.md
---

# Taskcard TC-NNNN — [Brief descriptive title]

## Objective

[1-2 sentences: what this taskcard achieves and why it matters.]

## Required spec references

- `specs/[spec_name].md` (Section: [what it defines])

## Scope

### In scope
- [Item 1]
- [Item 2]

### Out of scope
- [Item 1 — why excluded or where it belongs]

## Inputs

- [File, data, or artifact consumed by this task]

## Outputs

- [File, artifact, or state produced by this task]

## Allowed paths

- plans/taskcards/TC-NNNN_slug.md
- [other paths — must match frontmatter exactly]

### Allowed paths rationale
[Why each path is needed]

## Implementation steps

### Step 1: [Name]

[Detailed instructions, commands, expected output]

### Step 2: [Name]

[Continue with numbered steps]

## Failure modes

### Failure mode 1: [Scenario name]

**Detection**: [How to detect — command, log message, error code]
**Resolution**: [Step-by-step fix]
**Gate**: [Which gate or spec this relates to]

### Failure mode 2: [Scenario name]

**Detection**: [...]
**Resolution**: [...]
**Gate**: [...]

### Failure mode 3: [Scenario name]

**Detection**: [...]
**Resolution**: [...]
**Gate**: [...]

## Task-specific review checklist

1. [ ] [Item specific to THIS task]
2. [ ] [Item specific to THIS task]
3. [ ] [Item specific to THIS task]
4. [ ] [Item specific to THIS task]
5. [ ] [Item specific to THIS task]
6. [ ] [Item specific to THIS task]
<!-- Documentation checks (AG-019 — required when modifying src/launcher/** or specs/**) -->
7. [ ] Docstrings updated for all new/changed public functions
8. [ ] Spec file updated if worker behavior changed (or confirmed no spec drift)
9. [ ] Schema `"description"` fields present for all new/changed properties
<!-- Docs layer checks (AG-019 extension — docs/guides/ ownership map) -->
10. [ ] Checked `docs/README.md` ownership map — if a trigger event applies, relevant guide updated
11. [ ] If a new `docs/guides/` file was added: `docs/README.md` index updated

## Deliverables

1. [Concrete file/artifact at specific path]
2. [Evidence bundle location]

## Acceptance checks

1. [ ] [Measurable criterion — e.g., tests pass]
2. [ ] [Measurable criterion — e.g., gate passes]
3. [ ] [Measurable criterion — e.g., file exists with expected content]

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: [gate name] PASS
- [ ] Evidence captured: [location]
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --since HEAD~N` (or `--uncommitted` on orphan/single-commit branch) — clean / acknowledged

## E2E verification

```bash
# Concrete command(s) to verify end-to-end
.venv/Scripts/python.exe -m pytest [relevant tests] -v
```

**Expected results**:
- [Measurable outcome 1]
- [Measurable outcome 2]

## Integration boundary proven

**Upstream**: [What provides input to this work]
**Downstream**: [What consumes output from this work]
**Contract**: [Interface/schema/data format guaranteed between them]
