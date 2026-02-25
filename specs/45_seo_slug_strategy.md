---
title: "SEO Slug Strategy"
spec_id: "45"
status: Binding
created: "2026-02-22"
updated: "2026-02-22"
owner: TC-2420
---

# Spec 45: Two-Phase SEO Slug Strategy

## Purpose

Define the slug generation pipeline that balances deterministic reproducibility (W4)
with SEO optimization (W6). Slugs are the final path component in content URLs
(e.g., `getting-started` in `/cells/python/getting-started/`).

## Phase 1: Structural Slug Generation (W4 IAPlanner)

W4 generates safe, deterministic slugs from page metadata:

1. **Input**: page title or topic ID
2. **Transform**: `slugify(title)` — lowercase ASCII, replace spaces/punctuation with hyphens, collapse consecutive hyphens, strip leading/trailing hyphens
3. **Deduplication**: within each section scope, append `-2`, `-3`, etc. for collisions
4. **Determinism**: output is stable under `PYTHONHASHSEED=0`

### URL Structure

```
/{family}/{platform}/{section_path}/{slug}/
```

Example: `/3d/python/getting-started/installation/`

### Scope Rules

- Slugs MUST be unique within `{subdomain}/{family}/{platform}/{section}/`
- Cross-section collisions are allowed (e.g., `docs/getting-started/` and `kb/getting-started/`)
- The `_index` slug normalizes to `index` in all downstream processing

## Slug Ownership Contract (Agent 47)

**W4 is the sole producer of `slug`, `output_path`, and `url_path`.** W6 is metadata-only
by default and MUST NOT rewrite these fields unless `slug_rewrite_enabled: true` is set
in run_config.

```yaml
# run_config.yaml — opt in to W6 slug rewriting (experimental)
slug_rewrite_enabled: true   # default: false
```

This contract prevents orphaned draft files that arise when page_plan slugs diverge from
the actual draft file paths.

## Phase 2: SEO Refinement (W6 SEOOptimizer)

W6 optionally refines slugs for search engine visibility (requires `slug_rewrite_enabled: true`):

### Eligibility

| Section | SEO Slugs | Reason |
|---------|-----------|--------|
| KB | Yes | Discovery-oriented content benefits from keyword-rich URLs |
| Blog | Yes | Organic traffic target |
| Docs | No | Structural navigation; users expect predictable paths |
| Reference | No | API paths mirror code structure |
| Products | No | Landing pages with fixed canonical URLs |

### Refinement Algorithm

1. Extract primary keyword from page content via `keyword_utils.py`
2. Generate candidate slug via LLM (constrained to ≤60 chars, ASCII, hyphenated)
3. Validate uniqueness within section scope
4. Apply only if candidate improves keyword relevance score by ≥20%

### Caching

| Provider | TTL | Key Format |
|----------|-----|------------|
| PyTrends (keyword volume) | 1 hour | `pytrends:{keyword}:{region}` |
| LLM (slug generation) | 24 hours | `seo_slug:{page_id}:{model}` |

### Identity Preservation

SEO refinement MUST NOT change page identity:
- `page_id` remains tied to the original W4-generated slug
- Internal cross-references use `page_id`, not the display slug
- Redirects are NOT generated for slug changes (content is new, not migrated)

## Content Sanitization Pipeline

Post-generation content passes through a 5-phase sanitization pipeline
(defined in `content_sanitizer.py`) that addresses LLM formatting artifacts:

### Phase 1: Structural
- `fix_heading_missing_space`: `##Word` → `## Word`
- `fix_inline_heading`: `text.## Heading` → split into separate lines
- `fix_sentence_heading`: marketing sentences → clean verb-phrase titles
- `fix_missing_space_after_period`: `Python.The` → `Python. The`

### Phase 2: Fence Normalization
- Code fence detection, closing, and deduplication
- Language tag validation

### Phase 3: Content-Level
- Product name prefix stripping from headings
- Collapsed markdown table repair
- Emoji removal

### Phase 4: Pattern Stripping
- LLM scaffolding removal (`<think>` tags, instruction echoing)
- Pipeline comment removal
- Boilerplate sentence detection

### Phase 5: Quality Enforcement
- Minimum content density checks
- Claim marker validation

All sanitizers are idempotent and fence-aware (skip content inside code blocks).
W7 and W8 re-apply heading sanitizers after their own content modifications.

## Validation

- **Gate 4**: Verifies frontmatter SEO metadata (title, description, keywords)
- **Gate 17**: LLM-based formatting quality check (FQ-1 through FQ-7)
- **Gate 16**: Content hygiene (unmatched fences, orphan markers)

## Blog Slug Derivation (Spec v1.1, Agent 44)

Feature-highlight blog posts derive their slug from the highest-scoring workflow
rather than using a generic title-based slug:

1. **`score_blog_workflow(product_facts, snippet_catalog, product_slug, family_capabilities, platform)`** ranks workflows by:

   | Condition | Points |
   |-----------|--------|
   | Conversion workflow AND has evidenced snippets | +5 |
   | Workflow has ≥1 code snippet (tag or claim overlap) | +3 |
   | Workflow title/tag contains a high-intent verb (`convert`, `merge`, `create`, `render`, etc.) | +2 |

