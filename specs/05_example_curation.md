# Example Curation and Snippet Catalog

## Goal
Maximize use of real repo examples and make code reusable across sections.

## SnippetCatalog (snippet_catalog.json)
Each snippet must have:
- snippet_id (stable hash of normalized code + language)
- language (python, csharp, js, etc)
- tags (quickstart, convert, merge, extract, parse, render, etc)
- source:
  - type: repo_file | generated
  - path and line ranges (if repo_file)
  - generation_prompt_hash (if generated)
- requirements:
  - dependencies
  - runtime notes
- validation:
  - syntax_ok: true/false
  - runnable_ok: true/false/unknown
  - validation_log_path

## Curation steps
1) Discover candidate examples
- Scan standard example directories (see "Configurable example discovery directories" below) and docs/ code blocks
- Additionally scan ALL directories listed in `run_config.ingestion.example_directories` (if configured)
- extract minimal runnable segments if possible
- store provenance and line ranges

2) Normalize
- standardize imports, minimal boilerplate, consistent formatting
- ensure snippet is standalone where feasible

3) Tagging
- Apply deterministic tags:
  - based on folder name, file name, and doc headings
  - stable ordering and no duplicates

4) Validation
- Minimum: syntax validation for the language
- Optional: runnable validation in container if dependencies are discoverable

**Syntax validation failure handling (binding)**:
On syntax validation failure:
1. Mark snippet with `validation.syntax_ok=false`
2. Write validation error output to `validation_log_path`
3. Do NOT include snippet in catalog if `forbid_invalid_snippets=true` in ruleset
4. If `forbid_invalid_snippets=false`, include snippet with clear warning annotation
5. Emit telemetry event `SNIPPET_SYNTAX_INVALID` with snippet_id and error details

## Usage policy
- Writers must prioritize snippet_catalog items with source=repo_file.
- generated snippets allowed only if no repo snippets exist for that tag.
- generated snippets must be labeled internally and validated.

## Acceptance
- snippet_catalog.json validates schema
- At least one quickstart snippet exists (repo_file preferred)
- For each planned workflow in ProductFacts, at least one snippet is mapped or explicitly missing.

## Universal Example Strategy

### Example discovery order (binding)
Snippet extraction MUST follow a stable priority order:

1) Dedicated example folders: standard directories (`examples/`, `samples/`, `demo/`) PLUS any additional directories from `run_config.ingestion.example_directories` (see "Configurable example discovery directories" below)
2) README code fences (Quick Start blocks are usually the best)
3) Docs markdown code fences (including root-level implementation notes)
4) Tests (treat as example candidates; prefer tests that look like "usage")
5) Source code inline examples (docstrings, comments with usage patterns)
6) Generated minimal snippets (only when 1-5 yield nothing for a required workflow)

### Configurable example discovery directories (TC-1020)

The standard example directory list (`examples/`, `samples/`, `demo/`) MAY be extended via `run_config.ingestion.example_directories`:

```yaml
# run_config example
ingestion:
  example_directories:
    # These are IN ADDITION to the standard dirs (examples/, samples/, demo/)
    - "tutorials/"
    - "cookbook/"
    - "notebooks/"
    - "snippets/"
    - "quickstart/"
    - "use-cases/"
```

**Defaults:** If `run_config.ingestion.example_directories` is absent or empty, W3 MUST scan only the standard directories (`examples/`, `samples/`, `demo/`). This ensures backward compatibility with existing pilots.

**Merging behavior:** The configured list is UNIONED with the standard directories. Duplicates are removed. The final list is sorted alphabetically for determinism.

### Example generation policy (binding)
Generated snippets are allowed only when:
- the PagePlan requires a workflow and no repo-backed snippet exists, AND
- the adapter can identify a public entrypoint (package/module/class/function) to demonstrate.

PagePlanner MUST NOT generate snippets unless `allow_generated_snippets=true` in run_config.

Generated snippet requirements:
- MUST be minimal (hello-world / load-save / simplest successful call)
- MUST be validated at least for syntax (and ideally with a dry-run import)
- MUST include internal provenance: prompt hash + "generated" flag in SnippetCatalog


### Language detection and unknown files (TC-1020)

Language-based filtering MUST NOT exclude files from snippet discovery. Specifically:

- Files with recognized language extensions (`.py`, `.cs`, `.js`, `.java`, `.go`, `.rs`, etc.) MUST be tagged with the detected language.
- Files with unrecognized or missing extensions MUST still be recorded in the snippet candidate pool with `language: "unknown"`. They MUST NOT be silently dropped.
- Language detection failure MUST NOT prevent a file from being indexed as a snippet candidate. W3 MAY assign lower priority to `language: "unknown"` snippets, but MUST NOT exclude them.
- When `language: "unknown"`, syntax validation MAY be skipped (mark `validation.syntax_ok: null`) but the snippet MUST still appear in the catalog if it contains code-like content.

### Binary assets and sample files (universal)
If the repo includes binary sample files (e.g., `.one`, `.pdf`, images, archives):
- Snippet extraction MUST NOT read/parse binary payloads.
- Snippets may reference sample file paths (e.g., `testfiles/SimpleTable.one`) but must not embed binary contents.
- Prefer small text fixtures when available.

### Path verification (universal)
If docs mention an `examples/` path or sample location:
- The system MUST verify the path exists in the repo inventory before treating it as an example root.

### Mapping to launch tiers
- **minimal**: at least 1 quickstart snippet (repo-backed if available)
- **standard**: quickstart + 2–4 workflow snippets
- **rich**: quickstart + workflow snippets covering every claim_group where feasible
