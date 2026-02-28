# `launch heal` — Self-Driving Healing Iteration

## When to use

Use `launch heal` after a run has completed validation (W9) and `launch triage` shows
fixable failures. The heal command automates the triage → resume → validate loop,
converging toward green gates without manual intervention.

**Use heal when:**
- `launch triage` shows failures with clear recommended workers (W2, W5, W8, W10)
- You want hands-off convergence for known fixable patterns
- You want an audit trail of healing steps

**Do NOT use heal when:**
- The run has not yet reached W9 (use `launch run` or `launch phase` instead)
- Failures require manual investigation (e.g., config changes, missing repos)
- You need to modify run_config.yaml between steps

## Usage

```
launch heal <run_id> [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `run_id` | Run ID to heal (e.g., `r_20260226T120000Z_...`) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--run-dir PATH` | (from run_id) | Explicit run directory |
| `--max-steps N` | 5 | Maximum healing iterations |
| `--top N` | 3 | Number of triage recommendations to consider |
| `--dry-run` | false | Show planned steps without executing |
| `--mode MODE` | strict | Healing mode: `strict` or `aggressive` |
| `--verbose` | false | Increase logging verbosity |

### Modes

- **strict**: Follow the top-1 triage recommendation at each step. If it doesn't
  improve gate count, stop (stuck).

- **aggressive**: If the top recommendation doesn't help, try the next
  recommendation in the list. Continues until all top-K candidates are exhausted
  without improvement.

## Examples

### Basic usage
```bash
launch heal r_20260226T120000Z_launch_pilot-aspose-cells-foss-python_abc123
```

### With explicit run directory
```bash
launch heal dummy --run-dir runs/r_20260226T120000Z_.../
```

### Dry-run to preview
```bash
launch heal r_xxx --dry-run
```

### Aggressive mode with more recommendations
```bash
launch heal r_xxx --mode aggressive --top 5 --max-steps 10
```

### Example output

```
Starting heal loop: 3 failed gates, max 5 steps, mode=strict

Step 0: launch resume --run-dir runs/r_xxx --from-worker W10
  Reason: Scaffold/prompt leak or formatting issues (W10 auto-fixable)
  Failed gates before: 3
  Failed gates after: 1
  Improved: 3 → 1

Step 1: launch resume --run-dir runs/r_xxx --from-worker W8
  Reason: Cross-page link or patch issues
  Failed gates before: 1
  Failed gates after: 0
  Improved: 1 → 0

All gates pass! Healing complete.

Heal plan written to: runs/r_xxx/artifacts/heal_plan.json

Heal Summary:
  Steps taken:     2
  Stop reason:     all_gates_pass
  Failed gates:    0

Result: ALL GATES PASS
```

## Stop conditions

The heal loop stops when any of these conditions is met:

1. **all_gates_pass** — All gates pass. Exit code 0.
2. **stuck** — The same (worker, reason) was tried without reducing failed gate count.
3. **max_steps** — Maximum iterations reached.
4. **no_recommendation** — Triage has no specific fixable pattern (only W9 fallback).
5. **dry_run** — Planned step recorded without execution.
6. **resume_failed** — Resume execution raised an exception.

## Stuck cases

When the heal loop reports "stuck", it means:

- The recommended worker was tried, but the number of failed gates did not decrease
- This indicates the failures may not be auto-fixable by the recommended worker

**What to do when stuck:**
1. Run `launch triage <run_id>` to see the remaining issues
2. Check if failures are in gates that W10 cannot fix (e.g., hallucinated API,
   missing truth artifacts, duplication)
3. Consider manual fixes or running from an earlier worker (e.g., `launch resume --from-worker W5`)
4. Check `artifacts/heal_plan.json` for the full step history

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All gates pass |
| 1 | Stopped with remaining failures |

## Artifacts

### `artifacts/heal_plan.json`

Written after every heal run. Contains the complete audit trail:

```json
{
  "schema_version": "1.0",
  "run_id": "r_xxx",
  "mode": "strict",
  "max_steps": 5,
  "steps": [
    {
      "step_idx": 0,
      "chosen_worker": "W10",
      "reason": "Scaffold/prompt leak or formatting issues",
      "triage_snapshot": [...],
      "failed_gate_count_before": 3,
      "failed_gate_count_after": 1,
      "exit_code": 0,
      "notes": ""
    }
  ],
  "stop_reason": "all_gates_pass",
  "final_failed_gate_count": 0,
  "started_at_utc": "2026-02-27T12:00:00+00:00",
  "finished_at_utc": "2026-02-27T12:05:00+00:00"
}
```

### Events

The following events are appended to `events.ndjson`:

- `HEAL_STEP_STARTED` — emitted before each resume call
- `HEAL_STEP_COMPLETED` — emitted after each resume + re-validation
- `HEAL_STOPPED` — emitted when the loop terminates (with stop reason)

## Triage recommendation mapping

The heal command uses the triage recommendation engine to choose workers:

| Gate failure pattern | Recommended worker |
|---------------------|-------------------|
| Truth layer completeness | W2 |
| Code fence API validation | W5 |
| Scaffold leak / FQ-* formatting | W10 |
| Cross-page links / patches | W8 |
| No specific pattern | W9 (fallback, triggers no_recommendation stop) |

## TC-2950
