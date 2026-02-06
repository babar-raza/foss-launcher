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

- **troubleshooting**: KB article for problem-solution (kb/troubleshooting.md, kb/faq.md)
  - Purpose: Diagnose and resolve specific problems
  - Typical sections: kb
  - Content focus: Symptoms, causes, resolutions

- **api_reference**: API documentation (reference section)
  - Purpose: Technical reference for classes, methods, modules
  - Typical sections: reference
  - Content focus: API signatures, parameters, return values

**Binding**: W4 IAPlanner MUST assign page_role to all pages. W5 SectionWriter MUST use page_role to select appropriate templates. W7 Validator MUST validate page_role-specific constraints (Gate 14).

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
  - Binding: W4 MUST set to "all" for comprehensive_guide pages, W7 MUST validate all workflows present

**Binding**: W4 IAPlanner MUST populate content_strategy for all pages. W5 SectionWriter MUST respect forbidden_topics and claim_quota. W7 Validator MUST enforce via Gate 14.

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
