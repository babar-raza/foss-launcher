# Product Model

This document defines the family + platform taxonomy, auto-derived fields,
richness tiers, and how workers adapt behavior by tier.

## Family + Platform Taxonomy

Products are identified by two axes: **family** (what the library does) and
**platform** (what language/runtime it targets). The canonical registry
lives in `configs/families.yaml`.

### Families

| Key      | Display Name     | Category                      |
|----------|------------------|-------------------------------|
| cells    | Aspose.Cells     | Spreadsheet processing        |
| note     | Aspose.Note      | Digital notebook processing   |
| 3d       | Aspose.3D        | 3D modeling and rendering     |
| words    | Aspose.Words     | Document processing           |
| pdf      | Aspose.PDF       | PDF manipulation              |
| slides   | Aspose.Slides    | Presentation processing       |

### Platforms

| Key    | Import Template          | Install Command                       | Lang Tag   |
|--------|--------------------------|---------------------------------------|------------|
| python | `aspose_{family}_foss`   | `pip install aspose-{family}-foss`    | python     |
| java   | `com.aspose.{family}`    | maven                                 | java       |
| dotnet | `Aspose.{Family}`        | `dotnet add package Aspose.{Family}`  | csharp     |
| node   | `@aspose/{family}`       | `npm install @aspose/{family}`        | javascript |

## Auto-Derived Fields

Given a `(family, platform)` pair, the following fields are computed
automatically and locked for the entire pipeline run. Workers must use
these values exactly -- never infer or hallucinate alternatives.

| Field              | Derivation                                              |
|--------------------|---------------------------------------------------------|
| `display_name`     | `families[family].display + " FOSS for " + platform.title()` |
| `canonical_import` | `platforms[platform].import_tpl.format(family=family)`  |
| `runtime_import`   | `platforms[platform].runtime_import_tpl.format(family=family)` (Python only; see below) |
| `install_cmd`      | `platforms[platform].install_cmd.format(family=family)` |
| `lang_tag`         | `platforms[platform].lang_tag`                          |

Example for `(cells, python)`:
- `display_name` = "Aspose.Cells FOSS for Python"
- `canonical_import` = "aspose_cells_foss"
- `runtime_import` = "aspose.cells"
- `install_cmd` = "pip install aspose-cells-foss"
- `lang_tag` = "python"

These derived fields are stored in the `ProductIdentity` model
(`src/launcher/models/product.py`) and propagated through the pipeline
via the understanding bundle.

### `runtime_import` vs `canonical_import`

These two fields serve distinct purposes and must never be confused:

| Field | Purpose | Example |
|-------|---------|---------|
| `canonical_import` | The **pip package name** as installed (underscore-separated) | `aspose_3d_foss` |
| `runtime_import` | The **Python module path** used in `import` statements at runtime (dot-separated) | `aspose.threed` |

For Python packages, the pip install name and the runtime import name often differ.
For example, `aspose-3d-foss` is installed via pip but imported as `aspose.threed` at
runtime — using `import aspose_3d_foss` would raise `ModuleNotFoundError`.

**Rules**:
- `runtime_import` is only populated for the `python` platform. For `java`, `dotnet`,
  and `node`, the field is always an empty string.
- When `runtime_import` is empty, workers fall back to `canonical_import` for import
  validation and code generation.
- Per-family overrides for families whose runtime module path differs from the template
  are stored in `families.yaml` under `platforms.python.runtime_import_overrides`. For
  example, `3d` maps to `aspose.threed` rather than the template-derived `aspose.3d`.
- `RunConfig` may override `runtime_import` explicitly; the config value takes precedence
  over the families.yaml derivation.

### Frontmatter mapping

`ProductIdentity.canonical_import` remains the package/install identity. When the planner
builds page frontmatter, the frontmatter field named `canonical_import` is a code-facing
contract for downstream generation and evaluation, so Python pages emit
`runtime_import or canonical_import`. This is why a Python page may carry
`canonical_import: aspose.threed` in frontmatter even though the product identity still
stores `canonical_import = "aspose_3d_foss"` for packaging and install recipe purposes.

## Richness Tiers

Repositories are classified into richness tiers based on available
documentation, examples, API surface, and infrastructure. Classification
is performed by `src/launcher/shared/surface_classifier.py`.

### Scoring Rubric

| Signal              | Points                         |
|---------------------|--------------------------------|
| doc_files           | 1 per file, capped at 10      |
| readme_length       | 5 if > 500 chars               |
| example_files       | 1 per file, capped at 10      |
| api_surface confidence | high=10, medium=5, low=0    |
| public_classes count | 5 if > 20                     |
| has_tests           | 3                              |
| has_ci              | 2                              |

Maximum possible score: 45.

### Tier Thresholds

| Tier | Score Range | Label   | Description                           |
|------|-------------|---------|---------------------------------------|
| A    | >= 25       | Full    | Rich API surface, extensive docs/examples |
| B    | 12 -- 24    | Core    | Moderate API surface, some docs       |
| C    | < 12        | Minimal | Sparse docs, limited API surface      |

### Tier-to-Launch-Tier Mapping

