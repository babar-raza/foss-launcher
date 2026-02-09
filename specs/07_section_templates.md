# Section Templates

## Goal
Make section content consistent, reusable, and easy to validate.

## Common template rules
- Use ProductFacts fields, do not invent.
- Include claim markers for every factual bullet.
- Use snippet_catalog snippets by tag.
- Keep consistent naming across all pages.

## Section-specific style overrides
The ruleset allows optional per-section style configuration via `style_by_section`:
- `tone`: Controls the writing tone (e.g., "professional", "conversational", "technical")
- `voice`: Controls active/passive voice preference (e.g., "active", "passive", "direct")

**Default styles** (from `ruleset.v1.yaml`):
- products: professional tone, active voice
- docs: instructional tone, direct voice
- reference: technical tone, passive voice
- kb: conversational tone, active voice
- blog: informal tone, active voice

**Style application precedence:**
1. Section-specific `style_by_section` overrides (if defined in ruleset)
2. Global `style` defaults from ruleset
3. Template-specific style hints (fallback)

## Section-specific content limits
The ruleset supports optional per-section content limits via `limits_by_section`:
- `max_words`: Maximum word count per page in this section
- `max_headings`: Maximum number of headings per page
- `max_code_blocks`: Maximum number of code blocks per page

These limits help prevent content bloat and ensure pages remain focused. If not specified, no limits are enforced beyond template requirements.

## Products section template (landing)

**Mandatory pages** (TC-940):
- Overview/Landing page (slug: `overview` or `index`)

**Optional pages** (evidence-driven):
- Features page
- Quickstart page
- Supported Environments page

Required headings (landing page):
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

**Mandatory pages** (TC-940):
- Getting Started guide (slug: `getting-started`)
- At least one workflow-based how-to guide

**Optional pages** (evidence-driven):
- Additional how-to guides (one per validated workflow)
- Advanced tutorials
- Migration guides

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

**Mandatory pages** (TC-940):
- API Overview/Landing page (slug: `index` or `api-overview`)

**Optional pages** (evidence-driven):
- Module/namespace pages (prioritize by usage in snippets)
- Class/interface detail pages

Template types:
- reference landing: modules/namespaces list and navigation
- module page: purpose, key symbols, small usage snippet

Rules:
- Do not fabricate APIs. Only list symbols extracted in ProductFacts.api_surface_summary.
- Keep reference pages concise and link to docs for deeper explanation.

## KB section templates

**Mandatory pages** (TC-940):
- FAQ page
- Known Limitations page
- Basic troubleshooting guide

**Optional pages** (evidence-driven):
- Performance optimization guides
- Platform-specific deployment guides
- Additional troubleshooting scenarios

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

**Mandatory pages** (TC-940):
- Announcement post (product introduction)

**Optional pages** (evidence-driven):
- Deep-dive technical posts
- Release note style posts
- Use case showcases

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
- locale (RunConfig)
- launch_tier (minimal/standard/rich)
- product_type (optional RunConfig)

This prevents "one template fits all" failures when repo quality or product type varies.

### V1 template hierarchy (binding)

All templates use V1 layout (no platform folder):

```
Non-blog: specs/templates/<subdomain>/<family>/__LOCALE__/...
Blog:     specs/templates/blog.aspose.org/<family>/__POST_SLUG__/...
```

**Blog**: Blog templates do NOT use `__LOCALE__` folders. Blog URL structure is `blog.aspose.org/{family}/{slug}/`, so templates are rooted at `<family>/__POST_SLUG__/`.

> **Note (2026-02-09)**: V2 platform-aware layout has been removed. The `__PLATFORM__` token is obsolete and MUST NOT appear in any template paths. See `specs/32_platform_aware_content_layout.md` (DEPRECATED) for historical reference.

### Required template variants
For each section template family, maintain at least:
- `minimal` variant: smallest safe page structure (no deep claims)
- `standard` variant: normal structure (features + workflows + examples)
- `rich` variant: optional sections (FAQ, troubleshooting, deeper guides)

Writers MUST remove empty optional sections instead of leaving placeholders.

### Repo-driven optional blocks
Templates SHOULD support optional blocks for:
- Limitations / "Not supported yet"
- Dependencies / optional extras
- Testfiles/assets handling note (when repo includes binary samples)

---

