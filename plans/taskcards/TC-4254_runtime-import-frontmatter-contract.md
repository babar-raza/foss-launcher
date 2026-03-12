---
id: TC-4254
title: "Align runtime import semantics across planner frontmatter, install recipes, and section prompts"
status: In-Progress
priority: Critical
owner: "Agent-B"
updated: "2026-03-12"
tags: [python, runtime-import, planner, understand, generate, pilot]
depends_on: [TC-HYBRID-01, TC-4093, TC-4253]
allowed_paths:
  - plans/taskcards/TC-4254_runtime-import-frontmatter-contract.md
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/generate/section_prompt.py
  - src/launcher/workers/planner/plan.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/test_generate.py
  - tests/unit/workers/test_plan_slug_integration.py
  - tests/unit/workers/test_code_check.py
  - specs/product_model.md
  - specs/site_model_hugo.md
  - reports/TC-4254/evidence.md
  - reports/agents/B_implementation/ORCH-04/plan.md
  - reports/agents/B_implementation/ORCH-04/changes.md
  - reports/agents/B_implementation/ORCH-04/evidence.md
  - reports/agents/B_implementation/ORCH-04/self_review.md
  - reports/agents/B_implementation/ORCH-04/commands.sh
evidence_required:
  - reports/TC-4254/evidence.md
---

# Taskcard TC-4254 — Align runtime import semantics across planner frontmatter, install recipes, and section prompts

## Objective

Resolve the Python import-contract drift exposed by the `aspose-3d-foss-python` pilot. The planner must publish the runtime import expected by generated code and evaluation, while install recipes remain package-install oriented and section prompts must not leak pip-package imports into non-install pages.

## Required spec references

- `specs/product_model.md` (Section: `runtime_import` vs `canonical_import`)
- `specs/site_model_hugo.md` (Section: products frontmatter contract)
- `plans/twinkly-puzzling-minsky.md` (Rule 3 and Rule 6: harden at source, rerun with evidence)

## Scope

### In scope
- Change planner frontmatter emission so Python pages expose the runtime import used in code examples.
- Change Python install-recipe verification snippets to use `runtime_import` when available.
- Limit install recipe prompt injection to installation/getting-started contexts so it does not contaminate unrelated pages.
- Add regression tests covering planner frontmatter, prompt injection scoping, and install recipe verification code.
- Update affected specs to document the clarified contract.

### Out of scope
- Reworking evaluator grading thresholds or LLM review prompts beyond the import-contract fix.
- Changing non-Python package/import semantics.
- Fixing unrelated `NO_GO` findings unless they block verification of this contract.

## Inputs

- `runs/260312_102358_3d_python_dd06/evaluate_checkpoint.json` — evidence of import mismatch findings.
- `src/launcher/workers/planner/plan.py` — current frontmatter emission uses `product.canonical_import`.
- `src/launcher/workers/understand/extract/_deterministic.py` — current install verification code uses `canonical_import`.
- `src/launcher/workers/generate/section_prompt.py` — current install reference block is injected whenever `install_recipe` exists.

## Outputs

- Planner frontmatter for Python pages publishes the runtime import statement expected by downstream generation/evaluation.
- Install recipe verification snippets use valid Python runtime imports when present.
- Section prompts only expose install reference blocks on install-oriented pages.
- Regression evidence in tests and pilot artifacts showing pip-package imports are no longer injected as Python code imports.

## Allowed paths

- plans/taskcards/TC-4254_runtime-import-frontmatter-contract.md
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/planner/plan.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/test_generate.py
- tests/unit/workers/test_plan_slug_integration.py
- tests/unit/workers/test_code_check.py
- specs/product_model.md
- specs/site_model_hugo.md
- reports/TC-4254/evidence.md
- reports/agents/B_implementation/ORCH-04/plan.md
- reports/agents/B_implementation/ORCH-04/changes.md
- reports/agents/B_implementation/ORCH-04/evidence.md
- reports/agents/B_implementation/ORCH-04/self_review.md
- reports/agents/B_implementation/ORCH-04/commands.sh

### Allowed paths rationale

- `src/launcher/workers/planner/plan.py` — source of frontmatter contract drift.
- `src/launcher/workers/understand/extract/_deterministic.py` — source of Python verification import leakage.
- `src/launcher/workers/generate/section_prompt.py` — prompt-scoping fix to prevent unrelated sections from inheriting install snippets.
- `tests/unit/workers/*.py` — regression coverage for the exact defect class, including planner frontmatter behavior.
- `specs/*.md` — AG-019 requires the documented contract to match worker behavior.
- `reports/...` — evidence and self-review artifacts required by the orchestration protocol.

## Implementation steps

### Step 1: Confirm the failed pilot evidence and target contract

