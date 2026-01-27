# Rulesets and Templates Registry (versioned, deterministic)

## Purpose
`run_config` references `ruleset_version` and `templates_version`.
Implementers need an explicit contract for where these live and how they are selected so the system does not drift.

This document is binding.

## Rulesets (binding)
Rulesets MUST live at:
- `specs/rulesets/<ruleset_version>.yaml`

Ruleset version strings MUST match the file name exactly.

### Ruleset Structure (normative)

All rulesets MUST validate against `specs/schemas/ruleset.schema.json`.

**Required top-level keys**:
- `schema_version` (string) - Ruleset schema version (e.g., "1.0")
- `style` (object) - Content style rules
- `truth` (object) - Factual accuracy and citation rules
- `editing` (object) - File modification rules
- `sections` (object) - Per-section minimum page requirements

**Optional top-level keys**:
- `hugo` (object) - Hugo-specific rules (shortcodes, HTML)
- `claims` (object) - Claim marker configuration

#### `style` object (required)
**Required fields**:
- `tone` (string) - Writing tone (e.g., "technical", "friendly")
- `audience` (string) - Target audience (e.g., "developers", "end-users")
- `forbid_marketing_superlatives` (boolean) - If true, reject marketing language

**Optional fields**:
- `forbid_em_dash` (boolean) - If true, reject em-dashes (—)
- `prefer_short_sentences` (boolean) - Encourage concise sentences
- `forbid_weasel_words` (array of strings) - List of banned marketing/weasel words

#### `truth` object (required)
**Required fields**:
- `no_uncited_facts` (boolean) - If true, all claims must link to evidence
- `forbid_inferred_formats` (boolean) - If true, reject inferred file format support

**Optional fields**:
- `allow_external_citations` (boolean) - If true, permit citations to external sources
- `allow_inference` (boolean) - If true, permit limited inference from APIs

#### `editing` object (required)
**Required fields**:
- `diff_only` (boolean) - If true, prefer minimal diffs over full rewrites
- `forbid_full_rewrite_existing_files` (boolean) - If true, reject full file replacements

**Optional fields**:
- `forbid_deleting_existing_files` (boolean) - If true, forbid file deletions

#### `hugo` object (optional)
**Optional fields**:
- `allow_shortcodes` (array of strings) - List of permitted Hugo shortcodes
- `forbid_raw_html_except_claim_markers` (boolean) - If true, reject HTML except claim markers

#### `claims` object (optional)
**Optional fields**:
- `marker_style` (enum: "html_comment" | "frontmatter") - How claims are embedded
- `html_comment_prefix` (string) - Prefix for HTML comment markers (e.g., "claim_id:")
- `remove_markers_on_publish` (boolean) - If true, strip markers before publishing

#### `sections` object (required)
**Required fields** (all sub-objects with `min_pages` integer ≥ 0):
- `products` - Minimum pages for products section
- `docs` - Minimum pages for docs section
- `reference` - Minimum pages for reference section
- `kb` - Minimum pages for knowledge base section
- `blog` - Minimum pages for blog section

## Templates (binding)

### Template Resolution Order Algorithm

**Purpose:** Deterministic resolution when multiple templates match a file type

**Algorithm:**
1. Load all templates from registry (specs/20:70-85)
2. Filter templates where `file_pattern` regex matches target file path
3. If zero matches → Use default template (specs/08:45-60)
4. If one match → Use that template
5. If multiple matches → Sort by **specificity score** (highest first), break ties by **template name** (lexicographic)
6. Return first template from sorted list

**Specificity Score Calculation:**
- Start with 0
- +100 for each literal path segment (e.g., "src/pages" = 2 segments = +200)
- +50 for each extension match (e.g., ".md" = +50)
- +10 for each wildcard in pattern (e.g., "*.md" = 1 wildcard = +10)
- Longer patterns = higher specificity (more precise matching)

**Example:**
- Pattern: `src/pages/*.md` → Score: 200 (2 literal segments) + 50 (extension) + 10 (wildcard) = 260
- Pattern: `*.md` → Score: 50 (extension) + 10 (wildcard) = 60
- Pattern: `src/pages/about.md` → Score: 200 (2 segments) + 50 (extension) + 0 (no wildcard) = 250

**Determinism:** Guaranteed (specificity is deterministic, lexicographic tie-breaking is deterministic)

**Error Cases:**
- No templates in registry → ERROR: TEMPLATE_REGISTRY_EMPTY
- Circular template inheritance → ERROR: TEMPLATE_CIRCULAR_DEPENDENCY

### V1 Layout (Legacy)
All launch templates for V1 (non-platform-aware) MUST live under:
- `specs/templates/<subdomain>/<family>/<locale>/...`

