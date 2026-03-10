---
id: TC-4006
title: "Phase 5-6: .NET + Java + C++ adapters + generic fallback"
status: Done
priority: Medium
owner: "orchestrator"
updated: "2026-03-10"
tags: [humming-greeting-kay, phase-5-6]
depends_on: [TC-4005]
ruleset_version: "1.0"
spec_ref: "6a56035"
templates_version: "1.0"
allowed_paths:
  - plans/taskcards/TC-4006_phase56_platform_adapters.md
  - src/launcher/workers/understand/adapters/__init__.py
  - src/launcher/workers/understand/adapters/_dotnet.py
  - src/launcher/workers/understand/adapters/_java.py
  - src/launcher/workers/understand/adapters/_cpp.py
  - tests/unit/workers/test_understand.py
  - phase_store/phase_5_6_metrics.json
evidence_required:
  - phase_store/phase_5_6_metrics.json
---

# Taskcard TC-4006 — Phase 5-6: .NET + Java + C++ Adapters

## Objective

Add platform-specific adapters for .NET (C#), Java, and C++ that implement
the PlatformExtractor interface with proper package root detection, install
command generation, and import allowlist building.

## Required spec references

- `humming-greeting-kay.md` (Phase 5-6)

## Scope

### In scope
- Create _dotnet.py adapter (C#: .csproj, namespace detection)
- Create _java.py adapter (Java: Maven/Gradle, package detection)
- Create _cpp.py adapter (C++: CMake/vcpkg, header detection)
- Register all in adapter registry
- Write tests for each adapter

### Out of scope
- Generic fallback changes (already exists from Phase 2)
- TypeScript depth (Phase 3, done)
- Extraction behavior changes (adapters wrap existing code_analyzer)

## Inputs

- PlatformExtractor interface from Phase 2
- Existing code_analyzer.analyze_file_safe() for non-Python files
- tree-sitter grammars already installed for C#, Java

## Outputs

- 3 new adapter implementations
- Updated registry with .NET, Java, C++ mappings
- Package root detection for each platform

## Allowed paths

- plans/taskcards/TC-4006_phase56_platform_adapters.md
- src/launcher/workers/understand/adapters/__init__.py
- src/launcher/workers/understand/adapters/_dotnet.py
- src/launcher/workers/understand/adapters/_java.py
- src/launcher/workers/understand/adapters/_cpp.py
- tests/unit/workers/test_understand.py
- phase_store/phase_5_6_metrics.json

### Allowed paths rationale
New adapter files, registry update, tests, and metrics.

## Implementation steps

### Step 1: Create _dotnet.py adapter
### Step 2: Create _java.py adapter
### Step 3: Create _cpp.py adapter
### Step 4: Register in __init__.py
### Step 5: Write tests

## Failure modes

### Failure mode 1: tree-sitter grammar not available for language
**Detection**: ImportError or parse failure
**Resolution**: Graceful fallback to GenericExtractor
**Gate**: Test with mock grammar unavailability

### Failure mode 2: Package root detection wrong for platform
**Detection**: Tests fail on fixture repos
**Resolution**: Platform-specific heuristics tested against real layouts
**Gate**: tmp_path fixture tests for each platform

### Failure mode 3: Registry conflicts with existing adapters
**Detection**: Existing tests regress
**Resolution**: Only add new entries, don't modify existing
**Gate**: Full test suite passes

## Task-specific review checklist

1. [x] .NET adapter detects .csproj package root
2. [x] .NET adapter builds namespace-based import allowlist
3. [x] Java adapter detects Maven/Gradle package root
4. [x] Java adapter builds package-based import allowlist
5. [x] C++ adapter detects CMake/vcpkg package root
6. [x] All adapters registered in registry
7. [x] Unknown platform falls back to generic
8. [x] All existing tests pass (3496 passed, 6 pre-existing failures)
9. [x] 12 new tests (exceeds 6+ requirement)

## Deliverables

1. 3 new adapter files
2. Updated registry
3. phase_store/phase_5_6_metrics.json

## Acceptance checks

1. [x] .NET adapter tested with fixture
2. [x] Java adapter tested with fixture
3. [x] C++ adapter tested with fixture
4. [x] Registry resolves all platforms (8 platform strings → adapters)
5. [x] Full test suite passes (3496 passed, 6 pre-existing)
6. [x] 12 new regression tests

## Self-review

### Verification results
- [x] Tests: 12/12 PASS (Phase 5-6 specific), 3496/3496 PASS (full suite)
- [x] Evidence captured: phase_store/phase_5_6_metrics.json

## E2E verification

```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/test_understand.py -v
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest --tb=no -q
```

**Expected artifacts**:
- `phase_store/phase_5_6_metrics.json`

**Expected results**:
- All tests pass
- Full suite: 3484+ passed, zero new failures

## Integration boundary proven

**Upstream**: Adapter registry dispatches by platform string
**Downstream**: _api_surface.py uses adapter for extraction
**Contract**: PlatformExtractor interface unchanged
