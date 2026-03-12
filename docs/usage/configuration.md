# Configuration Reference

All configuration files live in `configs/`. Pilot configs go in `configs/pilots/`.

---

## Config Resolution Order

When a pilot config is loaded, fields are merged in this precedence (highest first):

1. **Pilot config** (`configs/pilots/*.yaml`) — always wins
2. **LLM defaults** (`configs/llm_defaults.yaml`) — applied where pilot config is silent
3. **System defaults** — built-in fallbacks in the codebase

This means a minimal pilot config (5 fields) is valid: everything else is
inherited from `llm_defaults.yaml` and system defaults.

---

## Pilot Config (`configs/pilots/*.yaml`)

Schema: `specs/schemas/run_config.schema.json`

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `family` | string | Product family. Must be a key in `configs/families.yaml` (e.g., `cells`, `note`, `words`, `pdf`). |
| `platform` | string | Target platform: `python`, `java`, `dotnet`, or `node`. |
| `repo_url` | string | GitHub HTTPS clone URL, ending in `.git`. |
| `canonical_import` | string | Python/Java/etc. import path for the library (e.g., `aspose_cells_foss`). |
| `product_name` | string | Full display name (e.g., `"Aspose.Cells for Python via .NET"`). |

### Minimal pilot config

```yaml
family: cells
platform: python
repo_url: "https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET.git"
canonical_import: "aspose_cells_foss"
product_name: "Aspose.Cells for Python via .NET"
```

### Optional fields

#### `launch_tier`

```yaml
launch_tier: auto    # auto | full | core | minimal
```

Controls how many pages are generated:
- `auto` — determined from repo richness score (default)
- `full` — all mandatory + optional pages
- `core` — mandatory pages only
- `minimal` — essential pages only (installation + getting-started)

#### `display_name`

```yaml
display_name: "Aspose.Cells"   # Short name for headings (defaults to family display name)
```

#### `validation_profile`

```yaml
validation_profile: pilot    # pilot | local | strict
```

Validation profile controls gate severity escalations:
- `pilot` — standard gate configuration for real content
- `local` — relaxed gates for local development (default if not set)
- `strict` — maximum gate sensitivity for pre-release audits

**Always set `validation_profile: pilot` for real runs.** Omitting it defaults
to `local`, which has relaxed thresholds and will silently produce lower-quality gates.

#### `llm` section

```yaml
llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  reasoning:
    model: "recommended"          # Model for review/eval tasks
  routing:
    extract: standard             # standard | reasoning
    generate: standard
    review: reasoning
  temperature: 0.0                # Must be 0.0 for deterministic output
  max_tokens: 6000
  max_concurrency: 4              # Parallel LLM requests
```

If the `llm` section is omitted entirely, values are taken from `configs/llm_defaults.yaml`.

#### `seo` section

```yaml
seo:
  enabled: true
  keyword_research: true          # LLM-assisted keyword expansion
  offline_mode: false             # true = skip network SEO requests
  cache_ttl_days: 7               # How long SEO cache entries are valid
```

#### `skills` section

```yaml
skills:
  enabled: true
  path: "skills.md"               # Injected into generation and evaluation prompts
```

`skills.md` contains the content quality standards (prose rules, code requirements,
depth by page role). Enable for production runs; disable for fast local tests.

#### `output` section

```yaml
output:
  goal: draft                     # draft | pr
  run_dir: "runs/"                # Base directory for run artifacts
```

- `draft` — generates content files locally (default)
- `pr` — opens a GitHub pull request after the publish worker completes

#### `telemetry` section

```yaml
telemetry:
  endpoint_url: "http://127.0.0.1:8765"
  project: "foss-launcher"
```

Optional. When present, pipeline metrics are emitted to the telemetry API.

### Full annotated pilot config

```yaml
# Required fields
family: cells
platform: python
repo_url: "https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET.git"
canonical_import: "aspose_cells_foss"
product_name: "Aspose.Cells for Python via .NET"

# Optional identity fields
display_name: "Aspose.Cells"
launch_tier: auto
validation_profile: pilot

# LLM configuration (omit to use llm_defaults.yaml)
llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  temperature: 0.0
  max_tokens: 6000
  max_concurrency: 4

# Quality and SEO
skills:
  enabled: true
  path: "skills.md"

seo:
  enabled: true
  keyword_research: true
  offline_mode: false
  cache_ttl_days: 7

# Output
output:
  goal: draft
  run_dir: "runs/"
```

