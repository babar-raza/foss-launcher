# DM-00 — Documentation Maintenance Healing Gap Index

## Context

AG-019 and its supporting infrastructure (`check_doc_freshness.py`, updated
`skills.md`, `TC-000_TEMPLATE.md`, `agents.md`, `.claude_code_rules`,
`specs/governance.md`) were implemented on 2026-03-08 as a first iteration.
A self-review immediately after delivery identified 10 gaps spanning
correctness, robustness, coverage, consistency, and testability.

These gaps are tracked here. Each gap is linked to exactly one taskcard.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|:--------:|----------|
| GR-01 | `--tc` flag documented in script docstring but not implemented in argparser — broken interface contract | High | DM-01 |
| GR-02 | No repo-root detection — script breaks silently when run from any subdirectory | High | DM-01 |
| GR-06 | `--since HEAD` produces empty diff → false-clean exit 0; silent failure | High | DM-01 |
| GR-10 | `matches_pattern` dual-path logic (fnmatch + startswith fallback) is fragile and undocumented | Medium | DM-01 |
| GR-03 | `CODE_TO_SPEC` covers only ~40% of codebase; `shared/**`, `clients/**`, `state/**`, `resilience/**`, `provenance/**`, `cli/**` have no mapping → false-clean exits for most real changes | High | DM-02 |
| GR-07 | `skills.md` TECHNICAL DOCUMENTATION STANDARDS section has no retroactive-scope disclaimer; agents may treat it as an immediate audit requirement on all existing files | Medium | DM-02 |
| GR-04 | `CLAUDE.md` still references AG-001..AG-018 after AG-019 was added | Medium | DM-03 |
| GR-08 | `specs/governance.md` goes from AG-015 to AG-019 with no entries for AG-016..AG-018; numbering gap is unexplained and confusing | Medium | DM-03 |
| GR-05 | `check_doc_freshness.py` has zero unit tests; `matches_pattern` and drift logic are untested | High | DM-04 |
| GR-09 | No JSON output mode; output is human-only, blocking programmatic/CI use | Low | DM-05 |

---

## Execution Order

```
DM-01  (script hardening — prerequisite for DM-04 and DM-05)
  │
  ├── DM-02  (independent of DM-01 — touches script + skills.md)
  │          (but applying CODE_TO_SPEC additions to DM-01's output is cleaner)
  │
  ├── DM-03  (independent — governance files only)
  │
  ├── DM-04  (depends on DM-01 being Done — tests the hardened script)
  │
  └── DM-05  (depends on DM-01 being Done — extends the hardened script)
```

Recommended serial order: **DM-01 → DM-02 → DM-04 → DM-05 → DM-03**
(DM-03 requires user authorization for protected files; run it when auth is available.)

---

## Status Summary

| Taskcard | Title | Status |
|----------|-------|--------|
| DM-01 | Harden `check_doc_freshness.py` | Done |
| DM-02 | Expand `CODE_TO_SPEC` + scope disclaimer | Done |
| DM-03 | Fix governance documentation consistency | Done |
| DM-04 | Add unit tests for `check_doc_freshness.py` | Done |
| DM-05 | Add JSON output mode to `check_doc_freshness.py` | Done |
