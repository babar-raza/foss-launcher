# Hugo Config Awareness (planning + validation)

## Purpose
Hugo configs decide **what is built** and **how** it is built. If the system ignores configs,
agents may generate content for a site/family that is not part of the build matrix, causing failed builds or silent omissions.

This spec makes the system Hugo-config aware in a deterministic, auditable way.

---

## Source of truth (binding)
At runtime, the system MUST read configs from the cloned **site repo**:

- `RUN_DIR/work/site/configs/`

The snapshot under:
- `specs/reference/hugo-configs/configs/`
is **reference-only** (used for tests and spec review). It MUST NOT replace runtime scanning.

---

## Deterministic config discovery (binding)

### Step 1: Enumerate
Scan `RUN_DIR/work/site/configs/` recursively and include files with extensions:
- `.toml`, `.yml`, `.yaml`

Sort deterministically by:
1) normalized path (POSIX separators, lowercase for sorting only)
2) then original path (tie-breaker)

### Step 2: Fingerprint
For each config file, record:
- `path` (relative to site repo root, using `/`)
- `sha256` (bytes hash)
- `bytes`
- `ext`

Write results into:
- `RUN_DIR/artifacts/site_context.json` under `hugo.config_files[]`

---

## Build matrix inference (binding)

### File patterns
Given the `aspose.org` repo, configs commonly appear as:
- `configs/common.toml` (global)
- `configs/<subdomain>.aspose.org.yml` (site-wide)
- `configs/<subdomain>.aspose.org/<name>.toml` (subdomain-scoped, often per-family)

### Family config candidates (heuristic, binding)
For each file matching:
- `configs/<subdomain>.aspose.org/<name>.toml`

Treat `<name>` as a **family candidate** unless `<name>` is in the ignore set:
- `home`, `page`, `common`

The inferred build matrix is:

`build_matrix = [{ subdomain, family, config_path }]`

Where:
- `subdomain` is one of: `products.aspose.org`, `docs.aspose.org`, `kb.aspose.org`, `reference.aspose.org`
- `family` is the `<name>` derived from the toml filename
- `config_path` is the matched file path

**Blog special-case (binding):**
If `configs/blog.aspose.org.yml|yaml|toml` exists, then `blog.aspose.org` is considered enabled.
Blog family enablement is determined by content scanning (see `specs/18_site_repo_layout.md`).

Record this into:
- `site_context.hugo.build_matrix[]`

---


## Normalized Hugo facts artifact (binding)

In addition to `site_context.json` (schema: `site_context.schema.json`), the system MUST write a normalized
Hugo facts artifact that planners and validators can consume without re-parsing TOML/YAML/JSON/Hugo modules.

**Artifact:** `RUN_DIR/artifacts/hugo_facts.json`

- schema: `specs/schemas/hugo_facts.schema.json`
- MUST be deterministic (stable ordering, stable JSON formatting).
- MUST be derived only from the discovered config sources under `RUN_DIR/work/site/configs/`.

**Minimum facts (binding):**
- languages: array of enabled language codes
- default_language: the default content language (from `defaultContentLanguage` key, default "en")
- default_language_in_subdir: boolean indicating if default language uses subdir URLs (from `defaultContentLanguageInSubdir` key, default false)
- permalinks map: custom permalink patterns by section
- outputs map: output format configuration
- taxonomies map: taxonomy definitions
- source_files list: relative paths under the config root used to compute these facts

**URL mapping fields (binding for TC-540 and TC-430):**
- `default_language` is required for URL path computation (dropping locale prefix for default language)
- `default_language_in_subdir` determines if ALL languages use locale prefixes in URLs
- `permalinks` may contain custom URL patterns that override default Hugo URL generation

See `specs/33_public_url_mapping.md` for the complete URL resolution contract.

## Planning constraints (binding)
The planner (W4) MUST refuse to plan pages for a `(subdomain, family)` pair that is not present in `site_context.hugo.build_matrix`,
unless the run explicitly sets `run_config.allow_inference=true` AND the section is marked optional.

Required behavior:
- If a required section cannot be planned due to missing Hugo config, open blocker issue: `HugoConfigMissing`.

---

## New validation gate: hugo_config (binding)

### Purpose
Fail fast before expensive checks when the run targets a site/family not configured for build.

### Minimum checks
1) `page_plan` targets are compatible:
   - each planned `output_path` matches the content root contract in `specs/18_site_repo_layout.md`
2) build matrix covers the planned `(subdomain, family)` for non-blog sections
3) config fingerprints exist in `site_context.json` and are non-empty

### Output
- gate name: `hugo_config`
- log file: `RUN_DIR/logs/gate_hugo_config.log`
- issues: normalized `issue.schema.json`

---

## Acceptance
- The run captures config fingerprints and build matrix in `site_context.json`.
- The run emits `hugo_facts.json` for deterministic Hugo-aware planning and validation.
- The planner does not generate content that Hugo will not build.
- The validator fails early with clear actionable issues when configs do not match the plan.
