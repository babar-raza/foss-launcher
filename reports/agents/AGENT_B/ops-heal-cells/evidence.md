# Agent B — ops-heal-cells: Evidence
<!-- Session: jiggly-puzzling-mccarthy | 2026-02-27 -->

## Commands Run

### Pre-flight
```bash
ls "$RUN/run.lock" 2>/dev/null && echo LOCKED || echo UNLOCKED  # → UNLOCKED
ls "$RUN/artifacts/validation_report.json"                       # → EXISTS
ls "$RUN/artifacts/heal_plan.json" 2>/dev/null || echo ABSENT   # → ABSENT
cp "$RUN/artifacts/validation_report.json" "$RUN/artifacts/validation_report.BEFORE_HEAL.json"  # → Snapshot saved
```

### Gate counts (before)
```python
Total gates: 41 | Failing: 3 | Errors: 14 | Warns: 213 | Profile: local
```

### Triage
```
41 total, 3 failed | 0 blocker, 14 error, 213 warn, 0 info
Recommendations: W2 > W5 > W10 > W8
```

### Dry-run
```
Step 0: would resume from W2 (Truth layer...) — dry-run
stop_reason: dry_run | exit_code: 0 | heal_plan.json written
```

### Live heal
```
Started: 2026-02-27T06:53:22Z
Step 0: W2 chosen → full pipeline W2→W11 ran (~30 min)
Completed: 2026-02-27T07:23:59Z
exit_code: 2 | gates_before=3, gates_after=3
stop_reason: stuck
```

### After gate counts
```python
Total gates: 41 | Failing: 3 | Errors: 9 | Warns: 257
Delta: 0 gates fixed at gate level; 5 errors removed; 44 new warns
```

### Post-heal triage
```
41 total, 3 failed | 0 blocker, 9 error, 257 warn, 0 info
Same 4 recommendations as before
```

## Artifact Pointers

| Artifact | Path |
|----------|------|
| heal_plan.json | `runs/r_20260226T220459Z.../artifacts/heal_plan.json` |
| Before snapshot | `runs/r_20260226T220459Z.../artifacts/validation_report.BEFORE_HEAL.json` |
| Evidence report | `reports/ops/heal_iteration_20260227_0723Z.md` |
| HEAL events | `runs/r_20260226T220459Z.../events.ndjson` (4 HEAL_* events) |
