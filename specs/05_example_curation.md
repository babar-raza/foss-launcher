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
- scan examples/, samples/, docs/ code blocks
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

1) Dedicated example folders (`examples/`, `samples/`, `demo/`)
2) README code fences (Quick Start blocks are usually the best)
3) Docs markdown code fences (including root-level implementation notes)
4) Tests (treat as example candidates; prefer tests that look like “usage”)
5) Generated minimal snippets (only when 1-4 yield nothing for a required workflow)

### Example generation policy (binding)
Generated snippets are allowed only when:
- the PagePlan requires a workflow and no repo-backed snippet exists, AND
- the adapter can identify a public entrypoint (package/module/class/function) to demonstrate.

Generated snippet requirements:
- Must be minimal (hello-world / load-save / simplest successful call)
- Must be validated at least for syntax (and ideally with a dry-run import)
- Must include internal provenance: prompt hash + “generated” flag in SnippetCatalog


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
