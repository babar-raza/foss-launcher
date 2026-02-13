---
id: TC-1200
title: "Page Expansion Epic — Specs & Schemas Foundation"
status: Draft
priority: Critical
owner: "Agent D (Docs & Specs)"
updated: "2026-02-11"
tags: ["specs", "schemas", "page-expansion", "phase-0"]
depends_on: []
allowed_paths:
  - plans/taskcards/TC-1200_page_expansion_specs_schemas.md
  - specs/08_content_distribution_strategy.md
  - specs/06_page_planning.md
  - specs/07_section_templates.md
  - specs/schemas/page_plan.schema.json
  - specs/schemas/run_config.schema.json
evidence_required:
  - reports/agents/AGENT_D/TC-1200/evidence.md
  - reports/agents/AGENT_D/TC-1200/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1200 — Page Expansion Epic — Specs & Schemas Foundation

## Objective
Extend the specification and schema layer to support 7 new page expansion strategies that dramatically increase page count per pilot run. Define new `optional_page_policy` sources, new `page_role` values, new config keys, and the contracts that W2/W4/W5 implementations will follow.

## Required spec references
- specs/08_content_distribution_strategy.md (current distribution strategy — will be extended)
- specs/06_page_planning.md (current page planning — will be extended with sub-page model)
- specs/07_section_templates.md (current templates — will add new template types)
- specs/schemas/page_plan.schema.json (current schema — will add new page_role enum values)
- specs/schemas/run_config.schema.json (current schema — will add new config keys)
- specs/rulesets/ruleset.v1.yaml (current ruleset — read-only reference for policy sources)
- plans/taskcards/00_TASKCARD_CONTRACT.md (taskcard rules)

## Scope

### In scope
1. **New optional_page_policy sources** — Define contracts for:
   - `per_format_pair`: One page per (input_format, output_format) conversion pair
   - `per_example`: One page per repo example that has claims AND snippets
   - `per_workflow_tutorial`: One page per multi-step workflow as a tutorial
   - `per_namespace_reference`: One reference page per namespace/module group
   - `per_feature_combination`: Pairwise feature deep-dive pages
   - `per_theme_group`: Thematic grouping of related features
   - `per_faq_topic`: One FAQ page per topic area (installation, licensing, per-feature)
2. **New page_role enum values** — Add: `format_conversion`, `example_walkthrough`, `tutorial`, `namespace_reference`, `feature_deep_dive`, `theme_overview`, `topic_faq`
3. **Sub-page model** — Define how a feature page can spawn child sub-pages (overview, quickstart, examples, troubleshooting) via `subsections` in PageIdentifier
4. **New run_config keys** — Define:
   - `page_expansion.format_pairs_override`: Explicit list of `[source, target]` pairs to add/remove
   - `page_expansion.reference_granularity`: `"namespace"` (default) or `"class"`
   - `page_expansion.max_feature_sub_pages`: Max sub-pages per feature (default 4)
   - `page_expansion.combination_top_n`: How many top features to pair (default 5)
   - `page_expansion.enabled_policies`: List of policy sources to activate (default: all)
5. **Schema extensions** — Update page_plan.schema.json with new enum values and sub-page fields
6. **run_config.schema.json** — Add `page_expansion` object with all new keys

### Out of scope
- Locale-based page multiplication (explicitly excluded)
- Implementation of W2/W4/W5 workers (TC-1202, TC-1203, TC-1204, TC-1206)
- Ruleset quota changes (TC-1201)
- Template file creation (TC-1205)
- Test implementation (TC-1207)

## Inputs
- Current specs/08_content_distribution_strategy.md
- Current specs/06_page_planning.md
- Current specs/07_section_templates.md
- Current specs/schemas/page_plan.schema.json
- Current specs/schemas/run_config.schema.json

## Outputs
- specs/08_content_distribution_strategy.md (UPDATED — +200 lines: 7 new policy source definitions)
- specs/06_page_planning.md (UPDATED — +150 lines: sub-page model, new page roles)
- specs/07_section_templates.md (UPDATED — +100 lines: 7 new template type definitions)
- specs/schemas/page_plan.schema.json (UPDATED — new page_role enum values, sub-page fields)
- specs/schemas/run_config.schema.json (UPDATED — page_expansion config object)
- Evidence bundle

## Allowed paths
- plans/taskcards/TC-1200_page_expansion_specs_schemas.md
- specs/08_content_distribution_strategy.md
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/schemas/page_plan.schema.json
- specs/schemas/run_config.schema.json

### Allowed paths rationale
TC-1200 is the specs-only foundation. All changes are in specs/ and schemas/. No code, no tests, no templates, no rulesets. This establishes the contracts that all other TC-120x taskcards implement.

## Implementation steps

