# Section Templates

## Goal
Make section content consistent, reusable, and easy to validate.

## Common template rules
- Use ProductFacts fields, do not invent.
- Include claim markers (HTML comments `<!-- claim: {id} -->`) for every factual bullet (TC-1650).
- Use snippet_catalog snippets by tag.
- Keep consistent naming across all pages.

**Claim Marker Format (TC-1650)**:
W5 specialized generators inject claim markers in HTML comment format for W7 validation:
```
<!-- claim: {claim_id} -->
```

These markers are invisible to end users but parseable by W7 gate_8 to verify content distribution.
Previous format `[claim: {id}]` was visible in rendered content (BLOCKER-2, fixed in TC-1650).

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

### Template hierarchy (binding)

Templates support both V1 (no platform folder) and V2 (with platform folder) layouts:

**V1 (no platform segment)**:
```
Non-blog: specs/templates/<subdomain>/<family>/__LOCALE__/...
Blog:     specs/templates/blog.aspose.org/<family>/__POST_SLUG__/...
```

**V2 (with platform segment)**:
```
Non-blog: specs/templates/<subdomain>/<family>/__LOCALE__/__PLATFORM__/...
Blog:     specs/templates/blog.aspose.org/<family>/__PLATFORM__/__POST_SLUG__/...
```

**Blog**: Blog templates do NOT use `__LOCALE__` folders. Blog URL structure is `blog.aspose.org/{family}/{slug}/` (V1) or `blog.aspose.org/{family}/{platform}/{slug}/` (V2), so templates are rooted at `<family>/__POST_SLUG__/` (V1) or `<family>/__PLATFORM__/__POST_SLUG__/` (V2).

The `__PLATFORM__` token is resolved to the `target_platform` value (e.g., `python`) at generation time. See `specs/32_platform_aware_content_layout.md` for the binding V2 layout contract.

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

Per-feature workflow page slugs MUST follow the Slug Sanitization Contract (see `specs/06_page_planning.md`):
- Slugs MUST NOT be derived from raw claim text truncation
- Slugs MUST use heuristic extraction, workflow/feature names, or LLM summarization
- Format: `{feature-slug}` or `{workflow-slug}` (lowercase, hyphenated, max 40 chars)
- Pattern: `^[a-z0-9][a-z0-9-]*[a-z0-9]$`
- Example: `model-loading`, `format-conversion`, `rendering`
- Placed under `docs/<family>/<locale>/developer-guide/` path (V1) or `docs/<family>/<locale>/<platform>/developer-guide/` (V2)

### Code Block Formatting Requirements (Round 13, binding)

All generated content MUST follow these code formatting rules:

1. **Triple backtick fences only**: ALL code blocks MUST use triple-backtick fences (` ``` `). Single-backtick inline code (`` ` ``) is for inline references only, NEVER for multi-line code.
2. **Language specification required**: Every code fence MUST specify the language (e.g., ` ```python `, ` ```csharp `). Bare ` ``` ` fences are WARNING-level.
3. **No nested fences**: Code blocks MUST NOT contain triple-backtick sequences. Use indentation-based code blocks inside code fences if needed.
4. **Consistent indentation**: Code within fences MUST use consistent indentation (spaces preferred over tabs).

5. **No excess backtick fences**: Code fences MUST use exactly 3 backticks. Fences with 4+ backticks (e.g., ``````) MUST be normalized to 3 backticks by the content sanitizer.
6. **Language extraction from single-backtick blocks**: When converting single-backtick code blocks to triple-backtick fences, if the first non-empty line is a recognized language identifier (e.g., `python`, `bash`, `csharp`), it MUST be extracted and placed on the opening fence line (` ```python `) rather than left as content inside the block.

**Single-backtick code block detection (Round 16, binding)**:

The `fix_single_backtick_code_blocks()` function MUST use a **line-based state machine**, not regex, to detect and convert single-backtick code blocks:

