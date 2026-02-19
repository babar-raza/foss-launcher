---
id: TC-1206
title: "Page Expansion — W5 Specialized Generators for New Page Types"
status: Draft
priority: High
owner: "Agent B (Backend/Workers)"
updated: "2026-02-11"
tags: ["w5", "section-writer", "page-expansion", "phase-3"]
depends_on: ["TC-1200", "TC-1203", "TC-1205"]
allowed_paths:
  - plans/taskcards/TC-1206_w5_expanded_generators.md
  - src/launch/workers/w5_section_writer/worker.py
  - tests/unit/workers/test_w5_page_expansion_generators.py
evidence_required:
  - reports/agents/AGENT_B/TC-1206/evidence.md
  - reports/agents/AGENT_B/TC-1206/self_review.md
spec_ref: "33242628c6242b03c2c83a5e978f73d5155f247a"
ruleset_version: "ruleset.v1"
templates_version: "templates.v1"
---

# Taskcard TC-1206 — Page Expansion — W5 Specialized Generators for New Page Types

## Objective
Implement specialized content generation functions in W5 for the 7 new page roles and 4 sub-page types, so that W5 can produce meaningful content for every page that W4 plans. Each generator either fills a template (if template_path is set) or generates content programmatically (for pages without templates).

## Required spec references
- specs/07_section_templates.md (updated by TC-1200 — new template type definitions)
- specs/08_content_distribution_strategy.md (updated by TC-1200 — content strategies per role)
- src/launch/workers/w5_section_writer/worker.py (current W5 — existing generators)
- specs/templates/ (new templates from TC-1205)

## Scope

### In scope
1. **7 new specialized generators** (one per new page_role):
   - `generate_format_conversion_content()` — Populate convert template with format-specific claims/snippets
   - `generate_example_walkthrough_content()` — Build example page with code walkthrough
   - `generate_tutorial_content()` — Build step-by-step tutorial from workflow data
   - `generate_namespace_reference_content()` — Build API reference page per namespace
   - `generate_feature_deep_dive_content()` — Build cross-feature analysis
   - `generate_topic_faq_content()` — Build topic-specific Q&A page
   - `generate_theme_overview_content()` — Build thematic guide
2. **4 sub-page generators**:
   - `generate_feature_overview_content()` — Feature overview sub-page
   - `generate_feature_quickstart_content()` — Feature quickstart sub-page
   - `generate_feature_examples_content()` — Feature examples sub-page
   - `generate_feature_troubleshooting_content()` — Feature-specific troubleshooting sub-page
3. **Routing logic** — Extend existing page_role → generator routing in W5's main dispatch
4. **Token generation** — Extend W4/W5 token generation for new template tokens (`__SOURCE_FORMAT__`, `__TARGET_FORMAT__`, `__FEATURE__`, etc.)
5. **Unit tests** — At least 1 test per generator

### Out of scope
- W4 page planning (TC-1203, TC-1204)
- Template creation (TC-1205)
- W7 ContentReviewer changes (existing reviewer handles all page roles)
- LLM prompt engineering (use existing W5 LLM call pattern)

## Inputs
- page_plan.json (with new page roles, content strategies, sub_pages)
- product_facts.json (claims, format_capabilities, examples, workflows, api_surface_summary)
- snippet_catalog.json
- Templates from TC-1205

## Outputs
- src/launch/workers/w5_section_writer/worker.py (UPDATED — +500 lines: 11 generators + routing + tokens)
- tests/unit/workers/test_w5_page_expansion_generators.py (NEW — ~200 lines)

## Allowed paths
- plans/taskcards/TC-1206_w5_expanded_generators.md
- src/launch/workers/w5_section_writer/worker.py
- tests/unit/workers/test_w5_page_expansion_generators.py

### Allowed paths rationale
W5 worker is the only code file modified. Tests in standard test directory.

## Implementation steps

