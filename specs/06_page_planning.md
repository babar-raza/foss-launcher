# Page Planning (IA Plan)

## Goal
Define exactly what pages to create and what each page must contain, before writing.

## PagePlan (page_plan.json)
Each PageSpec must include:
- section: products | docs | reference | kb | blog
- slug and output_path (derived from section mapping)
- url_path (public canonical URL path, derived via `specs/33_public_url_mapping.md`)
- title
- purpose
- required_headings (ordered)
- required_claim_ids (ordered)
- required_snippet_tags (ordered)
- cross_links (explicit target URLs, using url_path)
- seo_keywords (optional)
- forbidden_topics (optional)

**Path distinction (binding):**
- `output_path`: Content file path relative to site repo root (e.g., `content/docs.aspose.org/cells/en/python/overview.md`)
- `url_path`: Public canonical URL path used for cross-links and navigation (e.g., `/cells/python/overview/`)

**cross_links format (binding, TC-1002):**
The `cross_links` field contains **absolute URLs** pointing to related pages across subdomains:
- Format: `https://<subdomain>/<family>/<platform>/<slug>/`
- Example: `https://docs.aspose.org/cells/python/overview/`
- Supported subdomains:
  - `docs.aspose.org` - documentation pages
  - `kb.aspose.org` - knowledge base articles
  - `blog.aspose.org` - blog posts
  - `products.aspose.org` - product landing pages
  - `reference.aspose.org` - API reference pages

**Rationale**: In a subdomain architecture, relative cross-section links break because they resolve on the wrong subdomain. Absolute URLs ensure cross-subdomain navigation works correctly.

**Schema reference**: See `specs/schemas/page_plan.schema.json` > `cross_links` with `format: uri`.

## Planning rules
- Every section describes the same product with a different purpose:
  - products: positioning, overview, features, quickstart, supported environments
  - docs: tutorials and how-to flows
  - reference: API landing and navigation by modules/namespaces
  - kb: troubleshooting, FAQs, limitations, performance tips
  - blog: announcement plus a deep dive or release-note style post
- Cross-links are mandatory and consistent:
  - docs → reference
  - kb → docs
  - blog → products
- Cross-links MUST use `url_path` from `page_plan.pages[].url_path` (NOT `output_path`). See `specs/33_public_url_mapping.md` for URL resolution.

## Determinism
- Page order must be stable:
  - sort by section order from config then by slug
- Headings must be stable templates, not creative.

## Content quotas (minimum viable launch)
Minimum and maximum pages per section are configurable via ruleset:
- products: min 1, max 10 (landing page, features, supported environments)
- docs: min 2, max 50 (how-to guides based on workflows)
- reference: min 1, max 100 (API landing, module/namespace pages)
- kb: min 3, max 30 (FAQ, troubleshooting, limitations/perf)
- blog: min 1, max 20 (announcement and deep-dive posts)

**Quota enforcement:**
- `min_pages`: Minimum pages required for section to be viable (enforced by planner)
- `max_pages`: Maximum pages allowed to prevent unbounded growth (enforced by planner)
- If evidence would generate more than `max_pages`, prioritize by:
  1. Core/essential content (landing pages, getting started)
  2. Frequently used features (based on snippet usage)
  3. Content with strong claim coverage

**Configuration location:**
See `specs/rulesets/ruleset.v1.yaml` section quotas and `specs/schemas/ruleset.schema.json` for schema definition.

## Mandatory vs Optional Page Policy (TC-940)

### Mandatory Pages (Required for Launch)

Each section has a set of **mandatory pages** that MUST be included in every page plan to ensure minimum viability:

**products** (min: 1):
- Overview/Landing page (slug: `overview` or `index`)

**docs** (min: 2):
- Getting Started guide (slug: `getting-started`)
- At least one workflow-based how-to guide

**reference** (min: 1):
- API Overview/Landing page (slug: `index` or `api-overview`)

**kb** (min: 3):
- FAQ page
- Known Limitations page
- Basic troubleshooting guide

**blog** (min: 1):
- Announcement post (product introduction)

### Optional Pages (Evidence-Driven Selection)

Beyond mandatory pages, the planner MAY add **optional pages** up to `max_pages` based on evidence quality. Optional page types by section:

**products** (optional):
- Features page
- Quickstart page
- Supported Environments page
- Installation guide
- Additional feature showcases

**docs** (optional):
- Additional how-to guides (one per validated workflow)
- Advanced tutorials
- Migration guides

**reference** (optional):
- Module/namespace pages (prioritize by usage in snippets)
- Class/interface detail pages

**kb** (optional):
- Performance optimization guides
- Platform-specific deployment guides
- Additional troubleshooting scenarios
- Topic cluster pages (grouped by capability/format, see "Topic Cluster Strategy" below)

**blog** (optional):
- Deep-dive technical posts
- Release note style posts
- Use case showcases

---

## Content Distribution Strategy (2026-02-04)

### Page Roles

Each page MUST have a `page_role` field defining its strategic purpose in the content architecture. This field drives template selection, content strategy, and validation rules.

**Defined Page Roles**:

- **landing**: Product or section landing page (products overview, blog announcement)
  - Purpose: Position product, highlight key features, provide CTAs
  - Typical sections: products, blog
  - Content focus: High-level positioning, benefits, calls to action

- **toc**: Table of contents / navigation hub (docs/_index.md)
  - Purpose: List all documentation pages with navigation context
  - Typical sections: docs
  - Content focus: Navigation, page listing, brief descriptions
  - **Special constraint**: MUST NOT contain code snippets

- **comprehensive_guide**: Single page listing ALL scenarios (docs/developer-guide/_index.md)
  - Purpose: Comprehensive directory of all product usage scenarios
  - Typical sections: docs
  - Content focus: All workflows with descriptions and code examples
  - **Special constraint**: MUST cover ALL workflows from product_facts.workflows

