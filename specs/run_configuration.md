# Run Configuration

This document defines the RunConfig schema, field purposes, default values,
LLM endpoint configuration, and validation rules. The authoritative schema
is `specs/schemas/run_config.schema.json`; the pydantic model is
`src/launcher/models/run_config.py`.

## RunConfig Fields

### Top-Level Fields

| Field                | Type   | Required | Default     | Description                                  |
|----------------------|--------|----------|-------------|----------------------------------------------|
| `family`             | string | yes      | --          | Product family key (e.g., `cells`, `note`)   |
| `platform`           | string | yes      | --          | Target platform key (e.g., `python`, `java`) |
| `repo_url`           | string | yes      | --          | HTTPS URL of the source repository           |
| `launch_tier`        | string | no       | `"auto"`    | Content scope: `auto`, `full`, `core`, `minimal` |
| `validation_profile` | string | no       | `"default"` | Validation profile name (e.g., `pilot`, `production`) |
| `llm`                | object | no       | see below   | LLM endpoint configuration                  |
| `output`             | object | no       | see below   | Output directory and goal settings           |

### LLM Configuration (`llm`)

| Field             | Type   | Required | Default | Description                             |
|-------------------|--------|----------|---------|-----------------------------------------|
| `llm.primary`     | object | yes*     | --      | Primary LLM endpoint                    |
| `llm.fallback`    | object | no       | null    | Fallback LLM endpoint                   |
| `llm.temperature` | float  | no       | 0.0     | Sampling temperature (0.0 = deterministic) |
| `llm.max_tokens`  | int    | no       | 6000    | Maximum tokens per LLM response         |
| `llm.max_concurrency` | int | no      | 4       | Maximum concurrent LLM calls            |

*Required when the `llm` object is provided.

### LLM Endpoint Fields (`llm.primary`, `llm.fallback`)

| Field         | Type   | Required | Description                                |
|---------------|--------|----------|--------------------------------------------|
| `base_url`    | string | yes      | OpenAI-compatible API base URL             |
| `model`       | string | yes      | Model identifier                           |
| `api_key_env` | string | no       | Environment variable name holding API key  |

API key resolution order: explicit `api_key_env` value, then `litellm_key`,
then `ANTHROPIC_API_KEY`, then `OPENAI_API_KEY`.

### Output Configuration (`output`)

| Field     | Type   | Required | Default    | Description                          |
|-----------|--------|----------|------------|--------------------------------------|
| `goal`    | string | no       | `"draft"`  | Pipeline goal: `draft` or `pr`       |
| `run_dir` | string | no       | `"runs/"`  | Path for run artifacts               |

When `goal` is `draft`, the pipeline stops after Evaluate (no PR opened).
When `goal` is `pr`, the Publish worker applies patches and opens a PR.

## Default LLM Endpoints

When no `llm` block is provided in the run config, the pipeline uses
hardcoded defaults:

```yaml
llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next/oss"
    api_key_env: "litellm_key"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  temperature: 0.0
  max_tokens: 6000
  max_concurrency: 4
```

### LLM Fallback Chain

```
Primary (professionalize.llm, qwen3-next/oss)
    | on transient failure / circuit breaker trip
Fallback (local Ollama, gemma3:12b)
    | on schema validation failure after 2 retries
Deterministic: bullet-list rendering from claims + verbatim snippets
```

## Example Run Config

Pilot configuration for Aspose.Cells FOSS Python:

```yaml
family: cells
platform: python
repo_url: "https://github.com/aspose-cells/Aspose.Cells-for-Python-via-.NET"
launch_tier: auto
validation_profile: pilot

llm:
  primary:
    base_url: "https://llm.professionalize.com/v1"
    model: "qwen3-next/oss"
  fallback:
    base_url: "http://127.0.0.1:11434/v1"
    model: "gemma3:12b"
  temperature: 0.0
  max_tokens: 6000
  max_concurrency: 4

output:
  goal: draft
  run_dir: "runs/"
```

Pilot configs are stored in `configs/pilots/{family}-{platform}.yaml`.

## Validation Rules

RunConfig is validated at two levels before the pipeline starts.

### JSON Schema Validation

The config is validated against `specs/schemas/run_config.schema.json`.
Failures produce error code `CONFIG_INVALID` (severity: critical, hard
stop). The schema enforces:

- `family`, `platform`, `repo_url` are required strings
- `repo_url` must be a valid URI
- `launch_tier` must be one of `auto`, `full`, `core`, `minimal`
- `llm.primary.base_url` and `llm.primary.model` are required when `llm`
  is provided
- `llm.temperature` must be in range [0, 2]
- No additional properties allowed at the top level

### Semantic Validation

After schema validation, the pipeline performs semantic checks:

1. **Family exists**: `family` must be a key in `configs/families.yaml`.
   Failure: `CONFIG_FAMILY_UNKNOWN`.
2. **Platform exists**: `platform` must be a key in `configs/families.yaml`
   platforms section. Failure: `CONFIG_PLATFORM_UNKNOWN`.
3. **Repo URL reachable**: `repo_url` must be a valid, accessible HTTPS
   URL (checked during Intake or Understand). Failure is a worker-level
   error, not a config error.
4. **Validation profile valid**: `validation_profile` must match a known
   profile. Unknown profiles fall back to `default` with a warning.

### Pydantic Model Validation

The `RunConfig` pydantic model (`src/launcher/models/run_config.py`)
provides type-level enforcement at runtime. Fields use `Literal` types
for enum-like constraints and `Field(default_factory=...)` for defaults.
