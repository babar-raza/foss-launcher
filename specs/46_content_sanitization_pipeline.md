# Content Sanitization Pipeline

**Status**: Binding
**Version**: v1.0
**Date**: 2026-02-23
**Implementation**: `src/launch/workers/_shared/content_sanitizer.py`
**Zone guard**: `src/launch/workers/_shared/markdown_zones.py`

---

## Overview

The content sanitization pipeline is a deterministic post-processing pipeline for
generated markdown content. It runs after LLM generation to enforce structural
correctness, remove scaffolding artifacts, and normalize formatting — without making
any semantic changes to content.

**Key invariants**:
- No I/O, no LLM calls — pure string → string transformation
- Same input → same output always (fully deterministic)
- Never changes factual content; only structural/formatting fixes
- Idempotent: `f(f(x)) == f(x)` for all sanitizer functions

---

## Pipeline Phases

The pipeline runs sanitizers in 5 strictly-ordered phases. Within each phase,
functions are **independent** (no ordering dependency between functions in the same phase).

### Phase 1 — Structural (Early)

Structural fixes that other sanitizers may depend on. Runs first so downstream
sanitizers see normalized headings and spacing.

| Function | Purpose |
|----------|---------|
| `fix_inline_heading()` | Splits heading-in-heading (`### A## B` → two lines) |
| `fix_sentence_heading()` | Converts sentence-style headings to clean verb-phrase (`"empowers you to X"` → `"Work with X"`) |
| `fix_missing_space_after_period()` | `Python.The` → `Python. The` (requires ≥5 lowercase before period) |
| `fix_heading_missing_space()` | `##Heading` → `## Heading` |

**Phase 1 ordering within this phase (binding)**:
`fix_sentence_heading` → `fix_missing_space_after_period` → others

### Phase 2 — Fences

Code fence normalization chain. Strict ordering because each step depends on the previous.

| Function | Purpose |
|----------|---------|
| `fix_nested_code_fences()` | Repair incorrectly nested triple-backtick blocks |
| `fix_bare_code_fences()` | Add missing language tags to bare ` ``` ` fences |
| `fix_excess_code_fences()` | Remove duplicate/extra opening fences |
| `fix_single_backtick_code_blocks()` | Promote single-backtick blocks to triple-backtick |
| `fix_unicode_backtick_fences()` | Replace Unicode backtick characters with ASCII |

### Phase 3 — Content

Content-level fixes. Most functions are independent.

| Function | Purpose |
|----------|---------|
| `fix_license_page()` | Remove auto-generated license page blocks |
| `fix_related_links()` | Normalize related-link sections |
| `fix_self_referential_links()` | Remove links that point to the current page |
| `fix_h2_intros()` | Normalize H2 section introductory text |
| `fix_frontmatter()` | Repair malformed YAML frontmatter |
| `fix_claim_markers_in_urls()` | Remove claim markers accidentally embedded in URLs |
| `fix_faqs()` | Normalize FAQ section structure |
| `fix_truncated_sentences()` | Detect and remove trailing incomplete sentences |

### Phase 4 — Strip

Remove unwanted patterns. All functions are independent.

| Function | Purpose |
|----------|---------|
| `strip_llm_scaffolding()` | Remove prompt echo-back headings (17 compiled patterns) |
| `strip_boilerplate_sentences()` | Remove generic filler sentences |
| `strip_visible_claim_markers()` | Remove `[claim: id]` visible markers (leave HTML comments) |
| `strip_pipeline_comments()` | Remove internal `<!-- pipeline: ... -->` comments |
| `strip_forbidden_topic_headings()` | Remove headings for topics not allowed in the page |
| `strip_product_name_prefix()` | Remove repeated product name prefix from heading titles |
| `strip_raw_python_objects()` | Remove `<Class object at 0x...>` debug strings |
| `strip_double_periods()` | Normalize `..` → `.` in prose (zone-guarded) |
| `strip_emojis()` | Remove all emoji characters (zone-guarded) |
| `strip_ci_badges()` | Remove CI badge markdown from content |
| `strip_illustrative_comments()` | Remove `# illustrative example` style comments |
| `strip_inline_seo_keywords()` | Remove inline SEO keyword annotations (zone-guarded) |

### Phase 5 — Finalize

Quality enforcement and flag-only quality signals. May add content (e.g., injecting frontmatter).

| Function | Purpose |
|----------|---------|
| `run_pipeline()` | Orchestrator function — applies all phases in order |
| `flag_fragmented_howto_code(content, page)` | Flag-only: inserts `<!-- WARNING: fragmented-code detected (FQ-1) -->` for isolated code fences in KB how-to pages |

#### `flag_fragmented_howto_code` (Spec v1.1, Agent 43)

- **Triggers**: KB how-to pages (`page_role == "howto_article"`) with code fences that appear isolated from surrounding prose (not integrated into a step-by-step flow)
- **Action**: Inserts an HTML comment warning — never strips or modifies content
- **Flag**: `<!-- WARNING: fragmented-code detected (FQ-1) -->`
- **Gate binding**: `gate_kb_howto_structure` (gate 32) checks for FQ-1 presence in draft files and reports as severity `warn` (does not hard-fail the gate)

---

## Zone Guard Model

