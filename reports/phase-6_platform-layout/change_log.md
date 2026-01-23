# Phase 6 Change Log: Platform-Aware Content Layout

**Date**: 2026-01-22
**Phase**: Phase 6 Platform Layout
**Agent**: Claude Sonnet 4.5

---

## Summary of Changes

**Total Files Modified**: 23
**Total Files Created**: 4
**Total Lines Changed**: ~1,200 (additions + modifications)

---

## Work Item A: Binding Spec and Site Repo Layout

### Created Files

#### 1. `specs/32_platform_aware_content_layout.md`
**Type**: NEW - Binding specification
**Lines**: 250+
**Purpose**: Core contract defining V1/V2 layouts, auto-detection algorithm, platform mapping

**Key Sections**:
- V1 vs V2 layout definitions with examples
- Auto-detection algorithm (deterministic filesystem check)
- Platform mapping table (target_platform → platform_family)
- Products language-folder hard requirement
- Validation gate requirements

**Binding Status**: Referenced by TC-540, TC-403, TC-404, TC-570, TRACEABILITY_MATRIX.md

---

### Modified Files

#### 2. `specs/18_site_repo_layout.md`
**Changes**:
- Added "V2 Layout (Platform-Aware)" section after V1 description
- Documented `/{locale}/{platform}/` structure for non-blog
- Documented `/{platform}/` structure for blog (filename-based locale)
- Added products hard requirement callout box
- Added cross-reference to specs/32

**Lines Modified**: ~40 additions

---

## Work Item B: Schema and Example Configs

### Modified Files

#### 3. `specs/schemas/run_config.schema.json`
**Changes**:
- Added `target_platform` field (type: string, required for V2)
- Added `layout_mode` field (enum: ["auto", "v1", "v2"], default: "auto")
- Added descriptions explaining V2 layout requirements
- Updated `path_patterns` to include platform segment examples

**Lines Modified**: ~25 additions

**JSON Structure**:
```json
"target_platform": {
  "type": "string",
  "description": "Target platform directory name (e.g., python, typescript, go). Required for V2 platform-aware layout."
},
"layout_mode": {
  "type": "string",
  "enum": ["auto", "v1", "v2"],
  "default": "auto",
  "description": "Content layout version: v1 (legacy), v2 (platform-aware), auto (detect)"
}
```

---

#### 4. `specs/examples/launch_config.example.yaml`
**Changes**:
- Added `target_platform: "python"` field
- Added `layout_mode: "auto"` field
- Updated `allowed_paths` section with V2 examples:
  - `content/products.aspose.org/note/en/python/`
  - `content/docs.aspose.org/note/en/python/`
- Added inline comments explaining V2 paths

**Lines Modified**: ~15 additions/modifications

---

#### 5. `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml`
**Changes**:
- Added `target_platform: "python"`
- Added `layout_mode: "auto"`
- Updated `allowed_paths` to include both V2 and V1 patterns:
  - V2: `content/products.aspose.org/3d/en/python/`
  - V1 fallback: `content/products.aspose.org/3d/en/`

**Lines Modified**: ~10 additions

---

#### 6. `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml`
**Changes**:
- Added `target_platform: "python"`
- Added `layout_mode: "auto"`
- Updated `allowed_paths` with V2+V1 patterns
- Added note about auto-detection behavior

**Lines Modified**: ~10 additions

---

## Work Item C: Templates Contract

### Modified Files

#### 7. `specs/20_rulesets_and_templates_registry.md`
**Changes**:
- Added "V2 Layout (Platform-Aware)" section describing template hierarchy
- Documented template structure: `specs/templates/<subdomain>/<family>/<locale>/<platform>/...`
- Added `__PLATFORM__` token requirement
- Added token linting requirement (no leftover placeholders)
- Specified that V2 templates are optional (fallback to V1 if missing)

**Lines Modified**: ~50 additions

**Key Addition**:
```markdown
### V2 Layout (Platform-Aware)
Templates: specs/templates/<subdomain>/<family>/<locale>/<platform>/...
Required tokens: __LOCALE__, __FAMILY__, __PLATFORM__
Token lint requirement: No leftover placeholders in generated content
```

---

## Work Item D: Resolver, Gates, and Taskcards

### Modified Files

