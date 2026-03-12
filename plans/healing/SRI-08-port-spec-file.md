# SRI-08: Port Intake Spec Document from V1

**Status:** Done
**Gap linkage:** Intake port self-review, Dimension 7 (Documentation)
**Role:** Documentation
**Scope:** Port `specs/49_github_intake.md` from v1 main branch

---

## Problem

V1 has a spec file `specs/49_github_intake.md` documenting the intake discovery subsystem's design, data flow, and contracts. V2 has the code but not the spec. Without the spec, future developers lack design context.

## Acceptance Checks

- [ ] Spec file exists at `specs/github_intake.md` (unnumbered per v2 convention)
- [ ] References updated from `launch` to `launcher` package paths
- [ ] Any v1-specific details (v1 schema fields, v1 CLI patterns) updated to v2
- [ ] Spec is referenced from relevant module docstrings

## Deliverables

1. `specs/github_intake.md` — adapted from v1's `specs/49_github_intake.md`

## Hard Rules

- Use v2 naming convention (unnumbered specs)
- Don't fabricate content — port what exists, update references

## Runbook

1. `git show main:specs/49_github_intake.md` to get v1 content
2. Copy to `specs/github_intake.md`
3. Find/replace `launch` → `launcher` in paths
4. Update any v1-specific schema/CLI references
5. Review for accuracy
