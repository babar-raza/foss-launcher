# Platform-Aware Content Layout (V2) — Binding Contract

> **DEPRECATED (2026-02-09)**: V2 platform-aware layout has been removed. All content uses V1 layout only. This spec is retained for historical reference. All workers, validators, and downstream consumers MUST use V1 layout paths exclusively. References to `layout_mode`, `target_platform`, `platform_family`, and V2 path patterns are obsolete.

## Purpose

This document ~~defines~~ **previously defined** version-aware content layout for aspose.org site content. V2 platform-aware layout has been removed as of 2026-02-09. All content now uses V1 layout exclusively.

**Status**: ~~Binding~~ **DEPRECATED**. V2 layout is no longer supported. All path resolution, template selection, and validation MUST use V1 layout only. See `specs/18_site_repo_layout.md` for the current V1-only layout contract.

---

## Terminology (DEPRECATED)

> **DEPRECATED (2026-02-09)**: The following terminology was used for V2 platform-aware layout and is no longer active. Retained for historical reference only.

### target_platform (REMOVED)
~~The **directory segment** representing the target platform in content paths.~~

~~Examples: `python`, `typescript`, `javascript`, `go`, `java`, `cpp`, `ruby`, `php`~~

~~This is the literal folder name used in V2 layout paths.~~

**Status**: REMOVED. Platform segments are no longer used in content paths.

### platform_family (REMOVED)
~~The **adapter/tooling family** identifier used for repo detection and platform hints.~~

~~Examples: `node` (for typescript/javascript), `python`, `go`, `dotnet`, `java`, `cpp`~~

~~Mapping from `target_platform` to `platform_family` is defined in the Platform Mapping Table below.~~

**Status**: REMOVED. Platform family mapping is no longer used for path resolution.

---

## Layout Definitions (DEPRECATED)

> **DEPRECATED (2026-02-09)**: V2 layout has been removed. Only V1 layout is active. V2 sections below are retained for historical reference.

### V1 Layout (Active — No Platform Segment)

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

### V2 Layout (REMOVED — Platform-Aware)

> **REMOVED (2026-02-09)**: V2 platform-aware layout is no longer supported. The following is retained for historical reference only. Do NOT use V2 paths in any new work.

~~**Non-blog sections** (products, docs, kb, reference):~~
```
# REMOVED — Do not use
# {subdomain_root}/{family}/{locale}/{platform}/...
```

~~**Blog section**:~~
```
# REMOVED — Do not use
# {subdomain_root}/{family}/{platform}/...
```

---

## layout_mode Configuration (REMOVED)

> **REMOVED (2026-02-09)**: The `layout_mode` configuration field is no longer used. All content uses V1 layout exclusively. The `layout_mode`, `target_platform`, and auto-detection algorithm are all removed. If `layout_mode` or `target_platform` appear in run configs, they MUST be ignored.

~~The `layout_mode` field in run configuration controls path resolution behavior.~~

~~**Type**: enum string~~
~~**Values**: `v1` | `v2` | `auto`~~
~~**Default**: `auto`~~

**Current behavior**: All paths resolve as V1 (no platform segment). No configuration needed.

---

## Platform Mapping Table (REMOVED)

> **REMOVED (2026-02-09)**: Platform mapping is no longer used for path resolution. This table is retained for historical reference only.

~~Maps `target_platform` (directory name) to `platform_family` (adapter identifier).~~