The `launch_tier` field in RunConfig can be set to `auto`, `full`, `core`,
or `minimal`. When set to `auto`, the pipeline maps the richness tier to a
launch tier:

| Richness Tier | Auto Launch Tier |
|---------------|------------------|
| A             | full             |
| B             | core             |
| C             | minimal          |

An explicit `launch_tier` in the run config overrides the auto-classification.

## How Workers Adapt by Tier

### Understand

- **Tier A (full)**: Extracts all claim types. Plans the full page set
  from the ruleset (mandatory + optional pages).
- **Tier B (core)**: Extracts all claim types. Plans mandatory pages only.
  Skips optional page roles.
- **Tier C (minimal)**: Extracts only high-confidence claims. Plans a
  reduced page set (overview + installation + getting-started only).

### Generate

- **Tier A (full)**: Full per-section LLM generation with code examples
  required for all workflow page roles.
- **Tier B (core)**: Full per-section LLM generation. Code examples
  required for primary workflow roles only.
- **Tier C (minimal)**: Deterministic bullet-list rendering preferred.
  LLM used only for overview prose. Code examples included only when
  verbatim snippets exist in the repo.

### Evaluate

- **Tier A (full)**: All 8 quality checks active. GO criteria require
  >= 80% A+B grades and 0% D+F grades.
- **Tier B (core)**: All checks active. GO criteria relaxed to >= 60%
  A+B and <= 10% D+F.
- **Tier C (minimal)**: Safety-critical checks only (XSS, data leak,
  frontmatter). Content density and SEO checks disabled. GO criteria
  require 0 critical findings only.

### Publish

Publish behavior is identical across tiers. The tier affects only the
volume of content (number of pages) that reaches publish.

---

## Extended Spec (v2 Detail Addendum)

### Family + Platform Taxonomy (YAML Reference)

```yaml
families:
  cells:    { display: "Aspose.Cells",    category: "spreadsheet processing" }
  note:     { display: "Aspose.Note",     category: "digital notebook processing" }
  3d:       { display: "Aspose.3D",       category: "3D modeling and rendering" }
  words:    { display: "Aspose.Words",    category: "document processing" }
  pdf:      { display: "Aspose.PDF",      category: "PDF manipulation" }
  slides:   { display: "Aspose.Slides",   category: "presentation processing" }

platforms:
  python:   { import_tpl: "aspose_{family}_foss",  install: "pip install" }
  java:     { import_tpl: "com.aspose.{family}",   install: "maven" }
  dotnet:   { import_tpl: "Aspose.{Family}",       install: "dotnet add" }
  node:     { import_tpl: "@aspose/{family}",       install: "npm install" }
```

**Auto-derived fields** (computed by Intake; never configured manually):
- `display_name` = `families[family].display + " FOSS for " + platform.title()`
- `canonical_import` = `platforms[platform].import_tpl.format(family=family)`
- `runtime_import` = derived from `platforms.python.runtime_import_tpl` (Python only); per-family overrides in `runtime_import_overrides`; empty string for all other platforms

### Tier Identifier Mapping

The system uses two tier vocabularies. This mapping is fixed; never infer it:

| Classifier output | run_config `launch_tier` | IntakeBundle `effective_tier` | Meaning |
|------------------|--------------------------|-------------------------------|---------|
| `A` | `full` | `full` | Rich — all optional pages, all template variants |
| `B` | `core` | `core` | Moderate — standard optional expansion |
| `C` | `minimal` | `minimal` | Thin — mandatory pages only, minimal variant |
| (n/a) | `auto` | (resolved by Intake) | Intake classifies repo and resolves to full/core/minimal |

**Rules**:
- `surface_classifier.py` returns `Literal["A", "B", "C"]`.
- Intake translates to `Literal["full", "core", "minimal"]` before writing `IntakeBundle.effective_tier`.
- Downstream workers (Understand, Generate, Evaluate) only ever see `effective_tier ∈ {full, core, minimal}`.
- `auto`, `A`, `B`, `C` must never appear in `IntakeBundle.effective_tier`.

### Richness Scoring (Extended)

| Signal | Points |
|--------|--------|
| Doc files found (up to 10) | 1 each |
| README > 500 chars | 5 |
| Example files found (up to 10) | 1 each |
| API surface confidence = high | 10 |
| API surface confidence = medium | 5 |
| 20+ public classes | 5 |
| Has tests | 3 |
| Has CI | 2 |

| Tier | Score | effective_tier |
|------|-------|---------------|
| A | ≥ 25 | `full` |
| B | ≥ 12 | `core` |
| C | < 12 | `minimal` |

### Worker Behavior by Tier (Summary Table)

| Behavior | full (A) | core (B) | minimal (C) |
|----------|:--------:|:--------:|:-----------:|
| Claim extraction | Docs + code + README | README + code | README only |
| Snippets | Mostly extracted | Mix extracted + generated | Mostly generated |
| Template variant | `standard` or `steps` | `standard` | `minimal` |
| Page count | Full expansion | Standard expansion | Minimum pages |
| Gate strictness | All enforced | Safety gates enforced | Safety only |
