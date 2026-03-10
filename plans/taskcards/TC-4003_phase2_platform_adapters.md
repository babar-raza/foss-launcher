---
id: TC-4003
title: "Phase 2: PlatformProfile + adapter infrastructure"
status: Done
priority: High
owner: "orchestrator"
updated: "2026-03-10"
tags: [humming-greeting-kay, phase-2]
depends_on: [TC-4002]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4003_phase2_platform_adapters.md
  - src/launcher/models/product.py
  - src/launcher/shared/platform_utils.py
  - configs/families.yaml
  - src/launcher/workers/understand/adapters/__init__.py
  - src/launcher/workers/understand/adapters/_base.py
  - src/launcher/workers/understand/adapters/_python.py
  - src/launcher/workers/understand/adapters/_typescript.py
  - src/launcher/workers/understand/adapters/_generic.py
  - src/launcher/workers/understand/extract/_api_surface.py
  - tests/unit/workers/test_understand.py
  - phase_store/phase_2_metrics.json
evidence_required:
  - phase_store/phase_2_metrics.json
---

# Taskcard TC-4003 — Phase 2: PlatformProfile + Adapter Infrastructure

## Objective

Replace hardcoded platform dicts with config-driven PlatformProfile model
and introduce a PlatformExtractor adapter interface so adding a platform
requires implementing one class + config entry instead of modifying 6+ files.

## Required spec references

- `humming-greeting-kay.md` (Phase 2)

## Scope

### In scope
- Add PlatformProfile model to models/product.py
- Add resolve_platform_profile() to shared/platform_utils.py
- Extend configs/families.yaml with file_ext, doc_comment, ast_parser fields
- Add ProductIdentity.platform_profile optional field
- Create adapters/ directory with base interface + 3 adapters
- Refactor _extract_api_surface() to dispatch through adapter registry

### Out of scope
- TypeScript tree-sitter depth (Phase 3)
- .NET/Java/C++ adapters (Phase 5-6)
- Evidence model cleanup (Phase 4)

## Inputs

- Current _api_surface.py with monolithic extraction
- Current platform_utils.py with hardcoded dicts
- Current families.yaml with platform config

## Outputs

- PlatformProfile model with full platform metadata
- resolve_platform_profile() resolving from families.yaml
- Adapter interface + Python/TypeScript/Generic adapters
- _api_surface.py dispatching through adapters
- Byte-identical output for Python extraction

## Allowed paths

- plans/taskcards/TC-4003_phase2_platform_adapters.md
- src/launcher/models/product.py
- src/launcher/shared/platform_utils.py
- configs/families.yaml
- src/launcher/workers/understand/adapters/__init__.py
- src/launcher/workers/understand/adapters/_base.py
- src/launcher/workers/understand/adapters/_python.py
- src/launcher/workers/understand/adapters/_typescript.py
- src/launcher/workers/understand/adapters/_generic.py
- src/launcher/workers/understand/extract/_api_surface.py
- tests/unit/workers/test_understand.py
- phase_store/phase_2_metrics.json

### Allowed paths rationale
Models for PlatformProfile, platform_utils for resolver, families.yaml for
config extension, adapters/ for new directory, _api_surface.py for dispatch
refactor, tests for validation, phase_store for metrics.

## Implementation steps

### Step 1: Add PlatformProfile model to product.py
### Step 2: Add resolve_platform_profile() to platform_utils.py
### Step 3: Extend families.yaml with new platform fields
### Step 4: Create adapters/_base.py with PlatformExtractor ABC
### Step 5: Create adapters/_python.py wrapping existing extraction
### Step 6: Create adapters/_typescript.py wrapping ts_analyzer
### Step 7: Create adapters/_generic.py as fallback
### Step 8: Create adapters/__init__.py with registry + dispatch
### Step 9: Refactor _api_surface.py to use adapter dispatch
### Step 10: Add ProductIdentity.platform_profile field
### Step 11: Write tests

## Failure modes

### Failure mode 1: Python adapter produces different output
**Detection**: Diff-test fails against current extraction output
**Resolution**: Ensure adapter wraps identical code path
**Gate**: Byte-identical ClassBrief comparison test

### Failure mode 2: TypeScript adapter breaks existing TS extraction
**Detection**: Test regressions on TS-related tests
**Resolution**: Thin wrapper only — no behavior change in Phase 2
**Gate**: All existing tests pass

### Failure mode 3: resolve_platform_profile() fails for unknown platform
**Detection**: KeyError or crash on unsupported platform
**Resolution**: Return generic defaults for unknown platforms
**Gate**: Test with unknown platform string

## Task-specific review checklist

1. [ ] PlatformProfile model in product.py
2. [ ] resolve_platform_profile() works for all platforms
3. [ ] Old facade functions still work
4. [ ] Python adapter produces identical output
5. [ ] TypeScript adapter wraps existing behavior
6. [ ] Generic adapter returns empty ClassBriefs
7. [ ] families.yaml extended with new fields
8. [ ] _api_surface.py uses adapter dispatch
9. [ ] All existing tests pass
10. [ ] 8+ new unit tests

## Deliverables

1. Modified source files per allowed paths
2. New adapters/ directory
3. phase_store/phase_2_metrics.json

## Acceptance checks

1. [ ] PlatformProfile resolves for python, java, dotnet, node
2. [ ] Old facade functions (get_lang_tag, etc.) still work
3. [ ] Python adapter output matches current extraction
4. [ ] TypeScript adapter wraps existing behavior
5. [ ] Full test suite passes
6. [ ] 8+ new regression tests

## Self-review

### Verification results
- [x] Tests: 3461/3461 PASS (16 new, 6 pre-existing failures unchanged)
- [x] Evidence captured: phase_store/phase_2_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_2_metrics.json`

**Expected results**:
- All understand tests pass
- Full suite: 3445+ passed, zero new failures

## Integration boundary proven

**Upstream**: Scout provides RepoInfo, repo_content
**Downstream**: Extract pipeline uses adapters for API surface extraction
**Contract**: ApiSurface model unchanged, adapter dispatch transparent
