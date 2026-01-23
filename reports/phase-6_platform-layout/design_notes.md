# Phase 6 Design Notes: Platform-Aware Content Layout

**Date**: 2026-01-22
**Phase**: Phase 6 Platform Layout
**Agent**: Claude Sonnet 4.5

---

## Executive Summary

Phase 6 introduces **platform-aware content layout (V2)** to the foss-launcher system, enabling content organization by target platform (Python, TypeScript, Go, etc.) while maintaining backward compatibility with the legacy V1 layout.

**Key Achievement**: Implemented versioned content layout system with deterministic auto-detection, surgical spec updates, and comprehensive validation gates.

---

## Architectural Decisions

### 1. Versioned Layout System (V1/V2)

**Decision**: Implement two distinct layout modes with explicit versioning rather than forcing immediate migration.

**Rationale**:
- Preserves existing V1 content without breaking changes
- Allows gradual migration at section or family level
- Enables testing V2 layout in isolation before full rollout

**V1 Layout (Legacy)**:
```
content/<subdomain>/<family>/<locale>/...
```
No platform segment. Used by existing content.

**V2 Layout (Platform-Aware)**:
```
# Non-blog (language-folder based)
content/<subdomain>/<family>/<locale>/<platform>/...

# Blog (filename-based locale)
content/<subdomain>/<family>/<platform>/<slug>.<locale>.md
```

**Products Hard Requirement**: MUST use `/{locale}/{platform}/` NOT `/{platform}/` alone.

---

### 2. Auto-Detection Algorithm

**Decision**: Implement deterministic filesystem-based detection when `layout_mode: auto`.

**Algorithm**:
1. If `layout_mode == "v1"`: use V1 rules (explicit)
2. If `layout_mode == "v2"`: use V2 rules (explicit, requires `target_platform`)
3. If `layout_mode == "auto"`: check filesystem:
   - Non-blog: Check if `content/<subdomain>/<family>/<locale>/<platform>/` exists
   - Blog: Check if `content/<subdomain>/<family>/<platform>/` exists
   - If platform directory exists: V2
   - Else: V1

**Rationale**:
- No guesswork or heuristics
- Single source of truth: the filesystem structure
- Idempotent: same inputs always produce same result
- Supports mixed layouts within same repository

**Recorded State**: Resolver emits `layout_mode_resolved` in `ContentTarget` for audit trail.

---

### 3. Products Language-Folder Rule (Hard Requirement)

**Decision**: Products section MUST remain language-folder based in V2.

**Pattern Enforcement**:
```
✅ VALID:   content/products.aspose.org/words/en/python/
❌ INVALID: content/products.aspose.org/words/python/
```

**Rationale**:
- Products showcase localized marketing content
- Language is primary organizational axis
- Platform is secondary (same product, different SDK)
- Maintains SEO and i18n best practices

**Enforcement**:
- `validate_taskcards.py`: Rejects taskcard `allowed_paths` violating this rule
- `validate_platform_layout.py`: Gate F checks consistency across specs/schemas
- TC-540 resolver: Implements correct path construction logic

---

### 4. Schema Extensions

**Decision**: Add `target_platform` and `layout_mode` to `run_config` schema as first-class fields.

**Fields Added**:
```json
{
  "target_platform": {
    "type": "string",
    "description": "Target platform directory name (e.g., python, typescript, go). Required for V2."
  },
  "layout_mode": {
    "type": "string",
    "enum": ["auto", "v1", "v2"],
    "default": "auto"
  }
}
```

**Rationale**:
- Makes platform configuration explicit and validated
- Allows users to force V1 or V2 mode for testing
- Provides escape hatch if auto-detection fails

---

### 5. Template Hierarchy Extension

**Decision**: Templates must mirror content layout structure in V2.

**V2 Template Structure**:
```
specs/templates/<subdomain>/<family>/<locale>/<platform>/...
```

**New Token**: `__PLATFORM__`

**Rationale**:
- Templates can be platform-specific (e.g., Python-specific examples)
- Maintains symmetry between content and template organization
- Enables platform-specific rulesets and frontmatter contracts

**Validation**: Gate must lint for unresolved `__PLATFORM__` tokens in generated content.

---

