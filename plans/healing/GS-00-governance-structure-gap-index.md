# GS-00 — Governance Structure Healing Gap Index

## Context

DM-03 (executed 2026-03-08) closed the AG numbering gap in `specs/governance.md`
by inserting AG-016..AG-018 entries. A self-review immediately after found that
the insertion landed *outside* the `## Agent Governance Rules` section, creating
a two-zone inconsistency. Separately, the user added AG-020 to `CLAUDE.md` on
the same date — this rule is not yet reflected in `specs/governance.md`,
`.claude_code_rules`, or its referenced runbook (`.claude/runbooks/self-review.md`).

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|:--------:|----------|
| GS-01 | AG-016..AG-019 landed outside `## Agent Governance Rules` in `specs/governance.md`; dangling `###` headings without parent `##` section | High | GS-01 |
| GS-02 | AG-020 (Self-Review After Every Task) exists in `CLAUDE.md` but is absent from `specs/governance.md` and `.claude_code_rules` | High | GS-02 |
| GS-03 | `.claude/runbooks/self-review.md` referenced in `CLAUDE.md` AG-020 block but file does not exist | High | GS-03 |
| GS-04 | No post-edit documentation verification protocol in `agents.md`; agents mark docs Done without re-reading the modified section | Medium | GS-04 |

---

## Execution Order

```
GS-03  (independent — creates runbook, no auth needed)
GS-04  (independent — edits agents.md, no auth needed)
GS-01  (requires user auth for specs/governance.md)
GS-02  (requires user auth for specs/governance.md + .claude_code_rules;
        depends on GS-01 so AG-019 position is stable before AG-020 is appended)
```

Recommended order: **GS-03 → GS-04 → GS-01 → GS-02**

---

## Status Summary

| Taskcard | Title | Status |
|----------|-------|--------|
| GS-01 | Fix `specs/governance.md` section structure | Done |
| GS-02 | Add AG-020 to `specs/governance.md` + `.claude_code_rules` | Done |
| GS-03 | Create `.claude/runbooks/self-review.md` | Done |
| GS-04 | Add doc-edit verification protocol to `agents.md` | Done |