| target_platform | platform_family | Notes | Status |
|----------------|-----------------|-------|--------|
| `python` | `python` | Python SDKs/libraries | REMOVED |
| `typescript` | `node` | TypeScript/Node.js SDKs | REMOVED |
| `javascript` | `node` | JavaScript/Node.js SDKs | REMOVED |
| `go` | `go` | Go SDKs/libraries | REMOVED |
| `java` | `java` | Java SDKs/libraries | REMOVED |
| `dotnet` | `dotnet` | .NET SDKs (C#, F#, VB.NET) | REMOVED |
| `cpp` | `cpp` | C++ SDKs/libraries | REMOVED |
| `ruby` | `ruby` | Ruby SDKs/gems | REMOVED |
| `php` | `php` | PHP SDKs/libraries | REMOVED |
| `rust` | `rust` | Rust crates | REMOVED |
| `swift` | `swift` | Swift packages | REMOVED |
| `kotlin` | `kotlin` | Kotlin libraries | REMOVED |

---

## Path Resolution Rules by Section (DEPRECATED)

> **DEPRECATED (2026-02-09)**: V2 paths are removed. Only V1 paths below are active.

### Products Section
**V1 (active)**: `content/products.aspose.org/{family}/{locale}/`
~~**V2**: `content/products.aspose.org/{family}/{locale}/{platform}/`~~ (REMOVED)

### Docs Section
**V1 (active)**: `content/docs.aspose.org/{family}/{locale}/`
~~**V2**: `content/docs.aspose.org/{family}/{locale}/{platform}/`~~ (REMOVED)

### KB Section
**V1 (active)**: `content/kb.aspose.org/{family}/{locale}/`
~~**V2**: `content/kb.aspose.org/{family}/{locale}/{platform}/`~~ (REMOVED)

### Reference Section
**V1 (active)**: `content/reference.aspose.org/{family}/{locale}/`
~~**V2**: `content/reference.aspose.org/{family}/{locale}/{platform}/`~~ (REMOVED)

### Blog Section
**V1 (active)**: `content/blog.aspose.org/{family}/`
~~**V2**: `content/blog.aspose.org/{family}/{platform}/`~~ (REMOVED)

**Localization**: Filename-based (no locale directory segment).

---

## Template Selection Impact (DEPRECATED)

> **DEPRECATED (2026-02-09)**: V2 template paths are removed. Templates use V1 hierarchy only.

Templates MUST mirror the site content hierarchy.

**V1 template paths (active)**:
```
specs/templates/{subdomain}/{family}/{locale}/...
```

~~**V2 template paths**:~~
```
# REMOVED — Do not use
# specs/templates/{subdomain}/{family}/{locale}/{platform}/...
```

Template selection MUST:
1. Select templates from the V1 hierarchy
2. Templates MUST NOT include `__PLATFORM__` directory segments

See [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) for template token requirements.

---

## Validation Requirements (DEPRECATED)

> **DEPRECATED (2026-02-09)**: Gate 4 (Platform Layout Compliance) has been removed from `specs/09_validation_gates.md`. V2 path validation is no longer performed.

### Content Layout Platform Gate (REMOVED)

~~A validation gate MUST verify V2 path structure, platform-level allowed_paths, and token elimination.~~

**Current validation**: Gate 11 (Template Token Lint) now treats `__PLATFORM__`, `__PLATFORM_CAPITALIZED__`, and `__PLUGIN_PLATFORM__` as blocklisted tokens. Any occurrence triggers error code `GATE_TEMPLATE_V2_TOKEN_LEAKED`.

See [specs/09_validation_gates.md](09_validation_gates.md).

---

## Configuration Schema Impact (DEPRECATED)

> **DEPRECATED (2026-02-09)**: `target_platform` and `layout_mode` fields are removed from the active run_config schema. They may still appear in legacy configs but MUST be ignored.

~~The `run_config.schema.json` MUST include `target_platform` and `layout_mode`.~~

**Current schema**: Neither `target_platform` nor `layout_mode` is required or used. If present in legacy configs, they are silently ignored.

---

## Backward Compatibility (DEPRECATED)

> **DEPRECATED (2026-02-09)**: With V2 removed, backward compatibility concerns are moot. All content is V1-only.

### Migration Path
1. **All content**: Uses V1 layout exclusively
2. ~~**New V2 launches**~~: REMOVED
3. ~~**Hybrid families**~~: REMOVED

### Current Guarantees
- V1 paths are the only supported layout
- No platform segments in any content paths
- No `layout_mode` detection or configuration needed

---

## Acceptance Criteria (DEPRECATED)

> **DEPRECATED (2026-02-09)**: Original V2 acceptance criteria are superseded. Current acceptance: all content uses V1 layout only.

~~✅ Path resolution includes platform segment for V2 sections~~
~~✅ Products remain language-folder based (`/{locale}/{platform}/`)~~
~~✅ Auto-detection is deterministic and reproducible~~
~~✅ Templates mirror content hierarchy (include platform level)~~
~~✅ Validation gates enforce V2 structure constraints~~
✅ V1 layout is the sole supported layout
✅ No `__PLATFORM__` tokens in generated content (enforced by Gate 11)

---

## References

- [specs/18_site_repo_layout.md](18_site_repo_layout.md) — Site content layout contract
- [specs/20_rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) — Template selection rules
- [plans/taskcards/TC-540_content_path_resolver.md](../plans/taskcards/TC-540_content_path_resolver.md) — Path resolver implementation
- [specs/09_validation_gates.md](09_validation_gates.md) — Validation gate definitions
- [plans/taskcards/TC-570_validation_gates_ext.md](../plans/taskcards/TC-570_validation_gates_ext.md) — Extended validation gates

---

**Version**: 2.0
**Last Updated**: 2026-02-09
**Status**: DEPRECATED (V2 removed; V1-only)
