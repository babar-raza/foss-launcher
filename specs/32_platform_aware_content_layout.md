# Platform-Aware Content Layout (V2) — Binding Contract

## Purpose

This document defines **version-aware content layout** for aspose.org site content, enabling platform-specific directory organization while maintaining backward compatibility with legacy layouts.

**Status**: Binding. All path resolution, template selection, and validation gates MUST conform to this specification.

---

## Terminology

### target_platform
The **directory segment** representing the target platform in content paths.

Examples: `python`, `typescript`, `javascript`, `go`, `java`, `cpp`, `ruby`, `php`

This is the literal folder name used in V2 layout paths.

### platform_family
The **adapter/tooling family** identifier used for repo detection and platform hints.

Examples: `node` (for typescript/javascript), `python`, `go`, `dotnet`, `java`, `cpp`

Mapping from `target_platform` to `platform_family` is defined in the Platform Mapping Table below.

---

## Layout Definitions

### V1 Layout (Legacy, No Platform Segment)

**Non-blog sections** (products, docs, kb, reference):
```
{subdomain_root}/{family}/{locale}/...
```

Examples:
- `content/docs.aspose.org/cells/en/`
- `content/products.aspose.org/words/de/`
- `content/kb.aspose.org/3d/ja/`
- `content/reference.aspose.org/pdf/zh/`

**Blog section**:
```
{subdomain_root}/{family}/...
```
Localization: filename-based (e.g., `index.md`, `index.de.md`)

Examples:
- `content/blog.aspose.org/words/`
- `content/blog.aspose.org/cells/`

---

### V2 Layout (Platform-Aware)

**Non-blog sections** (products, docs, kb, reference):
```
{subdomain_root}/{family}/{locale}/{platform}/...
```

**HARD REQUIREMENT**: Products MUST remain **language-folder based**.
This means: `/words/en/typescript/` NOT `/words/typescript/`

Examples:
- `content/docs.aspose.org/cells/es/python/`
- `content/products.aspose.org/words/en/typescript/`
- `content/kb.aspose.org/slides/en/go/`
- `content/reference.aspose.org/pdf/de/python/`

**Blog section**:
```
{subdomain_root}/{family}/{platform}/...
```
Localization: filename-based (unchanged from V1)

Examples:
- `content/blog.aspose.org/words/python/`
- `content/blog.aspose.org/cells/typescript/`

---

## layout_mode Configuration

The `layout_mode` field in run configuration controls path resolution behavior.

**Type**: enum string
**Values**: `v1` | `v2` | `auto`
**Default**: `auto`

### Mode Behaviors

#### `v1` (Forced Legacy)
- Always resolves paths WITHOUT platform segment
- Ignores `target_platform` in path construction
- Use case: Legacy content migration, V1-only families

#### `v2` (Forced Platform-Aware)
- Always resolves paths WITH platform segment
- Requires `target_platform` to be specified in configuration
- Fails if `target_platform` is missing
- Use case: New product launches, platform-specific content

#### `auto` (Deterministic Detection)
The system MUST use the following deterministic algorithm:

**For each section** in `required_sections`:

1. **Non-blog sections** (products, docs, kb, reference):
   ```
   expected_v2_path = {subdomain_root}/{family}/{locale}/{target_platform}/

   IF directory exists at expected_v2_path:
       layout_mode_resolved = v2
   ELSE:
       layout_mode_resolved = v1
   ```

2. **Blog section**:
   ```
   expected_v2_path = {subdomain_root}/{family}/{target_platform}/

   IF directory exists at expected_v2_path:
       layout_mode_resolved = v2
   ELSE:
       layout_mode_resolved = v1
   ```

**Detection Requirements**:
- Detection MUST occur at planning time (before path resolution)
- Detection MUST be performed against the site repo filesystem
- Detection MUST be recorded in artifacts (see `TC-404_hugo_site_context_build_matrix.md`)
- Detection MUST be deterministic (same filesystem state → same result)

**Auto-detection outputs**:
```json
{
  "layout_mode_resolved_by_section": {
    "products": "v2",
    "docs": "v2",
    "kb": "v1",
    "reference": "v2",
    "blog": "v2"
  }
}
```

---

## Platform Mapping Table

Maps `target_platform` (directory name) to `platform_family` (adapter identifier).

