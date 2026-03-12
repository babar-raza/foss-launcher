---
id: TC-3906-gap-index
title: "TC-3906 Self-Review Healing — Snapshot IR Store"
status: Active
updated: "2026-03-09"
source: self-review of TC-3906 implementation
---

# TC-3906 Healing Gap Index

Self-review of TC-3906 (`snapshots/` IR Store + `phase_store/` + `ir_regenerate`) identified
7 gaps ranging from a silent correctness bug to missing test coverage. All gaps have been
converted to executable taskcards below.

---

## Gap Table

| Gap ID | Severity | Description | Taskcard |
|--------|----------|-------------|----------|
| G-3906-01 | Critical | Majority tracking compares per-call count vs cumulative — silent wrong winner in backfill | TC-3906-H1 |
| G-3906-02 | Critical | Zero new tests — no coverage for snapshot_manifest, phase_promoter, ir_regenerate | TC-3906-H2 |
| G-3906-03 | High | `phase_promoter.py` imports `_grade_ge` (private symbol) from `promoter.py` | TC-3906-H3 |
| G-3906-04 | High | `shutil.copy2` in `_update_phase_store` is non-atomic; `_PHASE_FILES` duplicates RunLayout | TC-3906-H4 |
| G-3906-05 | High | `project_root = deploy_dir.parent` is fragile; `schema_path` is relative to CWD | TC-3906-H5 |
| G-3906-06 | Medium | Dead `_NON_IR_NAMES` frozenset; `_auto_promote_phase_snapshots` bloats `promoter.py` by 50 lines | TC-3906-H6 |
| G-3906-07 | Medium | Snapshot promotion emits nothing to `events.ndjson` — invisible to audit trail | TC-3906-H7 |

---

## Priority order

1. **TC-3906-H1** — correctness bug, silent wrong behavior in production
2. **TC-3906-H2** — no tests means nothing is verified
3. **TC-3906-H3** + **TC-3906-H4** + **TC-3906-H5** — hardening (can be batched)
4. **TC-3906-H6** — code hygiene
5. **TC-3906-H7** — observability (lowest risk to defer)

## Dependencies

```
TC-3906-H1 (fix manifest model) ← TC-3906-H2 tests depend on corrected model
TC-3906-H3 (public grade_ge)    ← TC-3906-H4 may import same symbol
TC-3906-H5 (schema_path)        ← TC-3906-H2 tests need schema resolvable from tmp_path
```
