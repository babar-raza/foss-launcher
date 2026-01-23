# Templates Directory

This folder is intentionally checked in even when the full template corpus lives elsewhere.

## Binding contract

Templates support two layout versions. See `specs/32_platform_aware_content_layout.md` for binding rules.

### V1 Layout (Legacy - No Platform Segment)

At runtime, templates MUST exist under:

```
Non-blog: specs/templates/<subdomain>/<family>/<locale>/...
Blog:     specs/templates/blog.aspose.org/<family>/...
```

Example: `specs/templates/docs.aspose.org/cells/en/quickstart/_index.md`

### V2 Layout (Platform-Aware)

At runtime, templates MUST exist under:

```
Non-blog: specs/templates/<subdomain>/<family>/<locale>/<platform>/...
Blog:     specs/templates/blog.aspose.org/<family>/<platform>/...
```

Example: `specs/templates/docs.aspose.org/cells/en/python/quickstart/_index.md`

**Products MUST use language-folder based paths** (see `specs/32_platform_aware_content_layout.md`):
- ✅ VALID: `specs/templates/products.aspose.org/cells/en/python/...`
- ❌ INVALID: `specs/templates/products.aspose.org/cells/python/...`

### Subdomain values

Where `<subdomain>` is one of:
- products.aspose.org
- docs.aspose.org
- reference.aspose.org
- kb.aspose.org
- blog.aspose.org

### Related specs
- `specs/32_platform_aware_content_layout.md` — binding rules for V1/V2 layout detection
- `specs/20_rulesets_and_templates_registry.md` — template selection and token requirements

## How to supply templates
Any of the following are acceptable, as long as the resolved paths match the contract above:
- git submodule that populates `specs/templates/`
- bootstrap step that clones a templates repo into `specs/templates/`
- CI step that downloads templates as an artifact into `specs/templates/`

## Versioning
`run_config.templates_version` is a required input for determinism. The implementation MUST:
- record the templates version in artifacts and telemetry
- record the exact template file path used per generated page

If templates are sourced from another repo, the templates_version SHOULD be that repo's git SHA or tag.
