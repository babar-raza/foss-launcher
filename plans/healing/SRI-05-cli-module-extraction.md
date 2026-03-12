# SRI-05: Extract CLI Intake Commands to Separate Module

**Status:** Not Started
**Gap linkage:** Intake port self-review, Dimension 4 (Code Quality)
**Role:** Refactor
**Scope:** Move intake CLI commands from main.py to dedicated module

---

## Problem

All 4 intake subcommands (scan, classify, generate, onboard) plus helpers (`_repo_root()`, `_load_intake_config()`) were added directly to `src/launcher/cli/main.py`. This bloats the main CLI file. V2's CLI pattern should follow the same subcommand-per-file pattern used elsewhere.

## Acceptance Checks

- [ ] `src/launcher/cli/intake.py` exists with all 4 commands + helpers
- [ ] `main.py` imports and mounts `intake_app` from `intake.py`
- [ ] All CLI tests pass unchanged
- [ ] `python -m launcher.cli.main intake --help` still works
- [ ] No duplicate code between main.py and intake.py

## Deliverables

1. `src/launcher/cli/intake.py` — extracted intake CLI module
2. Updated `src/launcher/cli/main.py` — imports intake_app

## Hard Rules

- Pure extraction — no behavioral changes
- Keep same command names, options, help text

## Review Dimensions

- Module cohesion
- Import cleanliness
- Test stability

## Runbook

1. Create `src/launcher/cli/intake.py`
2. Move `intake_app`, all `@intake_app.command()` functions, `_repo_root()`, `_load_intake_config()` to new file
3. In `main.py`, replace with: `from launcher.cli.intake import intake_app`
4. Run CLI tests
5. Manual smoke test: `python -m launcher.cli.main intake --help`
