# Frontmatter Contract (authoritative)

This system cannot rely on a hand-written, site-specific frontmatter list.
Instead, it MUST build a deterministic "FrontmatterContract" from the target Hugo site repo during input cloning.

## Why
- Different Hugo sites (and even different sections) require different keys.
- Layouts and existing content may enforce required params (title, description, menu, etc).
- If this is not discovered and validated, writers will hallucinate keys and validation will be unstable.

## Artifact
During CLONED_INPUTS (or INGESTED for site), produce:

- runs/<run_id>/artifacts/frontmatter_contract.json
- Validate against: specs/schemas/frontmatter_contract.schema.json

## Deterministic discovery algorithm (site repo)
For each section in run_config.section_roots:

1) Sample selection (deterministic)
- Enumerate all .md files under the section root (excluding vendor, node_modules, public, resources).
- Sort lexicographically by path.
- Take the first N files (default N=50, configurable but pinned).

2) Parse YAML/TOML/JSON frontmatter
- If frontmatter parse fails: record an Issue (gate=frontmatter_schema, severity=error) and continue.

3) Determine keys
- required_keys = intersection of keys across the sampled set (excluding obviously variable keys like "date" unless present in >= 90% of samples)
- optional_keys = union(keys) - required_keys

4) Infer types (best-effort, stable)
- string, integer, number, boolean, date (ISO-like), array_string, object
- If mixed types appear for a key, type becomes "unknown" and validation only checks presence (not type).

5) Defaults (optional)
- If a key has the same value in >= 90% of samples, set it as default_value.

## How writers must use it
- For any new page, writers MUST emit frontmatter that:
  - includes all required_keys for that section
  - uses default_value when present (unless overridden by page plan)
  - avoids introducing unknown keys unless explicitly allowed by ruleset

## Gate behavior
- The frontmatter gate validates all created/modified pages against frontmatter_contract.json.
- Missing required keys is a blocker.
- Type mismatches are errors (unless contract type is "unknown").
