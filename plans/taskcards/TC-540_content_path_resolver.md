---
id: TC-540
title: "Content Path Resolver (Hugo content layout + blog localization rules)"
status: Done
owner: "CONTENT_AGENT"
updated: "2026-01-28"
depends_on:
  - TC-400
allowed_paths:
  - src/launch/resolvers/content_paths.py
  - src/launch/resolvers/slugify.py
  - src/launch/schemas/content_path.schema.json
  - tests/unit/resolvers/test_tc_540_content_paths.py
  - reports/agents/**/TC-540/**
evidence_required:
  - reports/agents/<agent>/TC-540/report.md
  - reports/agents/<agent>/TC-540/self_review.md
spec_ref: f48fc5dbb12c5513f42aabc2a90e2b08c6170323
ruleset_version: ruleset.v1
templates_version: templates.v1
---

# Taskcard TC-540 — Content Path Resolver (Hugo content layout + blog localization rules)

## Objective
Implement a deterministic **Content Path Resolver** that maps a target (subdomain, family, language, platform, page kind, slug, section path) to an exact Markdown file path in the aspose.org content repo.

This resolver MUST support both V1 (legacy, no platform segment) and V2 (platform-aware) layouts with deterministic auto-detection.

W4–W6 must call this resolver for every content read/write so the system never guesses where pages live.

## Required spec references
- specs/18_site_repo_layout.md
- specs/32_platform_aware_content_layout.md (V2 layout binding contract)
- specs/33_public_url_mapping.md (url_path vs output_path separation)
- specs/22_navigation_and_existing_content_update.md
- specs/31_hugo_config_awareness.md
- specs/10_determinism_and_caching.md
- specs/11_state_and_events.md
- specs/21_worker_contracts.md (W4–W6)
- specs/30_site_and_workflow_repos.md

## Scope
### In scope
- Implement `resolve_content_path()` and supporting dataclass(es)
- Encode the **Aspose content layout rule**:
  - `content/<subdomain>/<family>/...`
  - For all subdomains **except** `blog.aspose.org`: directory-based i18n under `<family>/<lang>/`
  - For `blog.aspose.org`: file-based i18n using filename suffixes (`.fr.md`, `.de.md`, etc), with English as unsuffixed `.md`
- Handle these page kinds deterministically:
  - `family_index` (landing for a family in a language)
  - `section_index` (landing for a nested section path)
  - `page` (a leaf page/post)
- Slug normalization and safe path joining (no path traversal)
- Unit tests for all mapping rules and edge cases

### Out of scope
- Writing content (W5)
- Patch application (W6)
- Validation of examples (W7) beyond path resolution correctness

## Inputs
- `site_context.json` from W1 (for locating content root, layout_mode detection per section)
- `run_config` containing `target_platform` and `layout_mode` fields
- A target structure from planner/writer:
  - `subdomain` (example: `docs.aspose.org`)
  - `family` (example: `cells`)
  - `lang` (example: `en`, `fr`, `ja`)
  - `target_platform` (example: `python`, `typescript`, `go`) - required for V2
  - `layout_mode` (example: `auto`, `v1`, `v2`) - determines path structure
  - `page_kind` (`family_index|section_index|page`)
  - `section_path` (list of folder slugs, may be empty)
  - `slug` (leaf slug, required for `page`)

## Outputs
- A deterministic `ContentTarget` object:
  - `repo_relpath` (posix path relative to site repo root)
  - `content_relpath` (posix path relative to `content/`)
  - `is_translation` and `translation_suffix` (blog mode only)
  - `canonical_id` used for hashing and diffing
  - `page_style` (`flat_md` or `bundle_index`) for leaf pages
  - `layout_mode_resolved` (`v1` or `v2`) for audit
- Emitted event: `CONTENT_TARGET_RESOLVED` with `canonical_id` and `repo_relpath`

## Allowed paths
- src/launch/resolvers/content_paths.py
- src/launch/resolvers/slugify.py
- src/launch/schemas/content_path.schema.json
- tests/unit/resolvers/test_tc_540_content_paths.py
- reports/agents/**/TC-540/**
## Mapping rules (binding for implementation)

### Layout Mode Resolution (MUST)
Before path construction, resolve the effective layout mode:
1. If `layout_mode == "v1"`: use V1 rules
2. If `layout_mode == "v2"`: use V2 rules (requires `target_platform`)
3. If `layout_mode == "auto"`: detect V2 by checking filesystem:
   - For non-blog: check if `content/<subdomain>/<family>/<lang>/<platform>/` exists
   - For blog: check if `content/<subdomain>/<family>/<platform>/` exists
   - If exists: use V2, else use V1

Record resolved mode per section in `ContentTarget.layout_mode_resolved`.

### A) Base folder
- `content_root = "content/<subdomain>/<family>"`

### B.1) V1 Non-blog subdomains (directory i18n, NO platform)
- Language is a folder:
  - `lang_root = "<content_root>/<lang>"`
- `family_index`: `"<lang_root>/_index.md"`
- `section_index`: `"<lang_root>/<section_path...>/_index.md"`
- `page`: `"<lang_root>/<section_path...>/<slug>.md"`

### B.2) V2 Non-blog subdomains (directory i18n WITH platform)
- Language and platform are folders:
  - `platform_root = "<content_root>/{locale}/{platform}"`
- **HARD REQUIREMENT**: Products MUST use `/{locale}/{platform}/` (NOT `/{platform}/` alone)
- `family_index`: `"<platform_root>/_index.md"`
- `section_index`: `"<platform_root>/<section_path...>/_index.md"`
- `page`: `"<platform_root>/<section_path...>/<slug>.md"`

### C.1) V1 Blog subdomain (file i18n, NO platform)
- No language folder, no platform folder.
- Filenames use suffix for non-English:
  - English: `<name>.md` (no suffix)
  - Non-English: `<name>.<lang>.md`
- `family_index`:
  - English: `"<content_root>/_index.md"`
  - Non-English: `"<content_root>/_index.<lang>.md"`
- `section_index`:
  - English: `"<content_root>/<section_path...>/_index.md"`
  - Non-English: `"<content_root>/<section_path...>/_index.<lang>.md"`
- `page`:
  - English: `"<content_root>/<section_path...>/<slug>.md"`
  - Non-English: `"<content_root>/<section_path...>/<slug>.<lang>.md"`

### C.2) V2 Blog subdomain (file i18n WITH platform)
- Platform is a folder, locale remains filename-based:
  - `platform_root = "<content_root>/<platform>"`
- Filenames use suffix for non-English (same as V1):
  - English: `<name>.md` (no suffix)
  - Non-English: `<name>.<lang>.md`
- `family_index`:
  - English: `"<platform_root>/_index.md"`
  - Non-English: `"<platform_root>/_index.<lang>.md"`
- `section_index`:
  - English: `"<platform_root>/<section_path...>/_index.md"`
  - Non-English: `"<platform_root>/<section_path...>/_index.<lang>.md"`
- `page`:
  - English: `"<platform_root>/<section_path...>/<slug>.md"`
  - Non-English: `"<platform_root>/<section_path...>/<slug>.<lang>.md"`

### D) Page style (flat_md vs bundle_index)
The resolver MUST support two leaf page styles:
- `flat_md`: `<slug>.md` (file directly in section folder)
- `bundle_index`: `<slug>/index.md` (page bundle with index file)

**Style detection** (binding per specs/22):
- Sample the first 50 sibling pages under the section root
- Determine dominant style (>= 70% threshold)
- Use dominant style for all new pages in that section

**Section indexes are always `_index.md`:**
- `_index.md` is a section list page (has children)
- `index.md` is a leaf bundle page (no children)
- These are distinct Hugo concepts and must not be confused

Record `page_style` in ContentTarget for audit.

### E) Safety and normalization
- `subdomain`, `family`, `lang`, `section_path`, `slug` must be normalized to safe path components:
  - spaces to hyphens
  - remove characters outside `[a-z0-9-_.]`
- Reject any component containing `/`, `\`, or `..`
- Resolver must be pure and deterministic.

## Implementation steps
1) Create `ContentTarget` dataclass with canonical fields and stable `canonical_id`.
2) Implement `normalize_component()` and `slugify()` helpers.
3) Implement `resolve_content_path()` following Mapping rules A–D.
4) Add unit tests:
   - non-blog: docs/products/kb/reference patterns
   - blog: suffix behavior for `en` and `fr`
   - section nesting, empty section list
   - traversal attempts rejected
5) Integrate call sites:
   - W4 produces targets only via this resolver
   - W5/W6 accept `ContentTarget` instead of free-form paths

## E2E verification
**Concrete command(s) to run:**
```bash
python -c "from launch.resolvers.content_paths import resolve_content_path; print(resolve_content_path('docs', 'cells', 'en', 'python', 'v2'))"
```

**Expected artifacts:**
- src/launch/resolvers/content_paths.py

**Success criteria:**
- [ ] V1 paths resolve correctly
- [ ] V2 paths include platform segment
- [ ] Products use /{locale}/{platform}/

> If E2E harness not yet implemented, this defines the stub contract for TC-520/522/523.

## Integration boundary proven
What upstream/downstream wiring was validated:
- Upstream: TC-404 (site_context with layout_mode)
- Downstream: TC-450 (patcher uses resolved paths)
- Contracts: specs/32_platform_aware_content_layout.md path rules

## Failure modes

### Failure mode 1: Layout mode auto-detection chooses wrong version (V1 vs V2)
**Detection:** Resolver generates path with missing or extra platform segment; W5 writes to wrong location causing duplicate content or 404s
**Resolution:** Check filesystem detection logic in resolve_content_path(); verify content/<subdomain>/<family>/<lang>/<platform>/ directory existence check; review run_config.layout_mode override if needed
**Spec/Gate:** specs/32_platform_aware_content_layout.md (V2 layout rules), specs/18_site_repo_layout.md (V1 layout rules)

### Failure mode 2: Blog locale suffix applied to non-blog subdomain or vice versa
**Detection:** Generated path has incorrect i18n format (e.g., cells.fr.md under docs instead of /fr/ folder, or /fr/ folder under blog instead of .fr.md suffix)
**Resolution:** Review subdomain detection logic; ensure blog.aspose.org uses filename-based i18n (_index.fr.md) while all other subdomains use directory-based i18n (/fr/_index.md); check mapping rules B vs C in taskcard
**Spec/Gate:** specs/18_site_repo_layout.md (blog localization rules), specs/32_platform_aware_content_layout.md (directory i18n)

### Failure mode 3: Section index uses index.md instead of _index.md
**Detection:** Hugo fails to render section list; page bundle created instead of section; navigation hierarchy breaks
**Resolution:** Review page_kind logic in resolve_content_path(); ensure section_index always produces _index.md (section list page) and page with bundle_index style produces <slug>/index.md (leaf bundle page); these are distinct Hugo concepts
**Spec/Gate:** specs/18_site_repo_layout.md (Hugo page types), specs/22_navigation_and_existing_content_update.md (section vs bundle distinction)

### Failure mode 4: V2 product path uses {platform} without {locale} segment
**Detection:** Generated path is content/docs/cells/python/_index.md instead of content/docs/cells/en/python/_index.md; fails V2 hard requirement
**Resolution:** Review V2 non-blog mapping rule B.2; ensure platform_root construction includes both {locale} and {platform} segments in correct order; products MUST use /{locale}/{platform}/ (NOT /{platform}/ alone)
**Spec/Gate:** specs/32_platform_aware_content_layout.md (V2 binding contract line ~45-50)

## Task-specific review checklist
Beyond the standard acceptance checks, verify:
- [ ] All outputs are written atomically per specs/10_determinism_and_caching.md
- [ ] No manual content edits made (compliance with no_manual_content_edits policy)
- [ ] Determinism verified by running task twice and comparing artifacts byte-for-byte
- [ ] All spec references listed in taskcard were consulted during implementation
- [ ] Evidence files (report.md, self_review.md) include all required sections and command outputs
- [ ] No placeholder values (PIN_ME, TODO, FIXME, etc.) remain in production code paths

## Deliverables
- Code: resolver + helpers
- Tests: `test_content_paths.py` (parametrized)
- Report: `reports/agents/<agent>/TC-540/report.md`
- Self review: `reports/agents/<agent>/TC-540/self_review.md`

## Acceptance checks
- [ ] 100% of tests pass
- [ ] V1 layout: Blog mapping matches suffix rules exactly (no platform)
- [ ] V1 layout: Directory i18n mapping matches folder rules exactly (no platform)
- [ ] V2 layout: Platform segment included for all sections
- [ ] V2 layout: Products use `/{lang}/{platform}/` (NOT `/{platform}/` alone)
- [ ] V2 layout: Blog uses `/{platform}/` with filename-based locale
- [ ] Auto-detection correctly chooses V1 vs V2 based on filesystem
- [ ] Traversal and invalid components are rejected
- [ ] Same inputs always yield identical `repo_relpath` bytes
- [ ] `layout_mode_resolved` recorded in ContentTarget
- [ ] Page style detection works for flat_md (`<slug>.md`)
- [ ] Page style detection works for bundle_index (`<slug>/index.md`)
- [ ] Section indexes always use `_index.md` (never `index.md`)
- [ ] `page_style` recorded in ContentTarget for leaf pages

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