### Step 1: Read current state of all target files
Read all 5 target files to understand current structure. The system state may have changed since this taskcard was written — implementation MUST adapt to the actual file contents at execution time.

**Resilience note**: Do NOT hardcode line numbers. Use section headers or unique markers to locate insertion points. If a section already exists (e.g., a prior agent added `per_format_pair`), extend rather than duplicate.

### Step 2: Extend specs/08_content_distribution_strategy.md — New Policy Sources
Add a new section `## Page Expansion Policies` after the existing `Optional Page Policies` section.

**For each new source, define:**
- Source name and description
- Evidence input (what data feeds it)
- Candidate generation algorithm
- Quality scoring formula
- Slug generation pattern
- Page role assignment
- Content strategy defaults (primary_focus, forbidden_topics, claim_quota)
- Example output for the 3D pilot

**7 new sources to define:**

1. **`per_format_pair`** — Generates one page per supported (input, output) format conversion.
   - Evidence: `product_facts.api_surface_summary` (format-capable classes) + W2 `format_capabilities` (NEW field from TC-1202)
   - Candidate: For each `(read_format, write_format)` pair where both are confirmed
   - Override: `page_expansion.format_pairs_override` in run_config can add `{"add": [...]}` or `{"remove": [...]}` pairs
   - Score: `(len(matching_claims) * 2) + (len(matching_snippets) * 3)`
   - Slug: `convert-{source_lower}-to-{target_lower}` (e.g., `convert-fbx-to-gltf`)
   - Role: `format_conversion`

2. **`per_example`** — Generates one page per repo example WITH evidence.
   - Evidence: `product_facts.examples[]` (from W2 enrich_examples) filtered to those with `claim_ids.length > 0 AND snippet_ids.length > 0`
   - Score: `(len(claim_ids) * 2) + (len(snippet_ids) * 3) + audience_level_bonus`
   - Slug: `example-{sanitized_example_name}`
   - Role: `example_walkthrough`

3. **`per_workflow_tutorial`** — Generates one standalone tutorial per workflow.
   - Evidence: `product_facts.workflows[]` (from W2 enrich_workflows)
   - Score: `(step_count * 2) + (len(matching_snippets) * 3) + complexity_bonus`
   - Slug: `tutorial-{sanitized_workflow_name}`
   - Role: `tutorial`

4. **`per_namespace_reference`** — One reference page per namespace/module.
   - Evidence: `product_facts.api_surface_summary.classes[]` grouped by module/namespace
   - Score: `(class_count * 2) + (function_count * 1)`
   - Slug: `ref-{sanitized_namespace}` (e.g., `ref-aspose-threed-entities`)
   - Role: `namespace_reference`

5. **`per_feature_combination`** — Pairwise deep-dive pages for top features.
   - Evidence: Top N features from `claim_groups["key_features"]` sorted by quality_score
   - N controlled by `page_expansion.combination_top_n` (default 5, generating up to N*(N-1)/2 pairs)
   - Score: `quality_score_A + quality_score_B + (1 if shared_snippets else 0) * 5`
   - Slug: `deep-dive-{featureA}-and-{featureB}` (alphabetical order for determinism)
   - Role: `feature_deep_dive`

6. **`per_theme_group`** — Thematic grouping of related features.
   - Evidence: `claim_groups` keys that have 3+ claim_ids (each key becomes a theme)
   - Score: `sum(claim_quality_scores) + (len(claim_ids) * 1)`
   - Slug: `guide-{sanitized_theme_name}` (e.g., `guide-key-features`, `guide-limitations`)
   - Role: `theme_overview`

7. **`per_faq_topic`** — One FAQ page per topic area.
   - Evidence: Claims grouped by `claim_kind` (installation, format, limitation, compatibility)
   - Only generates page if topic has 3+ claims
   - Score: `len(claims_in_topic) * 2`
   - Slug: `faq-{topic_name}` (e.g., `faq-installation`, `faq-formats`)
   - Role: `topic_faq`

### Step 3: Extend specs/06_page_planning.md — Sub-Page Model
Add section `## Feature Sub-Page Model` defining how features expand into sub-pages.

**Sub-page structure per feature:**
- `{feature}/` — Overview (what it does, when to use it)
- `{feature}/quickstart/` — Minimal code to get started
- `{feature}/examples/` — Multiple code samples with explanations
- `{feature}/troubleshooting/` — Common issues for that specific feature

**Rules:**
- Sub-pages are optional, controlled by `page_expansion.max_feature_sub_pages` (0 disables, default 4)
- Only generated for features with sufficient evidence (claim_count >= 3 AND snippet_count >= 1)
- Uses existing `subsections` field in PageIdentifier
- Parent feature page always exists; sub-pages are children
- URL structure: `/{family}/docs/developer-guide/{feature}/{sub-page}/`

