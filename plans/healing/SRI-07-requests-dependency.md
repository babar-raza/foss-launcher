# SRI-07: Verify `requests` in pyproject.toml Dependencies

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 6 (Dependency Management)
**Role:** Build Config
**Scope:** Ensure `requests` is declared as a project dependency

---

## Problem

`org_scanner.py` imports `requests` for GitHub API calls. While `requests` is likely already in the dependency tree (used by `clients/http.py`), this was never explicitly verified in `pyproject.toml`. If it's only a transitive dependency, it could break on clean installs.

## Acceptance Checks

- [ ] `requests` appears in `[project.dependencies]` or `[tool.poetry.dependencies]` in `pyproject.toml`
- [ ] If missing, add with version constraint (e.g., `requests>=2.28`)
- [ ] `pip install -e .` in clean venv succeeds and `import requests` works

## Deliverables

1. Verification result (already present or added to pyproject.toml)

## Hard Rules

- Don't add if already declared
- Use compatible version range, not pinned version

## Runbook

1. Read `pyproject.toml`
2. Search for `requests` in dependencies
3. If missing, add it
4. Verify with `pip install -e .` in clean venv
