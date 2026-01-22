# Determinism and Caching

## Determinism strategy
Hard controls:
- temperature: 0.0
- fixed decoding params
- stable prompts and prompt hashing
- schema-validated structured outputs
- stable ordering everywhere
- content hashing and caching

Soft controls:
- Two pass generation: plan first, fill second
- Minimize creative variance using templates

## Hashes
inputs_hash must include:
- github_repo_url + github_ref
- site_repo_url + site_ref
- templates_version
- ruleset_version
- launch_config content
- orchestrator version

prompt_hash must include:
- full prompt text
- schema reference id/version
- worker name and version

## Cache keys
cache_key = sha256(model_id + "|" + prompt_hash + "|" + inputs_hash)

## What to cache
- structured JSON outputs per worker
- snippet extraction results
- page plan
- drafts (only if deterministic markers match)

## Stable ordering rules
- Sort all lists deterministically:
  - paths lexicographically
  - sections in config order
  - pages by `(section_order, output_path)`
  - issues by `(severity_rank, gate, location.path, location.line, issue_id)`
  - claims by `claim_id`
  - snippets by `(language, tag, snippet_id)`

**Severity rank (binding):** `blocker` > `error` > `warn` > `info`.

## Acceptance
- Repeat run with the same inputs produces **byte-identical** artifacts (PagePlan, PatchBundle, drafts, reports).
- The only allowed run-to-run variance is inside the local event stream (`events.ndjson`) where `ts`/`event_id` values differ.