2. Winning workflow's title → `_derive_blog_evidence_slug()` → enriched slug (TC-2607)
3. `_derive_blog_evidence_slug()` enriches the base semantic slug with the product family keyword when not already present (e.g., `"convert-formats"` → `"convert-formats-3d-models"`)
4. Length guard: enriched slug capped at 40 chars; base slug returned if enrichment would overflow
5. Tiebreaker: alphabetical `workflow_tag` for determinism
6. Fallback: `"feature-highlight"` when no workflows exist or all score 0
7. Backward compat: when `product_slug=""` (legacy callers), falls back to `_derive_semantic_slug()`
8. `selected_workflow` metadata stored in `content_strategy` for W5 prompt injection

**Implementation**: `src/launch/workers/w4_ia_planner/worker.py::score_blog_workflow()`, `_derive_blog_evidence_slug()`

## Evidence-Aware How-To Slug Derivation (TC-2481)

KB how-to pages use an evidence-aware slug algorithm that incorporates the product family and detected formats/capabilities to produce SEO-optimized, product-specific slugs instead of generic ones.

### Algorithm

`_derive_evidence_aware_slug(topic_category, product_facts, shared_facts)` in W4 IAPlanner:

1. **Identify topic category** via `_infer_topic_category(page_spec)`: maps from ruleset mandatory how-to titles to one of: `load_file`, `save_file`, `convert_formats`, `troubleshoot`, `optimize_performance`
2. **Extract family keyword** via `_extract_family_keyword(product_facts)`: derives the product-specific domain noun (e.g., "3d-models", "spreadsheets", "notes")
3. **Extract format scope** via `_infer_format_scope(product_facts)`: detects primary format families from `supported_formats` (e.g., "fbx-obj", "xlsx-csv")
4. **Select slug template** from `_HOWTO_SLUG_TEMPLATES` dict keyed by `topic_category`
5. **Render slug** by filling template with `{family_keyword}` and `{platform}` (defaults to "python")

### Slug Templates (`_HOWTO_SLUG_TEMPLATES`)

All templates use `{platform}` (TC-2604). The `convert` template uses format-to-format
when evidence is available, falling back to `{family_keyword}` when no format evidence exists.

| Topic Category | Template | Example (3D, python) |
|---------------|----------|---------------------|
| `load_file` | `how-to-load-{family_keyword}-{platform}` | `how-to-load-3d-models-python` |
| `save_file` | `how-to-save-{family_keyword}-{platform}` | `how-to-save-3d-models-python` |
| `convert_formats` | `how-to-convert-{source_format}-to-{target_format}-{platform}` | `how-to-convert-fbx-to-obj-python` |
| `convert_formats` (no evidence) | `how-to-convert-{family_keyword}-{platform}` | `how-to-convert-3d-models-python` |
| `troubleshoot` | `how-to-fix-{family_keyword}-errors-{platform}` | `how-to-fix-3d-models-errors-python` |
| `optimize_performance` | `how-to-optimize-{family_keyword}-{platform}` | `how-to-optimize-3d-models-python` |

### Family Keyword Map (`FAMILY_KEYWORD_MAP`)

Canonical source: `src/launch/workers/_shared/slug_constants.py` (TC-2601).

| Product Family | Family Keyword |
|---------------|---------------|
| `3d` | `3d-models` |
| `cells` | `spreadsheets` |
| `note` | `notebooks` |
| `words` | `documents` |
| `pdf` | `pdf-files` |
| `slides` | `presentations` |
| `imaging` | `images` |

Families not in the map fall back to `"files"`. When `family_capabilities.json` provides
a `keyword` field, it overrides the map (TC-2514).

### Expected Slug Examples

| Pilot | Topic | Generated Slug |
|-------|-------|---------------|
| Aspose.3D | Load file | `how-to-load-3d-models-python` |
| Aspose.3D | Convert formats | `how-to-convert-fbx-to-obj-python` |
| Aspose.Cells | Load file | `how-to-load-spreadsheets-python` |
| Aspose.Cells | Save file | `how-to-save-spreadsheets-python` |
| Aspose.Note | Load file | `how-to-load-notebooks-python` |
| Aspose.Note | Troubleshoot | `how-to-fix-notebooks-errors-python` |

### Implementation

- Constants: `src/launch/workers/_shared/slug_constants.py` (TC-2601)
- Entry: `src/launch/workers/w4_ia_planner/worker.py::_derive_evidence_aware_slug()`
- Helpers: `_infer_topic_category()`, `extract_family_keyword()`, `_infer_format_scope()`
- Tests: `tests/unit/workers/test_evidence_aware_slugs.py`, `tests/unit/workers/test_slug_constants.py`

### Determinism

Evidence-aware slugs are fully deterministic: same product_facts input always produces same slug output. No LLM, no randomness, no environment dependency.

## References

- `specs/06_page_planning.md` — Page expansion and mandatory minimum enforcement
- `specs/21_worker_contracts.md` — W2/W4/W6 I/O contracts
- `specs/44_pipeline_parallelization.md` — Parallel execution within W5/W7
- `src/launch/workers/_shared/content_sanitizer.py` — Sanitizer implementation
- `src/launch/workers/w6_seo_optimizer/keyword_utils.py` — Keyword extraction
