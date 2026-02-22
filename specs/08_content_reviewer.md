# W7 Content Reviewer

**Status**: Binding Specification
**Updated**: 2026-02-20
**Owner**: W7_AGENT
**Related Specs**: [07_section_templates.md](07_section_templates.md), [09_validation_gates.md](09_validation_gates.md), [21_worker_contracts.md](21_worker_contracts.md)

---

## Purpose

This specification defines W7 ContentReviewer, the quality gate between W5 (SectionWriter) and W8
(LinkerPatcher) that reviews generated markdown content across three dimensions and applies automated
fixes or delegates to specialist LLM agents for complex issues.

## Pipeline Position

```
W5 SectionWriter → W7 ContentReviewer → W8 LinkerPatcher
```

W7 is enabled when `review_enabled: true` in run_config. When disabled, the pipeline passes
through with no impact on existing workers.

## Review Dimensions

W7 evaluates content across three dimensions, each with 12 checks:

### Dimension 1: Content Quality

Checks readability, structure, and completeness of generated markdown:
- Heading descriptiveness, heading density
- Content length and paragraph structure
- Bullet length, keyword density
- SEO title/description length
- Grammar and style

### Dimension 2: Technical Accuracy

Checks correctness of code, API references, and claims:
- Code syntax validity and fence balance
- Frontmatter required fields
- Claim validity and evidence linkage
- API hallucination detection
- Technical accuracy of stated facts

### Dimension 3: Usability

Checks navigation, accessibility, and user journey:
- Example clarity and completeness
- CTA presence
- Navigation structure

## Scoring

Each dimension receives a score from 1–5. Routing logic:
- **PASS** (≥4): Content ready for W8
- **NEEDS_CHANGES** (=3): LLM regen delegated to specialist agents
- **REJECT** (≤2): Severe issues requiring full redraft

Scores use per-page density thresholds to avoid false positives on large runs.

### Quality Gate (TC-2396)

W7 uses severity-weighted scoring: critical (1.0), high (0.75), medium (0.5), low (0.25).
Three outcomes: PASS (0 critical failures, ≤5 total warnings), REVIEW (>5 warnings, human flag),
FAIL (any critical failure OR >10 warnings). REVIEW routes to human queue.

Check severity registry:

| Check | Severity | Weight |
|---|---|---|
| code_syntax | critical | 1.0 |
| frontmatter_required | critical | 1.0 |
| claim_validity | critical | 1.0 |
| fence_balance | critical | 1.0 |
| seo_title_length | high | 0.75 |
| seo_description_length | high | 0.75 |
| api_hallucination | high | 0.75 |
| technical_accuracy | high | 0.75 |
| content_length | medium | 0.5 |
| keyword_density | medium | 0.5 |
| heading_descriptiveness | medium | 0.5 |
| example_clarity | medium | 0.5 |
| grammar_style | low | 0.25 |
| bullet_length | low | 0.25 |

The quality gate outcome is **additive** — it logs the result and sets `human_review_required=True`
on REVIEW, but does not replace the existing `route_review_result()` routing for backward
compatibility. The existing PASS/NEEDS_CHANGES/REJECT routing continues to drive pipeline decisions.

## Auto-Fixes

W7 applies nine deterministic markdown auto-fixes before scoring:
1. Heading descriptiveness — expand vague headings
2. Example clarity — add context to bare code blocks
3. Snippet attribution — add source attribution
4. Terminology consistency — normalize product terms
5. Placeholder content — replace stub text
6. Error message format — normalize error messages
7. Frontmatter fields — add missing required fields
8. Post-LLM sanitization — re-run content sanitizers after LLM regen
9. Code fence sanitization — normalize fence syntax

## LLM Regen

When NEEDS_CHANGES or REJECT, three specialist LLM agents are spawned:
- `content_enhancer` — improves readability and structure
- `technical_fixer` — corrects technical inaccuracies
- `usability_improver` — improves navigation and CTAs

After LLM modification, all checks re-run and a final score is computed.

## Artifacts

- Input: `artifacts/product_facts.json`, `artifacts/snippet_catalog.json`,
  `artifacts/page_plan.json`, `artifacts/evidence_map.json`, `drafts/**/*.md`
- Output: `artifacts/review_report.json`, `artifacts/iterations.json`

## Configuration

```yaml
review_enabled: false       # Enable W7 (default: false)
review_llm_verify: true     # LLM score verification (default: true)
redraft_enabled: false      # W7→W5 selective re-draft (default: false)
max_redraft_attempts: 1     # Max re-draft iterations
max_parallel_workers_w7: 4  # TC-2403: Parallel check dimensions + post-sanitization (default: 4)
```

## Performance

**TC-2403: Parallel check execution** reduces W7 wall-clock time by ~2–4x:

1. **Parallel dimension execution**: All 4 check dimensions (Content Quality, Technical Accuracy,
   Usability, Semantic Accuracy) are submitted to a `ThreadPoolExecutor(max_workers=max_parallel_workers_w7)`.
   Each dimension reads artifacts read-only and produces an independent issue list — no shared
   mutable state, no inter-dimension ordering dependencies.

2. **Semantic accuracy caching**: Semantic accuracy (LLM-based API hallucination, licensing, relevance)
   is the slowest dimension. After deterministic auto-fix passes (heading expansion, term normalization,
   frontmatter repair), the semantic issue list is **reused** rather than recomputed, since deterministic
   fixes cannot affect API hallucination or content relevance results. Semantic accuracy is only
   recomputed after LLM regen (which may introduce new hallucinations).

3. **Parallel post-sanitization**: The post-sanitization loop (22 sanitizers per draft file) is
   parallelized per file. Each file is processed independently by `_sanitize_draft_file()` in a
   `ThreadPoolExecutor(max_workers=max_parallel_workers_w7)`.

Config key `max_parallel_workers_w7` (default: 4, range: 1–8) controls all three parallelism levels.
Setting to 1 enables full sequential mode (identical to pre-TC-2403 behavior).

## Schema Reference

See `specs/schemas/review_report.schema.json` for the full review_report artifact schema.
