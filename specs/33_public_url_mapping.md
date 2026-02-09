# Public URL Mapping (binding)

## Purpose
Content files in the repository map to canonical public URLs. Without a binding contract for this mapping,
agents cannot correctly:
- Generate cross-links between pages
- Insert navigation entries with correct URLs
- Validate that produced content will be discoverable

This spec defines the deterministic mapping from content paths to public URLs.

---

## Terminology (binding)

- **content_path**: The file path relative to the site repo root, e.g., `content/docs.aspose.org/cells/en/getting-started.md`
- **url_path**: The canonical URL path (without scheme/host), e.g., `/cells/getting-started/`
- **subdomain**: The Hugo site subdomain, e.g., `docs.aspose.org`
- **family**: The product family, e.g., `cells`, `words`, `note`
- **locale**: The language code, e.g., `en`, `fr`, `de`
- **section_path**: Nested folder path within the locale root
- **page_kind**: Type of page: `section_index` (`_index.md`), `leaf_page` (`<slug>.md`), or `bundle_page` (`<slug>/index.md`)

---

## URL Computation Contract (binding)

### Input parameters
To compute a url_path, the resolver requires:
- `subdomain` (string)
- `family` (string)
- `locale` (string)
- `section_path` (list of strings, may be empty)
- `page_kind` (enum: `section_index` | `leaf_page` | `bundle_page`)
- `slug` (string, required for `leaf_page` and `bundle_page`)
- `hugo_facts` (object with `default_language`, `default_language_in_subdir`)

### Output
- `url_path` (string): The canonical URL path with leading `/` and trailing `/`

---

## URL Rules by Section Type (binding)

### A) Non-blog sections (products, docs, kb, reference)

**Filesystem layout (V1)**:
```
content/<subdomain>/<family>/<locale>/
  ├── _index.md                    # family/locale root
  ├── <section>/_index.md          # section index
  ├── <section>/<slug>.md          # leaf page (flat style)
  └── <section>/<slug>/index.md    # leaf page (bundle style)
```

**URL computation**:

For **default language** (from hugo_facts.default_language, typically `en`):
- Locale is **dropped** from the URL path (Hugo convention)

```
url_path = /<family>/<section_path...>/<slug>/
```

For **non-default language**:
- If hugo_facts.default_language_in_subdir == true: locale is **dropped** for all languages
- Otherwise (standard Hugo): locale **prefixes** the URL path

```
url_path = /<locale>/<family>/<section_path...>/<slug>/
```

**Examples (default_language=en, default_language_in_subdir=false)**:

| content_path | url_path |
|-------------|----------|
| `content/products.aspose.org/words/en/_index.md` | `/words/` |
| `content/products.aspose.org/words/en/overview.md` | `/words/overview/` |
| `content/products.aspose.org/words/fr/_index.md` | `/fr/words/` |
| `content/docs.aspose.org/cells/en/developer-guide/_index.md` | `/cells/developer-guide/` |
| `content/docs.aspose.org/cells/en/developer-guide/quickstart.md` | `/cells/developer-guide/quickstart/` |
| `content/kb.aspose.org/cells/en/troubleshooting.md` | `/cells/troubleshooting/` |
| `content/reference.aspose.org/cells/en/_index.md` | `/cells/` |

### B) Blog section (blog.aspose.org)

**Filesystem layout (V1)**:
```
content/blog.aspose.org/<family>/
  ├── _index.md                    # family root (English)
  ├── _index.<lang>.md             # family root (other languages)
  ├── <year>-<month>-<day>-<slug>.md       # post (English)
  └── <year>-<month>-<day>-<slug>.<lang>.md # post (other languages)
```

**URL computation**:
- Blog uses filename-based i18n (no locale folder)
- No platform segment in blog URLs
- Hugo typically generates blog URLs with date segments or flat slugs based on permalinks config

**Default behavior (no custom permalinks)**:
```
url_path = /<family>/<slug>/     # English
url_path = /<lang>/<family>/<slug>/  # Non-default language
```

**If permalinks specify date-based URLs**:
- Derive from hugo_facts.permalinks if present
- Otherwise use Hugo defaults

---