---

## LLM Defaults (`configs/llm_defaults.yaml`)

Applied to all pilot configs that do not explicitly set `llm.*` fields.
Pilot config values always override defaults.

```yaml
primary:
  base_url: "https://llm.professionalize.com/v1"
  model: "qwen3-next"

fallback:
  base_url: "http://127.0.0.1:11434/v1"
  model: "gemma3:12b"

temperature: 0.0          # Do not change — non-zero breaks determinism
max_tokens: 6000
max_concurrency: 4
api_key_env: "litellm_key"  # Environment variable name for the API key
request_timeout_s: 120
```

**Do not change `temperature`.** Non-zero temperature produces non-deterministic
output and breaks golden tests and checkpoint resumption.

Available models at `https://llm.professionalize.com/v1`:
- `qwen3-next` — standard generation (default, use for all tasks)
- `gpt-oss` — alternative standard model
- `recommended` — reasoning model (use for review/evaluation tasks only)
- `experimental` — unstable; do not use in production
- `qwen3-embedding-8b` — embedding model (used internally)
- `Qwen2.5-VL-7B` — vision model (used internally)

---

## Intake Config (`configs/intake_config.yaml`)

Used by `launch intake scan` and `launch intake onboard`.

```yaml
schema_version: "1.1"

# GitHub organizations to scan
organizations:
  - name: aspose-cells-foss
  - name: aspose-note-foss
  - name: groupdocs-free

scanner:
  per_page: 100               # Repos per GitHub API page (max 100)
  rate_limit_delay_s: 1.0     # Delay between paginated requests (seconds)
  activity_months: 12         # Repos with no commits in N months are skipped

classifier:
  min_stars: 0                # Minimum star count (0 = no filter)
  require_readme: true        # Skip repos with no README
  require_license: true       # Skip repos with no LICENSE file

scheduler:
  batch_size: 5               # Max repos per onboard run (0 = unlimited)
  sort_by: stars              # stars | name | updated
  sort_order: desc            # asc | desc

generator:
  output_dir: configs/pilots  # Where to write generated pilot YAML files
```

### Common intake config adjustments

| Goal | Field to change |
|------|----------------|
| Scan more repos before rate limiting | Increase `rate_limit_delay_s` |
| Only well-maintained repos | Set `activity_months: 6` |
| Only popular repos | Set `min_stars: 10` |
| Faster batch onboarding | Set `scheduler.batch_size: 20` |

---

## Families Taxonomy (`configs/families.yaml`)

Defines all supported product families and platforms. Used to derive
`display_name`, `canonical_import`, and other identity fields in pilot configs.

```yaml
families:
  cells:
    display: "Aspose.Cells"
    category: "spreadsheet processing"
  note:
    display: "Aspose.Note"
    category: "digital notebook processing"
  words:
    display: "Aspose.Words"
    category: "word processing"
  pdf:
    display: "Aspose.PDF"
    category: "PDF processing"
  slides:
    display: "Aspose.Slides"
    category: "presentation processing"
  # ... 20+ more families

platforms:
  - python
  - java
  - dotnet
  - node
```

The `family` field in a pilot config must be a key in this file.
Use `launch validate <config>` to catch invalid family names before running.

---

## Run Directory Structure

After a successful run, artifacts are in `runs/<run-id>/`:

| File | Contents |
|------|----------|
| `intake_checkpoint.json` | Repo metadata, SHA, tier, file index |
| `understand_checkpoint.json` | Claims, page plan, API surface |
| `planner_checkpoint.json` | Page plan with slugs and roles |
| `generate_checkpoint.json` | Generated section bodies |
| `evaluate_checkpoint.json` | Gate results, grades, verdict |
| `publish_checkpoint.json` | PR URL, patch list |
| `evaluation_report.json` | Final verdict + per-page grades + go_criteria |
| `pipeline_metrics.json` | Timing, LLM call counts, token usage |
| `events.ndjson` | Full structured event log (one JSON per line) |
| `heal_plan.json` | Healing session log (present only if `launch heal` was run) |
| `heal_quarantine.json` | Quarantined heal steps (present only if `launch heal` was run) |