The sanitizer uses a **zone guard** to protect code blocks and YAML frontmatter from
prose-targeted transformations.

**Implementation**: `src/launch/workers/_shared/markdown_zones.py`

### Zone Types

| Zone | Description |
|------|-------------|
| `FRONTMATTER` | YAML frontmatter between opening `---` and closing `---` |
| `CODE_FENCE` | Triple-backtick or tilde fenced code block |
| `HEADING` | Line(s) starting with `#` |
| `TABLE` | Lines containing `\|` separator (≥ 2 pipes) |
| `LIST` | Lines starting with `-`, `*`, `+`, or `N.` |
| `PROSE` | All other content (including blank lines) |

**Protected zones**: `FRONTMATTER` and `CODE_FENCE` are NEVER passed to prose sanitizers.

### Zone-Guarded Functions

The following Phase 4 sanitizers use `apply_to_prose_zones()` to skip protected zones:
`strip_inline_seo_keywords`, `strip_double_periods`, `strip_emojis`,
`normalize_module_names`, `strip_boilerplate_sentences`

---

## run_pipeline() — Orchestrator API

```python
def run_pipeline(
    content: str,
    ctx: SanitizerContext,
    *,
    include_frontmatter_injection: bool = False,
    frontmatter_injector: Optional[Callable] = None,
) -> str:
```

**Args**:
- `content`: Raw markdown string from LLM generation
- `ctx`: `SanitizerContext` — bundles `page`, `product_facts`, `run_config`, and optional section/slug
- `include_frontmatter_injection`: When `True`, Phase 5 injects YAML frontmatter using `frontmatter_injector`
- `frontmatter_injector`: Callable that produces frontmatter YAML block

**Returns**: Sanitized markdown string

---

## SanitizerContext

```python
class SanitizerContext:
    page: Optional[Dict]           # PageSpec entry (slug, section, page_role, etc.)
    product_facts: Optional[Dict]  # Product facts artifact
    run_config: Optional[Dict]     # Run configuration
    section: Optional[str]         # Content section (products/docs/reference/kb/blog)
    slug: Optional[str]            # Page slug
```

Context fields are optional — sanitizers degrade gracefully when fields are absent.

---

## Scheduling (Binding)

The sanitization pipeline runs in **two workers**:

| Worker | When | What runs |
|--------|------|-----------|
| **W5 SectionWriter** | After each page is drafted | Full `run_pipeline()` with `include_frontmatter_injection=True` |
| **W7 ContentReviewer** | After LLM format-fix pass (Phase 0) | Phase 3 sanitizers (post-LLM cleanup) |

**Phase 3 scheduling rule**: Phase 3 sanitizers run in both W5 and W7. This is intentional
defense-in-depth — LLM format-fix in W7 may introduce new structural issues that need cleanup.

**Phase 3 ordering (binding)**: Within Phase 3, these two functions MUST run first:
1. `fix_sentence_heading`
2. `fix_missing_space_after_period`

Then all remaining Phase 3 functions in any order.

---

## Key Regex Contracts

### `fix_missing_space_after_period` (binding)

```python
pattern = r'(?<=[a-z]{5})\.([A-Z][a-z])'
```

**Rationale**: Requires ≥5 lowercase characters before the period to avoid false positives on:
- Short identifiers (e.g., `docs.The` = only 4 chars = `docs`)
- Domain-style strings (e.g., `aspose.org`)

**Exclusions**: Pattern is skipped when:
- The line contains `://` (URL protection)
- The match is inside a backtick-quoted inline code span

### `strip_llm_scaffolding` (binding)

17 compiled regex patterns covering:
- Prompt echo-back headings: `## Product Context`, `## Instructions`, `## Output Rules`, `## SEO Keywords`, `## Audience`
- W5 prompt section headers: `## Source Material`, `## CRITICAL Rules`, `## Formatting`, `## Requirements`, `## Page-Specific Context`
- H1 variants and non-heading label variants

---

## Fence State Contract (TC-2378, binding)

All sanitizer functions that track code-fence state MUST use an integer depth counter
(not a boolean toggle):

- Counter increments when a stripped line starts with ` ``` ` or `~~~` AND depth is 0
- Counter decrements when a stripped line starts with ` ``` ` or `~~~` AND depth > 0
- Depth clamps to 0 (never goes negative). `in_fence` is derived as `depth > 0`
- **Idempotency**: `f(f(x)) == f(x)` is a hard requirement on all sanitizer functions

The canonical implementation is `_FenceState` in `content_sanitizer.py`.

---

## Acceptance Criteria

- All sanitizer functions are pure (no I/O, no network, no LLM)
- `run_pipeline(x, ctx)` called twice returns identical output for identical input
- `run_pipeline(run_pipeline(x, ctx), ctx)` equals `run_pipeline(x, ctx)` (idempotent)
- CODE_FENCE and FRONTMATTER zones are never modified by prose sanitizers
- Phase 3 ordering: `fix_sentence_heading` before `fix_missing_space_after_period`
- All 17 scaffolding patterns correctly detected and removed

---

## Related Specs

- `specs/21_worker_contracts.md` — W5 and W7 worker contracts
- `specs/07_section_templates.md` — Section template requirements (what content is expected)
- `specs/10_determinism_and_caching.md` — Determinism requirements
