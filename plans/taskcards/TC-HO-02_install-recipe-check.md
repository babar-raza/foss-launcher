---
id: TC-HO-02
title: "Install Recipe Check — verify install commands against product evidence"
status: Done
priority: High
owner: "orchestrator-agent"
updated: "2026-03-11"
tags: [evaluate, wave4a, understand-hardening]
depends_on: [TC-HO-03]
allowed_paths:
  - plans/taskcards/TC-HO-02_install-recipe-check.md
  - src/launcher/workers/evaluate/checks/install_recipe.py
  - src/launcher/workers/evaluate/checks/__init__.py
  - src/launcher/workers/evaluate/worker.py
  - tests/unit/workers/evaluate/checks/__init__.py
  - tests/unit/workers/evaluate/checks/test_install_recipe.py
  - reports/agents/wave4a/TC-HO-02/evidence.md
evidence_required:
  - reports/agents/wave4a/TC-HO-02/evidence.md
---

# Taskcard TC-HO-02 — Install Recipe Check

## Objective

Add `check_install_recipe()` to the evaluate worker's deterministic check
pipeline. The check verifies that getting_started/installation/quickstart
pages contain install commands that match `product_evidence.install_recipe`,
catching hallucinated package names before publication.

## Required spec references

- `specs/worker_evaluate.md` (Section: deterministic checks — Phase A)
- `specs/worker_understand.md` (Section: product_evidence.install_recipe)
- `specs/schemas/understanding_bundle.schema.json` (InstallRecipe definition)

## Scope

### In scope
- New file `src/launcher/workers/evaluate/checks/install_recipe.py`
- Export from `checks/__init__.py`
- Integration in `_run_deterministic_checks()` in `worker.py`
- Unit tests covering wrong command, correct command, non-install role, None recipe, no code blocks

### Out of scope
- Changing InstallRecipe model (already defined in understanding.py)
- Verifying npm, go get, cargo, dotnet commands (check is package-name-based substring match)
- Multi-platform install command variants

## Inputs

- `content`: Generated markdown text for a page
- `slug`: Page slug for Finding location
- `page_role`: Must be in `["getting_started", "installation", "quickstart"]` to run
- `product_evidence`: dict loaded from `understand_checkpoint.json` via `_load_understand_checkpoint`
- `InstallRecipe` from `product_evidence["install_recipe"]`

## Outputs

- `list[Finding]` where each Finding has:
  - `check="wrong_install_command"`
  - `severity="error"` (mapped to `"high"`)
  - `message` includes expected install_command and slug
  - `location=slug`

## Allowed paths

- plans/taskcards/TC-HO-02_install-recipe-check.md
- src/launcher/workers/evaluate/checks/install_recipe.py
- src/launcher/workers/evaluate/checks/__init__.py
- src/launcher/workers/evaluate/worker.py
- tests/unit/workers/evaluate/checks/__init__.py
- tests/unit/workers/evaluate/checks/test_install_recipe.py
- reports/agents/wave4a/TC-HO-02/evidence.md

### Allowed paths rationale
- `install_recipe.py`: new check implementation
- `checks/__init__.py`: add export for new check
- `worker.py`: integrate check into `_run_deterministic_checks()`
- `tests/`: unit tests for all five test cases specified in sprint brief
- `evidence.md`: required evidence artifact

## Implementation steps

### Step 1: Implement install_recipe.py

Create `src/launcher/workers/evaluate/checks/install_recipe.py` with:
- `check_install_recipe(content, slug, *, page_role, product_evidence)` function
- Skip if `page_role` not in `{"getting_started", "installation", "quickstart"}`
- Extract `install_recipe` dict from `product_evidence`; skip if None/missing
- Parse all fenced code blocks from `content`
- Skip if no fenced code blocks found
- Check if any code block contains `install_recipe["install_command"]` (substring match)
- If code blocks present but none match → emit `WRONG_INSTALL_COMMAND` finding
- Finding: `check="wrong_install_command"`, `severity="high"`

