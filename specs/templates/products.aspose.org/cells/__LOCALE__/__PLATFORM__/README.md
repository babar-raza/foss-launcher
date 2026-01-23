# V2 Platform-Aware Templates (products)

This folder contains V2 (platform-aware) templates for the products section.

## Layout version

- **V2**: `specs/templates/products.aspose.org/<family>/<locale>/<platform>/...`
- See `specs/32_platform_aware_content_layout.md` for binding rules.

## HARD REQUIREMENT

Products MUST use language-folder based paths:
- ✅ VALID: `products.aspose.org/cells/en/python/...`
- ❌ INVALID: `products.aspose.org/cells/python/...`

## Token requirements

- `__LOCALE__` — e.g., `en`, `de`, `fr`
- `__PLATFORM__` — e.g., `python`, `typescript`, `go`
- `__FAMILY__` — e.g., `cells`, `words`, `pdf`

## Relationship to V1

V2 templates mirror V1 templates with platform awareness. The template selection
logic will choose V2 templates when `layout_mode=v2` or when auto-detection
finds a platform directory in the content path.

See: `specs/20_rulesets_and_templates_registry.md`
