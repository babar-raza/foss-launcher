---
id: TC-4071
title: "Remove Python defaults from classifier and config_loader"
status: Done
priority: High
owner: agent
updated: "2026-03-11"
tags: [phase1, intake, classifier, multi-language]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4071_remove_python_defaults.md
  - src/launcher/intake/repo_classifier.py
  - src/launcher/intake/config_loader.py
  - tests/unit/intake/test_classifier.py
evidence_required:
  - reports/TC-4071/evidence.md
---

# Taskcard TC-4071 — Remove Python defaults from classifier

## Objective

Change `ClassifierConfig.require_python: bool = True` → `False` and
`ClassifierOverrides.require_python: bool = True` → `False` so that the default
classification pass is language-neutral. The field is already marked deprecated;
the default change removes silent Python bias.

## Required spec references

- `specs/github_intake.md` (Section 5 — classifier heuristics)

## Scope

### In scope
- `repo_classifier.py` line 55: default True → False
- `config_loader.py` line 71: default True → False
- `config_loader.py` line 195: YAML parse fallback True → False
- Update `tests/unit/intake/test_classifier.py`: two tests assert old wrong behavior (needs_review for non-Python), must be updated to assert `eligible`, plus add new test for explicit `require_python=True` still works

### Out of scope
- `OrgConfig.default_platform: str = "python"` — this is a per-org default, not system bias, leave as-is
- Removing the `require_python` field entirely (breaking change, out of scope)

## Inputs

- `src/launcher/intake/repo_classifier.py`
- `src/launcher/intake/config_loader.py`
- `tests/unit/intake/test_classifier.py`

## Outputs

- Updated classifier and config_loader with language-neutral defaults
- Updated tests reflecting correct multi-language behavior

## Allowed paths

- plans/taskcards/TC-4071_remove_python_defaults.md
- src/launcher/intake/repo_classifier.py
- src/launcher/intake/config_loader.py
- tests/unit/intake/test_classifier.py

### Allowed paths rationale
Two source files have the Python bias default. One test file has two tests asserting the old wrong behavior.

## Implementation steps

### Step 1: Update repo_classifier.py
Line 55: `require_python: bool = True` → `require_python: bool = False`

### Step 2: Update config_loader.py
Line 71: `require_python: bool = True` → `require_python: bool = False`
Line 195: `require_python=cls_raw.get("require_python", True)` → `require_python=cls_raw.get("require_python", False)`

### Step 3: Update test_classifier.py
`test_needs_review_non_python_language` (line 90): JavaScript repo under default config now gets `eligible` (not `needs_review`). Change assertion.
`test_needs_review_no_language` (line 96): No-language repo under default config: language check is SKIPPED (both require_language=None and require_python=False). Check if it becomes `eligible`. Update accordingly.
Add: `test_deprecated_require_python_still_works_when_explicit`: `ClassifierConfig(require_python=True)` with Java repo → `needs_review`.

## Failure modes

1. Other tests that create `ClassifierConfig()` and then pass non-Python repos may now unexpectedly get `eligible`. Scan all tests — there are likely more. Fix each one.
2. If any YAML config file has `require_python: true` (absent the change), load will now use `False` default. This is a behavioral change for YAML-driven runs — it is the INTENDED behavior.
3. `test_needs_review_no_language`: no-language repos may now be `eligible` (size check may still trigger needs_review). Verify the actual behavior after the change.

## Task-specific review checklist

- [ ] `ClassifierConfig()` with no args classifies a Java repo as `eligible` (not `needs_review`)
- [ ] `ClassifierConfig(require_python=True)` with Java repo still classifies as `needs_review` (backward compat)
- [ ] `ClassifierOverrides()` default is `require_python=False`
- [ ] YAML parse default for `require_python` is `False` (line 195 in config_loader.py)
- [ ] No test in `test_classifier.py` asserts `needs_review` for a non-Python repo under default config
- [ ] Warning log still fires when `require_python=True` (existing behavior preserved)

## Deliverables

- Updated `src/launcher/intake/repo_classifier.py`
- Updated `src/launcher/intake/config_loader.py`
- Updated `tests/unit/intake/test_classifier.py`

## Acceptance checks

- [x] `pytest tests/unit/intake/test_classifier.py -v` — all pass (196 intake tests pass, verified 2026-03-11)
- [x] `ClassifierConfig().require_python` is `False` (verified: False)
- [x] `ClassifierOverrides().require_python` is `False` (verified: False)

## Self-review

After change: `classify_repo({"full_name": "org/repo", "language": "JavaScript", ...})` with default config → `eligible` (assuming license + readme pass).

## E2E verification

`pytest tests/unit/intake/ -x` all pass.

## Integration boundary proven

A TypeScript or Java repo now passes through classification with no Python-specific rejection unless caller explicitly passes `require_python=True`.
