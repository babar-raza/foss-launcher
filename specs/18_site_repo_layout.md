# aspose.org Content Repo Layout (authoritative)

## Purpose
The system MUST write content into the correct subdomain, family, and locale folders in the aspose.org content repo.
All path decisions MUST use this contract, not hardcoded short paths like /docs or /products.

> **Updated (2026-02-09)**: V2 platform-aware layout has been removed. All content uses V1 layout exclusively. The spec `specs/32_platform_aware_content_layout.md` is DEPRECATED and retained for historical reference only.

## Root layout
Content is organized by subdomain folders under:

aspose.org/content/
  products.aspose.org/
  docs.aspose.org/
  kb.aspose.org/
  reference.aspose.org/
  blog.aspose.org/

## Family folders
Immediately under each subdomain folder is the product family folder:

content/products.aspose.org/<family>/
content/docs.aspose.org/<family>/
content/kb.aspose.org/<family>/
content/reference.aspose.org/<family>/
content/blog.aspose.org/<family>/

Examples:
content/products.aspose.org/note/
content/docs.aspose.org/cells/
content/kb.aspose.org/3d/
content/reference.aspose.org/pdf/
content/blog.aspose.org/words/

## Localization rule

### V1 Layout (Active)
For all subdomains EXCEPT blog.aspose.org, localization is directory-based:

content/<subdomain>/<family>/<locale>/

Examples:
content/products.aspose.org/note/de/
content/docs.aspose.org/cells/en/
content/kb.aspose.org/3d/ja/
content/reference.aspose.org/pdf/zh/

For blog.aspose.org, localization is NOT directory-based.
Blog uses Hugo filename-based localization (example patterns: index.md + index.de.md, or post.md + post.de.md).

### ~~V2 Layout (Platform-Aware)~~ (REMOVED)

> **REMOVED (2026-02-09)**: V2 platform-aware layout is no longer supported. All content uses V1 layout above. Platform directory segments (`/{platform}/`) are not used in any content paths. See `specs/32_platform_aware_content_layout.md` (DEPRECATED) for historical reference.

## Path resolution (MUST)
Given:
- section in {products, docs, kb, reference, blog}
- family (string)
- locale (string)

Return the section root:

**V1 layout** (active, no platform segment):
If section != blog:
  root = content/<section_subdomain>/<family>/<locale>/

If section == blog:
  root = content/blog.aspose.org/<family>/
  locale handling is file-based, determined from existing files.

> **Note (2026-02-09)**: V2 layout paths with `/{platform}/` segments are no longer supported. The `layout_mode` and `target_platform` configuration fields are removed.

## Allowed paths enforcement (MUST)
A run must declare allowed_paths in run_config.
The orchestrator MUST refuse any patch outside allowed_paths.
Recommended allowed paths for a run are the section roots for the target family and locale(s).

## Frontmatter contract discovery (MUST)
FrontmatterContract must be discovered per:
- section
- family
- locale (directory-based sections)

Discovery occurs within V1 roots:
- `content/<subdomain>/<family>/<locale>/` for non-blog sections
- `content/blog.aspose.org/<family>/` for blog

For blog (file-based localization), discovery is per family, by sampling existing files under the resolved roots.


## Hugo config awareness (binding)
Planning and validation MUST be Hugo-config aware.
See `specs/31_hugo_config_awareness.md`.
