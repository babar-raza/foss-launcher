---
id: TC-540
title: "Content Path Resolver (Hugo content layout + blog localization rules)"
status: Ready
owner: "unassigned"
updated: "2026-01-22"
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
---

# Taskcard TC-540 — Content Path Resolver (Hugo content layout + blog localization rules)

## Objective
Implement a deterministic **Content Path Resolver** that maps a target (subdomain, family, language, platform, page kind, slug, section path) to an exact Markdown file path in the aspose.org content repo.

This resolver MUST support both V1 (legacy, no platform segment) and V2 (platform-aware) layouts with deterministic auto-detection.

W4–W6 must call this resolver for every content read/write so the system never guesses where pages live.

## Required spec references
- specs/18_site_repo_layout.md
- specs/32_platform_aware_content_layout.md (V2 layout binding contract)
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
  - `platform_root = "<content_root>/<lang>/<platform>"`
- **HARD REQUIREMENT**: Products MUST use `/<lang>/<platform>/` (NOT `/<platform>/` alone)
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

### D) Safety and normalization
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

## Self-review
Use `reports/templates/self_review_12d.md`. Any dimension <4 must include a concrete fix plan.
