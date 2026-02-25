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

---

## Per-Page Input Hash (W5)

**Status**: Binding (TC-2450)
**Implementation**: `src/launch/workers/_shared/worker_cache.py`
**Full specification**: `specs/47_worker_cache_and_incremental_execution.md`

### Purpose

W5 SectionWriter computes a **per-page input hash** before each LLM generation call,
allowing identical-input pages to be skipped on incremental re-runs. This is
**page-level caching** as opposed to the **worker-level** skip provided by `launch resume`.

### Hash Contract

```
input_hash = SHA256(json.dumps(spec_fields, sort_keys=True))
```

Where `spec_fields` includes:
- `slug`, `section`, `page_role`, `title`, `purpose`
- `sorted(required_claim_ids)`, sorted resolved claim text
- `sorted(required_snippet_tags)`, sorted resolved snippet code + description
- `sorted(required_headings)`, `template_variant`

**Key rules**:
1. Hash is computed BEFORE the LLM call using only deterministic inputs
2. Hash is stored AFTER successful generation (`record_page()`)
3. A **failed generation** is NEVER cached — partial output cannot produce a valid cache entry
4. Skipped pages (`cache_hit` or `preserved`) get `duration_ms=0` in draft_manifest

### Cache Hit Contract

A cache hit requires **both**:
1. Stored `input_hash` matches computed hash for the current page spec, AND
2. The cached `draft_path` file **still exists**

Empty stored hash (`""`) → skip hash validation (backward-compat for pre-2.0 cache entries).

### Activation

Page-level caching is **opt-in** and disabled for all pilots:

```yaml
# run_config.yaml — enable page-level cache
caching:
  enabled: true
```

When `caching.enabled=false` (default), all cache operations are no-ops and determinism
is unaffected — W5 always generates every page.

### Relationship to Worker-Level Resume

| Mechanism | Granularity | Description |
|-----------|-------------|-------------|
| `launch resume --from-worker W5` | Worker-level | Skip W1–W4 entirely |
| `caching.enabled: true` | Page-level | Skip individual pages with matching input hash |
| `regen_failed_only: true` | Page-level (failures) | Only regenerate pages with gate failures |

Combining `launch resume --from-worker W5` + `regen_failed_only: true` provides the
most targeted re-run: skip W1–W4, then within W5 regenerate only the failing pages.
