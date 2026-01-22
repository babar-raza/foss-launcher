# Section Templates

## Goal
Make section content consistent, reusable, and easy to validate.

## Common template rules
- Use ProductFacts fields, do not invent.
- Include claim markers for every factual bullet.
- Use snippet_catalog snippets by tag.
- Keep consistent naming across all pages.

## Products section template (landing)
Required headings:
1) Overview
2) Key Features
3) Quickstart
4) Supported Environments
5) Links and Resources

Rules:
- Key Features must map to claim_ids.
- Quickstart must include at least one code snippet.
- Supported formats only if grounded.

## Docs section templates
Doc types:
- Quickstart tutorial
- How-to guides (one per workflow tag)

Required headings (how-to):
1) Goal
2) Prerequisites
3) Steps
4) Code Example
5) Notes and Troubleshooting
6) Related Links

## Reference section templates
- reference landing: modules/namespaces list and navigation
- module page: purpose, key symbols, small usage snippet

Rules:
- Do not fabricate APIs. Only list symbols extracted in ProductFacts.api_surface_summary.
- Keep reference pages concise and link to docs for deeper explanation.

## KB section templates
KB types:
- FAQ
- Troubleshooting
- Performance and Deployment
- Known limitations

Required headings:
1) Symptoms or Question
2) Cause
3) Resolution
4) Notes
5) Related Links

Rules:
- All limitations must be grounded claims.
- Avoid guarantees.

## Blog templates
Announcement post:
- What is it
- Why it matters
- Quickstart
- Links

Deep dive:
- Workflow-based narrative using snippets

Rules:
- Blog must not introduce new claims beyond ProductFacts.

## Frontmatter requirements
Frontmatter is site-specific. Implementers must use examples/frontmatter_models.md and launch_config section mapping.

## Universality: Template Variants

### Template selection rules (binding)
Template selection MUST be a function of:
- section (products/docs/reference/kb/blog)
- platform_family (from repo_profile)
- product_type (optional RunConfig)
- launch_tier (minimal/standard/rich)
- locale (RunConfig)

This prevents “one template fits all” failures when repo quality or product type varies.

### Required template variants
For each section template family, maintain at least:
- `minimal` variant: smallest safe page structure (no deep claims)
- `standard` variant: normal structure (features + workflows + examples)
- `rich` variant: optional sections (FAQ, troubleshooting, deeper guides)

Writers MUST remove empty optional sections instead of leaving placeholders.

### Repo-driven optional blocks
Templates SHOULD support optional blocks for:
- Limitations / “Not supported yet”
- Dependencies / optional extras
- Testfiles/assets handling note (when repo includes binary samples)
