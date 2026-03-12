---
id: TC-4255
title: "Filter invalid Python API evidence in understand extraction"
status: In-Progress
priority: Critical
owner: "Agent-B"
updated: "2026-03-12"
tags: [understand, python, snippets, api-surface, hallucination]
depends_on: [TC-HAL-07, TC-HAL-01, TC-4254]
allowed_paths:
  - plans/taskcards/TC-4255_understand-filter-invalid-python-api-evidence.md
  - src/launcher/workers/understand/adapters/_python.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - src/launcher/workers/understand/extract/_deterministic.py
  - src/launcher/workers/understand/extract/_snippets.py
  - src/launcher/workers/understand/extract/_validation.py
  - tests/unit/workers/test_understand.py
  - tests/unit/workers/understand/test_extract.py
  - reports/TC-4255/evidence.md
  - reports/agents/B_implementation/ORCH-04/plan.md
  - reports/agents/B_implementation/ORCH-04/changes.md
  - reports/agents/B_implementation/ORCH-04/evidence.md
  - reports/agents/B_implementation/ORCH-04/self_review.md
  - reports/agents/B_implementation/ORCH-04/commands.sh
evidence_required:
  - reports/TC-4255/evidence.md
---

# Taskcard TC-4255 — Filter invalid Python API evidence in understand extraction

## Objective

Stop the `understand` worker from passing invalid Python evidence downstream. Specifically, Python repos with `runtime_import` must not treat the pip package name as a valid runtime import, and extracted public snippets/claims must not preserve private-member examples like `._control_points` as source-verified API guidance.

## Required spec references

- `specs/product_model.md` (Section: `runtime_import` vs `canonical_import`)
- `specs/worker_understand.md` (Sections: API surface extraction, snippet extraction, post-LLM validation)
- `plans/twinkly-puzzling-minsky.md` (Rule 6: fix at the responsible upstream worker)

## Scope

### In scope
- Change Python import allowlist construction so `runtime_import` is the code-facing allowlist when present, including after `__init__.py` allowlist expansion.
- Filter extracted Python snippets that use private-member access or pip-name imports inconsistent with the runtime import contract.
- Filter extracted Python workflow examples that use private-member access before they reach downstream generation.
- Downgrade or reject public claims that reference private Python API members.
- Add regression tests for allowlist construction, snippet filtering, workflow-example filtering, and claim validation.

### Out of scope
- Reworking format-matrix heuristics beyond what is necessary to keep invalid Python evidence out of downstream generation.
- Changes to evaluator grading rules.
- Prompt-level fixes in `generate` unless this task uncovers a separate downstream defect.

## Inputs

- `runs/260312_110922_3d_python_23b9/understand_checkpoint.json` — shows `import_allowlist` contains both `aspose.threed` and `aspose_3d_foss`.
- `runs/260312_110922_3d_python_23b9/understand_checkpoint.json` — snippets still include `from aspose_3d_foss import ...` and `mesh._control_points.append(...)`.
- `runs/260312_110922_3d_python_23b9/evaluate_checkpoint.json` — remaining `factual_accuracy` / `api_consistency` findings point to invalid Python API evidence.

## Outputs

- Python `ApiSurface.import_allowlist` excludes the pip package name when `runtime_import` is available.
- Extracted Python snippets with private-member access or invalid import paths are filtered before downstream generation.
- Claim validation removes or downgrades public claims that cite private members.
- Regression evidence demonstrating the filtered evidence no longer reaches pilot outputs.

## Allowed paths

- plans/taskcards/TC-4255_understand-filter-invalid-python-api-evidence.md
- src/launcher/workers/understand/adapters/_python.py
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/extract/_deterministic.py
- src/launcher/workers/understand/extract/_snippets.py
- src/launcher/workers/understand/extract/_validation.py
- tests/unit/workers/test_understand.py
- tests/unit/workers/understand/test_extract.py
- reports/TC-4255/evidence.md
- reports/agents/B_implementation/ORCH-04/plan.md
- reports/agents/B_implementation/ORCH-04/changes.md
- reports/agents/B_implementation/ORCH-04/evidence.md
- reports/agents/B_implementation/ORCH-04/self_review.md
- reports/agents/B_implementation/ORCH-04/commands.sh

### Allowed paths rationale

- `adapters/_python.py` owns the active Python import-allowlist path when the platform adapter is selected.
- `_api_surface.py` owns the Python import allowlist contract.
- `_deterministic.py` owns workflow-example harvesting from tests/examples, which is where private-member Python evidence still leaks.
- `_snippets.py` is the correct upstream boundary for rejecting invalid public examples.
- `_validation.py` is the correct upstream boundary for rejecting invalid public claims.
- Existing `understand` test files already cover these boundaries and avoid scattering new regression coverage.
- Report paths capture the evidence and self-review required by the orchestrator protocol.

## Implementation steps

### Step 1: Fix Python import allowlist semantics

