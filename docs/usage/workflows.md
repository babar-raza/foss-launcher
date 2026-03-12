# Workflows

Step-by-step recipes for common operator scenarios.
For flag details see `docs/usage/cli.md`. For config options see `docs/usage/configuration.md`.

---

## 1. New Repo — First Run

Use this when you have a GitHub repository and want to generate documentation for it.

```bash
# Step 1: Set required environment variables
export GITHUB_TOKEN="ghp_..."
export litellm_key="sk-..."

# Step 2: Create a pilot config
cat > configs/pilots/my-repo.yaml << 'EOF'
family: cells
platform: python
repo_url: "https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET.git"
canonical_import: "aspose_cells_foss"
product_name: "Aspose.Cells for Python via .NET"
validation_profile: pilot
EOF

# Step 3: Validate the config
launch validate configs/pilots/my-repo.yaml

# Step 4: Run through understand only first (free check)
launch run configs/pilots/my-repo.yaml --stop-after understand
# Note the run ID printed at start: e.g., cells-python-20260308-a3f2b1

# Step 5: Inspect the understand output
#   - Claims >= 10? Good.
#   - Richness tier = high or medium? Good.
#   - Pages planned >= 5? Good.
# If all look good, continue:

# Step 6: Full run resuming from generate
launch run configs/pilots/my-repo.yaml \
  --resume-from generate \
  --run-id cells-python-20260308-a3f2b1

# Step 7: Check the verdict
#   Verdict: GO  → proceed to deploy
#   Verdict: NO-GO → see "Healing a NO-GO run" below
```

**Expected duration**: 5–15 minutes depending on repo size and LLM speed.
**LLM call budget**: ~150–200 calls, ~150–700 tokens each.

---

## 2. Batch Onboarding

Use this when you want to discover and process multiple repos from a GitHub organization.

```bash
# Step 1: Configure orgs in intake_config.yaml
#   (or override on the command line with --orgs)

# Step 2: Dry run to preview what would be discovered
launch intake onboard \
  --orgs aspose-cells-foss,aspose-note-foss \
  --batch-size 5 \
  --dry-run

# Step 3: Run the real onboard to generate pilot configs
launch intake onboard \
  --orgs aspose-cells-foss,aspose-note-foss \
  --batch-size 5 \
  --output configs/pilots

# Step 4: Review generated configs before running
ls configs/pilots/
# Verify family, platform, and repo_url in each generated file

# Step 5: Run the pipeline for each generated config
for config in configs/pilots/*.yaml; do
  echo "Running: $config"
  launch run "$config"
done
```

To run a subset and check results before committing:
```bash
# Run one, check verdict, then continue
launch run configs/pilots/aspose-cells-foss-python.yaml
launch run configs/pilots/aspose-note-foss-python.yaml
```

---

## 3. Iterative Improvement

Use this when you want to inspect and tune intermediate worker output before
continuing to the next stage.

```bash
# Run through understand only
launch run configs/pilots/my-repo.yaml --stop-after understand
# Run ID: cells-python-20260308-a3f2b1

# Inspect the understand checkpoint
cat runs/cells-python-20260308-a3f2b1/understand_checkpoint.json | python -c "
import json, sys
d = json.load(sys.stdin)
print('Claims:', len(d.get('claims', [])))
for p in d.get('page_plan', {}).get('pages', [])[:5]:
    print(' -', p.get('role'), p.get('slug'))"

# Optional: edit the checkpoint to adjust the page plan
#   (add/remove pages, adjust roles, fix slug)
# Edit: runs/cells-python-20260308-a3f2b1/understand_checkpoint.json

# Resume from planner (will use edited understand checkpoint)
launch run configs/pilots/my-repo.yaml \
  --resume-from planner \
  --run-id cells-python-20260308-a3f2b1

# Inspect generate output
launch run configs/pilots/my-repo.yaml \
  --resume-from generate \
  --stop-after generate \
  --run-id cells-python-20260308-a3f2b1

# When satisfied, run evaluate + publish
launch run configs/pilots/my-repo.yaml \
  --resume-from evaluate \
  --run-id cells-python-20260308-a3f2b1
```

**Note**: When you manually edit a checkpoint, the run_loop logs a hash-mismatch
warning. This is expected and does not block execution.

---

## 4. Healing a NO-GO Run

Use this when `launch run` finishes with `Verdict: NO-GO` and the automatic
re-run cycle (up to 2 attempts) did not reach the GO threshold.

**Choose a mode first:**

| Situation | Recommended mode |
|-----------|-----------------|
| First attempt, checkpoints are intact | `--mode worker` (default) |
| Checkpoint stale or content changed since run | `--mode full` |
| Want a plan before committing compute (CI, audit) | `--mode diagnose` |

