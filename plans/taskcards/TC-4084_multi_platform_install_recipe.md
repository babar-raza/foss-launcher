---
id: TC-4084
title: "Multi-platform install recipe + rename pip_command → install_command"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase4, understand, multi_platform, install_recipe]
depends_on: [TC-4083]
allowed_paths:
  - plans/taskcards/TC-4084_multi_platform_install_recipe.md
  - src/launcher/models/understanding.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/worker.py
  - src/launcher/workers/generate/section_prompt.py
  - tests/unit/workers/understand/test_extract.py
  - tests/integration/test_understand_pipeline.py
  - tests/unit/workers/test_section_prompt.py
  - tests/unit/workers/test_understand.py
evidence_required:
  - reports/TC-4084/evidence.md
---

# Taskcard TC-4084 — Multi-platform install recipe + rename pip_command → install_command

## Objective

`InstallRecipe.pip_command` is a Python-biased field name. Rename to `install_command`.
Add platform dispatch in `extract_install_recipe()` for TypeScript (npm), Java (mvn),
Go (go get), Rust (cargo), .NET (dotnet add package), Ruby (gem), PHP (composer).

## Allowed paths

All listed in frontmatter.

## Implementation steps

### Step 1: Rename field in model

`src/launcher/models/understanding.py`:
- `pip_command: str` → `install_command: str` with alias `pip_command` for backward compat

### Step 2: Add multi-platform dispatchers and update source_file attribution

### Step 3: Update all call sites and tests

## Failure modes

### Failure mode 1: pip_command still referenced after rename
**Detection**: ImportError or AttributeError in tests
**Resolution**: Search all files for pip_command and update

### Failure mode 2: Maven/POM parsing fails on complex POMs
**Detection**: Java recipe returns None
**Resolution**: Fall back to None — downstream handles gracefully

### Failure mode 3: SharedFacts source_file attribution wrong for TypeScript
**Detection**: source_file="pyproject.toml (cached)" for TypeScript
**Resolution**: Platform-specific source_file prefix in shared_facts path

## Task-specific review checklist

1. [ ] `install_command` field works; pip_command alias preserved for test compat
2. [ ] TypeScript repos produce `npm install {name}` command
3. [ ] Go repos produce `go get {module}` command
4. [ ] Rust repos produce `cargo add {crate}` command
5. [ ] Python behavior unchanged
6. [ ] All pip_command references updated in src/ and tests/
7. [ ] Docstrings updated
8. [ ] No regressions in existing install recipe tests

## Acceptance checks

1. [ ] `test_typescript_package_json` passes
2. [ ] `test_go_module` passes
3. [ ] `test_rust_cargo` passes
4. [ ] `test_install_command_not_pip_command` passes
5. [ ] All existing install recipe tests pass with updated field name

## E2E verification

```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -v -k install
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v -k install
```
