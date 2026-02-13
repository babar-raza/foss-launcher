---
id: TC-1205
title: "Page Expansion — Templates for New Page Types"
status: Draft
priority: High
owner: "Agent D (Docs & Specs)"
updated: "2026-02-11"
tags: ["templates", "page-expansion", "phase-3"]
depends_on: ["TC-1200"]
allowed_paths:
  - plans/taskcards/TC-1205_page_expansion_templates.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/convert-source-to-target.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/example-walkthrough.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/tutorial-workflow.variant-standard.md
  - specs/templates/reference.aspose.org/__FAMILY__/__LOCALE__/ref-namespace.variant-standard.md
  - specs/templates/kb.aspose.org/__FAMILY__/__LOCALE__/deep-dive-features.variant-standard.md
  - specs/templates/kb.aspose.org/__FAMILY__/__LOCALE__/faq-topic.variant-standard.md
  - specs/templates/blog.aspose.org/__FAMILY__/__POST_SLUG__/guide-theme.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/overview.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/quickstart.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/examples.variant-standard.md
  - specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/troubleshooting.variant-standard.md
evidence_required:
  - reports/agents/AGENT_D/TC-1205/evidence.md
  - reports/agents/AGENT_D/TC-1205/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1205 — Page Expansion — Templates for New Page Types

## Objective
Create markdown template files for all 7 new page types and 4 sub-page types, following the existing template conventions. These templates define the structure (headings, placeholders, frontmatter) that W5's content generators fill in.

## Required spec references
- specs/07_section_templates.md (updated by TC-1200 — new template type definitions)
- specs/08_content_distribution_strategy.md (updated by TC-1200 — page role content strategies)
- Existing templates in specs/templates/ (for convention reference)

## Scope

### In scope
1. **7 new page-type templates** (one per new page_role):
   - `convert-source-to-target.variant-standard.md` — Format conversion guide
   - `example-walkthrough.variant-standard.md` — Example page with full explanation
   - `tutorial-workflow.variant-standard.md` — Step-by-step tutorial
   - `ref-namespace.variant-standard.md` — Namespace/module API reference
   - `deep-dive-features.variant-standard.md` — Cross-feature deep dive
   - `faq-topic.variant-standard.md` — Topic-specific FAQ
   - `guide-theme.variant-standard.md` — Thematic overview
2. **4 sub-page templates**:
   - `__FEATURE__/overview.variant-standard.md`
   - `__FEATURE__/quickstart.variant-standard.md`
   - `__FEATURE__/examples.variant-standard.md`
   - `__FEATURE__/troubleshooting.variant-standard.md`
3. Each template includes: Hugo frontmatter, required headings, `__TOKEN__` placeholders, claim markers `[claim: __CLAIM_ID__]`

### Out of scope
- Template variant explosion (minimal/enhanced) — start with standard only
- W5 generator code (TC-1206)
- W4 template enumeration changes (TC-1203 handles policy-to-slug mapping; W4 already scans template dirs)

## Inputs
- Existing templates in specs/templates/ (for format/convention reference)
- specs/07_section_templates.md (template type definitions from TC-1200)

## Outputs
- 11 new template files in specs/templates/ hierarchy

## Allowed paths
- plans/taskcards/TC-1205_page_expansion_templates.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/convert-source-to-target.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/example-walkthrough.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/tutorial-workflow.variant-standard.md
- specs/templates/reference.aspose.org/__FAMILY__/__LOCALE__/ref-namespace.variant-standard.md
- specs/templates/kb.aspose.org/__FAMILY__/__LOCALE__/deep-dive-features.variant-standard.md
- specs/templates/kb.aspose.org/__FAMILY__/__LOCALE__/faq-topic.variant-standard.md
- specs/templates/blog.aspose.org/__FAMILY__/__POST_SLUG__/guide-theme.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/overview.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/quickstart.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/examples.variant-standard.md
- specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/__FEATURE__/troubleshooting.variant-standard.md

### Allowed paths rationale
Template files only. No code, no specs, no rulesets. Each template is a standalone markdown file.

## Implementation steps

### Step 1: Read existing template for convention reference
Read at least 2 existing templates (e.g., `feature.variant-standard.md` and `howto.variant-standard.md`) to understand:
- Frontmatter format (Hugo YAML)
- Token placeholder convention (`__PRODUCT_NAME__`, `__FAMILY__`, etc.)
- Claim marker format `[claim: __CLAIM_ID__]`
- Heading structure (H1, H2, H3 levels)
- Snippet placeholder format

**Resilience note**: Template conventions may have evolved. Use whatever pattern the CURRENT templates use, not what this taskcard assumes.

### Step 2: Create format conversion template
`specs/templates/docs.aspose.org/__FAMILY__/__LOCALE__/developer-guide/convert-source-to-target.variant-standard.md`

