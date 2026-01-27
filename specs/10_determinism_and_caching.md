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

### Byte-Identical Acceptance Criteria (REQ-079)

**Artifacts Subject to Byte-Identity Requirement**:
- `page_plan.json`
- `patch_bundle.json`
- All `*.md` files under `RUN_DIR/work/site/` (drafts)
- All `*.json` files under `RUN_DIR/artifacts/` except `events.ndjson`

**Allowed Variance**:
- `events.ndjson`: Timestamps (`ts` field) and event IDs (`event_id` field) may vary
- All other artifacts: **NO variance allowed**

**Clarifications**:
1. **Timestamps**: Artifacts MUST NOT include timestamps except in `events.ndjson`
2. **UUIDs**: UUID/event_id generation acceptable variance ONLY in `events.ndjson`
3. **Line Endings**: Line endings MUST be normalized to LF (`\n`) before byte comparison
4. **Whitespace**: Trailing whitespace MUST be stripped before comparison

**Determinism Harness Validation (TC-560)**:
1. Run pipeline twice with identical inputs
2. Normalize line endings to LF for all artifacts
3. Strip trailing whitespace from all text files
4. Exclude `events.ndjson` from comparison
5. Compare all other artifacts byte-for-byte using sha256 hashes
6. Test passes if all hashes match

### Prompt Versioning for Determinism

**Requirement**: All LLM-based features MUST version prompts to ensure determinism (REQ-079).

**Implementation**:
1. **Prompt Hash**: Compute sha256 hash of full prompt template (including system message, user message, and all placeholders)
2. **Prompt Version Field**: Include `prompt_version` (hash) in telemetry for every LLM call
3. **Determinism Validation**: TC-560 harness compares prompt versions across runs
   - If prompt_version differs → determinism cannot be guaranteed
   - If prompt_version matches + temperature=0.0 → determinism expected

**Affected Features**:
- FEAT-012 (Product Facts Extraction): LLM-based
- FEAT-034 (Template Rendering): LLM-based drafting
- FEAT-041/042 (Conflict Resolution): LLM-based fixer
- All workers using LLM calls

**Template Versioning Enforcement**:
- `ruleset_version` (from run_config) controls ruleset templates
- `templates_version` (from run_config) controls section templates
- Both must be pinned per run (Guarantee K)
- Prompt templates MUST reference these versions

**Acceptance Criteria** (TC-560):
- Two runs with same inputs produce same `prompt_version` for all LLM calls
- Prompt templates include version placeholders: `{{ruleset_version}}`, `{{templates_version}}`
