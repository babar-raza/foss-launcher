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

## Template Families

Templates are organized by **product family** (e.g., `cells`, `3d`, `note`). Each family represents a distinct product line with its own content structure.

### Available Families (TC-700)
As of templates.v1, the following family template packs are available:
- `cells` — Original family for spreadsheet/Excel products
- `3d` — Family for 3D modeling and CAD products (Pilot-1)
- `note` — Family for note-taking and OneNote products (Pilot-2)

All families share the same template structure and token placeholders. The `__FAMILY__` token is replaced at generation time with the appropriate family name.

### Template Structure Per Family
Each family contains templates for all 5 subdomains:
- `products.aspose.org/<family>/` — Product marketing pages
- `docs.aspose.org/<family>/` — Documentation guides
- `reference.aspose.org/<family>/` — API reference
- `kb.aspose.org/<family>/` — Knowledge base and troubleshooting
- `blog.aspose.org/<family>/` — Blog posts and announcements

## Quotas and Page Selection

### Maximum Pages Per Section
Each section in the page plan can be limited by `max_pages` quotas to control site growth:

**Default quotas** (when not specified in run_config):
- Products: 50 pages per family
- Docs: 20 guides per family
- Reference: 30 API pages per family
- KB: 15 articles per family
- Blog: 5 posts per family

**Quota enforcement:**
1. Mandatory pages (see `specs/06_page_planning.md`) are always included
2. Optional pages are selected up to the `max_pages` limit
3. Selection is deterministic (ordered by evidence quality, then alphabetical slug)
4. If quotas are exceeded, lower-priority pages are skipped with telemetry warning

### Variant Selection Rules

Templates support multiple variants for the same page type. Variant selection is determined by:

**Launch tier** (from run_config or auto-detected):
- `minimal`: Use simple variants with minimal sections (safe for sparse repos)
- `standard`: Use normal variants with standard features (default)
- `rich`: Use full variants with optional sections (requires strong evidence)

**Platform family** (from repo_profile):
- Affects template token values and code example language
- Maps to `__PLATFORM__` token in V2 templates

**Product type** (optional in run_config):
- `cli`: Emphasizes commands and installation
- `sdk`/`library`: Emphasizes imports and API surface
- `service`: Emphasizes endpoints and authentication

**Selection algorithm:**
1. Resolve launch_tier based on evidence quality (see `specs/06_page_planning.md`)
2. Select template variant matching (section, launch_tier, product_type)
3. If no exact match, fall back to `standard` variant
4. If no `standard` variant exists, use first available variant
5. Record selected template path in page_plan artifacts

### Template Token Placeholders

All templates use `__UPPER_SNAKE__` token placeholders that are replaced during page generation:

**Common tokens:**
- `__FAMILY__` — Product family (cells, 3d, note)
- `__LOCALE__` — Language code (en, de, fr)
- `__PLATFORM__` — Target platform (python, typescript, go)
- `__CONVERTER_SLUG__` — Converter identifier
- `__FORMAT_SLUG__` — Format identifier
- `__HEAD_TITLE__`, `__HEAD_DESCRIPTION__` — SEO metadata
- `__PAGE_TITLE__`, `__PAGE_DESCRIPTION__` — Page content
- `__BODY_*__` — Body section content (Markdown)

**Boolean toggles:**
- Must be replaced with `true` or `false` (no quotes)
- Examples: `__OVERVIEW_ENABLE__`, `__FAQ_ENABLE__`

**Conditional sections:**
- If a section `enable` is `false`, remove the entire section
- Never leave placeholder tokens in final content