```bash
# Step 1: Read the diagnosis
python -c "
import json
r = json.load(open('runs/cells-python-20260308-a3f2b1/evaluation_report.json'))
print('Verdict:', r['verdict'])
d = r.get('root_cause_diagnosis', {})
print('Worker :', d.get('responsible_worker'))
print('Issue  :', d.get('primary_issue'))
print('Fix    :', d.get('recommended_fix'))
"

# Step 2a (recommended): targeted worker re-run
launch heal runs/cells-python-20260308-a3f2b1

# Step 2b: get a structured action plan without executing
launch heal runs/cells-python-20260308-a3f2b1 --mode diagnose
# → writes heal_diagnosis.json; exits with code 2 if still failing

# Step 2c: full re-run with rollback protection (use when checkpoints stale)
launch heal runs/cells-python-20260308-a3f2b1 --mode full

# Step 3: Check heal output
#   [heal] Session complete: N fixes, M regressions, stop=...

# Step 4: If heal improved things, promote what's now passing
launch deploy promote runs/cells-python-20260308-a3f2b1 --min-grade C

# If NO-GO persists after heal, the issue is structural (not retryable).
# Follow the root_cause_diagnosis recommendation to make a code fix,
# then run a fresh pipeline with a new run ID.
```

**When to give up on healing and start fresh**:
- `heal_quarantine.json` contains every strategy that was tried
- `root_cause_diagnosis.primary_issue` points to a code change needed
- `max_re_runs` was exhausted before heal was run

In those cases: make the code fix (create a taskcard per AG-002 if touching
protected paths), then run `launch run configs/pilots/my-repo.yaml` fresh.

---

## 5. Deploying Content

Use this after a GO verdict to promote pages to the deploy directory.

```bash
# Step 1: Preview what would be promoted
launch deploy diff runs/cells-python-20260308-a3f2b1 --min-grade B

# Step 2: Promote pages graded B or better
launch deploy promote runs/cells-python-20260308-a3f2b1 --min-grade B

# Step 3: Check deploy status
launch deploy status

# Step 4: If you want to backfill from all historical runs for a family
launch deploy backfill --family cells --platform python --min-grade B

# Step 5: Preview backfill before running it
launch deploy backfill --family cells --platform python --dry-run
```

### Grade selection guidance

| Min grade | Effect |
|-----------|--------|
| `A` | Only exceptional pages (very selective) |
| `B` | High-quality pages (recommended for production) |
| `C` | Acceptable pages (default; includes work-in-progress) |
| `D` | Marginal pages (not recommended for public) |

For production deployment, use `--min-grade B`. Default (`C`) is appropriate
for staging or internal review.

---

## 6. Validating a Config Without Running

Use this before your first run or after editing a pilot config to catch errors
before spending LLM budget.

```bash
# Validate a single config
launch validate configs/pilots/my-repo.yaml

# Validate all pilot configs
for config in configs/pilots/*.yaml; do
  echo -n "$config: "
  launch validate "$config" && echo "OK" || echo "INVALID"
done
```

Exit code 0 = valid. Exit code 1 = invalid (error message printed).

---

## 7. Inspecting a Run After Completion

```bash
# Quick verdict check
python -c "
import json
r = json.load(open('runs/<run-id>/evaluation_report.json'))
print('Verdict:', r['verdict'])
for k, v in r['go_criteria'].items():
    status = '✓' if v['passed'] else '✗'
    print(f'  {status} {k}: {v[\"value\"]:.2f} (threshold {v[\"threshold\"]})')"

# Show grade distribution
python -c "
import json
r = json.load(open('runs/<run-id>/evaluation_report.json'))
agg = r['quality']['aggregate']
for grade in 'ABCDF':
    print(f'  {grade}: {agg.get(grade, 0)}')"

# Show event log summary (last 20 events)
python -c "
import sys, json
lines = open('runs/<run-id>/events.ndjson').readlines()
for line in lines[-20:]:
    e = json.loads(line)
    print(e.get('type'), e.get('worker',''), e.get('status',''))"

# Show pipeline timing
python -c "
import json
m = json.load(open('runs/<run-id>/pipeline_metrics.json'))
for worker, metrics in m.items():
    print(f'{worker}: {metrics.get(\"duration_s\", 0):.1f}s')"
```

---

## Common Issues

| Symptom | Likely cause | Quick fix |
|---------|-------------|-----------|
| `launch: command not found` | Not installed or venv not active | `pip install -e .` then activate venv |
| `CONFIG_INVALID` on startup | Missing required field in pilot YAML | Run `launch validate <config>` for details |
| `LLM_TIMEOUT` in events | LLM endpoint unreachable | Check `litellm_key`; verify endpoint at `configs/llm_defaults.yaml` |
| 0 claims extracted | Sparse or private repo | Verify `GITHUB_TOKEN` has `read:repo`; check README quality |
| `Verdict: NO-GO` after 2 re-runs | Structural content issue | Run `launch heal`; if still NO-GO, read `root_cause_diagnosis` |
| `SCHEMA_VERSION_MISMATCH` on resume | Edited checkpoint incompatibly | Update `engine_version` in checkpoint or start fresh run |