### Step 1: Read current W5 routing and generator pattern
Locate the dispatch logic that routes `page_role` → generator function. Understand the common pattern:
- Each generator receives `(page_entry, product_facts, snippet_catalog, ...)`
- Returns a markdown string (the page content)
- May call LLM or generate content programmatically

**Resilience note**: The dispatch may use a dict mapping, if/elif chain, or other pattern. Follow whatever pattern exists. Do NOT refactor the dispatch — just add new entries.

### Step 2: Implement `generate_format_conversion_content()`
This is the highest-value generator (drives the most new pages).

**Logic:**
1. Extract `__SOURCE_FORMAT__` and `__TARGET_FORMAT__` from page slug (split on `convert-` and `-to-`)
2. Find claims mentioning either format
3. Find snippets tagged with either format
4. If template exists: populate template tokens
5. If no template: generate programmatically with structure:
   - H1: Convert {Source} to {Target}
   - H2: Overview (claims about format support)
   - H2: Prerequisites
   - H2: Step-by-Step (load → configure → save)
   - H2: Complete Example (full snippet)
   - H2: Related Conversions (cross-links to other format pairs)

**Token mappings:**
```python
{
    "__SOURCE_FORMAT__": source_format.upper(),
    "__TARGET_FORMAT__": target_format.upper(),
    "__SOURCE_FORMAT_LOWER__": source_format.lower(),
    "__TARGET_FORMAT_LOWER__": target_format.lower(),
}
```

### Step 3: Implement `generate_example_walkthrough_content()`
**Logic:**
1. Find example metadata from `product_facts["examples"]` matching page slug
2. Extract description, audience level, code content
3. Find associated claims and snippets
4. Generate: Overview → What This Example Does → Prerequisites → Code Walkthrough → Running → Expected Output

### Step 4: Implement `generate_tutorial_content()`
**Logic:**
1. Find workflow from `product_facts["workflows"]` matching page slug
2. Extract steps, complexity, time estimate
3. For each step: heading + description + code snippet
4. Generate: Overview → What You'll Build → Prerequisites → Steps → Complete Code → Next Steps

### Step 5: Implement `generate_namespace_reference_content()`
**Logic:**
1. Find namespace/module from `api_surface_summary["classes"]` matching page slug
2. Group classes in this namespace
3. For each class: name, description, key methods (table)
4. Generate: Namespace Overview → Classes table → Key Methods → Usage Examples

### Step 6: Implement `generate_feature_deep_dive_content()`
**Logic:**
1. Parse two feature names from slug (split on `-and-`)
2. Find claims for each feature
3. Find snippets showing both features together (if any)
4. Generate: Overview → Feature A → Feature B → Using Together → Best Practices

### Step 7: Implement `generate_topic_faq_content()`
**Logic:**
1. Parse topic from slug (strip `faq-` prefix)
2. Find claims with matching `claim_kind`
3. Transform each claim into Q&A format (claim_text → question, evidence → answer)
4. Generate: Overview → Q&A pairs (H3 per question) → Related Topics

### Step 8: Implement `generate_theme_overview_content()`
**Logic:**
1. Parse theme from slug (strip `guide-` prefix)
2. Find claims in matching `claim_group`
3. Group by sub-topics
4. Generate: Overview → Features list → Common Patterns → Code Examples → Further Reading

### Step 9: Implement 4 sub-page generators
Each follows the same pattern but scoped to the parent feature:
- **overview**: Feature description, capabilities list, when to use, limitations
- **quickstart**: 3-step minimal guide with one snippet
- **examples**: Multiple snippets with explanations (H3 per example)
- **troubleshooting**: Limitation claims as issues, each with symptoms + solution

### Step 10: Extend dispatch routing
Add new entries to the page_role → generator mapping:

