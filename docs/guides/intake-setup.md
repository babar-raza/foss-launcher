# Intake Setup Walkthrough

Use this guide to onboard a new GitHub organization or repository from scratch:
authoring `intake_config.yaml`, running the scan and classify steps, generating
a pilot config, and executing the first pipeline run.

For the intake worker specification, see `specs/github_intake.md`.
For the intake config schema, see `specs/schemas/intake_config.schema.json`.

---

## Prerequisites

### Environment variables

```bash
export GITHUB_TOKEN="ghp_..."     # Required: read:org + read:repo scopes
export litellm_key="sk-..."       # Required: used by LLM-assisted classification
```

`GITHUB_TOKEN` without `read:org` will produce "Not Found" errors during org scanning.
`litellm_key` is needed only for the `classify` step — `scan` and `generate` are deterministic.

### Python environment

```bash
.venv/Scripts/python.exe -c "import launcher; print('OK')"
```

If this fails, run `pip install -e .` from the repo root.

---

## Step 1 — Author intake_config.yaml

Create or edit `configs/intake_config.yaml`. Minimum required fields:

```yaml
# configs/intake_config.yaml (annotated minimal example)

scanner:
  orgs:
    - aspose-free          # GitHub org name (not URL)
    - groupdocs-free       # Add as many orgs as needed
  max_repos_per_org: 50    # Limit to avoid rate-limit exhaustion on first scan
  include_forks: false     # Usually false; forks are rarely FOSS targets
  min_stars: 5             # Skip repos with < N stars (noise filter)

classifier:
  model: qwen3-next        # LLM model for classification — use qwen3-next
  temperature: 0.0         # Always 0.0 for deterministic classification
  eligibility_threshold: 0.7  # Confidence threshold for ELIGIBLE verdict

generator:
  output_dir: configs/pilots   # Where to write generated pilot YAML files
  family_map: configs/families.yaml  # Product family definitions
  default_platform: python     # Default platform if not inferred from repo
```

Full field reference: `specs/schemas/intake_config.schema.json`

### Key design decisions

- **`max_repos_per_org`**: Start low (20–50). You can always scan more once the
  first batch is clean. A large scan on first run hits GitHub's rate limit quickly.
- **`min_stars`**: Filters out abandoned forks and test repos. 5 is a safe default.
- **`eligibility_threshold`**: 0.7 means the classifier must be ≥70% confident a
  repo is a genuine FOSS library worth documenting. Lower values increase false positives.

---

## Step 2 — Dry-Run Scan

Always dry-run first to verify org access and get a count estimate.

```bash
.venv/Scripts/python.exe -m launcher.cli.intake scan \
    --config configs/intake_config.yaml \
    --dry-run
```

Expected output:
```
Scanning org: aspose-free ... 47 repos found
Scanning org: groupdocs-free ... 31 repos found
Total eligible for classification: 78
Rate limit remaining: 4821/5000
Output would write to: intake/scan_<date>.json
```

If you see `404 Not Found` for an org, check that `GITHUB_TOKEN` has `read:org`
scope and that the org name is spelled correctly.

### Running the real scan

```bash
.venv/Scripts/python.exe -m launcher.cli.intake scan \
    --config configs/intake_config.yaml
```

Output is written to `intake/scan_<date>.json`. The scan is deterministic and
can be re-run without side effects (it does not modify any repo).

---

## Step 3 — Classify Repos

Classify turns the raw scan list into ELIGIBLE / INELIGIBLE / NEEDS_REVIEW verdicts.

```bash
.venv/Scripts/python.exe -m launcher.cli.intake classify \
    --config configs/intake_config.yaml \
    --scan-file intake/scan_<date>.json
```

Output: `intake/classified_<date>.json`

### Reading classify output

```json
{
  "repo": "aspose-free/Aspose.Cells-for-Python-via-.NET",
  "verdict": "ELIGIBLE",
  "confidence": 0.94,
  "family": "cells",
  "platform": "python",
  "reason": "Active FOSS library with 45 stars; Python bindings for Cells API"
}
```

`NEEDS_REVIEW` means confidence was between threshold and threshold-0.2.
These require a human decision. Add them manually to the batch after review:

```bash
# Promote a NEEDS_REVIEW repo to ELIGIBLE manually
.venv/Scripts/python.exe -m launcher.cli.intake promote \
    --repo "aspose-free/Aspose.Cells-for-Python-via-.NET" \
    --classified-file intake/classified_<date>.json
```

---

## Step 4 — Generate Pilot Config