## New Template Types (Content Distribution Strategy, 2026-02-04)

### TOC Template (docs/_index.md)

**Purpose**: Navigation hub for documentation section

**Page Role**: `toc`

**Required Headings**:
- Introduction
- Documentation Index
- Quick Links

**Content Structure**:

1. **Introduction** (1-2 paragraphs):
   - Brief description of product documentation structure
   - What users can find in this documentation
   - High-level overview of documentation organization

2. **Documentation Index**:
   - Hierarchical list of child pages with purpose
   - Each entry: link + 1-sentence description
   - Maintain logical grouping (Getting Started, Guides, Advanced)
   - Use bullet lists with proper nesting

3. **Quick Links**:
   - Link to products overview
   - Link to API reference
   - Link to KB articles
   - Link to GitHub repository

**Forbidden Content**:
- Code snippets (BLOCKER violation if present)
- Duplicating child page content
- Deep explanations of features or concepts
- Step-by-step tutorials

**Content Strategy**:
- `primary_focus`: "Navigation hub for all documentation pages"
- `forbidden_topics`: ["duplicate_child_content", "code_snippets", "deep_explanations"]
- `claim_quota`: {"min": 0, "max": 2}
- `child_pages`: Must be populated by W4 with all doc page slugs

**Template Location**: `specs/templates/docs.aspose.org/{family}/__LOCALE__/_index.md`

**Validation**: Gate 14 MUST validate TOC pages have NO code snippets (BLOCKER if violated)

**Example Structure**:
```markdown
---
title: "{Product} Documentation"
description: "Complete documentation for {Product} SDK"
---

## Introduction

Welcome to the {Product} documentation. This guide provides comprehensive information about using {Product} to {primary_use_case}.

## Documentation Index

### Getting Started
- [Installation Guide](getting-started/) - Set up {Product} in your environment
- [Quick Start](quick-start/) - Your first {Product} application

### Developer Guides
- [Developer Guide](developer-guide/) - Comprehensive scenario listing
- [Advanced Topics](advanced-topics/) - Deep-dive tutorials

### Additional Resources
- [Troubleshooting](troubleshooting/) - Common issues and solutions

## Quick Links

- [Product Overview](https://products.aspose.org/{family}/)
- [API Reference](https://reference.aspose.org/{family}/)
- [Knowledge Base](https://kb.aspose.org/{family}/)
- [GitHub Repository]({repo_url})
```

---

### Comprehensive Guide Template (docs/developer-guide/_index.md)

**Purpose**: Single page listing ALL usage scenarios

**Page Role**: `comprehensive_guide`

**Required Headings**:
- Introduction
- Common Scenarios
- Advanced Scenarios
- Additional Resources

**Content Structure**:

1. **Introduction** (1 paragraph):
   - Explain purpose of developer guide
   - Note that this page covers all major scenarios
   - Link to getting-started for beginners

2. **Common Scenarios**:
   - For each common workflow:
     - H3 heading with scenario name
     - Description (2-3 sentences) explaining what the scenario does
     - Code snippet demonstrating the workflow
     - Links to repo example and API reference
   - Include 50-70% of total workflows here

3. **Advanced Scenarios**:
   - For each advanced workflow:
     - Same structure as common scenarios
     - More complex use cases
   - Include 30-50% of total workflows here

4. **Additional Resources**:
   - Link to API reference
   - Link to GitHub examples
   - Link to KB articles
   - Link to troubleshooting

**Forbidden Content**:
- Installation instructions (belongs in getting-started)
- Troubleshooting guides (belongs in KB)
- API deep-dive documentation (belongs in reference)
- Feature explanations without code examples

**Content Strategy**:
- `primary_focus`: "List all major usage scenarios with code"
- `forbidden_topics`: ["installation", "troubleshooting", "api_deep_dive"]
- `claim_quota`: {"min": <workflow_count>, "max": 50}
- `scenario_coverage`: "all" (MUST cover ALL workflows)

**Special Requirements**:
- MUST cover ALL workflows from product_facts.workflows
- Each workflow MUST have at least 1 claim
- Each workflow MUST have at least 1 code snippet
- Keep descriptions concise (not deep-dive tutorials)

**Template Location**: `specs/templates/docs.aspose.org/{family}/__LOCALE__/developer-guide/_index.md`