### Step 2: Export from checks/__init__.py

Add:
```python
from .install_recipe import check_install_recipe  # TC-HO-02
```
And add to `__all__`.

### Step 3: Integrate in worker.py

In `_run_deterministic_checks()`:
- Call `check_install_recipe(content, slug, page_role=page_role, product_evidence=product_evidence or {})`

### Step 4: Write unit tests

Create `tests/unit/workers/evaluate/checks/test_install_recipe.py` with Tests A–E.

### Step 5: Create evidence artifact

Write `reports/agents/wave4a/TC-HO-02/evidence.md`.

## Failure modes

### Failure mode 1: install_recipe dict vs model

**Detection**: `product_evidence["install_recipe"]` may be a dict (from JSON) not an InstallRecipe model
**Resolution**: Access `install_recipe` as a dict using `.get("install_command", "")` — no pydantic import needed in the check
**Gate**: Test A must pass with dict-based product_evidence

### Failure mode 2: Empty install_command string

**Detection**: `install_recipe["install_command"]` is `""` → every page skips (no false positives)
**Resolution**: Guard: if `install_command` is empty string, skip check (return `[]`)
**Gate**: Test D (install_recipe is None) must return `[]`

### Failure mode 3: Code blocks with no shell commands

**Detection**: Pages with only Python code blocks (no `pip install` lines) emit false positives
**Resolution**: The check tests if ANY code block contains the install command — only fires when code blocks exist but none contain the expected command. If the page has code but zero shell blocks, the check still fires (the page should include the install command if it's getting_started).
**Gate**: Test E (no code blocks) must return `[]`

## Task-specific review checklist

1. [ ] Check only runs for `page_role` in `{"getting_started", "installation", "quickstart"}`
2. [ ] Check skips gracefully when `install_recipe` is None or `install_command` is empty
3. [ ] Check skips when no fenced code blocks in content (Test E)
4. [ ] Finding `severity` is `"high"` (maps to error-level in grader)
5. [ ] `check="wrong_install_command"` is consistent across all emitted findings
6. [ ] Function handles empty `product_evidence` dict gracefully (returns `[]`)
7. [ ] Docstrings present for all public functions
8. [ ] Spec file confirmed: no new spec needed (check is additive to existing evaluate worker spec)
9. [ ] Schema `"description"` fields: no schema changes needed (Finding model unchanged)
10. [ ] Checked `docs/README.md` ownership map — evaluate worker guide may need update
11. [ ] No new `docs/guides/` file needed for this check

## Deliverables

1. `src/launcher/workers/evaluate/checks/install_recipe.py`
2. Updated `src/launcher/workers/evaluate/checks/__init__.py`
3. Updated `src/launcher/workers/evaluate/worker.py`
4. `tests/unit/workers/evaluate/checks/test_install_recipe.py`
5. `reports/agents/wave4a/TC-HO-02/evidence.md`

## Acceptance checks

1. [ ] All 5 unit tests (A–E) pass
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q` passes
3. [ ] `check_install_recipe` exported from `checks/__init__.py`
4. [ ] `_run_deterministic_checks()` calls the new check
5. [ ] No existing tests broken by changes to `worker.py` or `__init__.py`

## Self-review

### Verification results
- [ ] Tests: 5/5 PASS
- [ ] Validation: import from checks package PASS
- [ ] Evidence captured: reports/agents/wave4a/TC-HO-02/evidence.md

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/evaluate/checks/test_install_recipe.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/ -x -q
```

**Expected results**:
- 5 tests pass in test_install_recipe.py
- All workers unit tests pass

## Integration boundary proven

**Upstream**: `_load_understand_checkpoint(context)` in `worker.py` provides `product_evidence` dict
**Downstream**: `grade_page(findings)` consumes the `WRONG_INSTALL_COMMAND` findings
**Contract**: `Finding(check="wrong_install_command", severity="high", message=..., location=slug)`
