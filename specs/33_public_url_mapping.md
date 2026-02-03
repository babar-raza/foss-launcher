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

- **content_path**: The file path relative to the site repo root, e.g., `content/docs.aspose.org/cells/en/python/getting-started.md`
- **url_path**: The canonical URL path (without scheme/host), e.g., `/cells/python/getting-started/`
- **subdomain**: The Hugo site subdomain, e.g., `docs.aspose.org`
- **family**: The product family, e.g., `cells`, `words`, `note`
- **locale**: The language code, e.g., `en`, `fr`, `de`
- **platform**: The target platform (V2 layout), e.g., `python`, `java`, `go`
- **section_path**: Nested folder path within the platform/locale root
- **page_kind**: Type of page: `section_index` (`_index.md`), `leaf_page` (`<slug>.md`), or `bundle_page` (`<slug>/index.md`)

---

## URL Computation Contract (binding)

### Input parameters
To compute a url_path, the resolver requires:
- `subdomain` (string)
- `family` (string)
- `locale` (string)
- `platform` (string, required for V2; empty string for V1)
- `section_path` (list of strings, may be empty)
- `page_kind` (enum: `section_index` | `leaf_page` | `bundle_page`)
- `slug` (string, required for `leaf_page` and `bundle_page`)
- `hugo_facts` (object with `default_language`, `default_language_in_subdir`)

### Output
- `url_path` (string): The canonical URL path with leading `/` and trailing `/`

---

## URL Rules by Section Type (binding)

### A) Non-blog sections (products, docs, kb, reference)

**Filesystem layout (V2)**:
```
content/<subdomain>/<family>/<locale>/<platform>/
  ├── _index.md                    # platform root
  ├── <section>/_index.md          # section index
  ├── <section>/<slug>.md          # leaf page (flat style)
  └── <section>/<slug>/index.md    # leaf page (bundle style)
```

**URL computation**:

For **default language** (from hugo_facts.default_language, typically `en`):
- Locale is **dropped** from the URL path (Hugo convention)
- Platform appears immediately after family

```
url_path = /<family>/<platform>/<section_path...>/<slug>/
```

For **non-default language**:
- If hugo_facts.default_language_in_subdir == true: locale is **dropped** for all languages
- Otherwise (standard Hugo): locale **prefixes** the URL path

```
url_path = /<locale>/<family>/<platform>/<section_path...>/<slug>/
```

**Examples (default_language=en, default_language_in_subdir=false)**:

| content_path | url_path |
|-------------|----------|
| `content/products.aspose.org/words/en/python/_index.md` | `/words/python/` |
| `content/products.aspose.org/words/en/python/overview.md` | `/words/python/overview/` |
| `content/products.aspose.org/words/fr/python/_index.md` | `/fr/words/python/` |
| `content/docs.aspose.org/cells/en/python/developer-guide/_index.md` | `/cells/python/developer-guide/` |
| `content/docs.aspose.org/cells/en/python/developer-guide/quickstart.md` | `/cells/python/developer-guide/quickstart/` |
| `content/kb.aspose.org/cells/en/python/troubleshooting.md` | `/cells/python/troubleshooting/` |
| `content/reference.aspose.org/cells/en/python/_index.md` | `/cells/python/` |

### B) Blog section (blog.aspose.org)

**Filesystem layout (V2)**:
```
content/blog.aspose.org/<family>/<platform>/
  ├── _index.md                    # platform root (English)
  ├── _index.<lang>.md             # platform root (other languages)
  ├── <year>-<month>-<day>-<slug>.md       # post (English)
  └── <year>-<month>-<day>-<slug>.<lang>.md # post (other languages)
```

**URL computation**:
- Blog uses filename-based i18n (no locale folder)
- Platform appears after family (V2) or is absent (V1)
- Hugo typically generates blog URLs with date segments or flat slugs based on permalinks config

**Default behavior (no custom permalinks)**:
```
url_path = /<family>/<platform>/<slug>/     # English
url_path = /<lang>/<family>/<platform>/<slug>/  # Non-default language
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
- `_index.md` in `/<family>/<platform>/guide/` maps to `/family/platform/guide/`

### Leaf page (<slug>.md - flat style)
- Maps to parent URL + slug
- `guide/quickstart.md` maps to `/family/platform/guide/quickstart/`

### Bundle page (<slug>/index.md - bundle style)
- Maps identically to flat style
- `guide/quickstart/index.md` maps to `/family/platform/guide/quickstart/`
- The `index.md` file name is stripped; the folder name becomes the slug

---

## URL Resolution Algorithm (binding)

This algorithm computes the canonical public `url_path` for a content file given Hugo configuration.

### Inputs
- `output_path`: Content file path relative to content root (e.g., `content/docs.aspose.org/cells/en/python/overview.md`)
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
   platform = None
   page_slug = None

   # Detect locale and platform based on layout_mode
   if layout_mode == "v2":
       locale = parts[2]    # e.g., en
       platform = parts[3]  # e.g., python
       page_slug = "/".join(parts[4:]).removesuffix(".md")
   else:  # v1
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

   # Add platform segment (v2 only)
   if layout_mode == "v2":
       path_segments.append(platform)

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
   - Ensure no `__PLATFORM__` or `__LOCALE__` placeholders remain

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
    platform = target.platform
    section_path = target.section_path
    page_kind = target.page_kind
    slug = target.slug

    # Determine locale prefix
    if locale == hugo_facts.default_language and not hugo_facts.default_language_in_subdir:
        locale_prefix = ""
    else:
        locale_prefix = "/" + locale

    # Determine platform segment (empty for V1)
    platform_segment = "/" + platform if platform else ""

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
        url_path = locale_prefix + "/" + family + platform_segment + slug_segment + "/"
    else:
        # Non-blog: locale_prefix + family + platform + section + slug
        url_path = locale_prefix + "/" + family + platform_segment + section_segment + slug_segment + "/"

    # Normalize (remove double slashes, ensure leading/trailing /)
    url_path = normalize_path(url_path)

    return url_path
```

---

## V1 (Legacy) URL Mapping (reference)

For V1 layouts without platform:
- Simply omit the platform segment
- `content/docs.aspose.org/cells/en/getting-started.md` maps to `/cells/getting-started/` (default lang)
- `content/docs.aspose.org/cells/fr/getting-started.md` maps to `/fr/cells/getting-started/` (non-default lang)

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
- Platform appears immediately after family in V2 layouts
- Blog URLs follow filename-based i18n conventions
- All examples in this spec are verified by unit tests

---

## Implementation Notes (2026-02-03)

### Critical Architecture Clarification: Section is Implicit in Subdomain

**Key principle**: Section name NEVER appears in URL paths. The subdomain IS the section identifier.

**Why this matters**:
- Each section uses a dedicated subdomain (blog.aspose.org, docs.aspose.org, etc.)
- The subdomain already identifies the section, so including it in the path is redundant
- URL format is consistently: `/{family}/{platform}/{slug}/` across all sections
- Example: `docs.aspose.org/cells/python/guide/` NOT `docs.aspose.org/cells/python/docs/guide/`

This architecture is binding per lines 83-86 (docs example) and line 106 (blog example) above.

**Implementation reference**: See `src/launch/workers/w4_ia_planner/worker.py::compute_url_path()` (lines 376-416) for the reference implementation that correctly omits section from URL path.

**Related fixes**: HEAL-BUG1 (2026-02-03) corrected URL generation to remove section from path.
