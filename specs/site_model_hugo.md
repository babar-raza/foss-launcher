# Site Model: Hugo

## Overview

Generated content targets a Hugo static site with 5 subdomains. Each subdomain
has its own URL pattern, frontmatter requirements, and section/slug conventions.
The site model is the contract between the Generate worker (which produces PageIR)
and the Publish worker (which places files in the Hugo content tree).

---

## Subdomains

| Subdomain | Purpose | Content character |
|-----------|---------|-------------------|
| `products` | Product landing pages | Marketing, feature highlights |
| `docs` | Technical documentation | Tutorials, guides, API walkthroughs |
| `kb` | Knowledge base | How-to articles, FAQ, troubleshooting |
| `reference` | API reference | Class/method documentation |
| `blog` | Blog posts | Announcements, deep dives |

---

## URL Patterns

Each subdomain uses a deterministic URL pattern derived from family, platform,
and slug.

| Subdomain | URL pattern | Example |
|-----------|-------------|---------|
| `products` | `/{family}-foss-{platform}/` | `/cells-foss-python/` |
| `docs` | `/{family}-foss-{platform}/{slug}/` | `/cells-foss-python/installation/` |
| `kb` | `/{family}-foss-{platform}/kb/{slug}/` | `/cells-foss-python/kb/faq/` |
| `reference` | `/{family}-foss-{platform}/reference/{slug}/` | `/cells-foss-python/reference/api-overview/` |
| `blog` | `/blog/{family}-foss-{platform}/{slug}/` | `/blog/cells-foss-python/introducing-cells-foss-python/` |

### Slug Rules

- Slugs are lowercase, hyphen-separated.
- No trailing slashes in slug values; Hugo adds them.
- `_index` slugs create section list pages (Hugo branch bundles).
- Slugs must be unique within their subdomain for a given family+platform.
- Parameterized slugs (e.g., `introducing-{family}-foss-{platform}`) are
  resolved at plan time by the Understand worker.

---

## Frontmatter Requirements

All pages share a base set of frontmatter fields. Subdomains add specific fields.

### Base Frontmatter (all subdomains)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Page title |
| `type` | string | yes | Hugo content type (matches subdomain) |
| `url` | string | yes | Canonical URL (from URL pattern above) |
| `weight` | integer | yes | Sort order within section |
| `description` | string | yes | Meta description for SEO (max 160 chars) |
| `date` | string | yes | ISO-8601 date |
| `lastmod` | string | yes | ISO-8601 last-modified date |

### Products Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `family` | string | yes | Product family slug |
| `platform` | string | yes | Platform slug |
| `display_name` | string | yes | Human-readable product name |
| `canonical_import` | string | yes | Canonical code import statement; for Python this uses `runtime_import` when available (for example `aspose.threed`), otherwise it falls back to `canonical_import` |

### Docs Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_role` | string | yes | Semantic page role |
| `toc` | boolean | yes | Whether to render table of contents |
| `machine_readable` | object | no | Structured data for the page |

### KB Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_role` | string | yes | Semantic page role |
| `topic_category` | string | no | Topic classification |
| `seo_keywords` | string[] | no | Target keywords |

### Reference Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `page_role` | string | yes | Semantic page role |
| `api_module` | string | no | Module this page documents |
| `machine_readable` | object | no | Structured API data |

### Blog Frontmatter

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `author` | string | yes | Author name (use product display name) |
| `tags` | string[] | yes | Blog tags for categorization |
| `categories` | string[] | yes | Blog categories |

---

## Hugo Content Directory Layout

Files are placed in the Hugo content tree by the Publish worker:

```
content/
  {family}-foss-{platform}/
    _index.md                    # products landing
    docs/
      _index.md                  # docs TOC
      installation.md
      getting-started/
        _index.md                # folder index
      ...
    kb/
      _index.md                  # KB TOC
      faq.md
      troubleshooting.md
      how-to-open-a-file.md
      ...
    reference/
      _index.md                  # reference TOC
      api-overview.md
      ...
  blog/
    {family}-foss-{platform}/
      introducing-{f}-foss-{p}.md
      {f}-key-features.md
      ...
```

### Section Index Pages

- Every section directory has an `_index.md` with `page_role: toc` or
  `page_role: landing`.
- `_index.md` files use Hugo's branch bundle semantics.

### Folder Indexes

Some pages are folder indexes (e.g., `getting-started/_index.md`). These are
marked with `folder_index: true` in the ruleset. The Publish worker creates the
directory and places `_index.md` inside it.

---

## Permalink Determinism

Permalinks are computed at plan time and stored in frontmatter as `url`. This
ensures no Hugo-side slug derivation surprises. The Evaluate worker's permalink
gate verifies that all `url` values are unique across the entire site for the
given family+platform combination.
