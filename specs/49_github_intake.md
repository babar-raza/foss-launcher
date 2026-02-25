# Spec 49 -- GitHub Organization Intake System

**Status**: Active
**TC**: TC-2539, TC-2540, TC-2541, TC-2542, TC-2543, TC-2544, TC-2545

## 1. Purpose

The intake system automates the discovery, classification, and onboarding of
GitHub repositories from configured organizations into the FOSS Launcher
pipeline.  It produces pilot config YAML files compatible with the existing
`configs/pilots/` structure.

## 2. Components

| Component | Module | Responsibility |
|-----------|--------|---------------|
| **Org Scanner** | `src/launch/intake/org_scanner.py` | Paginated GitHub API discovery with rate limiting and state persistence |
| **Repo Classifier** | `src/launch/intake/repo_classifier.py` | Deterministic eligibility classification (eligible / ineligible / needs_review) |
| **Config Generator** | `src/launch/intake/config_generator.py` | YAML pilot config generation from repo metadata with dedup |
| **Scheduler** | `src/launch/intake/scheduler.py` | Priority queue, batch mode, dry-run report |
| **CLI** | `src/launch/cli/main.py` (intake sub-app) | `launch intake scan`, `launch intake classify`, `launch intake generate` |

## 3. Configuration

Schema: `specs/schemas/intake_config.schema.json`

Minimal example:

```yaml
schema_version: "1.0"
organizations:
  - name: aspose-3d-foss
  - name: aspose-cells-foss
scanner:
  github_token_env: GITHUB_TOKEN
  rate_limit_delay_s: 1.0
  activity_months: 12
classifier:
  min_stars: 0
  require_readme: true
  require_python: true
  require_license: true
scheduler:
  batch_size: 5
  sort_by: stars
generator:
  output_dir: configs/pilots
state_dir: intake
```

## 4. Org Scanner

### 4.1 API Interaction

- Base URL: `https://api.github.com`
- Endpoint: `GET /orgs/{org}/repos?type=public&per_page={per_page}`
- Authentication: `Authorization: token {GITHUB_TOKEN}` (optional but recommended)
- Pagination: follows `Link` header `rel="next"` up to `max_pages`

### 4.2 Rate Limiting

- Respects `X-RateLimit-Remaining` header
- When remaining < 10, sleeps until `X-RateLimit-Reset` epoch
- Configurable inter-request delay (`rate_limit_delay_s`)
- On HTTP 403 with rate-limit body, backs off automatically

### 4.3 Filtering

- Excludes archived repos (`archived == true`)
- Excludes forks (`fork == true`)
- Excludes repos with no code (`size == 0`)
- Activity filter: `pushed_at` within `activity_months`

### 4.4 State Persistence

- `{state_dir}/scan_state.json`: seen repo full_names, last scan timestamp
- Deterministic JSON: `indent=2, sort_keys=True`
- Incremental: only fetches repos not already in state

## 5. Repo Classifier

### 5.1 Decision Matrix

| Criterion | eligible | needs_review | ineligible |
|-----------|----------|-------------|-----------|
| Has README | required (if configured) | - | missing |
| Python code | required (if configured) | - | missing |
| OSS license | required (if configured) | unknown SPDX | missing |
| Not mirror/stub/template | required | is_template | - |
| Stars >= threshold | required | - | below |

### 5.2 Determinism

Classification is purely deterministic on the input repo metadata snapshot.
No LLM or network calls.

## 6. Config Generator

### 6.1 Template Rendering

Reads a base template (defaults to `configs/pilots/_template.pinned.run_config.yaml`)
and fills in:

- `product_slug`: derived from repo name (`pilot-{owner}-{repo_name_slug}`)
- `product_name`: from repo description or name
- `family`: extracted from repo name or org name heuristic
- `github_repo_url`: from repo `html_url`
- `github_ref`: `main` (unpinned; user must pin before production)

### 6.2 Dedup

Checks `{output_dir}/` for existing configs whose `github_repo_url` matches.
Skips duplicates.

## 7. Scheduler

### 7.1 Priority Queue

- Sorts eligible repos by configured criterion (stars, pushed_at, name)
- Batch mode: processes top N repos per invocation
- Dry-run: emits `intake_report.json` without writing configs

### 7.2 State

- `{state_dir}/schedule_state.json`: processed repo list, timestamps

## 8. CLI Commands

```
launch intake scan   --orgs "org1,org2" [--dry-run] [--config intake.yaml]
launch intake classify --repo <url>
launch intake generate --repo <url> --output configs/pilots/
```

All commands support `--verbose` for debug logging.

## 9. Testing

All GitHub API interactions are mocked via `unittest.mock.patch` on
`requests.get`.  Mock responses use realistic GitHub REST API v3 JSON.

Test modules:
- `tests/unit/intake/test_org_scanner.py`
- `tests/unit/intake/test_classifier.py`
- `tests/unit/intake/test_config_generator.py`
- `tests/unit/intake/test_scheduler.py`
- `tests/unit/intake/test_intake_cli.py`
