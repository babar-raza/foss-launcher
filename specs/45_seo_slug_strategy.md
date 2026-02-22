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

## Phase 2: SEO Refinement (W6 SEOOptimizer)

W6 optionally refines slugs for search engine visibility:

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

## References

- `specs/06_page_planning.md` — Page expansion and mandatory minimum enforcement
- `specs/21_worker_contracts.md` — W2/W4/W6 I/O contracts
- `specs/44_pipeline_parallelization.md` — Parallel execution within W5/W7
- `src/launch/workers/_shared/content_sanitizer.py` — Sanitizer implementation
- `src/launch/workers/w6_seo_optimizer/keyword_utils.py` — Keyword extraction