```python
# In the dispatch logic:
if page_role == "format_conversion":
    content = generate_format_conversion_content(page, product_facts, snippet_catalog)
elif page_role == "example_walkthrough":
    content = generate_example_walkthrough_content(page, product_facts, snippet_catalog)
elif page_role == "tutorial":
    content = generate_tutorial_content(page, product_facts, snippet_catalog)
elif page_role == "namespace_reference":
    content = generate_namespace_reference_content(page, product_facts, snippet_catalog)
elif page_role == "feature_deep_dive":
    content = generate_feature_deep_dive_content(page, product_facts, snippet_catalog)
elif page_role == "topic_faq":
    content = generate_topic_faq_content(page, product_facts, snippet_catalog)
elif page_role == "theme_overview":
    content = generate_theme_overview_content(page, product_facts, snippet_catalog)
```

For sub-pages, detect via `parent_page` field and route to sub-page generators.

### Step 11: Write unit tests
Create `tests/unit/workers/test_w5_page_expansion_generators.py`:

For each of the 11 generators:
1. **Happy path** — Provide mock data, verify output contains expected headings and claim markers

Additional:
2. **test_format_conversion_token_extraction** — Verify source/target format parsed from slug
3. **test_unknown_page_role_fallback** — Verify graceful fallback for unknown roles
4. **test_sub_page_parent_context** — Verify sub-page generators receive parent context

### Step 12: Run tests
```bash
.venv/Scripts/python.exe -m pytest tests/unit/workers/test_w5_page_expansion_generators.py -v
.venv/Scripts/python.exe -m pytest tests/unit/workers/ -k "w5" -v  # regression
```

## Failure modes

### Failure mode 1: Generator produces empty content for valid page
**Detection:** W5 output file is empty or has only frontmatter. W7 content validation fails.
**Resolution:** Each generator must have a fallback: if no claims/snippets match, generate a minimal page with the required headings and a "Content coming soon" placeholder. Never return empty string.
**Spec/Gate:** specs/08 content completeness rule, W9 Gate 14

### Failure mode 2: Token mismatch between template and generator
**Detection:** Output contains raw `__TOKEN__` strings because generator didn't populate them.
**Resolution:** After template population, scan for remaining `__TOKEN__` patterns. Log warning for any unpopulated tokens. Replace with sensible defaults.
**Spec/Gate:** specs/07 token registry, W9 Gate 11 template token lint

### Failure mode 3: Sub-page generator can't find parent context
**Detection:** Sub-page generator receives a page entry with `parent_page` slug but can't find the parent in the page plan.
**Resolution:** Pass the full page plan to generators (or a parent lookup dict). If parent not found, generate standalone content (degrade gracefully).
**Spec/Gate:** specs/06 sub-page model

## Task-specific review checklist
1. [ ] All 7 page-type generators implemented and routed
2. [ ] All 4 sub-page generators implemented and routed
3. [ ] Each generator produces valid markdown with required headings
4. [ ] Claim markers `[claim: claim_id]` present in output
5. [ ] Token generation covers all new template tokens
6. [ ] Fallback content for empty evidence (never return empty)
7. [ ] Sub-page generators receive parent context
8. [ ] Dispatch routing follows existing W5 pattern
9. [ ] Post-processing (think-tag stripping, fence removal) applies to new generators
10. [ ] 14+ unit tests (1 per generator + 3 cross-cutting)

## Deliverables
- src/launch/workers/w5_section_writer/worker.py (UPDATED — +500 lines)
- tests/unit/workers/test_w5_page_expansion_generators.py (NEW — ~200 lines)
- reports/agents/AGENT_B/TC-1206/evidence.md
- reports/agents/AGENT_B/TC-1206/self_review.md

## Acceptance checks
1. [ ] 11 generators implemented and routed
2. [ ] All produce valid markdown content
3. [ ] Claim markers present in all generated content
4. [ ] Token population works for template-based generation
5. [ ] All tests pass
6. [ ] Existing W5 tests pass (no regression)

## Preconditions / dependencies
- TC-1200 completed (content strategy specs)
- TC-1203 completed (W4 generates pages with new roles)
- TC-1205 completed (templates available)

## Self-review
[To be completed by Agent B after implementation]
