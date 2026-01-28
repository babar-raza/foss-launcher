# CI Workflow File Paths — 20260128-1849

## Primary Workflow File
- **Path**: `.github/workflows/ci.yml`
- **Type**: GitHub Actions workflow
- **Status**: Modified (complete overhaul)
- **Lines**: 67 (down from 71 in old version)

## Workflow Components

### Triggers
- `on.push.branches`: ["main"]
- `on.pull_request.branches`: ["main"]
- `on.workflow_dispatch`: (manual trigger)

### Concurrency Control
- `concurrency.group`: `ci-${{ github.ref }}`
- `concurrency.cancel-in-progress`: true

### Job: gates-and-tests
- **Runner**: ubuntu-latest
- **Steps**: 7 total

#### Step Breakdown
1. **Checkout** — actions/checkout@v4
2. **Choose Python version file** — Dynamic .python-version vs pyproject.toml
3. **Set up Python** — actions/setup-python@v6
4. **Install uv** — astral-sh/setup-uv@v7 (with caching)
5. **Create venv** — `python -m venv .venv`
6. **Install dependencies** — `uv sync --frozen` with UV_PROJECT_ENVIRONMENT=.venv
7. **Run gates** — tools/validate_swarm_ready.py → ci_artifacts/validate_swarm_ready.txt
8. **Run tests** — pytest -q → ci_artifacts/pytest.txt
9. **Upload CI logs** — actions/upload-artifact@v4 (if: always())

## Artifact Outputs
- **Artifact name**: ci_artifacts
- **Contents**:
  - `ci_artifacts/validate_swarm_ready.txt` — All 21 gates output
  - `ci_artifacts/pytest.txt` — All test results output
- **Persistence**: Available for download from failed runs for debugging

## Referenced Tools & Scripts
- `tools/validate_swarm_ready.py` — Gate enforcement (21 gates)
- `.venv/bin/python` — Canonical venv python interpreter
- `pytest` — Test runner (installed via uv sync)

## Configuration Files
- `.python-version` — Primary Python version source (if exists)
- `pyproject.toml` — Fallback Python version + dependency spec
- `uv.lock` — Frozen dependency lockfile (used by uv sync --frozen)

## Relative Paths Used in Workflow
All paths in the workflow are relative to repository root:
- `./.venv/bin/python` — Explicit .venv usage
- `ci_artifacts/` — Local artifact staging directory
- `tools/validate_swarm_ready.py` — Gate validation script

## Absolute Path (Local)
`C:\Users\prora\OneDrive\Documents\GitHub\foss-launcher\.github\workflows\ci.yml`
