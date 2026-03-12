# Templates and Rulesets

Canonical sources:
- Ruleset: `specs/rulesets/ruleset.yaml` (validated by `specs/schemas/ruleset.schema.json`)
- Templates: `specs/templates/{subdomain}/` (Hugo templates)

## Overview

Templates define the structural skeleton for generated pages. Rulesets define
which pages are mandatory or optional per subdomain and family. Together they
control the shape of every generated site.

---

## Template Variants

Each page role has up to 3 template variants. The variant controls content depth
and structure.

| Variant | Description | Typical use |
|---------|-------------|-------------|
| `standard` | Full-depth template with all sections | Full and core tiers |
| `minimal` | Condensed template with fewer sections | Minimal tier |
| `steps` | Step-by-step procedural format | How-to articles, installation |

### Variant Fields

A template variant specifies:
- **Sections**: Ordered list of section headings (the skeleton).
- **Required blocks**: Minimum block types per section (e.g., at least one code
  block in an installation section).
- **Max sections**: Upper bound on section count.
- **Heading constraints**: Allowed heading text patterns (to prevent
  template-label headings like "Section 1").

---

## Selection Algorithm

Template variant selection is tier-driven and deterministic.

### Input

- `launch_tier` (resolved): `full`, `core`, or `minimal`
- `page_role`: From the ruleset (e.g., `workflow_page`, `faq`, `howto_article`)

### Selection Rules

1. If `page_role` has a `steps` variant AND the role is procedural
   (`howto_article`, `workflow_page` with `topic_category` in
   `[load_file, save_file, convert_formats]`), select `steps`.
2. If `launch_tier` is `minimal`, select `minimal`.
3. Otherwise, select `standard`.

### Fallback

If the selected variant does not exist for a page role, fall back to `standard`.
If `standard` does not exist, the pipeline emits a hard error (schema violation).

---

## Template Directory Structure

```
specs/templates/
  products/
    landing.standard.yaml
    landing.minimal.yaml
  docs/
    toc.standard.yaml
    workflow_page.standard.yaml
    workflow_page.minimal.yaml
    workflow_page.steps.yaml
  kb/
    toc.standard.yaml
    faq.standard.yaml
    faq.minimal.yaml
    troubleshooting.standard.yaml
    howto_article.standard.yaml
    howto_article.steps.yaml
    feature_showcase.standard.yaml
  reference/
    toc.standard.yaml
    api_reference.standard.yaml
    api_reference.minimal.yaml
  blog/
    blog_announcement.standard.yaml
    feature_blog.standard.yaml
```

### Template File Format

Each template file is a YAML document:

```yaml
page_role: workflow_page
variant: standard
sections:
  - heading: "Overview"
    required_blocks: [paragraph]
    min_blocks: 1
  - heading: "Prerequisites"
    required_blocks: [list]
    min_blocks: 1
  - heading: "Implementation"
    required_blocks: [paragraph, code]
    min_blocks: 2
  - heading: "Complete Example"
    required_blocks: [code]
    min_blocks: 1
  - heading: "Next Steps"
    required_blocks: [paragraph]
    min_blocks: 1
max_sections: 8
```

---

## Ruleset Binding Rules

The ruleset (`specs/rulesets/ruleset.yaml`) governs which pages exist.

### Mandatory Pages

Each section declares mandatory pages with:
- `slug`: The URL slug for the page.
- `page_role`: The semantic role (links to a template).
- `folder_index` (optional): If true, rendered as `{slug}/_index.md`.
- `tier_minimum` (optional): Minimum tier required (e.g., `core` means the page
  is skipped at `minimal`).
- `topic_category` (optional): Used for template variant selection.

### Optional Policies

Optional pages are governed by policies:

| Policy kind | Trigger | Description |
|-------------|---------|-------------|
| `topic_cluster` | `claim_count > N` | Add topic pages when claims exceed threshold |
| `per_module` | Tier budget | Add per-module reference pages up to budget |
| `feature_showcase` | Tier budget | Add feature showcase pages per tier |
| `deep_dive` | Tier budget | Add deep-dive blog posts at full tier |

### Tier Budgets

Optional policies use tier budgets to cap page count:

```yaml
tier_budget:
  minimal: 0
  core: 2
  full: 3
```

The budget is the maximum number of optional pages of that kind.

### Family Overrides

The `family_overrides` section in the ruleset adds family-specific mandatory
pages. These are merged with (not replacing) the base section rules.

Example: The `cells` family adds `spreadsheet-operations` and
`formula-calculation` to the docs section.

---

## Binding Flow

1. **Understand worker** reads `ruleset.yaml` and resolves the page list for the
   given family + platform + launch_tier.
2. For each page, it looks up the template by `page_role` + selected variant.
3. The template skeleton becomes the `skeleton` field in the page plan.
4. The **Generate worker** uses the skeleton to structure LLM prompts.
5. The **Evaluate worker** checks that generated content matches the template
   structure (heading gate, density gate).

---

## Heading Gate

The template-heading gate verifies that generated section headings are meaningful
and not bare template labels. For example, a heading of "Implementation" is
acceptable; a heading of "Section 3" is not. The gate uses the template's heading
patterns as a reference but allows the LLM to use contextually appropriate
variations.