| target_platform | platform_family | Notes |
|----------------|-----------------|-------|
| `python` | `python` | Python SDKs/libraries |
| `typescript` | `node` | TypeScript/Node.js SDKs |
| `javascript` | `node` | JavaScript/Node.js SDKs |
| `go` | `go` | Go SDKs/libraries |
| `java` | `java` | Java SDKs/libraries |
| `dotnet` | `dotnet` | .NET SDKs (C#, F#, VB.NET) |
| `cpp` | `cpp` | C++ SDKs/libraries |
| `ruby` | `ruby` | Ruby SDKs/gems |
| `php` | `php` | PHP SDKs/libraries |
| `rust` | `rust` | Rust crates |
| `swift` | `swift` | Swift packages |
| `kotlin` | `kotlin` | Kotlin libraries |

**Extensibility**: This table MAY be extended for new platforms. Extensions MUST be documented here.

---

## Path Resolution Rules by Section

### Products Section
**V1**: `content/products.aspose.org/{family}/{locale}/`
**V2**: `content/products.aspose.org/{family}/{locale}/{platform}/`

**Binding constraint**: Products MUST use language-folder based paths in V2.
Example: `/words/en/typescript/` NOT `/words/typescript/`

### Docs Section
**V1**: `content/docs.aspose.org/{family}/{locale}/`
**V2**: `content/docs.aspose.org/{family}/{locale}/{platform}/`

### KB Section
**V1**: `content/kb.aspose.org/{family}/{locale}/`
**V2**: `content/kb.aspose.org/{family}/{locale}/{platform}/`

### Reference Section
**V1**: `content/reference.aspose.org/{family}/{locale}/`
**V2**: `content/reference.aspose.org/{family}/{locale}/{platform}/`

### Blog Section
**V1**: `content/blog.aspose.org/{family}/`
**V2**: `content/blog.aspose.org/{family}/{platform}/`

**Localization**: Filename-based in both V1 and V2 (no locale directory segment).

---

## Template Selection Impact

Templates MUST mirror the site content hierarchy.

**V2 template paths**:
```
specs/templates/{subdomain}/{family}/{locale}/{platform}/...
```

**V1 template paths** (legacy):
```
specs/templates/{subdomain}/{family}/{locale}/...
```

Template selection MUST:
1. Detect resolved `layout_mode` per section
2. Select templates from the matching hierarchy level
3. Fail with BLOCKER if template hierarchy does not match resolved layout mode

See [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) for template token requirements.

---

## Validation Requirements

### Content Layout Platform Gate

A validation gate MUST verify:

1. **V2 Path Structure**:
   - When `layout_mode` resolves to `v2` for a section:
     - Non-blog sections MUST contain `/{locale}/{platform}/` in output paths
     - Blog section MUST contain `/{platform}/` at correct depth
     - Products section MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)

2. **allowed_paths Compliance**:
   - All planned writes MUST be within taskcard `allowed_paths`
   - `allowed_paths` MUST include platform-level roots for V2 sections

3. **Token Elimination**:
   - Generated content MUST NOT contain unresolved `__PLATFORM__` tokens

4. **Consistency**:
   - Resolved `layout_mode` per section MUST be consistent across all planning artifacts

**Gate failure**: BLOCKER (no acceptable warnings)

See [specs/09_validation_gates.md](09_validation_gates.md) and [plans/taskcards/TC-570_validation_gates_ext.md](../plans/taskcards/TC-570_validation_gates_ext.md).

---

## Configuration Schema Impact

The `run_config.schema.json` MUST include:

```json
{
  "target_platform": {
    "type": "string",
    "description": "Target platform directory name (required for V2 layout)",
    "examples": ["python", "typescript", "javascript", "go"]
  },
  "layout_mode": {
    "type": "string",
    "enum": ["auto", "v1", "v2"],
    "default": "auto",
    "description": "Content layout version selection"
  }
}
```

See [Work Item B](#work-item-b) and [specs/schemas/run_config.schema.json](schemas/run_config.schema.json).

---

## Backward Compatibility

### Migration Path
1. **Existing V1 content**: Continues to work with `layout_mode: auto` or `layout_mode: v1`
2. **New V2 launches**: Use `layout_mode: v2` with `target_platform` specified
3. **Hybrid families**: Auto-detection handles mixed V1/V2 sections within same family

### Compatibility Guarantees
- V1 paths never break (auto-detection falls back to V1 when platform directories don't exist)
- V2 does not modify or migrate existing V1 content
- Tooling MUST support both layouts simultaneously

---

## Acceptance Criteria

✅ Path resolution includes platform segment for V2 sections
✅ Products remain language-folder based (`/{locale}/{platform}/`)
✅ Auto-detection is deterministic and reproducible
✅ Templates mirror content hierarchy (include platform level)
✅ Validation gates enforce V2 structure constraints
✅ Backward compatibility with V1 layouts preserved
✅ `target_platform` → `platform_family` mapping is explicit and extensible

---

## References

- [specs/18_site_repo_layout.md](18_site_repo_layout.md) — Site content layout contract
- [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) — Template selection rules
- [plans/taskcards/TC-540_content_path_resolver.md](../plans/taskcards/TC-540_content_path_resolver.md) — Path resolver implementation
- [specs/09_validation_gates.md](09_validation_gates.md) — Validation gate definitions
- [plans/taskcards/TC-570_validation_gates_ext.md](../plans/taskcards/TC-570_validation_gates_ext.md) — Extended validation gates

---

**Version**: 1.0
**Last Updated**: 2026-01-22
**Status**: Binding
