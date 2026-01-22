# Rulesets and Templates Registry (versioned, deterministic)

## Purpose
`run_config` references `ruleset_version` and `templates_version`.
Implementers need an explicit contract for where these live and how they are selected so the system does not drift.

This document is binding.

## Rulesets (binding)
Rulesets MUST live at:
- `specs/rulesets/<ruleset_version>.yaml`

Ruleset version strings MUST match the file name exactly.

A ruleset MUST define (minimum):
- section order (products, docs, reference, kb, blog)
- claim marker format and TruthLock requirements
- snippet tag taxonomy (approved tags)
- page kinds required per section (by launch_tier)
- validation gate configuration overrides (if any)

## Templates (binding)

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