#### 8. `plans/taskcards/TC-540_content_path_resolver.md`
**Changes**:
- Added `target_platform` and `layout_mode` to "Inputs" section
- Added "Mapping rules (binding for implementation)" section
- Documented layout mode resolution algorithm (3-step process)
- Added V2 path construction rules:
  - B.2) V2 Non-blog: `<content_root>/{locale}/{platform}/...`
  - C.2) V2 Blog: `<content_root>/<platform>/...<slug>.<lang>.md`
- Added products hard requirement enforcement
- Updated acceptance checks to include V2 validation
- Added reference to specs/32

**Lines Modified**: ~100 additions

**Critical Addition** (line 110):
```markdown
platform_root = "<content_root>/{locale}/{platform}"
**HARD REQUIREMENT**: Products MUST use /{locale}/{platform}/
```

---

#### 9. `plans/taskcards/TC-403_frontmatter_contract_discovery.md`
**Changes**:
- Added `target_platform` to "Inputs" section
- Added `layout_mode` to "Inputs" section
- Updated step 1 to include platform root resolution:
  - V1: `content/<subdomain>/<family>/<locale>/`
  - V2: `content/<subdomain>/<family>/<locale>/<platform>/`
- Added note about auto-detection integration with TC-540

**Lines Modified**: ~20 additions/modifications

---

#### 10. `plans/taskcards/TC-404_hugo_site_context_build_matrix.md`
**Changes**:
- Added `layout_mode_resolved_by_section` to "Outputs" section
- Added `detected_platforms_per_family` to "Outputs" section
- Added step 4 "Platform root detection (V2)":
  - Apply auto-detection algorithm from specs/32
  - Check if platform directories exist
  - Record resolved mode per section
- Updated acceptance checks to include platform detection

**Lines Modified**: ~30 additions

---

#### 11. `plans/taskcards/TC-570_validation_gates_ext.md`
**Changes**:
- Added "Platform layout gate (content_layout_platform)" to scope
- Added step 4 detailing platform layout gate validation:
  - Read resolved layout_mode from artifacts
  - Verify V2 paths contain correct platform segments
  - Verify products use `/{locale}/{platform}/` pattern
  - Check for unresolved `__PLATFORM__` tokens
  - Emit BLOCKER on violations
- Added platform layout acceptance checks (3 new items)
- Added reference to specs/32

**Lines Modified**: ~35 additions

---

#### 12. `specs/09_validation_gates.md`
**Changes**:
- Added Gate 4: "Platform layout compliance (content_layout_platform)"
- Documented gate validation criteria:
  - V2 path structure validation
  - Products language-folder rule enforcement
  - Token resolution checks
- Specified BLOCKER exit status (no acceptable warnings)
- Updated gate execution order to include new gate

**Lines Modified**: ~40 additions

---

## Work Item E: Validation Tooling

### Created Files

#### 13. `tools/validate_platform_layout.py`
**Type**: NEW - Validation script
**Lines**: 280
**Purpose**: Automated gate to enforce platform layout consistency across repository

**Validation Checks**:
1. Schema includes `target_platform` and `layout_mode` fields
2. Binding spec exists (specs/32_platform_aware_content_layout.md)
3. TC-540 mentions platform + V2 path forms
4. Example configs updated with platform fields
5. Key specs updated for V2 layout (specs/18, specs/20)

**Exit Codes**:
- 0: All checks pass
- 1: One or more checks failed

**Key Methods**:
- `check_schema_has_platform_fields()`: Validates run_config schema
- `check_binding_spec_exists()`: Ensures specs/32 exists and contains required terms
- `check_tc540_mentions_platform()`: Validates resolver taskcard
- `check_example_configs_updated()`: Checks example YAML files
- `check_key_specs_updated()`: Validates cross-references

---

### Modified Files

#### 14. `tools/validate_taskcards.py`
**Changes**:
- Added platform-aware layout validation (V2) section (lines 240-260)
- Implemented products language-folder rule enforcement:
  - Detects `content/products.aspose.org/` paths
  - Checks for platform segments (python, typescript, go, etc.)
  - Validates locale precedes platform (`/en/python/` not `/python/`)
  - Emits error referencing specs/32 on violation
- Added platform list (12 common platforms)

**Lines Modified**: ~25 additions

