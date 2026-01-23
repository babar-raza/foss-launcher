# V2 Platform-Aware Templates (blog)

This folder contains V2 (platform-aware) templates for the blog section.

## Layout version

Blog uses a different V2 pattern (no locale in path):

- **V2**: `specs/templates/blog.aspose.org/<family>/<platform>/...`
- See `specs/32_platform_aware_content_layout.md` for binding rules.

## Token requirements

- `__PLATFORM__` — e.g., `python`, `typescript`, `go`
- `__FAMILY__` — e.g., `cells`, `words`, `pdf`

Note: Blog uses filename-based localization, so `__LOCALE__` is not part of the path.

## Relationship to V1

V2 templates mirror V1 templates with platform awareness. The template selection
logic will choose V2 templates when `layout_mode=v2` or when auto-detection
finds a platform directory in the content path.

See: `specs/20_rulesets_and_templates_registry.md`
