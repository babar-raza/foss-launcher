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
Minimum pages per section (configurable):
- products: 1 landing page
- docs: 2 to 5 how-to guides (based on workflows)
- reference: 1 landing + 1 to 3 module pages (based on API summary)
- kb: 3 articles (FAQ, troubleshooting, limitations/perf)
- blog: 1 announcement

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
