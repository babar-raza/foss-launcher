# Platform-Aware Content Layout (V2) — Binding Contract

## Purpose

This document defines version-aware content layout for aspose.org site content. V2 platform-aware layout adds a `platform` segment (e.g., `python`) to content paths and URLs, enabling multi-platform documentation under a single product family.

**Status**: Binding
**Version**: 2.0
**Last Updated**: 2026-02-12

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

### V1 Layout (Legacy — No Platform Segment)

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

### V2 Layout (Active — Platform-Aware)

**Non-blog sections** (products, docs, kb, reference):
```
{subdomain_root}/{family}/{locale}/{platform}/...
```

Examples:
- `content/docs.aspose.org/cells/en/python/`
- `content/products.aspose.org/words/de/java/`
- `content/kb.aspose.org/3d/ja/python/`
- `content/reference.aspose.org/pdf/zh/dotnet/`

**Blog section**:
```
{subdomain_root}/{family}/{platform}/...
```

Examples:
- `content/blog.aspose.org/words/python/`
- `content/blog.aspose.org/cells/java/`

---

## layout_mode Configuration

The `layout_mode` field in run configuration controls path resolution behavior.

**Type**: enum string
**Values**: `v1` | `v2` | `auto`
**Default**: `auto`

### Auto-detection algorithm

When `layout_mode` is `auto`:
1. If `target_platform` is explicitly set in run config → use V2
2. If repo analysis detects a single dominant platform → use V2 with detected platform
3. Otherwise → use V1

### Explicit mode

- `layout_mode: v2` requires `target_platform` to be set (validation error if missing)
- `layout_mode: v1` ignores `target_platform` even if set

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

---

## Path Resolution Rules by Section

### Products Section
**V1**: `content/products.aspose.org/{family}/{locale}/`
**V2**: `content/products.aspose.org/{family}/{locale}/{platform}/`

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

**Localization**: Filename-based (no locale directory segment).

---

## Template Selection Impact

Templates MUST mirror the site content hierarchy.

**V1 template paths (legacy)**:
```
specs/templates/{subdomain}/{family}/{locale}/...
```

**V2 template paths (active)**:
```
specs/templates/{subdomain}/{family}/__LOCALE__/__PLATFORM__/...
```

Template selection MUST:
1. Select templates from the V2 hierarchy when `layout_mode` is `v2`
2. Templates MUST include `__PLATFORM__` directory segments for V2 layout
3. The `__PLATFORM__` token is resolved to the `target_platform` value at generation time

See [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) for template token requirements.

---

## Validation Requirements

### Content Layout Platform Gate

A validation gate MUST verify V2 path structure, platform-level allowed_paths, and token elimination.

Gate 11 (Template Token Lint) treats unreplaced `__PLATFORM__`, `__PLATFORM_CAPITALIZED__`, and `__PLUGIN_PLATFORM__` tokens as errors with code `GATE_TEMPLATE_V2_TOKEN_LEAKED`. These tokens must be resolved before output.

See [specs/09_validation_gates.md](09_validation_gates.md).

---

## Configuration Schema Impact

The `run_config.schema.json` MUST include `target_platform` and `layout_mode`.

- `target_platform` (string): The platform directory segment (e.g., `python`)
- `layout_mode` (enum: `v1` | `v2` | `auto`): Controls path resolution behavior

---

## Backward Compatibility

### Migration Path
1. **Existing V1 content**: Remains accessible at V1 paths. No migration required for existing content.
2. **New V2 launches**: New pilots targeting a specific platform SHOULD use V2 layout.
3. **Hybrid families**: A family may have both V1 (unplatformed) and V2 (platformed) content if needed.

### Guarantees
- V1 paths continue to work when `layout_mode` is `v1`
- V2 paths add a platform segment but do not break V1 content
- Auto-detection is deterministic and reproducible

---

## Acceptance Criteria

- Path resolution includes platform segment for V2 sections
- Products remain language-folder based (`/{locale}/{platform}/`)
- Auto-detection is deterministic and reproducible
- Templates mirror content hierarchy (include platform level)
- Validation gates enforce V2 structure constraints
- V1 layout remains supported for backward compatibility
- No unreplaced `__PLATFORM__` tokens in generated content (enforced by Gate 11)

---

## References

- [specs/18_site_repo_layout.md](18_site_repo_layout.md) — Site content layout contract
- [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) — Template selection rules
- [plans/taskcards/TC-540_content_path_resolver.md](../plans/taskcards/TC-540_content_path_resolver.md) — Path resolver implementation
- [specs/09_validation_gates.md](09_validation_gates.md) — Validation gate definitions
- [plans/taskcards/TC-570_validation_gates_ext.md](../plans/taskcards/TC-570_validation_gates_ext.md) — Extended validation gates

---

**Version**: 2.0
**Last Updated**: 2026-02-12
**Status**: Binding