**Validation**: Gate 14 MUST validate comprehensive guide covers all workflows (ERROR if any missing)

**Example Structure**:
```markdown
---
title: "{Product} Developer Guide"
description: "Complete guide to all {Product} usage scenarios"
---

## Introduction

This developer guide provides a comprehensive overview of all major usage scenarios for {Product}. Each scenario includes a description, code example, and links to detailed documentation.

For installation and basic setup, see [Getting Started](../getting-started/).

## Common Scenarios

### {Workflow 1 Name}

{Brief description of workflow 1, explaining what it does and when to use it.}

```{language}
{code snippet demonstrating workflow 1}
```

[View full example on GitHub]({repo_url}/examples/{workflow_1_path})
[API Reference]({api_reference_url})

### {Workflow 2 Name}

{Brief description of workflow 2...}

## Advanced Scenarios

### {Advanced Workflow Name}

{Brief description of advanced workflow...}

## Additional Resources

- [API Reference](https://reference.aspose.org/{family}/)
- [GitHub Examples]({repo_url}/examples/)
- [Knowledge Base](https://kb.aspose.org/{family}/)
- [Troubleshooting](https://kb.aspose.org/{family}/troubleshooting/)
```

---

### Feature Showcase Template (kb/how-to-*.md)

**Purpose**: How-to article for prominent feature

**Page Role**: `feature_showcase`

**Required Headings**:
- Overview
- When to Use
- Step-by-Step Guide
- Code Example
- Related Links

**Content Structure**:

1. **Overview**:
   - Feature description (2-3 sentences)
   - What problem it solves
   - Key benefits
   - Claim marker for the feature

2. **When to Use**:
   - 2-4 use cases for this feature
   - Scenarios where this feature is appropriate
   - When NOT to use this feature (optional)

3. **Step-by-Step Guide**:
   - 4-6 numbered steps
   - Each step: brief instruction + explanation
   - Logical progression from setup to completion

4. **Code Example**:
   - Complete working code example
   - Syntax highlighting
   - Comments explaining key lines
   - 1-2 snippets (focus on the feature)

5. **Related Links**:
   - Link to docs page with related content
   - Link to API reference for relevant classes/methods
   - Link to GitHub example (if available)
   - Link to other KB articles (if relevant)

**Forbidden Content**:
- General features overview (focus on single feature)
- API reference documentation (link instead)
- Other features (maintain single feature focus)
- Installation instructions (link to getting-started)

**Content Strategy**:
- `primary_focus`: "How-to guide for a specific prominent feature"
- `forbidden_topics`: ["general_features", "api_reference", "other_features"]
- `claim_quota`: {"min": 3, "max": 8}

**Special Requirements**:
- MUST focus on single feature (WARNING if > 3 distinct features mentioned)
- MUST have 1-2 code snippets demonstrating the feature
- Single feature focus prevents content sprawl

**Template Location**: `specs/templates/kb.aspose.org/{family}/__LOCALE__/howto.variant-*.md`

**Validation**: Gate 14 validates single feature focus (WARNING if too many features)

**Example Structure**:
```markdown
---
title: "How to {Feature Action} with {Product}"
description: "Learn how to use {Feature} in {Product}"
keywords: ["{feature}", "{product}", "{use_case}"]
---

## Overview

{Feature} allows you to {primary_capability}. This feature is useful when {use_case_description} and provides {key_benefit}.

## When to Use

Use {Feature} when you need to:
- {Use case 1}
- {Use case 2}
- {Use case 3}

## Step-by-Step Guide

1. **{Step 1 Title}**: {Step 1 instruction and explanation}
2. **{Step 2 Title}**: {Step 2 instruction and explanation}
3. **{Step 3 Title}**: {Step 3 instruction and explanation}
4. **{Step 4 Title}**: {Step 4 instruction and explanation}

## Code Example

```{language}
{code snippet demonstrating the feature}
```

## Related Links

- [Developer Guide](https://docs.aspose.org/{family}/developer-guide/)
- [API Reference](https://reference.aspose.org/{family}/{api_class}/)
- [GitHub Example]({repo_url}/examples/{feature_path})
```

---

## Per-Feature Workflow Page Templates (TC-983, 2026-02-05)

### Purpose

