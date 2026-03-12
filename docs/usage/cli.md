# CLI Reference

All commands are invoked via the `launch` entry point installed by `pip install -e .`

```
launch <command> [options]
```

---

## launch run

Execute the full pipeline (or a subset of workers) for a pilot config.

```bash
launch run <config> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `config` | Yes | Path to pilot YAML config file |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--resume-from` | worker name | — | Start execution from this worker (requires `--run-id`) |
| `--stop-after` | worker name | — | Stop after this worker completes |
| `--run-id` | string | — | Existing run ID to resume (requires `--resume-from`) |
| `--dry-run` | flag | false | Validate config and print LLM info; do not execute |
| `--verbose` / `-v` | flag | false | Enable debug logging |

### Worker names (pipeline order)

`intake` → `understand` → `planner` → `generate` → `evaluate` → `publish`

### Constraints

- `--run-id` requires `--resume-from`. Providing `--run-id` without `--resume-from` exits with error.
- `--resume-from` must name a worker at or after the position of `--stop-after` — you cannot resume past where you stopped.

### Examples

```bash
# Full run
launch run configs/pilots/aspose-cells-foss-python.yaml

# Stop after understand to inspect before committing budget
launch run configs/pilots/aspose-cells-foss-python.yaml --stop-after understand

# Resume an existing run from generate
launch run configs/pilots/aspose-cells-foss-python.yaml \
  --resume-from generate \
  --run-id cells-python-20260308-a3f2b1

# Validate config without running
launch run configs/pilots/aspose-cells-foss-python.yaml --dry-run

# Debug run with verbose output
launch run configs/pilots/aspose-cells-foss-python.yaml -v
```

### Output

On success, prints a per-worker summary block followed by the run directory path
and final verdict. Example for the evaluate worker:

```
Worker: evaluate
  Verdict  : GO
  Grade    : A=2, B=6, C=7, D=2, F=1
  ab_rate  : 0.53 ✓ (threshold ≥0.50)
  df_rate  : 0.17 ✓ (threshold ≤0.30)
  critical : 0 ✓

Run dir: runs/cells-python-20260308-a3f2b1/
Verdict: GO
```

---

## launch validate

Validate a pilot config without running the pipeline.

```bash
launch validate <config>
```

### Output

```
Valid: cells/python tier=auto
Primary LLM : qwen3-next @ https://llm.professionalize.com/v1
Fallback LLM: gemma3:12b @ http://127.0.0.1:11434/v1
```

Exits 0 on valid config, 1 on invalid.

---

## launch intake

Discover and onboard GitHub repositories.

### launch intake scan

Scan GitHub organizations for public repositories.

```bash
launch intake scan [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--orgs` | string | from config | Comma-separated org names (overrides config) |
| `--config` | path | `configs/intake_config.yaml` | Intake config file |
| `--dry-run` | flag | false | Print results; do not write to intake/ |
| `--verbose` / `-v` | flag | false | Debug logging |

```bash
# Scan using intake_config.yaml
launch intake scan

# Override orgs on the command line
launch intake scan --orgs aspose-cells-foss,aspose-note-foss

# Dry run to check access and counts
launch intake scan --dry-run
```

### launch intake classify

Classify a single repository for pipeline eligibility.

```bash
launch intake classify --repo <url> [OPTIONS]
```

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--repo` | URL | Yes | GitHub repository URL |
| `--verbose` / `-v` | flag | No | Debug logging |

```bash
launch intake classify \
  --repo https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET
