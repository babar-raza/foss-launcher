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

### Optional Page Selection Algorithm (Deterministic)

When evidence supports more pages than `max_pages`, the planner MUST select optional pages using this deterministic algorithm:

**Step 1: Add all mandatory pages**
Include all mandatory pages for the section (as listed above).

**Step 2: Calculate quality score for each optional page candidate**
```
quality_score = (claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)
```

**Step 3: Rank optional candidates**
Sort candidates by:
1. Priority tier (core navigation > workflow coverage > supplemental)
2. Quality score (descending)
3. Slug (ascending, for stable tie-breaking)

**Step 4: Select top N optional pages**
```
N = max_pages - mandatory_page_count
```
Select the top N candidates from the sorted list.

**Step 5: Record rejected candidates**
Emit telemetry event `PAGES_REJECTED` with:
- Section name
- Rejected page slugs
- Rejection reason (e.g., "exceeded max_pages limit")

**Determinism requirement**: Two runs with identical ProductFacts and RunConfig MUST produce identical page_plan.json (same pages in same order).

### Launch Tier Adjustments

Launch tier affects mandatory page requirements:

**minimal tier**:
- Reduces mandatory page count to absolute minimum (1 per section)
- Products: overview only
- Docs: getting-started only
- Reference: API overview only
- KB: 1-2 pages (FAQ or limitations)
- Blog: announcement only

**standard/rich tiers**:
- Use full mandatory page list as specified above
- Fill remaining slots with optional pages based on evidence quality

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

**Tier reduction signals** (force lower tier):
- `repository_health.ci_present == false` → reduce by one level
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