1. Track existing triple-backtick fences (skip their content entirely)
2. Detect **opener**: a stripped line that is a lone `` ` `` or `` `<known_lang> `` (NOT ``` `` ``` or ```` ``` ````)
3. Scan forward for **closer**: a stripped line that is `` ` `` or `` `. ``
4. If found with non-empty content between opener and closer: emit ``` ```lang ``` + content + ``` ``` ```
5. If no closer found: emit the line as-is (no data loss)

This approach avoids the regex pitfall where `[^`]` cannot cross inline backtick spans within the same match.

**Enforcement**:
- W5 `content_sanitizer.py` MUST fix single-backtick code blocks to triple-backtick fences with language extraction
- W5 `content_sanitizer.py` MUST normalize 4+ backtick fences to standard 3-backtick fences
- W5.5 ContentReviewer MUST check for and flag single-backtick code blocks
- W7 Gate 2 (Markdown Lint) validates code fence syntax

### Link Formatting Requirements (Round 13, binding)

All generated links MUST follow these formatting rules:

1. **No trailing whitespace in URLs**: Link URLs MUST NOT contain trailing spaces (e.g., `[text](url/ )` is FORBIDDEN)
2. **No double slashes in paths**: URLs MUST NOT contain `//` in path segments (protocol `://` excluded)
3. **Consistent trailing slashes**: Internal Hugo links SHOULD end with `/` for directory-style URLs

**Enforcement**:
- W5 `content_sanitizer.py` MUST strip trailing whitespace from link URLs
- W5.5 ContentReviewer MUST check for trailing whitespace in links
- W7 Gate 6 (Internal Links) validates link format

### Absolute Link Requirements (Round 16, binding)

All links injected into generated content MUST be absolute URLs with the correct subdomain. Relative links (e.g., `/3d/getting-started/`) are FORBIDDEN in final output.

**Subdomain mapping** — links MUST resolve to the correct subdomain for ALL sections:
- `/docs/...` or docs-section links → `https://docs.aspose.org/{family}/{platform}/...`
- `/reference/...` → `https://reference.aspose.org/{family}/{platform}/...`
- `/kb/...` → `https://kb.aspose.org/{family}/{platform}/...`
- `/blog/...` → `https://blog.aspose.org/{family}/{platform}/...`
- `/products/...` → `https://products.aspose.org/{family}/{platform}/...`
- Intra-section links (e.g., `/{family}/slug/`) → `https://{current_section}.aspose.org/{family}/{platform}/slug/`
- Already-absolute links (`https://...`) → unchanged
- Anchor links (`#heading`) → unchanged
- GitHub URLs → unchanged

**Enforcement**:
- W5 `content_sanitizer.py` Phase 4 MUST run `absolutize_links()` after all link injection is complete
- `absolutize_links()` requires `section`, `family`, and `platform` from `SanitizerContext`
- W5.5 ContentReviewer SHOULD flag any remaining relative links as warnings

### Code in Generated Content: Trailing Period Stripping (Round 16, binding)

LLMs sometimes append prose periods to code lines (e.g., `import Scene.`, `render(opts) #.`). These MUST be stripped from code blocks.

**Rules**:
1. Lines inside code fences ending with `#.` → strip the `#.` suffix
2. Lines inside code fences ending with a trailing `.` → strip the period, EXCEPT:
   - `pip install -e .` or other commands where `.` is a path argument
   - `...` (ellipsis)
   - Periods inside or adjacent to string literals (`"file.obj"`)
   - Comment lines (`# This is a comment.`) — preserve (prose in comments is acceptable)

**Enforcement**:
- W5 `content_sanitizer.py` Phase 2 MUST run `fix_trailing_periods_in_code()` after `fix_code_fences()` and before `merge_adjacent_code_blocks()`
- Only processes lines inside triple-backtick fences

### FAQ Formatting Requirements (Round 14, binding)

FAQ pages MUST follow these formatting rules:

1. **Single Q: prefix**: FAQ headings MUST use a single `Q:` prefix (e.g., `### Q: How do I...?`). Doubled `Q: Q:` prefixes MUST be stripped by the content sanitizer.
2. **Single A: prefix**: FAQ answers MUST use a single `**A:**` prefix. Doubled `**A:** A:` prefixes MUST be stripped by the content sanitizer.
3. **Substantive answers**: FAQ answers MUST NOT use placeholder text like "See documentation for details." Answers MUST be at least 2 sentences with actionable information.

**Enforcement**:
- W5 `content_sanitizer.py` MUST strip doubled `Q: Q:` prefixes to single `Q:`
- W5 `content_generators.py` MUST strip existing `Q:` prefix from claim text before adding `### Q:` heading
- W5.5 ContentReviewer checks FAQ answer quality

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

**V2 blog template structure** (with platform segment):
```
specs/templates/blog.aspose.org/{family}/__PLATFORM__/__POST_SLUG__/index.variant-*.md
```

**Obsolete blog template structures (must be filtered)**:
```
specs/templates/blog.aspose.org/{family}/__LOCALE__/__PLATFORM__/...     -- WRONG (no locale in blog)
```

### Template Discovery Filtering Rules (Binding)

Template enumeration MUST filter templates based on section requirements and layout mode:

1. **V1 layout mode**: MUST exclude templates with `__PLATFORM__` in path (V1 does not use platform segments)
   - Only templates without `__PLATFORM__` are valid for V1 layout

2. **V2 layout mode**: MUST include templates with `__PLATFORM__` in path
   - The `__PLATFORM__` token is resolved to the `target_platform` value at generation time
   - Templates without `__PLATFORM__` are excluded when V2 layout is active

3. **Blog section**: MUST additionally exclude templates with `__LOCALE__` in path (blog uses filename-based i18n)
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
- V2 restoration (2026-02-12): `__PLATFORM__` re-enabled for V2 layout mode; excluded only in V1 mode

---

## Target Template File Structure (Binding Ground Truth, TC-990, updated 2026-02-12)

> **Updated (2026-02-12)**: V2 platform-aware layout restored. Templates support both V1 (no `__PLATFORM__`) and V2 (with `__PLATFORM__`) hierarchies. Template selection depends on `layout_mode`.

This section defines the authoritative template file structure per subdomain. All template files, template discovery logic, and W4 path resolution MUST conform to these hierarchies. Any template files using patterns not listed below (e.g., `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__`) are **obsolete** and MUST NOT be used for page planning.

### DOCS -- `docs.aspose.org/{family}/{locale}/` (V1) or `docs.aspose.org/{family}/{locale}/{platform}/` (V2)

Template root: `specs/templates/docs.aspose.org/{family}/`

**V1 templates** (no `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Layout-driven | docs | Lists sections |
| `__LOCALE__/developer-guide/_index.md` | Content-rich | docs | Comprehensive guide |
| `__LOCALE__/developer-guide/feature.variant-*.md` | **1..N repeatable** | docs | Per-feature workflow pages |
| `__LOCALE__/getting-started/_index.md` | Content-rich | docs | Getting started section |
| `__LOCALE__/getting-started/installation.md` | Concrete | docs | Installation guide |
| `__LOCALE__/getting-started/license.md` | Concrete | docs | License info |

**V2 templates** (with `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/__PLATFORM__/_index.md` | Layout-driven | docs | Lists sections |
| `__LOCALE__/__PLATFORM__/developer-guide/_index.md` | Content-rich | docs | Comprehensive guide |
| `__LOCALE__/__PLATFORM__/developer-guide/feature.variant-*.md` | **1..N repeatable** | docs | Per-feature workflow pages |
| `__LOCALE__/__PLATFORM__/getting-started/_index.md` | Content-rich | docs | Getting started section |
| `__LOCALE__/__PLATFORM__/getting-started/installation.md` | Concrete | docs | Installation guide |
| `__LOCALE__/__PLATFORM__/getting-started/license.md` | Concrete | docs | License info |

### PRODUCTS -- `products.aspose.org/{family}/{locale}/` (V1) or `products.aspose.org/{family}/{locale}/{platform}/` (V2)

Template root: `specs/templates/products.aspose.org/{family}/`

**V1 templates** (no `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Content-rich | plugin | Product landing |

**V2 templates** (with `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/__PLATFORM__/_index.md` | Content-rich | plugin | Product landing |

### KB -- `kb.aspose.org/{family}/{locale}/` (V1) or `kb.aspose.org/{family}/{locale}/{platform}/` (V2)

Template root: `specs/templates/kb.aspose.org/{family}/`

**V1 templates** (no `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Content-rich | - | Uses `{{</* sections */>}}` shortcode |
| `__LOCALE__/howto.variant-*.md` | **1..N repeatable** | topic | Step1-step10 fields |

**V2 templates** (with `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/__PLATFORM__/_index.md` | Content-rich | - | Uses `{{</* sections */>}}` shortcode |
| `__LOCALE__/__PLATFORM__/howto.variant-*.md` | **1..N repeatable** | topic | Step1-step10 fields |

### BLOG -- `blog.aspose.org/{family}/{slug}/` (V1) or `blog.aspose.org/{family}/{platform}/{slug}/` (V2) (NO locale)

Template root: `specs/templates/blog.aspose.org/{family}/`

**V1 templates** (no `__PLATFORM__`):

| Template path | Content type | Notes |
|---|---|---|
| `__POST_SLUG__/index.variant-*.md` | **1..N repeatable** | Blog posts, family-level only |

**V2 templates** (with `__PLATFORM__`):

| Template path | Content type | Notes |
|---|---|---|
| `__PLATFORM__/__POST_SLUG__/index.variant-*.md` | **1..N repeatable** | Blog posts, platform-scoped |

**Blog constraints (binding)**:
- Blog templates MUST NOT contain `__LOCALE__` in any path segment
- V1 blog content is organized by `{family}/{post_slug}/`
- V2 blog content is organized by `{family}/{platform}/{post_slug}/`

### REFERENCE -- `reference.aspose.org/{family}/{locale}/` (V1) or `reference.aspose.org/{family}/{locale}/{platform}/` (V2)

Template root: `specs/templates/reference.aspose.org/{family}/`

**V1 templates** (no `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/_index.md` | Layout-driven | - | Reference root |
| `__LOCALE__/reference.variant-*.md` | **1..N repeatable** | reference-single | API reference pages |

**V2 templates** (with `__PLATFORM__`):

| Template path | Content type | Hugo type | Notes |
|---|---|---|---|
| `__LOCALE__/__PLATFORM__/_index.md` | Layout-driven | - | Reference root |
| `__LOCALE__/__PLATFORM__/reference.variant-*.md` | **1..N repeatable** | reference-single | API reference pages |

### Active V2 Tokens

The following tokens are active for V2 platform-aware layout:

- `__PLATFORM__` -- directory segment for `target_platform` (e.g., `python`). Used in V2 template paths. Unreplaced tokens in generated content trigger `GATE_TEMPLATE_V2_TOKEN_LEAKED` error.
- `__PLATFORM_CAPITALIZED__` -- capitalized display name for the platform (e.g., `Python`)
- `__PLUGIN_PLATFORM__` -- plugin identifier for the platform

### Obsolete Patterns (MUST NOT be used)

The following template filename patterns are **obsolete** and MUST NOT appear in any new template files or be referenced by W4 page planning:

- `__CONVERTER_SLUG__` -- was used for format-converter page hierarchies; replaced by flat structure
- `__FORMAT_SLUG__` -- was used for per-format sub-pages; replaced by repeatable variant templates
- `__SECTION_PATH__` -- was used for arbitrary nested section folders; replaced by concrete folder names (`developer-guide/`, `getting-started/`)