Convert classified ELIGIBLE repos into pilot run configs.

```bash
.venv/Scripts/python.exe -m launcher.cli.intake generate \
    --config configs/intake_config.yaml \
    --classified-file intake/classified_<date>.json
```

Each eligible repo produces a YAML file in `configs/pilots/`:
```
configs/pilots/
  aspose-cells-foss-python.yaml
  aspose-words-foss-python.yaml
  ...
```

### What to manually verify before running the pipeline

Open each generated pilot YAML and check:

```yaml
# Must be the actual GitHub SSH/HTTPS clone URL, not the web URL
repo_url: https://github.com/aspose-free/Aspose.Cells-for-Python-via-.NET.git

# Must match a key in configs/families.yaml
family: cells

# Must be one of: python, java, dotnet, node
platform: python

# Should be the FOSS repo's primary branch
branch: main

# Check that the run_id prefix is readable and unique
run_id_prefix: cells-python
```

Common generation errors to catch:
- `repo_url` missing `.git` suffix (clone will fail)
- `family` set to `unknown` (classifier was uncertain — set manually)
- `branch` set to `master` when repo uses `main` (check GitHub)

---

## Step 5 — First Pipeline Run (Stop After Understand)

Do not commit your full content budget until you have inspected the
`understand` worker output. Use `--stop-after understand` for the first run.

```bash
.venv/Scripts/python.exe -m launcher.cli.main run \
    configs/pilots/aspose-cells-foss-python.yaml \
    --stop-after understand
```

The run ID is printed at start: `Run ID: cells-python-20240315-a3f2b1`

### Inspecting the understand checkpoint

```bash
cat runs/cells-python-20240315-a3f2b1/understand_checkpoint.json | python -c "
import json, sys
d = json.load(sys.stdin)
claims = d.get('claims', [])
print(f'Claims extracted: {len(claims)}')
for c in claims[:5]:
    print(' -', c.get('text','')[:80])
pages = d.get('page_plan', {}).get('pages', [])
print(f'Pages planned: {len(pages)}')
for p in pages[:5]:
    print(' -', p.get('role',''), p.get('slug',''))
"
```

Quality signals to check before proceeding:
- At least 10 claims extracted (fewer suggests README is too sparse)
- Page plan includes a mix of roles (`howto_article`, `installation`, `getting_started`)
- No `unknown` family or platform in the bundle
- `understanding_bundle.schema.json` validation passes (the worker validates on write)

If the checkpoint looks wrong, fix the run config or intake config and re-run.
Do not resume into `generate` with bad `understand` output.

### Continuing the full run

```bash
.venv/Scripts/python.exe -m launcher.cli.main run \
    configs/pilots/aspose-cells-foss-python.yaml \
    --resume-from generate \
    --run-id cells-python-20240315-a3f2b1
```

---

## Step 6 — Common First-Run Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| `CONFIG_INVALID` on startup | Missing required field in pilot YAML | Add the field; check `specs/schemas/run_config.schema.json` |
| `git clone` fails | `repo_url` is wrong or private | Verify URL and that `GITHUB_TOKEN` has `read:repo` scope |
| 0 claims extracted | Repo has no README or all content is binary | Set `min_content_score: 0` temporarily to inspect what scout found |
| `SCHEMA_MISMATCH` on understand output | Mismatched schema version after config change | Delete checkpoint and re-run from the start |
| `LLM_TIMEOUT` in classify | `litellm_key` expired or endpoint unreachable | Refresh key; check `https://llm.professionalize.com/v1` reachability |
| `family: unknown` in generated pilot | Classifier uncertain | Set family manually in the pilot YAML |

---

## Step 7 — Batch Onboarding

Once a single pilot is clean, onboard a full batch:

```bash
.venv/Scripts/python.exe -m launcher.cli.intake onboard \
    --config configs/intake_config.yaml \
    --classified-file intake/classified_<date>.json \
    --batch-size 5 \
    --parallel 2
```

`--batch-size 5` runs 5 repos; `--parallel 2` runs 2 pipelines concurrently.

Output: `intake/batch_report_<date>.json`

```json
{
  "total": 5,
  "success": 4,
  "failed": 1,
  "failures": [
    {
      "repo": "aspose-free/Aspose.Words-for-Python-via-.NET",
      "error": "RERUN_LIMIT",
      "run_id": "words-python-20240315-x9y2z1"
    }
  ]
}
```

Failed runs must be investigated individually using `docs/guides/ops-debug.md`.
Do not re-queue failed runs without understanding the failure.