When evidence is rich enough to justify optional pages beyond mandatory ones, W4 generates **per-feature workflow pages** under the developer-guide section. These are optional pages generated from evidence via `optional_page_policies` with `source: "per_feature"` or `source: "per_workflow"` in the ruleset config.

### Page Role: `workflow_page`

Per-feature workflow pages use the same `workflow_page` page_role as the getting-started guide, but are focused on a **single feature or workflow** rather than onboarding.

### Template Structure

**Required Headings**:
- Overview
- Prerequisites
- Step-by-Step Guide
- Code Example
- Related Links

**Content Structure**:

1. **Overview** (1-2 paragraphs):
   - Feature/workflow description from product_facts
   - What problem it solves
   - When to use this specific workflow

2. **Prerequisites**:
   - Required dependencies
   - Assumed knowledge
   - Link to getting-started if not yet set up

3. **Step-by-Step Guide**:
   - 3-6 numbered steps
   - Each step with clear instruction
   - Based on evidence from product_facts.workflows

4. **Code Example**:
   - Complete code snippet from snippet_catalog
   - Syntax highlighting for target language
   - Comments explaining key lines

5. **Related Links**:
   - Link to developer-guide (parent comprehensive guide)
   - Link to API reference for relevant classes
   - Link to GitHub example (if available)

### Candidate Generation

Per-feature workflow pages are generated by the Optional Page Selection Algorithm (see `specs/06_page_planning.md`):

1. For `source: "per_feature"`: W4 creates one candidate page per `product_facts.key_features` entry that has associated claims
2. For `source: "per_workflow"`: W4 creates one candidate page per `product_facts.workflows` entry
3. Each candidate is scored using `quality_score = (claim_count * 2) + (snippet_count * 3)`
4. Candidates are ranked by priority, quality_score, and slug (deterministic)
5. Top N candidates selected where N = effective_max_pages - mandatory_page_count

### Slug Convention

Per-feature workflow page slugs follow the pattern:
- `{feature-slug}` or `{workflow-slug}` (lowercase, hyphenated)
- Example: `model-loading`, `format-conversion`, `rendering`
- Placed under `docs/<family>/<locale>/developer-guide/` path

### Validation

Gate 14 validates per-feature workflow pages with the same rules as other `workflow_page` pages:
- Must have `page_role: "workflow_page"`
- Must have `content_strategy` with `primary_focus` and `forbidden_topics`
- Must respect claim_quota limits

### Example

For family "3d" with rich evidence (806 claims, 5 workflows):
- Mandatory docs pages: 5 (global) + 2 (family_overrides: model-loading, rendering) = 7
- Optional candidates: per_feature workflow pages for remaining features
- Selected: top N by quality_score until effective_max_pages reached

---

## Template Discovery and Filtering (2026-02-03, updated 2026-02-05)

### Blog Template Structure Requirements (Binding)

**Blog section uses NO `__LOCALE__` folders.** Blog URL structure is `blog.aspose.org/{family}/{slug}/`, so templates are rooted directly under the family folder.

**Correct blog template structure**:
```
specs/templates/blog.aspose.org/{family}/__POST_SLUG__/index.variant-*.md
```

**Obsolete blog template structures (must be filtered)**:
```
specs/templates/blog.aspose.org/{family}/__PLATFORM__/__POST_SLUG__/...  -- WRONG (DEPRECATED token)
specs/templates/blog.aspose.org/{family}/__LOCALE__/__PLATFORM__/...     -- WRONG (no locale, DEPRECATED token)
```

### Template Discovery Filtering Rules (Binding)

Template enumeration MUST filter templates based on section requirements:

1. **All sections**: MUST exclude templates with `__PLATFORM__` in path (V2 platform-aware layout removed as of 2026-02-09)
   - `__PLATFORM__` is a DEPRECATED token and MUST NOT appear in any template paths
   - Templates containing `__PLATFORM__` are obsolete and cause incorrect output paths

2. **Blog section**: MUST additionally exclude templates with `__LOCALE__` in path (blog uses filename-based i18n)
   - Blog content is family-level, not locale-directory-based
   - HEAL-BUG4 rule: exclude `__LOCALE__` in blog templates

3. **Non-blog sections** (docs, products, kb, reference): MAY include `__LOCALE__` in path
   - These sections use locale folders in content structure
   - Example: `content/docs.aspose.org/3d/en/...`