Capture the `NO_GO` findings showing `aspose_3d_foss` in frontmatter or generated code where `aspose.threed` is required. Confirm from specs that `canonical_import` is the package/install identity while Python code execution uses `runtime_import`.

### Step 2: Fix planner frontmatter semantics

Update planner frontmatter generation so Python pages emit the runtime import value when one exists, while non-Python pages continue using `canonical_import`. Preserve backwards-compatible behavior for platforms without `runtime_import`.

### Step 3: Fix install recipe verification code

Update `extract_install_recipe()` so Python `verification_code` imports `runtime_import` when present and falls back to `canonical_import` only when no runtime import exists. Keep the package install command derived from the package name.

### Step 4: Scope install recipe prompt injection

Update `build_section_prompt()` so install reference blocks are injected only for install-oriented page roles or headings. Ensure other page types do not receive package-install snippets that can bias the LLM toward pip-package imports in code examples.

### Step 5: Add regression tests

Add tests that fail without the fix:
- planner/frontmatter test proving Python frontmatter exposes `aspose.threed`
- understand test proving install recipe verification code uses `import aspose.threed`
- generate test proving install blocks are excluded from non-install pages and included for install/getting-started pages

### Step 6: Update specs and evidence

Document the clarified frontmatter/import contract in `specs/site_model_hugo.md` and `specs/product_model.md`. Record commands, findings, and test results in the task evidence and agent workspace files.

## Failure modes

### Failure mode 1: Frontmatter still advertises the pip package name for Python

**Detection**: Pilot drafts or plan artifacts show `canonical_import: aspose_3d_foss` for Python pages.
**Resolution**: Recheck planner frontmatter selection logic and add/assert the Python runtime-import branch in tests.
**Gate**: Planner/frontmatter regression test and pilot grep over generated markdown.

### Failure mode 2: Install page guidance regresses for non-Python platforms

**Detection**: Install recipe tests fail for Java/.NET/Node or generated prompts omit install commands for install pages.
**Resolution**: Keep platform fallback behavior unchanged and scope the Python-specific verification import branch carefully.
**Gate**: Existing `test_understand.py` install recipe coverage plus targeted generate prompt tests.

### Failure mode 3: Prompt contamination persists on non-install pages

**Detection**: Grep of generated markdown still finds `import aspose_3d_foss` outside installation-related pages.
**Resolution**: Tighten install-block gating to page role/heading and rerun the pilot from generate or full run as needed.
**Gate**: Generate regression tests plus pilot artifact grep.

## Task-specific review checklist

1. [ ] Python planner frontmatter uses `runtime_import` when available.
2. [ ] Non-Python planner frontmatter still uses `canonical_import`.
3. [ ] Python install recipe verification code uses `runtime_import` not the pip package name.
4. [ ] Install recipe block is injected only for install-oriented page contexts.
5. [ ] Regression tests fail without the fix and pass with it.
6. [ ] Pilot artifacts no longer show `import aspose_3d_foss` in Python code examples outside install/package contexts.
7. [ ] Docstrings updated for modified public behavior where needed.
8. [ ] Spec file updated to reflect behavior change.
9. [ ] Schema changes not required and explicitly confirmed.
10. [ ] Checked `docs/README.md` ownership map — no trigger requiring docs/guides update beyond specs.
11. [ ] No new docs/guides file added.

## Deliverables

1. Protected-path code fixes in planner, understand, and generate.
2. Regression coverage in `tests/unit/workers/test_understand.py`, `tests/unit/workers/test_generate.py`, and `tests/unit/workers/test_code_check.py` if needed.
3. Regression coverage in `tests/unit/workers/test_plan_slug_integration.py` for planner frontmatter semantics.
4. Updated specs in `specs/product_model.md` and `specs/site_model_hugo.md`.
5. Evidence bundle at `reports/TC-4254/evidence.md`.

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k install_recipe -q`
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -k install_recipe -q`
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -k canonical_import -q`
4. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml`
5. [ ] Pilot evidence shows the prior pip-name import mismatch no longer appears in generated Python code/frontmatter.

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: pilot rerun confirms import-contract fix
- [ ] Evidence captured: `reports/TC-4254/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k install_recipe -q
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m pytest tests/unit/workers/test_generate.py -k install_recipe -q
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m pytest tests/unit/workers/test_plan_slug_integration.py -k canonical_import -q
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml
```

**Expected results**:
- Targeted regression tests pass.
- The pilot no longer produces pip-package imports as Python runtime imports in frontmatter or generated code.

## Integration boundary proven

**Upstream**: `ProductIdentity.canonical_import` and `ProductIdentity.runtime_import` from intake/understand.
**Downstream**: Planner frontmatter, generate prompt context, and evaluate import checking during pilot execution.
**Contract**: Python package identity remains the install/package name, while Python code/frontmatter import identity uses `runtime_import` when available.
