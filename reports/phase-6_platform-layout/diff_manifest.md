# Phase 6 Diff Manifest: Platform-Aware Content Layout

**Date**: 2026-01-22
**Phase**: Phase 6 Platform Layout
**Agent**: Claude Sonnet 4.5

---

## Files Added (4)

### Specifications

1. **specs/32_platform_aware_content_layout.md**
   - **Type**: NEW - Binding specification
   - **Size**: ~250 lines
   - **Purpose**: Core contract for V1/V2 layout, auto-detection, platform mapping
   - **Referenced By**: TC-540, TC-403, TC-404, TC-570, TRACEABILITY_MATRIX.md

### Tools

2. **tools/validate_platform_layout.py**
   - **Type**: NEW - Validation script
   - **Size**: ~280 lines
   - **Purpose**: Gate F enforcement (platform layout consistency)
   - **Exit Codes**: 0 (pass) / 1 (fail)

### Reports

3. **reports/phase-6_platform-layout/design_notes.md**
   - **Type**: NEW - Design documentation
   - **Size**: ~250 lines
   - **Purpose**: Architectural decisions and rationale

4. **reports/phase-6_platform-layout/change_log.md**
   - **Type**: NEW - Change documentation
   - **Size**: ~400 lines
   - **Purpose**: Comprehensive modification log

---

## Files Modified (19)

### Specifications (Binding)

5. **specs/18_site_repo_layout.md**
   - **Type**: MODIFIED - Specification
   - **Changes**: Added V2 layout section, products rule, cross-reference to specs/32
   - **Lines Changed**: +40
   - **Impact**: Documents platform-aware directory structure

6. **specs/20_rulesets_and_templates_registry.md**
   - **Type**: MODIFIED - Specification
   - **Changes**: Added V2 template hierarchy, __PLATFORM__ token requirement
   - **Lines Changed**: +50
   - **Impact**: Defines template organization for platform-specific content

7. **specs/09_validation_gates.md**
   - **Type**: MODIFIED - Specification
   - **Changes**: Added Gate 4 (content_layout_platform)
   - **Lines Changed**: +40
   - **Impact**: Mandates platform layout validation

### Schemas

8. **specs/schemas/run_config.schema.json**
   - **Type**: MODIFIED - JSON Schema
   - **Changes**: Added target_platform and layout_mode fields
   - **Lines Changed**: +25
   - **Impact**: Enables platform configuration validation

### Examples and Pilots

9. **specs/examples/launch_config.example.yaml**
   - **Type**: MODIFIED - Example config
   - **Changes**: Added target_platform, layout_mode, V2 allowed_paths examples
   - **Lines Changed**: +15
   - **Impact**: Demonstrates V2 configuration

10. **specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml**
    - **Type**: MODIFIED - Pilot config
    - **Changes**: Added target_platform, layout_mode, V2+V1 allowed_paths
    - **Lines Changed**: +10
    - **Impact**: Enables V2 testing for 3D pilot

11. **specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml**
    - **Type**: MODIFIED - Pilot config
    - **Changes**: Added target_platform, layout_mode, V2+V1 allowed_paths
    - **Lines Changed**: +10
    - **Impact**: Enables V2 testing for Note pilot

### Taskcards (4 out of 35 updated)

12. **plans/taskcards/TC-540_content_path_resolver.md**
    - **Type**: MODIFIED - Taskcard
    - **Changes**: Added V2 mapping rules, layout mode resolution algorithm, products rule
    - **Lines Changed**: +100
    - **Impact**: Core resolver implements platform-aware path construction

13. **plans/taskcards/TC-403_frontmatter_contract_discovery.md**
    - **Type**: MODIFIED - Taskcard
    - **Changes**: Added platform root resolution for V2
    - **Lines Changed**: +20
    - **Impact**: Discovers frontmatter in platform-specific directories

14. **plans/taskcards/TC-404_hugo_site_context_build_matrix.md**
    - **Type**: MODIFIED - Taskcard
    - **Changes**: Added platform detection step, outputs layout_mode_resolved
    - **Lines Changed**: +30
    - **Impact**: Detects platform directories and records layout mode

15. **plans/taskcards/TC-570_validation_gates_ext.md**
    - **Type**: MODIFIED - Taskcard
    - **Changes**: Added platform layout gate implementation step
    - **Lines Changed**: +35
    - **Impact**: Validation runner includes platform layout checks

### Validation Tools

16. **tools/validate_taskcards.py**
    - **Type**: MODIFIED - Validation script
    - **Changes**: Added products language-folder rule enforcement (lines 240-260)
    - **Lines Changed**: +25
    - **Impact**: Rejects taskcard allowed_paths violating products rule

17. **tools/validate_swarm_ready.py**
    - **Type**: MODIFIED - Validation script
    - **Changes**: Added Gate F (platform layout consistency)
    - **Lines Changed**: +10
    - **Impact**: Swarm readiness includes platform validation

### Documentation

18. **GLOSSARY.md**
    - **Type**: MODIFIED - Documentation
    - **Changes**: Added "Platform-Aware Layout Terms (V2)" section (5 terms)
    - **Lines Changed**: +30
    - **Impact**: Defines platform-related terminology