```

Output:
```
Verdict  : ELIGIBLE
Confidence: 0.94
Family   : cells
Platform : python
Reason   : Active FOSS library with 45 stars; Python bindings for Cells API
```

### launch intake generate

Generate a pilot config YAML for a single repository.

```bash
launch intake generate --repo <url> [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--repo` | URL | required | GitHub repository URL |
| `--output` | path | `configs/pilots` | Output directory |
| `--platform` | string | auto-detected | Override platform (python, java, dotnet, node) |
| `--verbose` / `-v` | flag | false | Debug logging |

```bash
launch intake generate \
  --repo https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET \
  --output configs/pilots
```

Output:
```
Generated: configs/pilots/aspose-cells-foss-python.yaml
```

### launch intake onboard

Complete intake workflow: scan → classify → generate in one command.

```bash
launch intake onboard [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--orgs` | string | from config | Comma-separated org names |
| `--config` | path | `configs/intake_config.yaml` | Intake config |
| `--batch-size` | int | 0 (all) | Max repos to process |
| `--output` | path | `configs/pilots` | Output directory |
| `--template` | path | — | Custom base template YAML |
| `--dry-run` | flag | false | Preview without writing |
| `--verbose` / `-v` | flag | false | Debug logging |

```bash
# Onboard up to 10 repos from all configured orgs
launch intake onboard --batch-size 10

# Dry run to preview what would be generated
launch intake onboard --dry-run
```

Output (summary table):
```
Metric             Count
─────────────────  ─────
Total scanned         42
Eligible              28
Needs review           5
Ineligible             9
Skipped (dedup)        0
Processed             28

Repo                                      Platform  Stars  Action
────────────────────────────────────────  ────────  ─────  ─────────
aspose-cells-foss/Aspose.Cells-for-…    python      150  GENERATED
aspose-note-foss/Aspose.Note-for-…      python       34  GENERATED
```

---

## launch deploy

Manage content promotion from run directories to the deploy target.

### launch deploy promote

Promote pages from a completed run to `deploy/`.

```bash
launch deploy promote <run_dir> [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `run_dir` | path | required | Path to the run directory |
| `--deploy-dir` | path | `deploy` | Deploy target directory |
| `--min-grade` | A/B/C/D/F | `C` | Minimum grade to promote |
| `--dry-run` | flag | false | Preview without writing |
| `--verbose` / `-v` | flag | false | Per-page detail |

```bash
# Promote all pages graded B or better
launch deploy promote runs/cells-python-20260308-a3f2b1 --min-grade B

# Preview what would be promoted
launch deploy promote runs/cells-python-20260308-a3f2b1 --dry-run
```

Output:
```
Run: cells-python-20260308-a3f2b1
Pages in run  : 18
Promoted      : 8
Skipped (< B) : 7
Skipped (same): 3
```

### launch deploy backfill

Promote from all completed runs for a family/platform pair.

```bash
launch deploy backfill [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--family` | string | required | Product family (e.g., `cells`) |
| `--platform` | string | required | Platform (e.g., `python`) |
| `--runs-root` | path | `runs` | Root containing run directories |
| `--deploy-dir` | path | `deploy` | Deploy target directory |
| `--min-grade` | A/B/C/D/F | `C` | Minimum grade |
| `--dry-run` | flag | false | Preview without writing |

```bash
launch deploy backfill --family cells --platform python --min-grade B
```

### launch deploy status

Show current deploy manifest summary.

```bash
launch deploy status [--deploy-dir <path>]
```

Output:
```
Deploy directory: deploy/
Total pages    : 127
Last promotion : 2026-03-08T15:42:33Z

Grade distribution:
  A:  5
  B: 23
  C: 56
  D: 28
  F: 15

Source runs: 7
```

### launch deploy diff

Preview what a run would contribute to the deploy directory (always read-only).

```bash
launch deploy diff <run_dir> [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `run_dir` | path | required | Run directory to diff |
| `--deploy-dir` | path | `deploy` | Deploy target |
| `--min-grade` | A/B/C/D/F | `C` | Minimum grade |

```bash
launch deploy diff runs/cells-python-20260308-a3f2b1 --min-grade B
```

Output:
```
8 page(s) would be promoted:
  [NEW B]       docs/aspose-cells-python/installation.md
  [UPGRADE C→B] docs/aspose-cells-python/getting-started.md
  [NEW B]       docs/aspose-cells-python/open-workbook.md
```

---

## launch heal

Iterative LLM-driven healing of pages that failed evaluation.

```bash
launch heal <run_dir> [OPTIONS]
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `run_dir` | path | required | Run directory to heal |
| `--mode` | str | `worker` | Execution mode: `full`, `worker`, or `diagnose` |
| `--max-steps` | int | 10 | Maximum heal iterations |
| `--min-confidence` | float | 0.6 | Minimum LLM confidence to accept a heal step |
| `--min-steps` | int | 1 | Minimum steps before early stopping |
| `--regression-threshold` | float | 0.05 | D+F rate increase that triggers quarantine |
| `--dry-run` | flag | false | Print HealDecision without executing |

### Execution modes

| Mode | Behaviour | When to use |
|------|-----------|-------------|
| `worker` *(default)* | Validates checkpoint integrity, then re-runs only the responsible worker + evaluate. Falls back to `full` if checkpoint hash is invalid. | Most sessions — fastest path to a quality improvement. |
| `full` | Re-runs the entire pipeline from the responsible worker through evaluate (never publish). Saves a rollback snapshot and restores it on regression. | When the checkpoint is stale or you need a clean re-run. |
| `diagnose` | Skips execution entirely. Writes `heal_diagnosis.json` with per-page action recommendations sorted by confidence. Exits with code 2 if failing pages remain. | CI pipelines, dry-run audits, or when you want a structured action plan before committing compute. |

```bash
# Heal a failed run (default: worker mode)
launch heal runs/cells-python-20260308-a3f2b1

# Diagnose without executing — writes heal_diagnosis.json
launch heal runs/cells-python-20260308-a3f2b1 --mode diagnose

# Full pipeline re-run with rollback protection
launch heal runs/cells-python-20260308-a3f2b1 --mode full

# Preview the LLM decision without executing
launch heal runs/cells-python-20260308-a3f2b1 --dry-run
```

Output:
```
[heal] Step 0: worker=generate, confidence=0.75, strategy=Regenerate failing sections
[heal] Step 1: worker=understand, confidence=0.82, strategy=Re-analyze API surface
[heal] Wrote heal_plan.json (2 steps, stop=llm_stop)
[heal] Session complete: 2 fixes, 0 regressions, stop=llm_stop
```

Produces in the run directory:
- `heal_plan.json` — full healing session log with per-step decisions and mode used
- `heal_quarantine.json` — heal steps that caused regressions (will not be retried)
- `heal_diagnosis.json` — structured action plan (diagnose mode only)
- `heal_rollback_{n}.json` — temporary rollback snapshots (removed after each step)

After healing, run `launch deploy promote` to promote any newly passing pages.