- **workflow_page**: How-to guide for specific task (docs/guides/*.md)
  - Purpose: Step-by-step tutorial for accomplishing a specific task
  - Typical sections: docs
  - Content focus: Single workflow, detailed instructions, code examples

- **feature_showcase**: KB article showcasing prominent feature (kb/how-to-*.md)
  - Purpose: Deep-dive how-to for a specific notable feature
  - Typical sections: kb
  - Content focus: Single feature, use cases, step-by-step guide, code examples

- **troubleshooting**: KB article for problem-solution (kb/troubleshooting.md)
  - Purpose: Diagnose and resolve specific problems
  - Typical sections: kb
  - Content focus: Symptoms, causes, resolutions

- **faq**: FAQ page with question-answer pairs (kb/faq.md)
  - Purpose: Answer frequently asked questions in a concise Q&A format
  - Typical sections: kb
  - Content focus: Common questions, direct answers, links to detailed docs
  - Claim source: `claim_kind=faq` claims from product_facts

- **best_practices**: Best practice recommendations page (kb/best-practices.md)
  - Purpose: Provide recommended approaches, optimization tips, and guidelines
  - Typical sections: kb
  - Content focus: Do/don't patterns, optimization advice, architectural guidance
  - Claim source: `claim_kind=best_practice` claims from product_facts

- **tutorial**: Step-by-step tutorial guide (kb/tutorial-*.md)
  - Purpose: Educational walkthrough for learning a specific technique
  - Typical sections: kb
  - Content focus: Structured learning path, progressive complexity, complete examples
  - Claim source: `claim_kind=tutorial` claims from product_facts

- **api_reference**: API documentation (reference section)
  - Purpose: Technical reference for classes, methods, modules
  - Typical sections: reference
  - Content focus: API signatures, parameters, return values

**Binding**: W4 IAPlanner MUST assign page_role to all pages. W5 SectionWriter MUST use page_role to select appropriate templates. W9 Validator MUST validate page_role-specific constraints (Gate 14).

### Content Strategy

Each page MUST have a `content_strategy` object defining content distribution rules and overlap prevention.

**Content Strategy Fields**:

- **primary_focus** (string, required): What this page is about (1-2 sentences)
  - Example: "Comprehensive listing of all product usage scenarios"
  - Purpose: Guide content generation, prevent scope creep

- **forbidden_topics** (array of strings, required): Topics/concepts to explicitly avoid on this page
  - Example: `["installation", "troubleshooting", "api_deep_dive"]`
  - Purpose: Prevent content duplication and maintain clear boundaries
  - Binding: W5 MUST NOT generate content on forbidden topics, W7 MUST validate compliance

- **claim_quota** (object, required): Minimum and maximum claims allowed on this page
  - Fields:
    - `min` (number): Minimum claims required
    - `max` (number): Maximum claims allowed
  - Example: `{"min": 5, "max": 10}`
  - Purpose: Control content volume, prevent pages from becoming too sparse or too dense
  - Binding: W4 MUST distribute claims within quotas, W7 MUST validate actual claim count

- **child_pages** (array of strings, optional, TOC only): Slugs of child pages to list
  - Example: `["getting-started", "developer-guide", "advanced-topics"]`
  - Purpose: Define navigation structure for TOC pages
  - Binding: W4 MUST populate for TOC pages, W7 MUST validate all children referenced

- **scenario_coverage** (string, optional, comprehensive_guide only): "single" | "all" | "subset"
  - Example: `"all"` for developer-guide (MUST cover all workflows)
  - Purpose: Ensure comprehensive guides actually cover all scenarios
  - Binding: W4 MUST set to "all" for comprehensive_guide pages, W9 MUST validate all workflows present

**Binding**: W4 IAPlanner MUST populate content_strategy for all pages. W5 SectionWriter MUST respect forbidden_topics and claim_quota. W9 Validator MUST enforce via Gate 14.

### Content Distribution Algorithm

W4 IAPlanner MUST distribute content according to these rules (from specs/08_content_distribution_strategy.md):

**Claim Distribution Priority**:

1. **Products** (page_role = "landing"): positioning claims, key_features (first 10 features)
   - Claim quota: 5-10 claims
   - Focus: High-level feature highlights

2. **Getting-started** (page_role = "workflow_page"): install_steps, quickstart_steps (first 5 claims)
   - Claim quota: 3-5 claims
   - Focus: Onboarding, first task

3. **Developer-guide** (page_role = "comprehensive_guide"): workflow_claims (all workflows, one per workflow)
   - Claim quota: One claim per workflow (all workflows MUST be listed)
   - Focus: Comprehensive scenario coverage

4. **KB showcases** (page_role = "feature_showcase"): key_features with snippets (2-3 features, one per page)
   - Claim quota: 3-8 claims per page (single feature focus)
   - Focus: Deep-dive on notable features

5. **Blog** (page_role = "landing", section = "blog"): synthesized overview (rephrase, don't duplicate)
   - Claim quota: 10-20 claims (broad coverage)
   - Special: Exempted from duplication check (may reuse claims but must synthesize)

**Snippet Distribution**:

- **Getting-started**: First quickstart snippet (1 snippet)
- **Developer-guide**: One snippet per workflow (all workflows)
- **KB showcases**: 1-2 snippets per feature
- **Blog**: 1 representative snippet
- **TOC pages**: 0 snippets (BLOCKER if violated)

**Conflict Resolution**: If a claim is eligible for multiple pages, assign to the FIRST page in priority order above. Each claim appears on ONE primary page (except blog, which synthesizes).

### Mandatory Pages by Section (Updated 2026-02-05, TC-983)

Mandatory pages are now **configured via ruleset** (`specs/rulesets/ruleset.v1.yaml`) rather than hardcoded. Each section's `mandatory_pages` array defines the slugs and page_roles that MUST be present in every page plan. See `specs/schemas/ruleset.schema.json` `sectionMinPages` $def for the schema definition.

**products** (min: 1, configured via `sections.products.mandatory_pages`):
- Overview/Landing page (slug: `overview`) - page_role: "landing"

**docs** (min: 5, was 2, configured via `sections.docs.mandatory_pages`):
- TOC index page (slug: `_index`) - page_role: "toc"
- Installation guide (slug: `installation`) - page_role: "workflow_page"
- Getting Started guide (slug: `getting-started`) - page_role: "workflow_page"
- Overview page (slug: `overview`) - page_role: "landing"
- Developer Guide comprehensive listing (slug: `developer-guide`) - page_role: "comprehensive_guide"

**reference** (min: 1, configured via `sections.reference.mandatory_pages`):
- API Overview page (slug: `api-overview`) - page_role: "api_reference"

**kb** (min: 4, was 3, configured via `sections.kb.mandatory_pages`):
- FAQ page (slug: `faq`) - page_role: "troubleshooting"
- Troubleshooting page (slug: `troubleshooting`) - page_role: "troubleshooting"

**blog** (min: 1, configured via `sections.blog.mandatory_pages`):
- Announcement post (slug: `announcement`) - page_role: "landing"

**Rationale for changes (TC-983)**: Mandatory pages are now data-driven from the ruleset to support per-family customization via `family_overrides`. The docs section min_pages increased from 2 to 5 to reflect all mandatory pages. KB min_pages increased from 3 to 4. See "Configurable Page Requirements" section below for merge logic.

### Configurable Page Requirements (TC-983, 2026-02-05)

Mandatory page lists are no longer hardcoded in W4 Python code. They are configured through the ruleset and can be customized per product family.

**Configuration sources**:
1. **Global mandatory pages**: `specs/rulesets/ruleset.v1.yaml` > `sections.<section>.mandatory_pages[]`
2. **Family overrides**: `specs/rulesets/ruleset.v1.yaml` > `family_overrides.<family>.sections.<section>.mandatory_pages[]`

**Merge logic** (binding):
1. Load global `mandatory_pages` for the section from ruleset `sections.<section>.mandatory_pages`
2. If `family_overrides.<product_family>` exists and has `sections.<section>.mandatory_pages`:
   - UNION the family mandatory_pages with the global list
   - If a slug already exists in the global list, the family entry is skipped (deduplicate by slug)
3. The merged list is the **effective mandatory pages** for the section

**Example**: For family "3d", docs section:
- Global: `[_index, installation, getting-started, overview, developer-guide]`
- Family override: `[model-loading, rendering]`
- Merged: `[_index, installation, getting-started, overview, developer-guide, model-loading, rendering]` (7 mandatory pages)

**Schema reference**: `specs/schemas/ruleset.schema.json` > `$defs/sectionMinPages` > `mandatory_pages` array and `optional_page_policies` array. Top-level `family_overrides` property.

**Worker reference**: W4 IAPlanner reads merged page requirements. See `specs/21_worker_contracts.md` W4 contract for input/output details.

### Optional Page Selection Algorithm (Deterministic, Updated TC-983)

When evidence supports more pages than `max_pages`, the planner MUST select optional pages using this deterministic algorithm:

**Step 0: Compute evidence volume** (TC-983)
Before selecting optional pages, W4 MUST compute the `evidence_volume` metrics from product_facts and snippet_catalog:
```
evidence_volume = {
  total_score: (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1),
  claim_count: <total claims in product_facts>,
  snippet_count: <total snippets in snippet_catalog>,
  api_symbol_count: <total symbols in api_surface_summary>,
  workflow_count: <total workflows in product_facts.workflows>,
  key_feature_count: <total features in product_facts.key_features>
}
```
The evidence_volume MUST be recorded in `page_plan.evidence_volume` (see `specs/schemas/page_plan.schema.json`).

**Step 1: Add all mandatory pages**
Include all mandatory pages for the section from the **merged** ruleset config (global + family_overrides). See "Configurable Page Requirements" section above.

**Step 1.5: Compute effective quotas** (TC-983)
Using evidence_volume and launch_tier, compute per-section effective quotas:
- Tier scaling coefficients: minimal=0.3, standard=0.7, rich=1.0
- Evidence-based section targets (before tier capping):
  - products: 1 (always landing only)
  - docs: len(mandatory_pages) + workflow_count
  - reference: 1 + api_symbol_count // 3
  - kb: len(mandatory_pages) + min(key_feature_count, 5)
  - blog: 1 + (1 if total_score > 200)
- Effective max = clamp(evidence_target, min_pages, tier_adjusted_max)
The effective_quotas MUST be recorded in `page_plan.effective_quotas` (see `specs/schemas/page_plan.schema.json`).

**Step 2: Generate optional page candidates** (TC-983)
For each `optional_page_policies` entry in the merged section config, generate candidates from evidence:
- `source: "per_feature"`: one candidate page per key_feature claim
- `source: "per_workflow"`: one candidate page per workflow
- `source: "per_key_feature"`: one KB showcase per key_feature with snippet coverage
- `source: "per_api_symbol"`: one reference page per API class/module
- `source: "per_deep_dive"`: one blog post if total_score > 200

**Step 3: Calculate quality score for each optional page candidate**
```
quality_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)
```
Where claim_count, snippet_count, and api_symbol_count are scoped to the **specific candidate** (not global totals).

**Minimum quality threshold**: Optional pages from `per_key_feature` source MUST have `quality_score >= 5` (at least 1 matching snippet). Pages below this threshold are excluded to prevent thin content with only 1 claim and no snippet coverage (quality_score = 2).

**Step 4: Rank optional candidates**
Sort candidates by:
1. Priority from `optional_page_policies[].priority` (ascending, lower = higher priority)
2. Quality score (descending)
3. Slug (ascending, for stable tie-breaking)

**Step 5: Select top N optional pages**
```
N = effective_max_pages - mandatory_page_count
```
Select the top N candidates from the sorted list. Use `effective_max_pages` from computed effective_quotas (not raw `max_pages`).

**Step 6: Record rejected candidates**
Emit telemetry event `PAGES_REJECTED` with:
- Section name
- Rejected page slugs
- Rejection reason (e.g., "exceeded effective max_pages limit")

**Determinism requirement**: Two runs with identical ProductFacts, RunConfig, and ruleset MUST produce identical page_plan.json (same pages in same order).

### Topic Cluster Strategy (Round 13, KB section)

For the KB section, optional pages SHOULD be organized into **topic clusters** rather than flat lists. This mirrors the proven pattern from production sites (e.g., aspose.net KB structure).

**Cluster structure**:
```
kb/{family}/{platform}/{locale}/
├── _index.md                              (KB landing — mandatory)
├── faq.md                                 (FAQ — mandatory)
├── troubleshooting.md                     (Troubleshooting — mandatory)
├── {cluster-slug}/                        (Topic cluster directory)
│   ├── _index.md                          (Cluster landing — page_role: toc)
│   ├── how-to-{action-1}-{tech}.md        (Feature showcase)
│   ├── how-to-{action-2}-{tech}.md        (Feature showcase)
│   └── ...
└── {cluster-slug-2}/
    ├── _index.md
    └── ...
```

**Cluster formation rules** (binding):
1. Group `key_feature` claims by semantic similarity (shared `claim_group` or keyword overlap)
2. A cluster requires **minimum 2 pages** to justify a directory — single-page features remain flat
3. Each cluster gets a `_index.md` with `page_role: toc` listing its child pages
4. Child pages use `page_role: feature_showcase` with `how-to-{verb}-{object}` slug format
5. Cluster slugs are derived from the shared capability theme (e.g., `format-conversion`, `rendering`, `model-loading`)

**When to use clusters** (optional_page_policies source: `per_topic_cluster`):
- `launch_tier: rich` — always generate clusters when 3+ key_features share a theme
- `launch_tier: standard` — generate clusters only when 5+ key_features share a theme
- `launch_tier: minimal` — no clusters (flat KB only)

**Naming convention**:
- Cluster slug: `{capability-theme}` (e.g., `format-conversion`, `image-processing`)
- Page slug: `how-to-{verb}-{object}` (e.g., `how-to-convert-3d-models`, `how-to-render-scenes`)
- Page title: "How to {Action} with {Product}" (e.g., "How to Convert 3D Models with Aspose.3D")

### Launch Tier Adjustments (Updated TC-983)

Launch tier affects mandatory page requirements:

**minimal tier**:
- Reduces mandatory page count to absolute minimum (1 per section)
- Products: overview only
- Docs: getting-started only
- Reference: API overview only
- KB: 1-2 pages (FAQ or limitations)
- Blog: announcement only

**standard/rich tiers**:
- Use full mandatory page list from merged ruleset config (see "Configurable Page Requirements" above)
- Fill remaining slots with optional pages based on evidence quality and effective_quotas

**CI-absent tier reduction softening** (TC-983, binding):
- **Previous behavior**: CI-absent alone reduced standard tier to minimal
- **New behavior**: CI-absent ALONE no longer reduces to minimal. Only when BOTH CI-absent AND tests-absent are true does the tier reduce to minimal.
- Rationale: Many FOSS repos lack CI but have a meaningful test suite. Reducing to minimal for CI-absent alone collapses most FOSS repos to the bare minimum, producing too few pages.
- **Rule**: `if not ci_present and not tests_present: reduce tier by one level`
- **Rule**: `if not ci_present and tests_present: keep tier, record adjustment "CI absent but tests present, keeping tier"`
- This change is reflected in `specs/06_page_planning.md` "Tier reduction signals" section below.

## Acceptance
- page_plan.json validates schema
- All required sections have at least minimum pages
- Every page references claim_ids and snippet tags that exist

## Planning Failure Modes (binding)

### Insufficient Evidence for Required Section
If a required section (from `run_config.required_sections`) cannot meet minimum page count due to lack of evidence:
1. Open BLOCKER issue with:
   - `issue_id`: `plan_incomplete_{section}`
   - `error_code`: `IA_PLANNER_PLAN_INCOMPLETE`
   - `severity`: `blocker`
   - `message`: "Cannot plan {section}: insufficient evidence for minimum page count ({actual} < {minimum})"
   - `suggested_fix`: "Add evidence to ProductFacts or reduce minimum via launch_tier=minimal"
2. Emit telemetry event `PLAN_INCOMPLETE` with section and deficit details
3. Halt planning and return to orchestrator with FAILED state
4. Do NOT proceed to drafting

### Zero Pages Planned for Optional Section
If an optional section has zero pages due to lack of evidence:
1. Emit telemetry warning `SECTION_SKIPPED` with section and reason
2. Continue planning other sections
3. Record in `page_plan.skipped_sections[]` with rationale

### URL Path Collision Detected
If multiple pages resolve to the same `url_path` (per specs/33_public_url_mapping.md):
1. Open BLOCKER issue with:
   - `error_code`: `IA_PLANNER_URL_COLLISION`
   - `files`: list of colliding output_path values
   - `message`: "URL collision detected: {url_path} maps to multiple pages"
2. Emit telemetry event `URL_COLLISION_DETECTED`
3. Halt planning with FAILED state

## Universality: Launch Tiers and Product Types

### Launch tiers (binding)
PagePlanner MUST select a **launch_tier** (from RunConfig or inferred):
- `minimal`: safe “announce + quickstart + links” launch for sparse repos
- `standard`: default for normal repos (docs + examples available)
- `rich`: for repos with strong docs/examples and a clear API surface

The selected tier MUST be recorded in artifacts and telemetry.

### Tier-driven page inventory (rules)
- minimal:
  - products: overview page
  - docs: getting-started page (or a single guide)
  - reference: API overview (high-level surface, no exhaustive lists)
  - kb: 1–2 “how to” articles based on verified workflows
  - blog: announcement + one deep-dive post (optional if evidence is weak)
- standard:
  - products: overview + key features
  - docs: getting-started + 2–5 guides (workflows)
  - reference: API overview + key classes/modules pages
  - kb: 3–8 “how to” articles
  - blog: announcement + showcase post
- rich:
  - expand standard, but ONLY when grounded by claim_groups/snippets (no speculation)

### Product type adaptation (binding)
If RunConfig `product_type` is provided, PagePlanner MUST adjust headings and token usage:
- `cli`: emphasize install + commands + exit codes + examples of flags
- `sdk`/`library`: emphasize import/use patterns + API surface + supported formats
- `service`: emphasize endpoints + auth + SDK usage + limits

### Launch tier quality signals (universal, binding)

The PagePlanner MUST adjust launch_tier based on repository quality signals:

**Tier elevation signals** (allow higher tier):
- `repository_health.ci_present == true` with passing badge
- `repository_health.tests_present == true` with >10 test files
- `example_roots` contains validated, non-empty examples directory
- `doc_roots` contains structured documentation

**Tier reduction signals** (force lower tier, updated TC-983):
- `repository_health.ci_present == false` AND `repository_health.tests_present == false` → reduce by one level (TC-983: both must be absent; CI-absent alone no longer triggers reduction)
- `repository_health.ci_present == false` AND `repository_health.tests_present == true` → keep tier, record adjustment reason "CI absent but tests present, keeping tier" (TC-983)
- `phantom_paths` detected for claimed examples → reduce by one level
- `contradictions` array is non-empty and unresolved → force `minimal`
- `example_roots` is empty AND `snippet_catalog` has only generated snippets → force `minimal`

**Override rules**:
- Explicit `launch_tier` in RunConfig takes precedence over auto-adjustment
- Tier can never be elevated above what evidence supports (rich requires grounded workflows)

### Recording launch tier decision
The final `launch_tier` and adjustment reasoning MUST be recorded in:
- `page_plan.launch_tier`
- `page_plan.launch_tier_adjustments[]` (list of applied adjustments with reasons)

---

## Expected Page Counts (Reference)

The total pages produced per pilot is intentionally bounded. This section explains typical output so operators can verify correctness without assuming a bug.

**Why page counts are low relative to claims**:
- Claims are **distributed** across pages, not mapped 1:1. A single page may hold 3-50 claims depending on its `page_role` and `claim_quota`.
- Ruleset quotas cap sections: products ~6, docs ~10, reference ~6, kb ~10, blog ~3 (max ~35 total).
- Launch tier scaling reduces effective maximums: minimal 30%, standard 70%, rich 100%.
- The standard tier (default for most FOSS repos) yields roughly 60-70% of max quotas.

**Typical output per pilot** (standard tier):
- Products: 2 pages (overview + features)
- Docs: 5-9 pages (mandatory: index, getting-started, installation, overview, developer-guide + optional workflow pages)
- Reference: 2 pages (api-overview + index)
- KB: 3-4 pages (faq, troubleshooting, howto + optional showcases)
- Blog: 1 page (announcement)
- **Total: 13-18 pages** is normal for standard tier

**Claim-to-page ratio examples**:
- 42 claims across 18 pages = ~2.3 claims/page average (3D pilot, sparse evidence)
- 806 claims across 16 pages = ~50 claims/page average (Note pilot, rich evidence)

Both are correct: the planner selects claims per page by section and role, not by total count.

---

## Slug Sanitization Contract (Round 13, binding)

All dynamically generated slugs (from claims, workflows, features) MUST follow these rules. This contract addresses malformed slugs produced by raw text truncation (e.g., `claim_text[:40]`), which create unusable URLs and break Hugo builds.

### Derivation Rules (binding)

1. Slugs MUST NOT be derived by truncating raw claim text (e.g., `claim_text[:40]` is FORBIDDEN)
2. Slugs MUST be derived using one of these methods, in order of preference:
   - **Heuristic extraction**: Extract the core noun phrase or action verb from the claim text (e.g., "Convert 3D models between formats" → `format-conversion`)
   - **Workflow/feature name**: Use the workflow or feature `name` field directly if it is concise and already slug-like (e.g., "Model Loading" → `model-loading`)
   - **LLM summarization**: Use LLM to generate a 2-4 word slug from the claim text (fallback when heuristic extraction fails)
3. Maximum slug length: **40 characters** (excluding any prefix such as `how-to-`)
4. Slug format: lowercase, hyphen-separated, alphanumeric only, matching `^[a-z0-9][a-z0-9-]*[a-z0-9]$`
5. No spec-header-derived slugs: Claims that begin with a number followed by a section reference (e.g., "11 Section 3: In cases where...") MUST be filtered out by W2 before reaching W4

### Title Derivation Rules (binding)

1. Page titles MUST NOT be derived by truncating raw claim text (e.g., `claim_text[:50]` is FORBIDDEN)
2. Titles MUST be human-readable, descriptive, and suitable for SEO:
   - **For per_feature pages**: Use the feature name or a concise summary (e.g., "3D Model Format Conversion")
   - **For per_workflow pages**: Use the workflow `name` field (e.g., "Loading 3D Models")
   - **For per_key_feature KB pages**: Use "How to {action}" format (e.g., "How to Convert 3D Models")
3. Maximum title length: **70 characters** (SEO best practice)
4. Titles MUST NOT contain raw claim IDs, spec section numbers, or truncated text

### Slug Deduplication (binding)

W4 MUST ensure slug uniqueness across the entire page plan:

1. Maintain a `used_slugs: Dict[str, Set[str]]` mapping section → set of slugs
2. Before adding a page, check if `slug` already exists in `used_slugs[section]`
3. If collision detected, append a numeric suffix: `{slug}-2`, `{slug}-3`, etc.
4. Record deduplication events in telemetry

### Keyword Sanitization (binding)

1. Keywords MUST NOT contain raw template tokens (e.g., `__PLATFORM__`, `__LOCALE__`)
2. Keywords MUST NOT contain claim IDs, angle brackets, or raw claim text fragments
3. Keywords MUST be validated against pattern `^[a-zA-Z0-9][a-zA-Z0-9 _-]*$`
4. Invalid keywords MUST be stripped, not passed through to output

### Implementation Location

- **Slug generation**: `src/launch/workers/w4_ia_planner/worker.py` > `generate_optional_pages()` (4 sites: per_feature, per_workflow, per_key_feature, feature text)
- **Title generation**: Same function, all title assignment sites
- **Deduplication**: W4 `run()` method, applied after all pages are generated
- **Keyword sanitization**: W4 keyword generation sites + `content_sanitizer.py`

---

## Cross-Section Link Transformation (2026-02-03)

### Cross-Subdomain Navigation Requirements (Binding)

**Problem**: In a subdomain architecture (blog.aspose.org, docs.aspose.org, etc.), relative links that cross section boundaries will break because they resolve on the wrong subdomain.

Example of broken relative link:
```markdown
<!-- From blog.aspose.org page -->
See [Getting Started](../../docs/3d/python/getting-started/)
<!-- Browser resolves to blog.aspose.org/docs/3d/python/getting-started/ ❌ 404 -->
```

**Solution**: Cross-section links MUST be transformed to absolute URLs during content generation.

### Link Transformation Rules (Binding)

**Transform to absolute** (cross-section links):
- Blog → Docs: `[Guide](../../docs/3d/python/guide/)` → `[Guide](https://docs.aspose.org/3d/python/guide/)`
- Docs → Reference: `[API](../../reference/cells/python/api/)` → `[API](https://reference.aspose.org/cells/python/api/)`
- KB → Docs: `[Tutorial](../../docs/cells/python/tutorial/)` → `[Tutorial](https://docs.aspose.org/cells/python/tutorial/)`
- Products → Docs: Similar transformation

**Do NOT transform** (preserve as-is):
- Same-section links: `[Next Page](./next-page/)` (keep relative)
- Internal anchors: `[Install](#installation)` (keep as-is)
- External links: `[Python](https://python.org)` (already absolute)

### Implementation Location (Binding)

Cross-section link transformation MUST occur during draft generation in W5 SectionWriter:

1. **Worker**: W5 SectionWriter
2. **Module**: `src/launch/workers/w5_section_writer/link_transformer.py`
3. **Function**: `transform_cross_section_links(markdown_content, current_section, page_metadata)`
4. **Integration point**: After LLM generates markdown content, before writing to drafts/

**Why W5 (not W6)**: Transforming links at draft generation ensures:
- Content previews show correct links
- Patches already contain absolute URLs
- No need to parse and modify patches later

### Link Detection Algorithm

The transformer uses regex pattern matching to detect section-specific URL patterns:

```python
section_patterns = {
    "docs": r"(?:\.\.\/)*docs\/",
    "reference": r"(?:\.\.\/)*reference\/",
    "products": r"(?:\.\.\/)*products\/",
    "kb": r"(?:\.\.\/)*kb\/",
    "blog": r"(?:\.\.\/)*blog\/",
}
```

For each markdown link `[text](url)`:
1. Check if URL is already absolute (http://, https://) → skip
2. Check if URL is internal anchor (#...) → skip
3. Detect target section from URL pattern
4. If target section == current section → skip (same-section link)
5. Parse URL components (family, platform, subsections, slug)
6. Build absolute URL using `build_absolute_public_url()` from TC-938
7. Replace link with absolute URL

**Graceful degradation**: If transformation fails (parsing error, invalid URL), keep original link and log warning. Never break existing links.

**Implementation reference**: See `src/launch/workers/w5_section_writer/link_transformer.py` for complete implementation.

**Related fixes**: HEAL-BUG3 (2026-02-03) integrated cross-section link transformation into W5 pipeline, completing TC-938.

---

## Semantic Claim Selection (Round 12, binding)

W4 MUST use the `ClaimKindRegistry.select_claims_for_page()` method (or `select_claims_semantic()` when audience matching is enabled) instead of positional array slicing.

### Selection Algorithm

1. For each page in the plan, determine `page_role` and `section`
2. Look up `_PAGE_ROLE_CLAIM_PRIORITIES` for the role's preferred claim groups
3. Select claims from each group in priority order, up to `_PAGE_ROLE_MAX_CLAIMS`
4. Apply `exclude_ids` filter: claims already assigned to previous pages are deprioritized
5. Enforce `min_claims` guarantee: if selection returns fewer than min_claims (default: 1), relax exclude_ids constraint

### Cross-Page Deduplication

W4 MUST maintain a `used_claim_ids: Set[str]` across all pages during planning. For each page:
- Prefer claims NOT in used_claim_ids
- Only reuse claims when no unused alternatives exist for a required group
- After assignment, add page's claim_ids to used_claim_ids

### Missing Page Role Mappings

The following page roles MUST have claim priority mappings:
- `landing`: key_features, use_cases, compatibility_notes
- `api_reference`: key_features, compatibility_notes, limitations
- `blog_announcement`: key_features, use_cases, tutorials
- `performance_guide`: performance, best_practices, limitations

---

## Incremental Page Preservation (Round 12, binding)

When `run_config.incremental.enabled` is true, W4 MUST compute page preservation metadata by comparing the new plan against the previous run's `page_plan.json`.

### Page Identity

Pages are identified by the tuple `(section, slug)`. This identity is stable across runs regardless of changes to claim_ids, headings, or content.

### Preservation Algorithm

1. Load previous `page_plan.json` from incremental config
2. For each page in new plan: find matching (section, slug) in previous plan
3. Compute claim overlap score: `Jaccard(old_claim_ids, new_claim_ids)` = |intersection| / |union|
4. Assign page_status:
   - `overlap ≥ threshold` (default 0.75): `page_status: "preserved"`
   - `0 < overlap < threshold`: `page_status: "updated"`
   - `overlap == 0` (no match): `page_status: "new"`
5. For previous pages not matched in new plan: `page_status: "deleted"`

### Preservation Metadata

Each page MAY include `preservation_metadata`:
```json
{
  "previous_page_id": "page from previous run",
  "claim_overlap_score": 0.85,
  "should_preserve": true,
  "preservation_reason": "high_claim_overlap"
}
```

### Downstream Effects

- `preserved` pages: W5 skips generation, copies draft from previous run
- `updated` pages: W5 runs multi-pass with previous draft as refine context
- `new` pages: W5 runs full multi-pass (or deterministic fallback)
- `deleted` pages: W6 generates DELETE patch, W9 includes in PR delta summary

---

## Cross-Page Linking (Round 12, binding)

W4 MUST compute claim-overlap cross-links between pages for the `related_pages` field.

### Algorithm

1. Build mapping: `claim_id → Set[page_slug]`
2. For each page A, compute overlap with every other page B: `|A_claims ∩ B_claims|`
3. Top 3 pages by overlap score → `related_pages` for page A

### Related Pages Field

```json
"related_pages": [
  {"slug": "getting-started", "url_path": "/cells/python/getting-started/", "overlap_score": 0.4},
  {"slug": "developer-guide", "url_path": "/cells/python/developer-guide/", "overlap_score": 0.3}
]
```

### W8 See Also Injection

W8 LinkerPatcher MUST read `related_pages` and inject a "## See Also" section at the end of each content page. Injection is idempotent — do not duplicate if already present.

### Link Validation

W6 MUST validate all internal links `[text](url)` in generated content resolve to existing or planned pages. Broken links are reported as WARNING issues.

---

## SEO Slug Strategy

### Two-Phase Slug Generation

**Phase 1 (W4)**: Safe structural slugs derived from page titles/topic IDs:
- `slugify(title)` using lowercase ASCII, hyphens, no trailing hyphens
- Deduplication via numeric suffix (`-2`, `-3`) when slugs collide within a section
- Deterministic: same inputs always produce same slugs (PYTHONHASHSEED=0)

**Phase 2 (W6)**: Optional SEO refinement gated on `run_config.seo_enabled`:
- Applies to KB and blog sections only (docs and reference retain structural slugs)
- Keyword injection into slugs via `keyword_utils.py` (target 1.5% density in page content)
- Cache contract: PyTrends 1h TTL, LLM provider 24h TTL
- Refinement MUST NOT change page identity — `page_id` remains tied to original slug

### Slug Uniqueness

Slugs MUST be unique within their section scope (`{subdomain}/{family}/{platform}/{section}/`). Cross-section slug collisions are allowed (e.g., both `docs/getting-started/` and `kb/getting-started/` are valid).

### Mandatory Minimum Enforcement

W4 MUST enforce `page_expansion.{section}.min_pages` from run_config:
- If a required section produces fewer pages than `min_pages`, W4 MUST raise `ConfigurationError`
- `required_sections ∩ skip_sections ≠ ∅` MUST be rejected at config validation time
- Fallback topic injection ensures at least `min_pages` pages per required section

---

## Policy Layer (Optional Content Evidence Gating)

The Policy Layer is an optional mechanism that gates optional page candidates based on their evidence quality score. It activates **only** when `run_config["policy"]` key is present. When the key is absent, behavior is completely unchanged — no gating, no artifact written.

### Activation

```yaml
# run_config.yaml — add to enable policy gating
policy:
  optional_content_min_score: 0.5
  dry_run_optional: false
```

If `run_config["policy"]` is missing or `null`, `load_policy_config()` returns `None` and the engine never runs.

### Configuration Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `optional_content_min_score` | float | `0.5` | Minimum normalized quality score for optional pages to be included |
| `dry_run_optional` | bool | `false` | If `true`, accepted pages are marked `dry_run: true` in page_plan instead of being removed |

### Scoring Formula

```
normalized_score = min(quality_score / 30.0, 1.0)
```

- `quality_score` is the raw integer score attached to each optional page candidate (0–30+ range)
- Normalized result is clamped to `[0.0, 1.0]`
- Acceptance condition: `normalized_score >= optional_content_min_score`

### Dry-Run Mode

When `dry_run_optional: true`:
- Pages that pass the score threshold are added to `page_plan.json` with `dry_run: true`
- W5 SectionWriter MUST skip any page where `page.get("dry_run")` is truthy
- This allows inspection of which pages _would_ be generated without actually writing content

### Mandatory Pages are Never Evaluated

The policy engine MUST NOT evaluate mandatory pages. Only optional page candidates (those produced by optional section enumeration) are passed to `ContentPolicy.evaluate()`. Mandatory pages bypass the policy entirely.

### Artifact

When the policy engine runs, it writes `artifacts/content_policy.json`:

```json
{
  "schema_version": "1.0",
  "policy": {
    "optional_content_min_score": 0.5,
    "dry_run_optional": false
  },
  "summary": {
    "total_candidates": 12,
    "accepted": 9,
    "rejected": 3
  },
  "decisions": [
    {
      "slug": "advanced-usage",
      "section": "docs",
      "normalized_score": 0.8333,
      "accepted": true,
      "rejection_reason": null,
      "is_dry_run": false
    }
  ]
}
```

Decisions are sorted by `(section, slug)` for deterministic output.

### Implementation

- Module: `src/launch/workers/w4_ia_planner/content_policy.py`
- Entry point: `load_policy_config(run_config) -> Optional[ContentPolicy]`
- W5 guard: skip pages with `page.get("dry_run") == True`

---

## Evidence-Based Policy Engine (v2)

*Added: TC-2447. Coexists with the v1 per-candidate policy above.*

The Evidence-Based Policy Engine computes **per-section** `optional_max_pages` caps from multiple repo artifact signals. Unlike v1 (which gates individual candidates by score), v2 operates at the **section level** — limiting the total number of optional pages a section can receive based on how rich the underlying evidence is.

### Activation

```yaml
# run_config.yaml — add to enable v2 evidence-based policy
use_content_policy: true   # default: false
```

When `use_content_policy` is absent or `false`:
- Zero behavior change — no artifact written, no caps applied
- V1 `policy` key (per-candidate gating) continues to work independently
- Pilots MUST NOT have this key set

### Evidence Signals

All signals are **deterministic** (artifact-based, no LLM):

| Signal | Source Artifact | Weight |
|--------|-----------------|--------|
| Claim volume | `product_facts.claims[]` count | 0.25 |
| Claim diversity | distinct `claim_kind` values | 0.20 |
| Citation density | avg `citations[]` per claim | 0.20 |
| High-confidence claims | `confidence == "high"` count | 0.10 |
| Snippet coverage | `snippet_catalog.snippets[]` count | 0.15 |
| Doc chunk depth | `source_chunks.count` | 0.10 |
| Claim group richness | `len(product_facts.claim_groups)` | 0.05 |

### Global Evidence Score Formula

Each component contributes a fractional score. The sum of all component maxima is 1.0.

| Component | Max | Thresholds |
|-----------|-----|-----------|
| Claim volume | 0.25 | 50+→0.25, 20+→0.20, 10+→0.15, 5+→0.10, 1+→0.05 |
| Claim diversity | 0.20 | 5+ kinds→0.20, 3+→0.15, 2→0.10, 1→0.05 |
| Citation density | 0.20 | avg≥3→0.20, ≥2→0.15, ≥1→0.10, ≥0.5→0.05 |
| High-confidence | 0.10 | 10+→0.10, 5+→0.07, 2+→0.04, 1+→0.02 |
| Snippet coverage | 0.15 | 20+→0.15, 10+→0.10, 5+→0.07, 1+→0.04 |
| Doc chunk depth | 0.10 | 50+→0.10, 20+→0.07, 5+→0.04, 1+→0.02 |
| Claim group richness | 0.05 | min(0.05, groups × 0.005) |

**Repo tier multiplier** (from `repo_profile.quality_tier` if present):

| Tier | Multiplier |
|------|-----------|
| `rich` | 1.00 |
| `standard` (default when absent) | 0.90 |
| `minimal` | 0.75 |

### Section-Level Factor

Derived from `topic_manifest.per_section_counts[section]`:

| Topics discovered | Section factor |
|-------------------|---------------|
| 3 or more | 1.00 |
| 1–2 | 0.85 |
| 0 | 0.70 |

`section_score = clamp(global_score × tier_multiplier × section_factor, 0.0, 1.0)`

### Optional Max Pages from Section Score

| `section_score` | `optional_max_pages` |
|-----------------|----------------------|
| ≥ 0.80 | `section_cap` (unrestricted) |
| ≥ 0.60 | min(4, cap) |
| ≥ 0.40 | min(3, cap) |
| ≥ 0.25 | min(2, cap) |
| ≥ 0.15 | min(1, cap) |
| < 0.15 | 0 |

### Invariants

1. Mandatory pages are **never** reduced by the evidence policy.
2. `optional_max_pages` only restricts `effective_max` in `generate_optional_pages()` — it never adds pages.
3. `EvidenceBasedPolicy.build()` is a **pure function** — no I/O, no LLM calls, fully deterministic.
4. The old v1 `policy` (per-candidate, TC-2434) is completely unaffected.

### Artifact

When the engine runs, it writes `artifacts/evidence_content_policy.json`:

```json
{
  "schema_version": "2.0",
  "engine": "evidence_based_v2",
  "global_evidence_score": 0.72,
  "repo_tier": "standard",
  "tier_multiplier": 0.9,
  "sections": [
    {
      "section": "docs",
      "mandatory_min_pages": 1,
      "optional_max_pages": 4,
      "evidence_score": 0.648,
      "allowed_optional_page_roles": ["tutorial", "how-to", "blog_post"],
      "reasons": ["global_score=0.72 × tier=0.90 × section_factor=1.00 = 0.648", "score≥0.60 → max 4"]
    }
  ]
}
```

### Implementation

- Module: `src/launch/content/policy/content_policy.py`
- Entry point: `EvidenceBasedPolicy.build(sections, product_facts, snippet_catalog, ...)`
- W4 integration: `generate_optional_pages()` receives `evidence_policy=` parameter
- Feature flag: `run_config["use_content_policy"]` (default: `False`)

---

## Blog Workflow-Derived Slug (Agent 44, Spec v1.1)

The mandatory `feature_blog` page derives its slug from the most marketable evidenced workflow via `score_blog_workflow(product_facts, snippet_catalog)`.

### Scoring Algorithm

| Signal | Points | Condition |
|--------|--------|-----------|
| Conversion + snippet | +5 | Workflow tag/title contains "convert" AND has snippet evidence |
| Snippet evidence | +3 | Workflow has snippet overlap (tag or claim_id) |
| High-intent verb | +2 | Workflow contains: convert, merge, create, protect, render, export, import, transform, generate, extract |

**Tiebreaker**: alphabetical `workflow_tag` (ascending).
**Fallback**: slug `"feature-highlight"`, score 0 when no workflows or all score 0.

### Output

- Winning workflow's title → `_derive_semantic_slug()` → blog page slug
- `content_strategy.selected_workflow` stores `{workflow_tag, score}` for W5

---

## Format Evidence Injection (Agent 43, Spec v1.1)

W4 detects conversion how-to pages during mandatory page injection (slug or title contains "convert") and injects format evidence from `product_facts` into `content_strategy`:

- `is_conversion_howto: true`
- `supported_formats: [{format, direction}]` — from `product_facts.supported_formats`
- `conversion_pairs: [{source, target}]` — from `product_facts.claim_groups.conversion_pairs`

W5 uses this evidence in the howto prompt (`{format_evidence}` placeholder) and in the deterministic fallback to list only evidenced formats. Pages with no format evidence emit: `"No format conversion evidence was found in this repository."`

---

## Reference Object Page Enumeration (Agent 45, Spec v1.1)

The `per_api_object` source handler in W4 generates reference pages from `product_facts.api_surface_summary.classes`.

### Richness-Based Quality Boost

```
quality_score = (matching_claims * 2) + (matching_snippets * 3)
quality_score += min(methods_count // 3, 5)   # +1 per 3 methods, max +5
quality_score += min(properties_count, 3)      # +1 per property, max +3
```

### Priority Configuration

In `ruleset.v1_1.yaml`, `per_api_object` has priority 1 (over `per_api_symbol` at priority 2), ensuring object pages fill available slots first.

### Mandatory Role Override

When the ruleset specifies `page_role: "toc"` for a mandatory page (e.g., reference `_index`), W4 overrides the template-enumerated page's role. This enables `child_pages` population, which the W5 toc generator uses to list and link to object pages.