19. **TRACEABILITY_MATRIX.md**
    - **Type**: MODIFIED - Documentation
    - **Changes**: Added REQ-010 (Platform-aware content layout V2)
    - **Lines Changed**: +15
    - **Impact**: Maps platform requirement to specs/taskcards/gates

### Bug Fixes

20. **reports/phase-5_swarm-hardening/gate_outputs/GATE_SUMMARY.md**
    - **Type**: MODIFIED - Report (bug fix)
    - **Changes**: Fixed broken link path (../../ → ../../../)
    - **Lines Changed**: 1
    - **Impact**: Gate D (markdown links) now passes

### Phase 6 Reports

21. **reports/phase-6_platform-layout/diff_manifest.md**
    - **Type**: NEW - Report
    - **Size**: This file
    - **Purpose**: Structured file listing

22. **reports/phase-6_platform-layout/self_review_12d.md**
    - **Type**: NEW - Report
    - **Size**: ~350 lines
    - **Purpose**: 12-dimensional quality assessment

---

## Gate Outputs Created

### reports/phase-6_platform-layout/gate_outputs/

23. **validate_taskcards.txt**
    - **Type**: Command output
    - **Command**: `python tools/validate_taskcards.py`
    - **Result**: PASS (35/35 taskcards valid)

24. **validate_swarm_ready.txt**
    - **Type**: Command output
    - **Command**: `python tools/validate_swarm_ready.py`
    - **Result**: 5/6 gates pass (A1 fails - missing dependencies)

25. **validate_platform_layout.txt**
    - **Type**: Command output
    - **Command**: `python tools/validate_platform_layout.py`
    - **Result**: PASS (all platform layout checks pass)

26. **validate_spec_pack.txt**
    - **Type**: Command output
    - **Command**: `python tools/validate_spec_pack.py`
    - **Result**: FAIL (missing jsonschema module - expected)

27. **validate_markdown_links.txt**
    - **Type**: Command output
    - **Command**: `python tools/validate_markdown_links.py`
    - **Result**: PASS (159 files, all links valid)

28. **audit_allowed_paths.txt**
    - **Type**: Command output
    - **Command**: `python tools/audit_allowed_paths.py`
    - **Result**: PASS (0 violations, 0 critical overlaps)

---

## Directory Structure Changes

### Created Directories

```
reports/phase-6_platform-layout/
├── design_notes.md
├── change_log.md
├── diff_manifest.md
├── self_review_12d.md
└── gate_outputs/
    ├── validate_taskcards.txt
    ├── validate_swarm_ready.txt
    ├── validate_platform_layout.txt
    ├── validate_spec_pack.txt
    ├── validate_markdown_links.txt
    └── audit_allowed_paths.txt
```

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Files added** | 4 core files + 6 gate outputs = 10 |
| **Files modified** | 19 |
| **Total files changed** | 29 |
| **Taskcards updated** | 4 (out of 35 total) |
| **Specs added** | 1 (binding) |
| **Specs modified** | 3 |
| **Schemas modified** | 1 |
| **Tools added** | 1 |
| **Tools modified** | 2 |
| **Lines added (estimate)** | ~1,200 |
| **Bug fixes** | 1 |

---

## Critical Path Files

These files form the binding contract for platform-aware layout:

1. **specs/32_platform_aware_content_layout.md** (NEW - binding spec)
2. **plans/taskcards/TC-540_content_path_resolver.md** (MODIFIED - implements resolver)
3. **specs/schemas/run_config.schema.json** (MODIFIED - validates config)
4. **tools/validate_platform_layout.py** (NEW - enforces consistency)
5. **tools/validate_taskcards.py** (MODIFIED - enforces products rule)

---

## Files NOT Modified (Intentional)

The following files were explicitly **not modified** to maintain scope discipline:

- **Template engine taskcards** (TC-510, TC-511, TC-512): Already use token-based system, no changes needed
- **Writer/patcher taskcards** (TC-520, TC-530, TC-550, TC-560): Accept ContentTarget from resolver, no layout logic
- **LLM planning taskcards** (TC-400, TC-410, TC-420, TC-430): Operate on abstract targets
- **Adapter taskcards** (TC-500): platform_family field defined in specs/32, implementation deferred
- **Other 31 taskcards**: No direct interaction with content path construction

**Rationale**: Leverage existing abstractions; resolver encapsulates all layout logic.

---

## Validation Status

| Gate | Status | Notes |
|------|--------|-------|
| A1 (Spec pack) | ❌ FAIL | Missing jsonschema - requires `make install` (expected) |
| A2 (Plans) | ✅ PASS | Zero warnings |
| B (Taskcards) | ✅ PASS | 35/35 valid, products rule enforced |
| C (Status board) | ✅ PASS | Generated successfully |
| D (Markdown links) | ✅ PASS | 159 files, all links valid (fixed broken link) |
| E (Allowed paths) | ✅ PASS | 0 violations, 0 critical overlaps |
| F (Platform layout) | ✅ PASS | All consistency checks pass |

**Overall**: 6/7 gates pass. Gate A1 failure is expected (dependency prerequisite).

---

**Diff manifest complete**. All file changes documented with traceability.