## Hugo Facts Required for URL Mapping (binding)

The hugo_facts.json artifact MUST include these fields for URL resolution:

| Field | Type | Description |
|-------|------|-------------|
| `default_language` | string | The default language code (e.g., "en") |
| `default_language_in_subdir` | boolean | If true, all languages (including default) use subdir URLs |
| `permalinks` | object | Custom permalink patterns by section (may be empty) |

### Discovery approach (binding)

1. **default_language**: Read from Hugo config `defaultContentLanguage` key. If absent, default to `"en"`.

2. **default_language_in_subdir**: Read from Hugo config `defaultContentLanguageInSubdir` key. If absent, default to `false`.

3. **permalinks**: Read from Hugo config `permalinks` section. If absent, use empty object `{}`.

If the Hugo config does not expose these values:
- Use Hugo defaults (default_language="en", default_language_in_subdir=false)
- Record discovery method in OPEN_QUESTIONS.md if heuristic fallback was required

---

## Section Index vs Leaf Page vs Bundle Page (binding)

### Section index (_index.md)
- Always maps to the parent URL without a slug
- `_index.md` in `/<family>/guide/` maps to `/family/guide/`

### Leaf page (<slug>.md - flat style)
- Maps to parent URL + slug
- `guide/quickstart.md` maps to `/family/guide/quickstart/`

### Bundle page (<slug>/index.md - bundle style)
- Maps identically to flat style
- `guide/quickstart/index.md` maps to `/family/guide/quickstart/`
- The `index.md` file name is stripped; the folder name becomes the slug

---

## URL Resolution Algorithm (binding)

This algorithm computes the canonical public `url_path` for a content file given Hugo configuration.

### Inputs
- `output_path`: Content file path relative to content root (e.g., `content/docs.aspose.org/cells/en/overview.md`)
- `hugo_facts`: Normalized Hugo config facts from `artifacts/hugo_facts.json`
- `section`: Section name (products, docs, kb, reference, blog)

### Algorithm Steps

1. **Extract path components**:
   ```python
   # Parse output_path
   parts = output_path.removeprefix("content/").split("/")
   subdomain = parts[0]  # e.g., docs.aspose.org
   family = parts[1]      # e.g., cells
   locale = None
   page_slug = None

   # V1 layout only — no platform segment
   locale = parts[2]    # e.g., en
   page_slug = "/".join(parts[3:]).removesuffix(".md")
   ```

2. **Apply Hugo URL rules**:
   ```python
   # Start with base URL
   if subdomain in hugo_facts.baseURL_by_subdomain:
       base_url = hugo_facts.baseURL_by_subdomain[subdomain]
   else:
       base_url = f"https://{subdomain}"

   # Build path segments
   path_segments = []

   # Add locale segment (for non-blog or if blog includes locale)
   if section != "blog" or hugo_facts.blog_includes_locale:
       if locale != hugo_facts.default_language or not hugo_facts.remove_default_locale:
           path_segments.append(locale)

   # Add family segment
   path_segments.append(family)

   # No platform segment — V1 layout only

   # Add page slug segments
   if page_slug and page_slug != "_index":
       path_segments.extend(page_slug.split("/"))

   # Join segments
   url_path = "/" + "/".join(path_segments) + "/"

   # Apply permalinks overrides if configured
   if section in hugo_facts.permalinks:
       url_path = apply_permalink_pattern(url_path, hugo_facts.permalinks[section])

   return url_path
   ```

3. **Handle special cases**:
   - `_index.md` files: URL ends at parent directory (no page slug)
   - Blog posts: May include date segments from frontmatter `date` field
   - Custom permalinks: Apply pattern substitution from `hugo_facts.permalinks`

4. **Validate URL**:
   - Ensure URL starts with `/`
   - Ensure URL ends with `/` (Hugo default, overridden by permalinks)
   - Ensure no `//` sequences
   - Ensure no `__LOCALE__` placeholders remain
   - Ensure no `__PLATFORM__` placeholders remain (DEPRECATED token, must never appear)

### Permalink Pattern Substitution