Where:
- `<subdomain>` is one of:
  - `products.aspose.org`
  - `docs.aspose.org`
  - `reference.aspose.org`
  - `kb.aspose.org`
  - `blog.aspose.org`
- `<family>` is the product family folder (e.g., `cells`, `note`, `3d`)
- `<locale>` is the target locale folder, or `__LOCALE__` in template placeholders

### V2 Layout (Platform-Aware)
All launch templates for V2 (platform-aware) MUST live under:
- `specs/templates/<subdomain>/<family>/<locale>/<platform>/...`

Where platform levels include the same subdomain/family/locale as V1, plus:
- `<platform>` is the target platform folder (e.g., `python`, `typescript`, `go`) or `__PLATFORM__` in template placeholders

**Non-blog sections**: `specs/templates/<subdomain>/<family>/<locale>/<platform>/...`
**Blog section**: `specs/templates/blog.aspose.org/<family>/<platform>/...` (locale is filename-based)

Template selection MUST detect the resolved `layout_mode` per section and select from the matching hierarchy

### Template selection map (recommended, binding when present)
If present, the planner MUST use a map file:
- `specs/templates/<subdomain>/<family>/template_map.yaml`

The map MUST:
- enumerate all allowed templates for that (subdomain, family)
- map `(page_kind, variant)` → a single relative path (under the locale folder)
- forbid globbing outside the allowlist

If no map file exists, the planner MAY use deterministic globbing only with:
- an explicit allowlist of file patterns
- stable sorting
- a single unambiguous match per (page_kind, variant), else fail with a blocker issue.


## Required template classes (binding)

The following template classes MUST exist for V2 (platform-aware) launches:

### Platform root templates (non-blog)
For each non-blog subdomain, a platform root _index.md template MUST exist:
- `specs/templates/products.aspose.org/<family>/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/docs.aspose.org/<family>/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/kb.aspose.org/<family>/__LOCALE__/__PLATFORM__/_index.md`
- `specs/templates/reference.aspose.org/<family>/__LOCALE__/__PLATFORM__/_index.md`

These templates define the landing page for a specific platform within a product family.
They MUST include the standard frontmatter fields required by that subdomain's theme.

### Blog platform root (optional)
Blog may use theme-provided index pages. If a custom template is needed:
- `specs/templates/blog.aspose.org/<family>/__PLATFORM__/_index.md`

### Template variants
Templates MAY have variants indicated by suffix:
- `_index.md` - default variant
- `_index.variant-<name>.md` - named variant (e.g., `variant-minimal`, `variant-rich`)

The planner MUST select variants based on `launch_tier` and section requirements.

## Templates sourcing (allowed)
Templates may be maintained outside the launcher repo, but they MUST be materialized into `specs/templates/` before planning or writing.
Acceptable approaches include a git submodule, bootstrap clone, or CI artifact download.
The planner and writers MUST treat `specs/templates/` as read-only inputs for the run.

## Placeholder replacement contract (binding)
Templates use `__UPPER_SNAKE__` tokens and these MUST be replaced.

**Required tokens**:
- `__LOCALE__` - Target locale (e.g., `en`, `de`, `fr`)
- `__FAMILY__` - Product family (e.g., `cells`, `note`, `words`)
- `__PLATFORM__` - Target platform (V2 only, e.g., `python`, `typescript`, `go`)
- Plus other context-specific tokens (product name, slug, etc.)

Rules:
- Unknown tokens are forbidden.
- Booleans MUST be replaced with `true` or `false` (no quotes).
- After writing any output file, there MUST be **zero** remaining `__UPPER_SNAKE__` tokens anywhere in:
  - front matter
  - body
  - file paths

**Token lint requirement**: No leftover `__PLATFORM__`, `__LOCALE__`, or `__FAMILY__` placeholders in generated content paths or content.

This is enforced by TemplateTokenLint (see `specs/19_toolchain_and_ci.md`).

## Body scaffolding contract (binding)
Templates MUST include a section-specific body outline via tokens:
- `__BODY_CONTENT__` or more specific `__BODY_*__` tokens

Writers MUST:
- replace body scaffolding tokens with the planned outline for that page kind
- remove unused headings/tokens rather than leaving empty placeholders

## Required provenance (binding)
The orchestrator MUST record:
- `ruleset_version`
- `templates_version`
- the exact template file path used for each generated page

These MUST appear:
- in telemetry events (`ARTIFACT_WRITTEN` and page generation spans)
- and in `artifacts/evidence_map.json` (template provenance section)

## Acceptance
- The same run_config always resolves the same ruleset + templates deterministically.
- Template selection does not depend on filesystem iteration order.
- Template tokens never leak into final content.