**Key Code**:
```python
# Platform-aware layout validation (V2)
if "content/products.aspose.org/" in path:
    platforms = ["python", "typescript", "javascript", "go", ...]
    for platform in platforms:
        if f"/{platform}/" in path:
            if not re.search(r'/[a-z]{2}/' + re.escape(platform) + r'/', path):
                errors.append(
                    f"Products MUST use /{{locale}}/{{platform}}/ "
                    f"NOT /{{platform}}/ alone."
                )
```

---

#### 15. `tools/validate_swarm_ready.py`
**Changes**:
- Added Gate F: "Platform layout consistency (V2)"
- Integrated `validate_platform_layout.py` into gate runner
- Updated gate count from 5 to 6
- Added platform layout gate description to output

**Lines Modified**: ~10 additions

---

## Documentation Updates

### Modified Files

#### 16. `GLOSSARY.md`
**Changes**:
- Added "Platform-Aware Layout Terms (V2)" section
- Defined 5 new terms:
  - **target_platform**: Directory segment for platform
  - **platform_family**: Adapter/tooling family identifier
  - **layout_mode**: Configuration field (auto|v1|v2)
  - **Auto-detection**: Deterministic filesystem-based algorithm
  - **Language-folder based**: Products rule (locale before platform)

**Lines Modified**: ~30 additions

---

#### 17. `TRACEABILITY_MATRIX.md`
**Changes**:
- Added REQ-010: "Platform-aware content layout (V2)"
- Listed binding spec: specs/32_platform_aware_content_layout.md
- Listed implementing taskcards: TC-540, TC-403, TC-404, TC-570
- Listed validation gates: Gate F (platform layout consistency)
- Defined acceptance criteria: Products use `/{locale}/{platform}/` paths in V2

**Lines Modified**: ~15 additions

---

## Bug Fixes

### Modified Files

#### 18. `reports/phase-5_swarm-hardening/gate_outputs/GATE_SUMMARY.md`
**Type**: Bug fix (broken link)
**Changes**:
- Fixed broken link to `00_TASKCARD_CONTRACT.md`
- Changed: `../../plans/taskcards/00_TASKCARD_CONTRACT.md`
- To: `../../../plans/taskcards/00_TASKCARD_CONTRACT.md`
- Reason: Corrected relative path from `gate_outputs/` subfolder

**Lines Modified**: 1 line

**Impact**: Gate D (markdown link validation) now passes

---

## Phase 6 Report Files

### Created Files

#### 19. `reports/phase-6_platform-layout/design_notes.md`
**Type**: NEW - Phase 6 design documentation
**Lines**: 250+
**Purpose**: Architectural decisions, rationale, and lessons learned

---

#### 20. `reports/phase-6_platform-layout/change_log.md`
**Type**: NEW - Phase 6 change documentation
**Lines**: This file
**Purpose**: Comprehensive log of all modifications

---

#### 21. `reports/phase-6_platform-layout/diff_manifest.md`
**Type**: NEW - Phase 6 file listing
**Purpose**: Structured list of all changed files with modification types

---

#### 22. `reports/phase-6_platform-layout/self_review_12d.md`
**Type**: NEW - Phase 6 self-assessment
**Purpose**: 12-dimensional quality review

---

#### 23. `reports/phase-6_platform-layout/gate_outputs/` (directory)
**Type**: NEW - Gate execution logs
**Contents**:
- `validate_taskcards.txt`
- `validate_swarm_ready.txt`
- `validate_platform_layout.txt`
- `validate_spec_pack.txt`
- `validate_markdown_links.txt`
- `audit_allowed_paths.txt`

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Files created | 4 (specs/tools/reports) |
| Files modified | 19 (specs/taskcards/tools/docs) |
| Taskcards updated | 4 (TC-540, TC-403, TC-404, TC-570) |
| New validation gates | 1 (Gate F) |
| Schema fields added | 2 (target_platform, layout_mode) |
| New glossary terms | 5 |
| Bug fixes | 1 (broken link) |
| Lines added (estimate) | ~1,200 |

---

## Git Status Before Commit

All files are currently untracked (new repository). Phase 6 changes are ready for initial commit once dependencies are installed and Gate A1 passes.

---

**Change log complete**. All modifications documented with rationale and traceability.