Update `_build_import_allowlist()` so Python repos with `runtime_import` use that runtime module path as the code-facing import root instead of seeding the allowlist with `canonical_import`, and do not reintroduce the pip package name through `__init__.py` expansion.

### Step 2: Filter invalid Python snippets

Extend `_extract_snippets()` or its validation helpers to reject Python snippets that:
- import the pip package name instead of the runtime import
- use private-member access such as `._control_points`

Keep the filter deterministic and evidence-based; do not rewrite snippet code.

### Step 3: Filter invalid Python workflow examples

Extend `extract_workflow_examples()` so Python workflow examples harvested from tests/examples are rejected when they rely on private-member access such as `._control_points`.

### Step 4: Filter invalid Python claims

Extend `_validate_and_normalize_claims()` so public Python claims that reference private-member API names are downgraded out of the public claim set before they can bias planning and generation.

### Step 5: Add regression tests

Add tests that fail without the fix:
- Python runtime-import allowlist excludes `aspose_3d_foss`
- `_extract_snippets()` drops `._control_points` and pip-name-import snippets for Python runtime-import repos
- `extract_workflow_examples()` drops Python examples that rely on `._control_points`
- `_validate_and_normalize_claims()` rejects a public claim mentioning `_control_points`

### Step 6: Verify against the pilot

Run targeted `understand` tests, then rerun the `aspose-3d-foss-python` pilot and confirm the old invalid evidence no longer appears in `understand_checkpoint.json` or generated pages.

## Failure modes

### Failure mode 1: Valid Python snippets are filtered too aggressively

**Detection**: Snippet counts collapse and generate loses real code examples on the rerun.
**Resolution**: Keep the filter narrow to private-member access and invalid runtime imports; do not generalize to all underscore tokens or all dotted imports.
**Gate**: New snippet regression tests plus pilot snippet count comparison.

### Failure mode 2: Python allowlist regression breaks canonical-only repos

**Detection**: Existing allowlist tests for repos without `runtime_import` fail.
**Resolution**: Use `runtime_import` only when populated; otherwise preserve current `canonical_import` fallback.
**Gate**: Existing allowlist tests and new runtime-import-specific test.

### Failure mode 3: Invalid claims still survive via non-snippet paths

**Detection**: `understand_checkpoint.json` still contains public claims with `_control_points` or similar private-member references.
**Resolution**: Tighten `_validation.py` claim filtering on private-member patterns and rerun from `understand`.
**Gate**: New claim-validation regression plus checkpoint grep.

## Task-specific review checklist

1. [ ] Python `import_allowlist` prefers `runtime_import` over the pip package name.
2. [ ] PIP-name Python imports are filtered from extracted snippets when `runtime_import` exists.
3. [ ] Private-member Python snippets such as `._control_points` are filtered from extracted snippets.
4. [ ] Public claims referencing private members are removed or downgraded before downstream use.
5. [ ] Regression tests fail without the fix and pass with it.
6. [ ] Pilot `understand_checkpoint.json` no longer contains the prior bad Python evidence patterns.
7. [ ] Docstrings updated for modified public behavior where needed.
8. [ ] Spec drift assessed; spec updates added or explicitly ruled out with evidence.
9. [ ] No schema changes required.
10. [ ] Checked `docs/README.md` ownership map — no docs/guides trigger beyond specs.
11. [ ] No unrelated dirty-worktree changes were overwritten.

## Deliverables

1. `understand` worker fixes in `_api_surface.py`, `_snippets.py`, and `_validation.py`.
2. Regression coverage in `tests/unit/workers/test_understand.py` and `tests/unit/workers/understand/test_extract.py`.
3. Evidence bundle at `reports/TC-4255/evidence.md`.

## Acceptance checks

1. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k allowlist -q`
2. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -k control_points -q`
3. [ ] `PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml`
4. [ ] `understand_checkpoint.json` for the rerun no longer contains `from aspose_3d_foss import` or `._control_points`
5. [ ] Generated pilot pages no longer surface the filtered invalid evidence.

## Self-review

### Verification results
- [ ] Tests: X/X PASS
- [ ] Validation: pilot rerun confirms invalid Python evidence is filtered upstream
- [ ] Evidence captured: `reports/TC-4255/evidence.md`
- [ ] Doc freshness: `python scripts/check_doc_freshness.py --uncommitted` — clean / acknowledged

## E2E verification

```bash
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -k allowlist -q
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_extract.py -k control_points -q
$env:PYTHONHASHSEED='0'; .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-python.yaml
```

**Expected results**:
- Targeted `understand` regressions pass.
- The rerun no longer carries the invalid Python imports/private-member evidence forward from `understand`.

## Integration boundary proven

**Upstream**: Python source files, README/docs snippets, and `ProductIdentity.runtime_import`.
**Downstream**: Planner/generate/evaluate consume `ApiSurface.import_allowlist`, public claims, and extracted snippets from `understand`.
**Contract**: Python public evidence must describe the runtime import and public API surface only; pip-package imports and private-member snippets are not valid downstream evidence.
