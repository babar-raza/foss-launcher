---
id: TC-100
title: "Bootstrap repo for deterministic implementation"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
depends_on: []
allowed_paths:
  - pyproject.toml
  - src/launch/__init__.py
  - scripts/bootstrap_check.py
  - .github/workflows/ci.yml
  - tests/unit/test_bootstrap.py
  - reports/agents/**/TC-100/**
evidence_required:
  - reports/agents/<agent>/TC-100/report.md
  - reports/agents/<agent>/TC-100/self_review.md
  - "Test output: python -m pytest -q"
  - "Import check: python -c 'import launch'"
---

# Taskcard TC-100 — Bootstrap repo for deterministic implementation

## Objective
Establish a **deterministic, CI-ready** Python repository skeleton that matches the project structure, toolchain, and entrypoint expectations defined in the specs (importable package, runnable tests, pinned tooling).

## Required spec references
- specs/29_project_repo_structure.md
- specs/19_toolchain_and_ci.md
- specs/25_frameworks_and_dependencies.md
- specs/10_determinism_and_caching.md

## Scope
### In scope
- Ensure repo structure matches `specs/29_project_repo_structure.md` (folders present, naming consistent)
- Ensure packaging is correct (importable `launch` package)
- Ensure minimal CLI entrypoints exist (stubs are OK here; full behavior is in later taskcards)
- Ensure a pinned toolchain + CI commands exist and are documented

### Out of scope
- Worker implementations (W1–W9)
- Orchestrator logic beyond basic wiring (handled in TC-300+)

## Inputs
- This spec pack repository (current working directory)
- Python version per `specs/19_toolchain_and_ci.md`
- Tooling per `specs/25_frameworks_and_dependencies.md` (uv preferred, otherwise pinned pip tooling)

## Outputs
- A repo structure that conforms to `specs/29_project_repo_structure.md`
- Packaging files (pyproject + lockfile) enabling deterministic installs
- Importable `launch` package (CLI entrypoint wiring handled by TC-530)
- Minimal test scaffolding that passes in CI

## Allowed paths
- pyproject.toml
- src/launch/__init__.py
- scripts/bootstrap_check.py
- .github/workflows/ci.yml
- tests/unit/test_bootstrap.py
- reports/agents/**/TC-100/**
## Implementation steps
1) **Repo structure**: create any missing top-level folders required by `specs/29_project_repo_structure.md` (do not rename existing ones unless specs require).
2) **Packaging**:
   - ensure `src/launch/__init__.py` exists
   - ensure `pyproject.toml` declares the package under `src/`
   - prefer uv for lockfile; otherwise use the pinned alternative specified in `specs/19_toolchain_and_ci.md`
3) **Entrypoints (stubs acceptable)**:
   - add stub modules for `launch_run`, `launch_validate`, `launch_mcp` if needed
   - Note: CLI entrypoint wiring (including `__main__.py`) is handled by TC-530
4) **CI commands**:
   - ensure `python -m pytest -q` passes (placeholder tests allowed, but must be meaningful, e.g., import tests)
   - ensure lint/format targets (if specified by specs) are runnable
5) **Determinism baseline**:
   - ensure the repo does not introduce time-dependent defaults in code stubs (no timestamps in generated filenames, etc.)
   - ensure any “generated” artifacts are written under RUN_DIR only (even in stubs)

## E2E verification
**Concrete command(s) to run:**
```bash
python -m pytest tests/unit/ -v --tb=short
python -m launch.cli --version
```

**Expected artifacts:**
- src/launch/__init__.py (package marker)
- pyproject.toml (valid package config)

**Success criteria:**
- [ ] Exit code 0
- [ ] Package version displayed

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: None (bootstrap task)
- Downstream: TC-200 (schemas), TC-300 (orchestrator)
- Contracts: pyproject.toml validates against PEP 517/518

## Deliverables
- Code:
  - packaging + basic package structure
- Tests:
  - at least one test proving package importability
- Docs/specs/plans:
  - (README updates handled by TC-530)
- Reports (required):
  - reports/agents/<agent>/TC-100/report.md
  - reports/agents/<agent>/TC-100/self_review.md

## Acceptance checks
- [ ] `python -c "import launch"` succeeds
- [ ] `python -m pytest -q` succeeds
- [ ] Toolchain pins are not `PIN_ME` and lockfile exists
- [ ] Agent reports are written
- [ ] (CLI entrypoint functionality testing is in TC-530)

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