4. **Index page de-duplication**: If multiple `_index.md` variants exist for the same section, select only the first alphabetically by template path
   - Prevents URL collisions from duplicate section index pages
   - Deterministic selection ensures consistent behavior across runs

**Implementation reference**: See `src/launch/workers/w4_ia_planner/worker.py::enumerate_templates()` for template filtering and `classify_templates()` for index page de-duplication.

**Related fixes**:
- HEAL-BUG4 (2026-02-03): Added blog template filtering (exclude `__LOCALE__`)
- HEAL-BUG2 (2026-02-03): Added index page de-duplication
- TC-990 (2026-02-05): Corrected blog exclusion to also exclude `__PLATFORM__`
- V2 removal (2026-02-09): `__PLATFORM__` excluded from ALL sections, not just blog

---

## Target V1 Template File Structure (Binding Ground Truth, TC-990, updated 2026-02-09)

> **Updated (2026-02-09)**: V2 platform-aware layout removed. All `__PLATFORM__` segments removed from template paths. Templates now use V1 hierarchy only.

This section defines the authoritative template file structure per subdomain. All template files, template discovery logic, and W4 path resolution MUST conform to these hierarchies. Any template files using patterns not listed below (e.g., `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__`, `__PLATFORM__`) are **obsolete** and MUST NOT be used for page planning.

### DOCS -- `docs.aspose.org/{family}/{locale}/`

Template root: `specs/templates/docs.aspose.org/{family}/`

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Layout-driven | docs | Lists sections |
| `__LOCALE__/developer-guide/_index.md` | Content-rich | docs | Comprehensive guide |
| `__LOCALE__/developer-guide/feature.variant-*.md` | **1..N repeatable** | docs | Per-feature workflow pages |
| `__LOCALE__/getting-started/_index.md` | Content-rich | docs | Getting started section |
| `__LOCALE__/getting-started/installation.md` | Concrete | docs | Installation guide |
| `__LOCALE__/getting-started/license.md` | Concrete | docs | License info |

### PRODUCTS -- `products.aspose.org/{family}/{locale}/`

Template root: `specs/templates/products.aspose.org/{family}/`

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Content-rich | plugin | Product landing |

### KB -- `kb.aspose.org/{family}/{locale}/`

Template root: `specs/templates/kb.aspose.org/{family}/`

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Content-rich | - | Uses `{{</* sections */>}}` shortcode |
| `__LOCALE__/howto.variant-*.md` | **1..N repeatable** | topic | Step1-step10 fields |

### BLOG -- `blog.aspose.org/{family}/{slug}/` (NO locale)

Template root: `specs/templates/blog.aspose.org/{family}/`

| Template path | Content type | Notes |
|---|---|---|
| `__POST_SLUG__/index.variant-*.md` | **1..N repeatable** | Blog posts, family-level only |

**Blog constraints (binding)**:
- Blog templates MUST NOT contain `__LOCALE__` in any path segment
- Blog content is organized solely by `{family}/{post_slug}/`

### REFERENCE -- `reference.aspose.org/{family}/{locale}/`

Template root: `specs/templates/reference.aspose.org/{family}/`

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Layout-driven | - | Reference root |
| `__LOCALE__/reference.variant-*.md` | **1..N repeatable** | reference-single | API reference pages |

### Obsolete Patterns (MUST NOT be used)

The following template filename patterns are **obsolete** and MUST NOT appear in any new template files or be referenced by W4 page planning:

- `__PLATFORM__` -- was used for V2 platform-aware directory hierarchy; **REMOVED (2026-02-09)** as V2 layout is deprecated. Presence of this token in content triggers `GATE_TEMPLATE_V2_TOKEN_LEAKED` error.
- `__PLATFORM_CAPITALIZED__` -- was used for V2 display names; **REMOVED (2026-02-09)**
- `__PLUGIN_PLATFORM__` -- was used for V2 plugin identifiers; **REMOVED (2026-02-09)**
- `__CONVERTER_SLUG__` -- was used for format-converter page hierarchies; replaced by flat structure
- `__FORMAT_SLUG__` -- was used for per-format sub-pages; replaced by repeatable variant templates
- `__SECTION_PATH__` -- was used for arbitrary nested section folders; replaced by concrete folder names (`developer-guide/`, `getting-started/`)