### 6. Validation Gates Enhancement

**Decision**: Add new mandatory gate `content_layout_platform` (Gate F).

**Gate Responsibilities**:
- Verify schema includes `target_platform` and `layout_mode`
- Check binding spec exists (specs/32_platform_aware_content_layout.md)
- Validate TC-540 implements platform-aware resolution
- Ensure example configs demonstrate V2 usage
- Confirm key specs reference platform layout

**Exit Criteria**: BLOCKER on failure (no acceptable warnings).

**Rationale**:
- Prevents regression to V1-only thinking
- Enforces consistency across specs/schemas/taskcards
- Automated enforcement of "products language-folder rule"

---

### 7. Taskcard Scope Discipline

**Decision**: Update only taskcards directly affected by platform-aware paths.

**Updated Taskcards**:
- TC-540: Content path resolver (core implementation)
- TC-403: Frontmatter contract discovery (platform root resolution)
- TC-404: Hugo site context (platform detection)
- TC-570: Validation gates (platform layout gate)

**Not Updated**:
- Template engine taskcards (TC-510): Already use token-based system
- Writer/patcher taskcards: Accept `ContentTarget` objects from resolver
- LLM planning/scoring: Operate on abstract content targets

**Rationale**:
- Minimize change surface area
- Leverage existing abstractions (`ContentTarget` dataclass)
- Let resolver encapsulate all layout logic

---

### 8. Backward Compatibility Strategy

**Decision**: V1 paths continue working indefinitely; V2 is additive.

**Migration Path**:
1. Current state: All content uses V1 (no platform segment)
2. Pilot phase: Add V2 paths to `allowed_paths`, set `layout_mode: auto`
3. Resolver detects V1 (no platform dirs exist yet)
4. Writer creates V2 structure when generating new platform content
5. Auto-detection switches to V2 for that section
6. Old V1 paths remain accessible (no deletion required)

**Rationale**:
- Zero breaking changes
- Allows A/B testing V1 vs V2 performance
- Supports incremental rollout per family or subdomain

---

## Platform Mapping Design

**Decision**: Define platform families to handle tooling variations.

**Mapping Table** (from specs/32):
| target_platform | platform_family | Notes |
|----------------|----------------|-------|
| python | python | Single-platform family |
| typescript | node | Shares Node.js tooling |
| javascript | node | Shares Node.js tooling |
| go | go | Single-platform family |
| java | jvm | JVM-based |
| kotlin | jvm | JVM-based |

**Rationale**:
- `platform_family` used for adapter/tooling selection (future TC-500)
- `target_platform` used for content directory naming (TC-540)
- Enables shared adapters for TypeScript/JavaScript (both use Node.js)

---

## Traceability and Evidence

**Binding Specification**: specs/32_platform_aware_content_layout.md

**Traceability Matrix Entry**: REQ-010 (Platform-aware content layout V2)

**Taskcards Implementing**:
- TC-540: Content Path Resolver
- TC-403: Frontmatter Contract Discovery
- TC-404: Hugo Site Context
- TC-570: Validation Gates

**Validation Gates**:
- Gate F: Platform layout consistency (new)
- Gate B: Taskcard validation (updated with platform rule enforcement)

---

## Open Questions (None)

All design questions resolved during Phase 6 implementation. No entries required in `OPEN_QUESTIONS.md`.

---

## Lessons Learned

1. **Surgical edits work**: Updated only 4 taskcards instead of all 35. Abstraction boundaries held.
2. **Validation gates catch regressions**: Gate F immediately caught missing `{locale}/{platform}` literal in TC-540.
3. **Auto-detection is powerful**: Deterministic filesystem check eliminates configuration burden.
4. **Hard requirements prevent drift**: "Products language-folder rule" encoded in 3 validation layers.

---

## Future Considerations

1. **Platform aliasing**: May need `python-net` → `python` mapping for marketing vs technical names
2. **Locale fallback chains**: V2 doesn't change locale fallback, but worth documenting in TC-540
3. **Platform-specific rulesets**: Templates registry may need per-platform frontmatter contracts
4. **Migration tooling**: Future taskcard for V1→V2 batch migration script

---

**Status**: Design complete and validated. Ready for implementation phase.