```markdown
---
title: "Convert __SOURCE_FORMAT__ to __TARGET_FORMAT__ using __PRODUCT_NAME__"
linktitle: "__SOURCE_FORMAT__ to __TARGET_FORMAT__"
description: "Learn how to convert __SOURCE_FORMAT__ files to __TARGET_FORMAT__ format using __PRODUCT_NAME__ for __PLATFORM__."
url: /__FAMILY__/docs/developer-guide/convert-__SOURCE_FORMAT_LOWER__-to-__TARGET_FORMAT_LOWER__/
---

# Convert __SOURCE_FORMAT__ to __TARGET_FORMAT__

## Overview
[claim: __CLAIM_ID__]

## Prerequisites
- __PRODUCT_NAME__ installed ([Installation Guide](__INSTALL_URL__))
- Input file in __SOURCE_FORMAT__ format

## Step-by-Step Conversion

### Step 1: Load the __SOURCE_FORMAT__ File
__SNIPPET_LOAD__

### Step 2: Configure Conversion Options
__SNIPPET_OPTIONS__

### Step 3: Save as __TARGET_FORMAT__
__SNIPPET_SAVE__

## Complete Example
__SNIPPET_COMPLETE__

## Supported Options
| Option | Description | Default |
|--------|-------------|---------|
| __OPTION_ROWS__ |

## Related Conversions
__CROSS_LINKS__

## See Also
- [API Reference](__REF_URL__)
- [All Format Conversions](__CONVERSIONS_INDEX_URL__)
```

### Step 3: Create example walkthrough template
Similar structure with: Overview, What This Example Does, Prerequisites, Code Walkthrough, Running the Example, Expected Output, Variations, Related Examples.

### Step 4: Create tutorial workflow template
Structure: Overview, What You'll Build, Prerequisites, Step 1..N (from workflow steps), Complete Code, Next Steps.

### Step 5: Create namespace reference template
Structure: Namespace Overview, Classes (table with class/description/link), Key Methods, Usage Examples, See Also.

### Step 6: Create deep-dive features template
Structure: Overview, Feature A Deep Dive, Feature B Deep Dive, Using A and B Together, Performance Considerations, Best Practices.

### Step 7: Create FAQ topic template
Structure: Overview, Q&A pairs (H3 per question), Related Topics, Getting Help.

### Step 8: Create theme overview template
Structure: Overview, Features in This Theme (list), Common Patterns, Code Examples, Further Reading.

### Step 9: Create 4 sub-page templates
Under `__FEATURE__/` directory:
- `overview.variant-standard.md`: Feature overview, key capabilities, when to use, limitations
- `quickstart.variant-standard.md`: Minimal code, prerequisites, 3-step guide, next steps
- `examples.variant-standard.md`: Multiple examples (H3 per example), complete code, output
- `troubleshooting.variant-standard.md`: Common issues (H3 per issue), symptoms, solutions, FAQ

### Step 10: Validate all templates
- Verify Hugo frontmatter is valid YAML
- Verify all `__TOKEN__` placeholders use consistent naming
- Verify claim markers present
- Verify heading hierarchy (no skipped levels)

## Failure modes

### Failure mode 1: Template tokens don't match W5 token generation
**Detection:** W5 fails to populate a token because the template uses a different token name than W5 expects.
**Resolution:** Use ONLY tokens that are already in the W4 token generation system OR that TC-1206 will add. Cross-reference with `specs/07_section_templates.md` token registry.
**Spec/Gate:** specs/07 token registry

### Failure mode 2: Hugo frontmatter invalid
**Detection:** Hugo build fails to parse template frontmatter. W7 Gate 13 fails.
**Resolution:** Validate YAML frontmatter with `python -c "import yaml; yaml.safe_load(...)"` for each template.
**Spec/Gate:** specs/09 Gate 13 Hugo build validation

### Failure mode 3: Template directory structure doesn't match W4 enumeration
**Detection:** W4 `enumerate_templates()` doesn't find new templates because they're in unexpected directories.
**Resolution:** Follow EXACT directory structure used by existing templates. W4 scans `specs/templates/{subdomain}/{family}/__LOCALE__/` and `specs/templates/{subdomain}/__FAMILY__/__LOCALE__/`. Use `__FAMILY__` placeholder.
**Spec/Gate:** W4 template enumeration logic

## Task-specific review checklist
1. [ ] 7 page-type templates created with correct heading structure
2. [ ] 4 sub-page templates created under `__FEATURE__/` directory
3. [ ] All templates have valid Hugo YAML frontmatter
4. [ ] All templates use `__TOKEN__` placeholder convention
5. [ ] All templates include `[claim: __CLAIM_ID__]` markers
6. [ ] Template directory paths match W4 enumeration expectations
7. [ ] No skipped heading levels (H1 → H2 → H3, not H1 → H3)
8. [ ] Cross-links use `__CROSS_LINKS__` or explicit `__URL__` tokens
9. [ ] Each template has purpose-appropriate headings per spec/07
10. [ ] Tokens are registered or will be registered in TC-1206

## Deliverables
- 11 template files in specs/templates/
- reports/agents/AGENT_D/TC-1205/evidence.md
- reports/agents/AGENT_D/TC-1205/self_review.md

## Acceptance checks
1. [ ] 11 template files created in correct directories
2. [ ] Valid Hugo frontmatter in all templates
3. [ ] Consistent token naming across all templates
4. [ ] Claim markers present in all content templates
5. [ ] Heading hierarchy correct

## Preconditions / dependencies
- TC-1200 completed (template type definitions in spec)
- Existing templates accessible for convention reference

## Self-review
[To be completed by Agent D after implementation]
