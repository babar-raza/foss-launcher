# Toolchain, CI, and Telemetry

## Overview

This spec defines the CI pipeline structure, telemetry events, and project
repository layout for foss-launcher v2.

---

## Project Repository Structure

```
foss-launcher-v2/            # v2 branch (orphan), git worktree
  src/
    launcher/                # Python package (note: "launcher", not "launch")
      __init__.py
      cli.py                 # Entry point
      pipeline/              # Pipeline runner, graph builder
      workers/               # Intake, Understand, Generate, Evaluate, Publish
      llm/                   # LLM provider, cache, circuit breaker
      models/                # Pydantic models for all schemas
      io/                    # File I/O, hashing, YAML
      gates/                 # Quality gates
      rendering/             # IR renderer (PageIR -> Markdown)
      templates/             # Template loader
  tests/
    unit/                    # Fast, isolated unit tests
    integration/             # Cross-worker integration tests
    fixtures/                # Recorded LLM responses, sample repos
  specs/
    *.md                     # Spec files (unnumbered, descriptive names)
    schemas/                 # JSON schemas (19+)
    templates/               # Hugo template YAML files by subdomain
    rulesets/                # ruleset.yaml
  configs/
    families.yaml            # Family + platform taxonomy
    pipeline.yaml            # Pipeline topology
    pilots/                  # Per-pilot run configs
  .github/
    workflows/               # CI workflow definitions
  pyproject.toml             # Project metadata, dependencies
  CLAUDE.md                  # Agent instructions
```

---

## CI Pipeline Structure

CI runs on every push to the `v2` branch and on pull requests targeting `v2`.

### Jobs

| Job | Trigger | What it does |
|-----|---------|-------------|
| `lint` | push, PR | Ruff linting + formatting check |
| `typecheck` | push, PR | Mypy strict mode |
| `test-unit` | push, PR | Unit tests with PYTHONHASHSEED=0 |
| `test-integration` | push, PR | Integration tests (uses fixture LLM responses) |
| `schema-validate` | push, PR | Validate all YAML/JSON configs against schemas |
| `pilot-dry-run` | manual, nightly | Full pipeline with cached LLM, no publish |

### Test Execution

```bash
export PYTHONHASHSEED=0
.venv/Scripts/python.exe -m pytest tests/unit/ -x --tb=short
.venv/Scripts/python.exe -m pytest tests/integration/ -x --tb=short
```

### Schema Validation Job

Validates:
- `configs/pipeline.yaml` against `specs/schemas/pipeline.schema.json`
- `configs/pilots/*.yaml` against `specs/schemas/run_config.schema.json`
- `specs/rulesets/ruleset.yaml` against `specs/schemas/ruleset.schema.json`

### Pilot Dry Run

- Runs both pilot configs (`aspose-cells-foss-python`, `aspose-note-foss-python`).
- Uses cached LLM responses from `tests/fixtures/`.
- Validates all output artifacts against schemas.
- Produces `validation_report.json` and `quality_metrics.json`.
- Does NOT publish (no PR creation).

---

## Telemetry Events

Telemetry is built on the event stream (`events.ndjson`). No external telemetry
service is required; all data is local and inspectable (Rule 2).

### Pipeline-Level Metrics

Derived from events at the end of a run:

| Metric | Source events | Description |
|--------|-------------|-------------|
| `total_duration_s` | `run_created` to last `worker_completed` | Wall-clock run time |
| `worker_durations` | `worker_started` / `worker_completed` pairs | Per-worker timing |
| `llm_call_count` | Count of `llm_call_completed` | Total LLM calls |
| `llm_total_tokens` | Sum of `usage` in `llm_call_completed` | Token consumption |
| `fallback_count` | `llm_call_completed` where endpoint=fallback | Fallback usage |
| `cache_hit_rate` | `llm_call_completed` where cache_hit=true | Cache effectiveness |
| `gate_pass_rate` | `gate_executed` where passed=true | Gate health |
| `re_run_count` | Count of `re_run_triggered` | Re-generation cycles |

### Quality Metrics

Produced by the Evaluate worker and stored in `quality_metrics.json`:

| Metric | Description |
|--------|-------------|
| `pages_by_grade` | Count of pages per grade (A-F) |
| `avg_word_count` | Average words per page |
| `claim_coverage` | Fraction of claims used in content |
| `ab_rate` | Percentage of pages graded A or B |
| `df_rate` | Percentage of pages graded D or F |
| `verdict` | GO, NO_GO, or NEEDS_HUMAN_REVIEW |

### Metrics File

- Path: `{run_dir}/{run_id}/quality_metrics.json`
- Written by the Evaluate worker after all gates execute.
- Schema: ad-hoc (not schema-validated, but JSON with known keys).