### Step 4: Extend specs/07_section_templates.md — New Template Types
Add template type definitions for each new page role.

### Step 5: Update specs/schemas/page_plan.schema.json
- Add to `page_role` enum: `format_conversion`, `example_walkthrough`, `tutorial`, `namespace_reference`, `feature_deep_dive`, `theme_overview`, `topic_faq`
- Add `sub_pages` array field to page entry (list of child page identifiers)
- Add `parent_page` optional string field (slug of parent, for sub-pages)
- All new fields MUST be optional (backward compatible)

### Step 6: Update specs/schemas/run_config.schema.json
Add `page_expansion` object:
```json
{
  "page_expansion": {
    "type": "object",
    "description": "TC-1200: Controls page expansion policies for increasing page count.",
    "properties": {
      "enabled_policies": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of policy sources to activate. Empty = all enabled.",
        "default": []
      },
      "format_pairs_override": {
        "type": "object",
        "properties": {
          "add": {"type": "array", "items": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}},
          "remove": {"type": "array", "items": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}}
        }
      },
      "reference_granularity": {
        "type": "string",
        "enum": ["namespace", "class"],
        "default": "namespace"
      },
      "max_feature_sub_pages": {
        "type": "integer",
        "minimum": 0,
        "maximum": 6,
        "default": 4
      },
      "combination_top_n": {
        "type": "integer",
        "minimum": 2,
        "maximum": 10,
        "default": 5
      }
    },
    "additionalProperties": false
  }
}
```

### Step 7: Cross-validate all specs for consistency
Verify no contradictions between specs/06, specs/07, specs/08, and schemas.

## Failure modes

### Failure mode 1: Schema backward incompatibility
**Detection:** Existing page_plan.json files fail validation against updated schema. Tests that load old page plans break.
**Resolution:** All new fields MUST be optional. New enum values are additive. Run `jsonschema.Draft202012Validator.check_schema()` and validate existing test fixtures against updated schema.
**Spec/Gate:** JSON Schema Draft 2020-12, CONTRIBUTING.md rule #6

### Failure mode 2: Conflicting page_role assignments between old and new policies
**Detection:** Two policy sources generate candidates with the same slug but different page_roles.
**Resolution:** Define explicit priority order in specs/08: existing policies > new policies. Slug collision detection is already in W4 — extend collision error codes for new sources.
**Spec/Gate:** specs/08_content_distribution_strategy.md collision detection section

### Failure mode 3: Sub-page model conflicts with existing URL structure
**Detection:** Sub-page URLs collide with existing page URLs (e.g., `{feature}/examples/` collides with a template page).
**Resolution:** Sub-page slugs use reserved prefixes. Define collision detection rule in spec. Sub-pages always nest under their parent's URL.
**Spec/Gate:** specs/06_page_planning.md URL construction rules

## Task-specific review checklist
1. [ ] All 7 new policy sources fully defined with evidence input, scoring, slug pattern, and role
2. [ ] All 7 new page_role enum values added to schema
3. [ ] Sub-page model defined with URL structure, evidence thresholds, and config controls
4. [ ] `page_expansion` config object defined in run_config schema with all 5 keys
5. [ ] All new schema fields are OPTIONAL (backward compatible)
6. [ ] Format pairs override mechanism defined (add/remove lists)
7. [ ] Template type definitions added for all new page roles
8. [ ] Quality scoring formulas are deterministic (no randomness)
9. [ ] Slug generation patterns are deterministic (alphabetical ordering for pairs)
10. [ ] Cross-references between specs/06, specs/07, specs/08 are consistent

## Deliverables
- Updated specs/08_content_distribution_strategy.md (+200 lines)
- Updated specs/06_page_planning.md (+150 lines)
- Updated specs/07_section_templates.md (+100 lines)
- Updated specs/schemas/page_plan.schema.json (new enums + fields)
- Updated specs/schemas/run_config.schema.json (page_expansion object)
- reports/agents/AGENT_D/TC-1200/evidence.md
- reports/agents/AGENT_D/TC-1200/self_review.md

## Acceptance checks
1. [ ] 7 new policy sources defined in specs/08
2. [ ] 7 new page_role values in page_plan.schema.json
3. [ ] Sub-page model in specs/06 with URL rules and config controls
4. [ ] page_expansion object in run_config.schema.json with 5 keys
5. [ ] Schema validation passes (Draft 2020-12)
6. [ ] All new fields optional (backward compatible)
7. [ ] No contradictions between specs
8. [ ] Deterministic scoring and slug generation documented

## Preconditions / dependencies
- No code dependencies — this is pure specs/schemas work
- Must be completed BEFORE TC-1201, TC-1202, TC-1203, TC-1204, TC-1205, TC-1206

## Self-review
[To be completed by Agent D after implementation]
