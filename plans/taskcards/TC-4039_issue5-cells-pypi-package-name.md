---
id: TC-4039
title: "ISSUE-5: Fix aspose-cells pilot canonical_import and runtime_import"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-11"
tags: [crispy-growing-pebble, issue-5]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-4039_issue5-cells-pypi-package-name.md
  - configs/pilots/aspose-cells-foss-python.yaml
evidence_required:
  - reports/TC-4039/evidence.md
---

# Taskcard TC-4039 — ISSUE-5: Fix cells pilot package names

## Objective
The cells-python pilot config has wrong import values: `canonical_import: "aspose_cells"` (should be `"aspose_cells_foss"` — the actual PyPI package name) and `runtime_import: "aspose_cells"` (should be `"aspose.cells"` — the actual Python runtime import). These wrong values cause the LLM to generate wrong pip install instructions and wrong import paths.

## Required spec references
- `crispy-growing-pebble.md` ISSUE-5

## Scope
### In scope
- Fix `canonical_import` in `configs/pilots/aspose-cells-foss-python.yaml`
- Fix `runtime_import` in `configs/pilots/aspose-cells-foss-python.yaml`

### Out of scope
- Other pilot configs (3D, Note, Slides — check separately if needed)
- Install command template in platform_utils.py (already correct: `pip install aspose-{family}-foss`)

## Inputs
- `configs/pilots/aspose-cells-foss-python.yaml`
- Platform template: `aspose_{family}_foss` for canonical_import → `aspose_cells_foss`
- Runtime template: `aspose.{family}` for runtime_import → `aspose.cells`

## Outputs
- Updated `configs/pilots/aspose-cells-foss-python.yaml` with correct values

## Allowed paths
- plans/taskcards/TC-4039_issue5-cells-pypi-package-name.md
- configs/pilots/aspose-cells-foss-python.yaml

## Implementation steps
### Step 1: Update canonical_import
Change `canonical_import: "aspose_cells"` → `canonical_import: "aspose_cells_foss"`

### Step 2: Update runtime_import
Change `runtime_import: "aspose_cells"` → `runtime_import: "aspose.cells"`

## Failure modes
### Failure mode 1: runtime_import change breaks existing code generation tests
**Detection**: Tests expecting `aspose_cells` fail
**Resolution**: Tests should expect `aspose.cells` which is the correct runtime import; update fixtures if needed
**Gate**: All code generation tests pass

### Failure mode 2: canonical_import change breaks import allowlist
**Detection**: section_validator rejects `import aspose_cells_foss`
**Resolution**: The validator already accepts both `canonical_import` and `runtime_import` bases; no change needed
**Gate**: Validation tests pass

### Failure mode 3: Different PyPI name assumed by test fixtures
**Detection**: Tests asserting `canonical_import == "aspose_cells"` fail
**Resolution**: Update fixture to `"aspose_cells_foss"`
**Gate**: All affected tests pass

## Task-specific review checklist
1. [ ] `canonical_import: "aspose_cells_foss"` in pilot config
2. [ ] `runtime_import: "aspose.cells"` in pilot config
3. [ ] Tests pass
4. [ ] No other cells pilot configs with wrong values

## Deliverables
1. Updated `configs/pilots/aspose-cells-foss-python.yaml`

## Acceptance checks
1. [ ] `canonical_import` is `aspose_cells_foss`
2. [ ] `runtime_import` is `aspose.cells`
3. [ ] Tests pass

## Self-review
### Verification results
- [ ] Tests: X/X PASS

## E2E verification
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/ --tb=short -q
```

## Integration boundary proven
**Upstream**: Pilot config read by run_config.py at pipeline start
**Downstream**: ProductIdentity built from config; used in section_prompt.py, section_validator.py, fallback.py
**Contract**: canonical_import = PyPI package name (underscored); runtime_import = Python import path