---

## MCP Endpoints

MCP (Model Context Protocol) endpoints are not used in v2 at this time. The LLM
provider uses standard OpenAI-compatible HTTP endpoints. If MCP integration is
needed in the future, it would be added as an alternative transport in the LLM
provider layer, with no changes to worker code.

---

## Dependencies

Key Python dependencies:

| Package | Purpose |
|---------|---------|
| `pydantic` | Model validation for all contracts |
| `jsonschema` | JSON Schema validation at boundaries |
| `requests` | HTTP client for GitHub API and telemetry calls |
| `pyyaml` | YAML parsing for configs and templates |
| `click` | CLI framework |
| `ruff` | Linting and formatting |
| `mypy` | Type checking |
| `pytest` | Test framework |

---

## Engine Version

The pipeline engine version is a semver string (e.g., `2.0.0`). It is:

- Embedded in checkpoint artifacts.
- Included in LLM cache keys (version bump invalidates cache).
- Bumped on any change that affects output (prompt changes, schema changes,
  rendering changes).
- Not bumped for internal refactors that do not change output.

---

## Extended Spec (v2 Detail Addendum)

### Structured Logging Schema

All log output uses `structlog` with JSON renderer in production and ConsoleRenderer in development. Every log event carries these mandatory fields:

```json
{
  "timestamp": "2026-03-08T14:22:01.234Z",
  "level": "INFO",
  "run_id": "20260308-cells-python-a1b2c3",
  "worker": "understand",
  "phase": "B_extract",
  "event": "claim_extracted",
  "re_run_count": 0
}
```

**Optional context fields** (worker-specific):

| Worker | Phase | Context Fields |
|--------|-------|---------------|
| Understand | A (Scout) | `repo_url`, `file_count`, `doc_count` |
| Understand | B (Extract) | `source_file`, `claim_count`, `skipped_count`, `llm_model` |
| Understand | C (Plan) | `page_count`, `total_claims_assigned` |
| Generate | section | `page_id`, `section_id`, `block_count`, `word_count`, `llm_model`, `fallback_used` |
| Evaluate | Phase A | `check_id`, `file_count`, `issue_count`, `severity` |
| Evaluate | Phase B | `page_id`, `grade`, `llm_model` |
| Evaluate | verdict | `verdict`, `a_b_pct`, `d_f_pct`, `critical_count` |
| LLM client | any | `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, `fallback_level` |

**Log level policy**:
- `DEBUG`: Internal state; not emitted in production (controlled by `LOG_LEVEL` env var)
- `INFO`: Normal milestones (worker started, checkpoint written, claim extracted)
- `WARNING`: Non-fatal issues (fallback LLM used, page below min claims)
- `ERROR`: Recoverable errors (LLM call failed, retrying)
- `CRITICAL`: Non-recoverable failures that halt the pipeline

**Re-run correlation**: `"re_run_of": "<original_run_id>"` in all events when `re_run_count > 0`.

**Cost budget log event**:
```json
{
  "event": "llm_cost_update",
  "model": "qwen3-next",
  "prompt_tokens": 512,
  "completion_tokens": 1024,
  "total_tokens_this_run": 45231,
  "budget_tokens_remaining": 204769,
  "budget_pct_used": 18.1
}
```
Budget: 250,000 tokens/run (configurable via `run_config.token_budget`). WARNING at 80%; halt with `BUDGET_EXCEEDED` at 100%.

### pyproject.toml Test Configuration

Required `[tool.pytest.ini_options]` stanza:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = ["--tb=short", "--strict-markers", "-q"]
env = ["PYTHONHASHSEED=0"]
log_cli = true
log_cli_level = "WARNING"
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:pydantic",
    "ignore::DeprecationWarning:langgraph",
    "ignore::PendingDeprecationWarning",
]
markers = [
    "integration: tests requiring a real LLM endpoint",
    "slow: tests taking > 5s",
    "golden: golden-file regression tests",
]
```

Required test deps:
```toml
[project.optional-dependencies]
test = ["pytest>=8.0", "pytest-env>=1.1", "pytest-asyncio>=0.23", "pytest-timeout>=2.2"]
```

### CI Configuration (Extended)

- Run: `.venv/Scripts/python.exe -m pytest -m "not integration" --timeout=30`
- Integration tests: `pytest -m integration` (requires `litellm_key` env var)
- Determinism check: `PYTHONHASHSEED=0` enforced via `pytest-env` in `pyproject.toml`
- Coverage: `pytest --cov=src/launcher --cov-report=term-missing`

### Evidence Files

Every LLM call saves request+response to `runs/<run_id>/evidence/llm_calls/<call_id>.json`. Prompt hashing (SHA-256) for cache keys and dedup.
