# TC-3911 Verification Gaps — Healing Plan Index

**Source**: Self-review of the TC-3911 pilot verification response (2026-03-09)
**Scope**: Only `plans/healing/` files may be created/modified by this healing plan.
**Code changes** are executed in subsequent taskcards that own their own allowed_paths.

---

## Context

TC-3911 deleted 7 orphaned files/packages. A smoke-test pilot was run but
stopped at `--stop-after understand` (2 of 6 workers). The self-review identified
5 gaps that leave the verification incomplete and the conclusion overstated.

---

## Gap Table

| Gap ID | Description | Severity | Taskcard |
|--------|-------------|----------|----------|
| GAP-01 | `evaluate` worker (and planner/generate/publish) never exercised at runtime | Critical | TC3911-VER-01 |
| GAP-02 | Smoke import + negative deletion assertions not run (taskcard AC-2, AC-3 skipped) | High | TC3911-VER-02 |
| GAP-03 | Only 1 of 5 pilots tested; cross-pilot coverage not explicitly verified | Medium | TC3911-VER-01 |
| GAP-04 | Prompt-path warning dismissed as "pre-existing" without baseline evidence | Medium | TC3911-VER-01 |
| GAP-05 | Evidence bundle (`reports/TC-3911/evidence.md`) never created | Medium | TC3911-VER-03 |

---

## Taskcards in This Healing Plan

| Taskcard | File | Fixes |
|----------|------|-------|
| TC3911-VER-01 | `TC3911-VER-01-evaluate-pipeline-run.md` | GAP-01, GAP-03, GAP-04 |
| TC3911-VER-02 | `TC3911-VER-02-deletion-assertions.md` | GAP-02 |
| TC3911-VER-03 | `TC3911-VER-03-evidence-bundle.md` | GAP-05 |
