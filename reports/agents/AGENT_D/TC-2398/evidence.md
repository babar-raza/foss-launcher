# TC-2398 Evidence: Spec 43 — Resumable Pipeline Execution

## Files Created/Modified

| File | Action | Size |
|---|---|---|
| `specs/43_resumable_pipeline.md` | Created | ~3.5 KB |
| `plans/taskcards/TC-2398_spec_43_resumable_pipeline_execution.md` | Created | ~3.2 KB |
| `plans/taskcards/INDEX.md` | Updated | Added 2 entries |

## Spec Verification

```
specs/43_resumable_pipeline.md
  Status: Binding ✅
  Version: v1.0 ✅
  Short aliases documented: W1–W11 (11 entries) ✅
  Full node names documented: 11 entries ✅
  Artifact pre-validation table: 11 rows ✅
  RUN_RESUMED event JSON schema: present ✅
  Governance section: local vs prod profile rules ✅
  Exit code table: 6 cases covered ✅
  run_pilot.py integration: described ✅
  Determinism warning: present ✅
```

## INDEX.md Update

```
## Resumable Pipeline Execution (2026-02-21)
- TC-2398 — Spec 43: Resumable Pipeline Execution (AGENT_D, P0, no deps) — Done
- TC-2399 — Implement `launch resume` command with dynamic graph entry point (AGENT_B, P1, depends: TC-2398) — In-Progress
```

## Acceptance Checks

- [x] `specs/43_resumable_pipeline.md` exists and is ≥1000 bytes
- [x] Spec status line reads "**Status**: Binding"
- [x] All 22 aliases documented (11 short + 11 full node names)
- [x] INDEX.md contains "TC-2398" and "TC-2399" entries
- [x] No code files modified