If `hugo_facts.permalinks[section]` exists:
```python
def apply_permalink_pattern(url_path, pattern):
    # Example pattern: "/:year/:month/:slug/"
    # Substitution variables from frontmatter:
    # :year, :month, :day, :slug, :title, :section
    # This requires frontmatter parsing, so url_path is computed post-frontmatter
    ...
```

### Collision Detection

After computing all `url_path` values in `page_plan.pages[]`:
1. Build map: `url_path → [output_path]`
2. If any `url_path` has multiple `output_path` entries:
   - Open BLOCKER issue with error_code `IA_PLANNER_URL_COLLISION`
   - List all colliding pages
   - Suggested fix: "Rename pages or adjust permalinks to ensure unique URLs"

## Algorithm (binding - reference implementation)

```
function resolve_public_url(target, hugo_facts):
    subdomain = target.subdomain
    family = target.family
    locale = target.locale
    section_path = target.section_path
    page_kind = target.page_kind
    slug = target.slug

    # Determine locale prefix
    if locale == hugo_facts.default_language and not hugo_facts.default_language_in_subdir:
        locale_prefix = ""
    else:
        locale_prefix = "/" + locale

    # No platform segment — V1 layout only

    # Build section path
    section_segment = "/" + "/".join(section_path) if section_path else ""

    # Build slug segment
    if page_kind == "section_index":
        slug_segment = ""
    else:
        slug_segment = "/" + slug

    # Compose URL path
    if subdomain == "blog.aspose.org":
        # Blog: no locale folder in content, but URL may have locale prefix
        url_path = locale_prefix + "/" + family + slug_segment + "/"
    else:
        # Non-blog: locale_prefix + family + section + slug
        url_path = locale_prefix + "/" + family + section_segment + slug_segment + "/"

    # Normalize (remove double slashes, ensure leading/trailing /)
    url_path = normalize_path(url_path)

    return url_path
```

---

## V1 URL Mapping (binding)

All content uses V1 layout (no platform segment):
- `content/docs.aspose.org/cells/en/getting-started.md` maps to `/cells/getting-started/` (default lang)
- `content/docs.aspose.org/cells/fr/getting-started.md` maps to `/fr/cells/getting-started/` (non-default lang)
- `content/blog.aspose.org/words/2026-01-15-announcement.md` maps to `/words/announcement/` (blog, default lang)

---

## Validation Requirements (binding)

1. Every page in page_plan.json MUST have a `url_path` field populated by the resolver
2. Cross-links MUST use url_path (not content_path) for href values
3. Navigation inserts MUST use url_path for menu URLs

---

## OPEN QUESTIONS

If any of the following cannot be determined from Hugo config:
- Log to `RUN_DIR/reports/OPEN_QUESTIONS.md`
- Use Hugo defaults as fallback
- Mark the fallback in artifacts for audit

---

## Acceptance

- The resolver produces identical url_path for identical inputs
- Default language URLs drop the locale prefix
- Non-default language URLs include the locale prefix (unless default_language_in_subdir=true)
- No platform segment in any URL paths (V1-only)
- Blog URLs follow filename-based i18n conventions: `/{family}/{slug}/`
- All examples in this spec are verified by unit tests

---

## Implementation Notes (2026-02-03)

### Critical Architecture Clarification: Section is Implicit in Subdomain

**Key principle**: Section name NEVER appears in URL paths. The subdomain IS the section identifier.

**Why this matters**:
- Each section uses a dedicated subdomain (blog.aspose.org, docs.aspose.org, etc.)
- The subdomain already identifies the section, so including it in the path is redundant
- URL format is consistently: `/{family}/{slug}/` across all sections (V1 layout, no platform segment)
- Example: `docs.aspose.org/cells/guide/` NOT `docs.aspose.org/cells/docs/guide/`

This architecture is binding per the URL examples above.

**Implementation reference**: See `src/launch/workers/w4_ia_planner/worker.py::compute_url_path()` for the reference implementation that correctly omits section from URL path.

**Related fixes**: HEAL-BUG1 (2026-02-03) corrected URL generation to remove section from path.

**V2 removal (2026-02-09)**: Platform segment removed from all URL paths. URLs are now `/{family}/{slug}/` (no `/{platform}/` component).
