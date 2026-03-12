# Quickstart

Get foss-launcher v2 running and producing your first content in under 10 minutes.

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Check: `python --version` |
| git | Must be on PATH |
| `GITHUB_TOKEN` | Personal access token with `read:org` + `read:repo` scopes. Required for intake scan; optional for running a known repo URL directly. |
| `litellm_key` | API key for the LLM endpoint. Required for all pipeline runs. |

Set environment variables before running any `launch` command:

```bash
export GITHUB_TOKEN="ghp_..."
export litellm_key="sk-..."
```

On Windows PowerShell:
```powershell
$env:GITHUB_TOKEN = "ghp_..."
$env:litellm_key  = "sk-..."
```

---

## Install

```bash
git clone https://github.com/your-org/foss-launcher-v2.git
cd foss-launcher-v2

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

Verify:
```bash
launch --help
```

You should see the top-level help with `run`, `validate`, `intake`, `deploy`, and `heal` commands listed.

---

## Configure: Minimal Pilot YAML

A pilot config tells the pipeline which repository to process and who it is.
Create `configs/pilots/my-first-run.yaml` with these five required fields:

```yaml
family: cells
platform: python
repo_url: "https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET"
canonical_import: "aspose_cells_foss"
product_name: "Aspose.Cells for Python via .NET"
```

Replace with your target repository. `family` must be one of the keys in
`configs/families.yaml` (e.g., `cells`, `note`, `words`, `pdf`, `slides`).

LLM endpoint and other settings are auto-applied from `configs/llm_defaults.yaml`.
No further configuration is needed to start.

Validate the config before running:
```bash
launch validate configs/pilots/my-first-run.yaml
```

Expected output:
```
Valid: cells/python tier=auto
Primary LLM : qwen3-next @ https://llm.professionalize.com/v1
Fallback LLM: gemma3:12b @ http://127.0.0.1:11434/v1
```

---

## First Run: Stop After Understand

Do not commit your full LLM budget until you have verified the pipeline can
read and understand the repository. Run with `--stop-after understand` first.

```bash
launch run configs/pilots/my-first-run.yaml --stop-after understand
```

This runs the `intake` and `understand` workers only, then stops.
A run ID is printed at the start — note it for later:

```
Run ID: cells-python-20260308-a3f2b1
Run dir: runs/cells-python-20260308-a3f2b1/
```

### Reading the understand output

```
Worker: understand
  Richness tier  : high (score: 0.82)
  Claims         : 47 extracted
  Code snippets  : 12
  Pages planned  : 18 (14 mandatory, 4 optional)
  API surface    : 8 public classes
  Files read     : 23 (148 KB)
```

| Field | What it means |
|-------|--------------|
| Richness tier | `high`/`medium`/`low` — quality of source material. Low = thin content warning. |
| Claims | Facts extracted from the repo. Fewer than 10 suggests the repo README is sparse. |
| Pages planned | How many content pages will be generated. |
| Mandatory | Pages the ruleset requires for this family/platform. |
| Optional | Pages included based on available content. |

If claims < 10 or richness is `low`, check that the repo has a substantial README
and that `canonical_import` is correct. See `docs/guides/ops-debug.md` for diagnostics.

---

## Full Run

Once the understand output looks good, run the full pipeline:

```bash
launch run configs/pilots/my-first-run.yaml \
  --resume-from generate \
  --run-id cells-python-20260308-a3f2b1
```

Or start fresh without the stop:

```bash
launch run configs/pilots/my-first-run.yaml
```

### Reading the final output

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

A `GO` verdict means content quality meets the publication threshold.
A `NO-GO` verdict means the pipeline attempted re-generation but did not
reach the threshold. See `docs/usage/workflows.md#healing-a-no-go-run` for next steps.

---

## Next Steps

| Goal | Where to go |
|------|-------------|
| Deploy content after a GO verdict | `docs/usage/workflows.md` — Deploying content |
| Understand all CLI flags | `docs/usage/cli.md` |
| Configure LLM or SEO options | `docs/usage/configuration.md` |
| Onboard multiple repos at once | `docs/usage/workflows.md` — Batch onboarding |
| Fix a NO-GO run | `docs/usage/workflows.md` — Healing a NO-GO run |
| Debug a failed run | `docs/guides/ops-debug.md` |
