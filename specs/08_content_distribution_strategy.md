# Content Distribution Strategy

**Status**: Binding Specification
**Updated**: 2026-02-04
**Owner**: Product Team
**Related Specs**: [06_page_planning.md](06_page_planning.md), [07_section_templates.md](07_section_templates.md), [09_validation_gates.md](09_validation_gates.md)

---

## Purpose

This specification defines the canonical content distribution strategy for the FOSS Launcher, establishing clear rules for distributing repository information across products, docs, KB, and blog sections to prevent content duplication, ensure clear page roles, and maintain appropriate content boundaries.

## Problem Statement

The FOSS Launcher currently lacks a clear strategy for distributing repository information across different site sections (products, docs, KB, blog). This leads to:

1. Missing pages (no docs TOC index, no comprehensive developer guide)
2. Wrong content focus (KB is troubleshooting-only, not feature showcases)
3. No overlap prevention mechanism
4. Unclear page roles (each page type's strategic purpose is implicit, not explicit)

Users require specific content in specific places:
- products.aspose.org/3d/_index.md: Product landing with features
- docs.aspose.org/3d/_index.md: TOC listing ALL doc pages
- docs.aspose.org/3d/developer-guide/_index.md: Comprehensive listing of ALL scenarios
- kb.aspose.org/3d/how-to-*.md: 2-3 feature showcases + 1-2 troubleshooting
- blog.aspose.org/3d/announcing-*/index.md: Synthesized overview

## Scope

**In Scope**:
- Content distribution rules for all sections (products, docs, KB, blog)
- Page role definitions and strategic purposes
- Claim and snippet allocation algorithms
- Content overlap prevention rules
- Validation requirements (Gate 14)

**Out of Scope**:
- Template implementation (covered in specs/07_section_templates.md)
- Worker implementation (W4, W5, W7)
- Schema definition (covered in specs/schemas/page_plan.schema.json)

---

## Binding Principles

These principles are MANDATORY for all workers (W4, W5, W7) and templates:

1. **Hierarchical Delegation**: Parent pages delegate details to children. TOC pages list children but don't duplicate their content. Landing pages link to detailed guides but don't explain features in depth.

2. **No Content Duplication**: Each claim appears once on a single primary page (except blog, which synthesizes but must rephrase). Claims are distributed by priority order across sections.

3. **Clear Boundaries**: Each page type has explicit forbidden topics. Workers MUST respect forbidden_topics from content_strategy and MUST NOT generate content on prohibited subjects.

4. **Strategic Roles**: Every page has an explicit page_role defining its purpose in the content architecture. Page roles determine content strategy, claim quotas, and template selection.

---

## Section Responsibilities

This section defines the canonical responsibilities for each site section and page type.

### products.aspose.org/{family}/_index.md

**Role**: Product landing page

**Primary Focus**: Positioning, top 5-10 features, getting started CTA

**Content Strategy**:
- Highlight features (not explain in depth)
- Link to docs for tutorials
- Link to repo for code examples
- Emphasize product benefits and use cases

**Forbidden Topics**:
- Detailed API documentation
- Step-by-step tutorials
- Troubleshooting guides
- Known limitations or issues

**Claim Quota**: 5-10 claims (positioning, key_features groups)

**Snippet Quota**: 0-1 snippets (optional hero code example)

**Validation**:
- MUST have page_role = "landing"
- MUST have 5-10 claims
- MUST link to docs section
- MUST link to repository

---

### docs.aspose.org/{family}/_index.md

**Role**: Table of contents / navigation hub

**Primary Focus**: List ALL doc pages with descriptions

**Content Strategy**:
- Brief intro (1-2 paragraphs about documentation structure)
- Hierarchical list of child pages with purpose
- Quick links to products, reference, KB, GitHub repo
- Navigation aid only (no teaching)

**Forbidden Topics**:
- Duplicating child page content
- Code snippets (TOC MUST NOT contain code)
- Deep explanations of features or concepts
- Workflow tutorials

**Claim Quota**: 0-2 claims (intro only, if needed)

**Snippet Quota**: 0 snippets (BLOCKER if violated)

**Special Requirements**:
- MUST reference all child pages from content_strategy.child_pages
- MUST maintain hierarchical structure
- MUST provide navigation context

**Validation**:
- MUST have page_role = "toc"
- MUST NOT contain code snippets (```...```) - BLOCKER violation
- MUST reference all child pages
- claim_quota.max = 2

---

### docs.aspose.org/{family}/getting-started/_index.md

**Role**: Onboarding guide

**Primary Focus**: Installation and first task ("hello world")

**Content Strategy**:
- Prerequisites (system requirements, dependencies)
- Installation steps (package manager, manual install)
- Basic usage (1 simple example)
- Next steps links to developer-guide

**Forbidden Topics**:
- Advanced scenarios
- Complete feature listings
- Troubleshooting (should link to KB instead)
- API deep-dive

**Claim Quota**: 3-5 claims (install, quickstart groups)

**Snippet Quota**: 1 snippet (quickstart example)

**Validation**:
- MUST have page_role = "workflow_page"
- MUST have 3-5 claims
- MUST have exactly 1 quickstart snippet

---

### docs.aspose.org/{family}/developer-guide/_index.md

**Role**: Comprehensive scenario listing (single page)

**Primary Focus**: List ALL workflows from product_facts.workflows

**Content Strategy**:
- Introduction paragraph explaining guide purpose
- For each scenario:
  - H3 heading with scenario name
  - Description (2-3 sentences)
  - Code snippet demonstrating the workflow
  - Links to repo and API reference
- Keep concise (not deep-dive tutorials)
- Sections: Common Scenarios, Advanced Scenarios, Additional Resources

**Forbidden Topics**:
- Installation instructions
- Troubleshooting guides
- API deep-dive documentation
- Feature explanations (focus on usage patterns)

**Claim Quota**: One claim per workflow (all workflows MUST be listed)

**Snippet Quota**: One snippet per workflow (all workflows MUST have code)

**Special Requirements**:
- MUST cover ALL workflows from product_facts.workflows
- content_strategy.scenario_coverage MUST be "all"
- MUST include at least one claim per workflow
- MUST include at least one snippet per workflow

**Validation**:
- MUST have page_role = "comprehensive_guide"
- content_strategy.scenario_coverage MUST be "all"
- MUST cover all workflows (ERROR if any workflow missing)
- Each workflow MUST have at least 1 claim (WARNING if missing)

---

### kb.aspose.org/{family}/*.md

**Role**: Feature showcases (2-3) + troubleshooting (1-2)

KB section serves two distinct purposes with different page roles:

#### Feature Showcase Articles (page_role = "feature_showcase")

**Primary Focus**: How-to guide for a specific prominent feature

**Content Strategy**:
- Feature overview with claim marker
- Use cases (when to use this feature)
- Step-by-step instructions (4-6 steps)
- Code example with syntax highlighting
- Related links to docs, API reference, GitHub

**Forbidden Topics**:
- General features overview
- API reference documentation
- Other features (single feature focus only)
- Installation instructions

**Claim Quota**: 3-8 claims (single feature focus)

**Snippet Quota**: 1-2 snippets per article

**Page Count**: 2-3 feature showcase articles per product

**Validation**:
- MUST have page_role = "feature_showcase"
- MUST focus on single feature (WARNING if > 3 distinct features mentioned)
- MUST have 1-2 code snippets

#### Troubleshooting Articles (page_role = "troubleshooting")

**Primary Focus**: Problem-solution guide

**Content Strategy**:
- Symptoms description
- Root cause explanation
- Resolution steps
- Prevention notes

**Forbidden Topics**:
- Feature explanations
- Installation guides
- General how-to content

**Claim Quota**: 1-5 claims

**Snippet Quota**: 0-1 snippets

**Page Count**: 1-2 troubleshooting articles per product

**Validation**:
- MUST have page_role = "troubleshooting"
- MUST have 1-5 claims

---

### blog.aspose.org/{family}/{post}/index.md

**Role**: Comprehensive launch announcement

**Primary Focus**: Synthesized overview of ALL repository information

**Content Strategy**:
- Introduction (what the product is)
- Key features (from products section, but rephrased)
- Getting started (from docs, but synthesized)
- Use cases (from developer-guide, but summarized)
- Next steps and calls to action

**Special Exception**: Can cover same topics as other sections BUT MUST synthesize (rephrase/restructure), not copy-paste. Blog is allowed to reuse claims but MUST present them differently.

**Forbidden Topics**: None (blog can cover all topics, but must synthesize)

**Claim Quota**: 10-20 claims (broad coverage)

**Snippet Quota**: 1 representative snippet

**Validation**:
- MUST have page_role = "landing" and section = "blog"
- MUST have 10-20 claims
- Exempted from content duplication check (may reuse claims)

---

## Content Allocation Rules

### Claim Distribution Priority

Claims MUST be distributed according to this priority order:

1. **Single-use rule**: Each claim appears on ONE primary page (except blog, which synthesizes)

2. **Priority order**:
   - **Products** (landing): positioning claims, key_features (first 10 features)
   - **Getting-started**: install_steps, quickstart_steps (first 5 claims)
   - **Developer-guide**: workflow_claims (all workflows, one claim per workflow)
   - **KB feature showcases**: key_features with snippets (2-3 features, 3-8 claims each)
   - **Blog**: synthesized overview (rephrase all above, 10-20 claims)

3. **Distribution Algorithm** (W4 implementation):
   ```
   claims_by_priority = [
     (products_page, positioning_claims + key_features[0:10]),
     (getting_started_page, install_claims + quickstart_claims[0:5]),
     (developer_guide_page, workflow_claims),
     (kb_showcase_pages, remaining_key_features[10:13]),
     (blog_page, all_claims_rephrased)
   ]
   ```

4. **Conflict Resolution**: If a claim is eligible for multiple pages, assign to the FIRST page in priority order above.

### Snippet Distribution

Snippets MUST be distributed according to these rules:

1. **Getting-started**: First quickstart snippet only (1 snippet)
2. **Developer-guide**: One snippet per workflow (all workflows MUST have snippets)
3. **KB feature showcases**: 1-2 snippets per article (demonstrating the featured capability)
4. **Blog**: 1 representative snippet (typically a simple "hello world" example)
5. **Products**: 0-1 snippets (optional hero code example)

### Cross-Link Strategy

Cross-links MUST follow these patterns:

- **Docs pages** → Reference pages (2 links max per page)
- **KB pages** → Docs pages (2 links max per page)
- **Blog pages** → Products overview (1 link mandatory)
- **All pages** → GitHub repository (1 link mandatory)
- **TOC pages** → All child pages (MUST link to all children)

---

## Validation Rules (Gate 14)

Gate 14 MUST validate the following rules. See [specs/09_validation_gates.md](09_validation_gates.md) for full Gate 14 specification.

1. **Schema Compliance**: All pages MUST have `page_role` and `content_strategy` fields
2. **TOC Validation**: TOC pages MUST NOT contain code snippets (BLOCKER)
3. **TOC Children**: TOC pages MUST reference all child pages from content_strategy.child_pages
4. **Comprehensive Guide**: comprehensive_guide pages MUST cover all workflows (scenario_coverage = "all")
5. **Forbidden Topics**: Pages MUST NOT mention topics from content_strategy.forbidden_topics
6. **Claim Quotas**: Pages MUST stay within claim_quota limits (min <= actual <= max)
7. **Content Duplication**: No exact content duplication across non-blog pages
8. **Feature Showcase Focus**: feature_showcase KB pages MUST focus on single feature (WARNING if > 3 claims on different features)

---

## Worker Implementation Requirements

### W4 IAPlanner

W4 MUST:
1. Assign page_role to all pages using assign_page_role() function
2. Build content_strategy for all pages using build_content_strategy() function
3. Populate content_strategy.child_pages for TOC pages
4. Set content_strategy.scenario_coverage = "all" for comprehensive_guide pages
5. Distribute claims according to priority order (Section: Content Allocation Rules)
6. Distribute snippets according to quota rules
7. Validate claim quotas are achievable given available evidence

### W5 SectionWriter

W5 MUST:
1. Respect content_strategy.forbidden_topics (MUST NOT generate content on prohibited topics)
2. Respect content_strategy.claim_quota (MUST NOT exceed max, SHOULD meet min)
3. Use appropriate templates based on page_role
4. For TOC pages: list child pages, provide navigation context, NO code snippets
5. For comprehensive_guide pages: cover ALL workflows with claims and snippets
6. For feature_showcase pages: focus on single feature with 1-2 snippets

### W7 Validator

W7 MUST:
1. Implement Gate 14 validation per specs/09_validation_gates.md
2. Validate page_role and content_strategy fields present on all pages
3. Validate TOC pages have no code snippets (BLOCKER if violated)
4. Validate comprehensive_guide pages cover all workflows
5. Validate forbidden_topics compliance (scan markdown for prohibited keywords)
6. Validate claim quotas (count claims, compare to min/max)
7. Validate content duplication (detect claim reuse across non-blog pages)

---

## Backward Compatibility

**Phase 1 (Current)**: page_role and content_strategy fields are OPTIONAL in page_plan.schema.json to maintain backward compatibility. Workers SHOULD populate these fields, validators SHOULD check them if present.

**Phase 2 (Future)**: After all workers updated, fields will become REQUIRED. Gate 14 will ERROR if fields missing.

**Migration Path**:
1. Deploy specs and schema updates (TC-971)
2. Update W4, W5, W7 to populate/respect fields (TC-972, TC-973, TC-974)
3. Run pilots, verify fields present and correct
4. Make fields REQUIRED in schema
5. Gate 14 enforces strictly

---

## Acceptance Criteria

1. All 6 section responsibilities defined (products, docs/_index, docs/getting-started, docs/developer-guide, kb, blog)
2. All 7 page roles documented (landing, toc, comprehensive_guide, workflow_page, feature_showcase, troubleshooting, api_reference)
3. Claim distribution algorithm defined with priority order
4. Snippet distribution rules defined
5. Validation rules documented (Gate 14 requirements)
6. Worker implementation requirements specified (W4, W5, W7)
7. Backward compatibility strategy documented

---

## Related Documentation

- [06_page_planning.md](06_page_planning.md) - Page planning logic and mandatory pages
- [07_section_templates.md](07_section_templates.md) - Template definitions for page roles
- [09_validation_gates.md](09_validation_gates.md) - Gate 14 specification
- [specs/schemas/page_plan.schema.json](schemas/page_plan.schema.json) - Page plan schema with page_role and content_strategy
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Spec authority and governance

---

## Configurable Page Requirements (TC-983, 2026-02-05)

### Overview

Mandatory pages and optional page generation policies are now configured through the ruleset (`specs/rulesets/ruleset.v1.yaml`) rather than hardcoded in W4 Python code. This enables per-family customization via `family_overrides` and evidence-driven page scaling.

### Optional Page Policies

Each section in the ruleset may define `optional_page_policies[]`, which describe how optional pages are generated from evidence. Each policy specifies:

- **page_role**: The strategic role of generated pages (must match `page_plan.schema.json` page_role enum)
- **source**: The evidence source used to generate page candidates
- **priority**: Ranking priority (1 = highest; lower values selected first when quota allows)

**Supported sources**:

| Source | Evidence Input | Candidate Generation |
|--------|---------------|---------------------|
| `per_feature` | `product_facts.key_features` | One workflow_page per key feature with claims |
| `per_workflow` | `product_facts.workflows` | One workflow_page per validated workflow |
| `per_key_feature` | `product_facts.key_features` + `snippet_catalog` | One feature_showcase KB page per feature with snippet coverage |
| `per_api_symbol` | `product_facts.api_surface_summary` | One api_reference page per API class/module |
| `per_deep_dive` | `evidence_volume.total_score` | One blog landing page if total_score > 200 |

### Candidate Generation from Evidence

For each `optional_page_policies` entry in the merged section config:

1. **per_feature**: Iterate `product_facts.key_features`. For each feature with at least one claim, create a candidate with:
   - slug: feature slug (lowercase, hyphenated)
   - page_role: from policy
   - quality_score: `(feature_claim_count * 2) + (feature_snippet_count * 3)`

2. **per_workflow**: Iterate `product_facts.workflows`. For each workflow, create a candidate with:
   - slug: workflow slug
   - page_role: from policy
   - quality_score: `(workflow_claim_count * 2) + (workflow_snippet_count * 3)`

3. **per_key_feature**: Iterate `product_facts.key_features`. For each feature with at least one snippet in `snippet_catalog`, create a candidate with:
   - slug: `how-to-{feature-slug}`
   - page_role: from policy
   - quality_score: `(feature_claim_count * 2) + (feature_snippet_count * 3)`

4. **per_api_symbol**: Iterate `product_facts.api_surface_summary.modules` (or equivalent). For each module/class, create a candidate with:
   - slug: module/class slug
   - page_role: from policy
   - quality_score: `(symbol_count * 1)`

5. **per_deep_dive**: If `evidence_volume.total_score > 200`, create one candidate with:
   - slug: `deep-dive`
   - page_role: from policy
   - quality_score: `evidence_volume.total_score`

### Quality Score Selection

Candidates are selected using the Optional Page Selection Algorithm defined in `specs/06_page_planning.md`:

1. Sort candidates by (priority ascending, quality_score descending, slug ascending) for determinism
2. Select top N where N = effective_max_pages - mandatory_page_count
3. Rejected candidates recorded via telemetry

### Interaction with Content Allocation Rules

Optional pages generated from evidence follow the same claim distribution priority as mandatory pages (see "Content Allocation Rules" above). Specifically:
- Per-feature docs pages receive claims from their feature's claim group
- Per-key-feature KB pages receive claims from their feature with snippet coverage
- Per-api-symbol reference pages receive claims from their module's API surface
- Claim quotas from content_strategy apply to optional pages the same as mandatory pages

### Configuration Reference

- Ruleset: `specs/rulesets/ruleset.v1.yaml` > `sections.<section>.optional_page_policies[]`
- Schema: `specs/schemas/ruleset.schema.json` > `$defs/sectionMinPages` > `optional_page_policies`
- Algorithm: `specs/06_page_planning.md` > "Optional Page Selection Algorithm"
- Templates: `specs/07_section_templates.md` > "Per-Feature Workflow Page Templates"

---

## Revision History

- 2026-02-05: Added Configurable Page Requirements section (TC-983)
- 2026-02-04: Initial specification (TC-971)
