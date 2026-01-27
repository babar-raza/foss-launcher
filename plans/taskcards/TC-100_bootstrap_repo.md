---
id: TC-100
title: "Bootstrap repo for deterministic implementation"
status: Done
owner: "FOUNDATION_AGENT"
updated: "2026-01-27"
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
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
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
python scripts/bootstrap_check.py
python -m pytest tests/unit/test_bootstrap.py -v
python -c "import launch"
```

**Expected artifacts:**
- src/launch/__init__.py (package marker)
- pyproject.toml (valid package config)
- scripts/bootstrap_check.py
- tests/unit/test_bootstrap.py

**Success criteria:**
- [ ] bootstrap_check.py exits with code 0
- [ ] pytest passes all bootstrap tests
- [ ] Package import succeeds

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: None (bootstrap task)
- Downstream: TC-200 (schemas), TC-300 (orchestrator)
- Contracts: pyproject.toml validates against PEP 517/518

## Failure modes
1. **Failure**: Schema validation fails for output artifacts
   - **Detection**: `validate_swarm_ready.py` or pytest fails with JSON schema errors
   - **Fix**: Review artifact structure against schema files in `specs/schemas/`; ensure all required fields are present and types match
   - **Spec/Gate**: specs/11_state_and_events.md, specs/09_validation_gates.md (Gate C)

2. **Failure**: Nondeterministic output detected
   - **Detection**: Running task twice produces different artifact bytes or ordering
   - **Fix**: Review specs/10_determinism_and_caching.md; ensure stable JSON serialization, stable sorting of lists, no timestamps/UUIDs in outputs
   - **Spec/Gate**: specs/10_determinism_and_caching.md, tools/validate_swarm_ready.py (Gate H)

3. **Failure**: Write fence violation (modified files outside allowed_paths)
   - **Detection**: `git status` shows changes outside allowed_paths, or Gate E fails
   - **Fix**: Revert unauthorized changes; if shared library modification needed, escalate to owning taskcard
   - **Spec/Gate**: plans/taskcards/00_TASKCARD_CONTRACT.md (Write fence rule), tools/validate_taskcards.py

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

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
