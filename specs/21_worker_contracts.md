# Worker Contracts (I/O, determinism, and handoffs)

## Purpose
Workers must be executable without guessing:
- what to read
- what to write
- what decisions they are allowed to make
- how they hand off to the next step

This document defines the minimum worker set and the binding artifact contracts.
Coordination and decision loops are defined in `specs/28_coordination_and_handoffs.md`.

## Global worker rules (binding)
- Workers MUST only read declared inputs.
- Workers MUST only write declared outputs.
- Workers MUST be idempotent: re-running with the same inputs MUST reproduce the same outputs.
- Every JSON artifact output MUST validate against its schema under `specs/schemas/`.
- If an input artifact is missing, the worker MUST fail with a **blocker** issue (`issue.schema.json`).
- All ordering MUST follow `specs/10_determinism_and_caching.md`.

## Common conventions

### Paths (authoritative)
All workers operate inside a run folder:

- `RUN_DIR = runs/<run_id>/`

- `runs/<run_id>/artifacts/` — JSON artifacts (schema-validated)
- `runs/<run_id>/drafts/<section>/` — draft Markdown (writer-only)
- `runs/<run_id>/reports/` — human-readable reports (optional)
- `runs/<run_id>/events.ndjson` — local event log (append-only)

### Required events (per worker run)
Each worker execution MUST emit:
- `WORK_ITEM_STARTED`
- `WORK_ITEM_FINISHED` or `WORK_ITEM_FAILED`

Each artifact write MUST emit:
- `ARTIFACT_WRITTEN` with `{ name, path, sha256, schema_id }`

If a worker opens or resolves issues:
- `ISSUE_OPENED` / `ISSUE_RESOLVED`

### Failure handling (binding)
- If a worker fails due to a retryable external error (network, 429, timeout), it MUST return a normalized retryable error.
- The Orchestrator decides retries and attempts (workers do not self-retry except for short internal retries like HTTP idempotent POST).
- Workers MUST never partially write an output artifact. Write to a temp file and atomically rename.

### Telemetry Requirements for LLM-Using Workers (binding)

Every worker that makes LLM calls (W2 FactsBuilder, W5 SectionWriter) MUST integrate with the telemetry system as specified in `specs/16_local_telemetry_api.md` and `specs/11_state_and_events.md`.

#### Required Context Propagation

Workers MUST accept telemetry context via `run_config`:
- `_telemetry_client`: Optional[TelemetryClient] instance (None = no telemetry)
- `_telemetry_trace_id`: String (trace ID for correlation)
- `_telemetry_parent_span_id`: String (parent span ID for hierarchical tracking)

Note: Keys prefixed with `_` are internal context fields, not user-facing configuration.

#### LLMProviderClient Initialization

When creating LLMProviderClient, workers MUST pass telemetry context:

```python
llm_client = LLMProviderClient(
    api_base_url=api_base_url,
    model=model,
    run_dir=run_dir,
    # Telemetry context (all optional)
    telemetry_client=run_config.get("_telemetry_client"),
    telemetry_run_id=run_id,
    telemetry_trace_id=run_config.get("_telemetry_trace_id", generate_trace_id()),
    telemetry_parent_span_id=run_config.get("_telemetry_parent_span_id", "root"),
)
```

#### Telemetry Client Initialization (Fallback)

If `_telemetry_client` is not provided in run_config and not in offline mode, workers MAY initialize their own TelemetryClient:

```python
telemetry_client = run_config.get("_telemetry_client")

if telemetry_client is None and not run_config.get("offline_mode", False):
    try:
        telemetry_api_url = os.environ.get("TELEMETRY_API_URL", "http://localhost:8765")
        telemetry_client = TelemetryClient(
            endpoint_url=telemetry_api_url,
            run_dir=run_dir,
            timeout=5,  # Short timeout for non-blocking
        )
    except Exception as e:
        logger.warning("telemetry_client_init_failed", error=str(e))
        # Continue without telemetry (graceful degradation)
```

#### Graceful Degradation (binding)

ALL telemetry operations MUST follow graceful degradation:
1. If `telemetry_client` is None, skip telemetry (log once at debug level, not warning)
2. If telemetry operations fail, log warnings and continue (NEVER crash)
3. Workers MUST complete successfully even if telemetry is unavailable
4. Offline mode (`run_config.offline_mode=true`) implies no telemetry

#### Event Emission

Workers making LLM calls MUST emit events to `runs/<run_id>/events.ndjson`:
- `LLM_CALL_STARTED` (before LLM API call)
- `LLM_CALL_FINISHED` (on success)
- `LLM_CALL_FAILED` (on failure)

Event emission is handled automatically by LLMProviderClient when telemetry context is provided.

#### Example: W2 FactsBuilder Integration

```python
def execute_facts_builder(run_dir: Path, run_config: Dict[str, Any]) -> Dict[str, Any]:
    # Extract telemetry context
    telemetry_client = run_config.get("_telemetry_client")
    trace_id = run_config.get("_telemetry_trace_id", generate_trace_id())
    span_id = run_config.get("_telemetry_parent_span_id", "root")

    # Initialize fallback if needed
    if telemetry_client is None and not run_config.get("offline_mode", False):
        try:
            telemetry_client = TelemetryClient(
                endpoint_url=os.environ.get("TELEMETRY_API_URL", "http://localhost:8765"),
                run_dir=run_dir,
                timeout=5,
            )
        except Exception as e:
            logger.warning("telemetry_init_failed", error=str(e))

    # Create LLM client with telemetry context
    llm_client = None
    if api_base_url and model:
        llm_client = LLMProviderClient(
            api_base_url=api_base_url,
            model=model,
            run_dir=run_dir,
            telemetry_client=telemetry_client,
            telemetry_run_id=run_id,
            telemetry_trace_id=trace_id,
            telemetry_parent_span_id=span_id,
        )

    # ... rest of worker logic ...
```

#### Acceptance Criteria for Worker Telemetry Integration

- Every LLM call from worker creates child TelemetryRun with `job_type=llm_call`
- Trace/span IDs propagate correctly from orchestrator → worker → LLM client
- Worker continues normally if telemetry unavailable
- Offline mode works without telemetry errors
- Worker tests pass with and without telemetry client

---

## Shared Module: Zone-Aware Sanitizer Model (TC-2375, RD-02)

**File**: `src/launch/workers/_shared/markdown_zones.py`

The content sanitizer (`content_sanitizer.py`) has 45+ transformation functions. Prior to TC-2375, several functions applied regex rules to ALL content including code blocks and frontmatter — causing cascading failures (a fix for prose could corrupt code).

TC-2375 introduces a zone-aware model: markdown is split into typed zones before any transformation is applied. Sanitizers that should only modify prose content are wrapped with `apply_to_prose_zones()`, which preserves `CODE_FENCE` and `FRONTMATTER` zones untouched.

### Zone Types

| Zone | Description |
|------|-------------|
| `FRONTMATTER` | YAML frontmatter between opening `---` and closing `---` |
| `CODE_FENCE` | Triple-backtick or tilde fenced code block |
| `HEADING` | Line(s) starting with `#` |
| `TABLE` | Lines containing `|` separator (≥ 2 pipes) |
| `LIST` | Lines starting with `-`, `*`, `+`, or `N.` |
| `PROSE` | All other content (including blank lines) |

### API

- `parse_zones(text: str) -> List[Zone]`: Split markdown into Zone objects
- `render_zones(zones: List[Zone]) -> str`: Concatenate zones back to string
- `apply_to_prose_zones(fn, content: str) -> str`: Apply sanitizer to non-protected zones only
- **Round-trip invariant**: `render_zones(parse_zones(text)) == text` for any input

### Protected Zones

`FRONTMATTER` and `CODE_FENCE` zones are **never** passed to prose sanitizers. All other zones are passed through.

### Wrapped Sanitizers (initial pass)

Five sanitizers in `run_pipeline()` are wrapped with `apply_to_prose_zones()`:
`strip_inline_seo_keywords`, `strip_double_periods`, `strip_emojis`,
`normalize_module_names`, `strip_boilerplate_sentences`.

Additional sanitizers may be wrapped in future passes without changing `run_pipeline()`'s public signature.

### Shared.1 Fence Parser Contract (TC-2378, binding)

> All sanitizer functions that track code-fence state MUST use an integer depth counter (not a boolean toggle).
>
> - The counter increments when a stripped line starts with ` ``` ` or `~~~` and depth is 0.
> - The counter decrements when a stripped line starts with ` ``` ` or `~~~` and depth is > 0.
> - Depth clamps to 0 (never goes negative). `in_fence` is derived as `depth > 0`.
> - **Idempotency contract**: `f(f(x)) == f(x)` is a hard requirement on all sanitizer functions.
>
> The canonical implementation is `_FenceState` in `content_sanitizer.py`. All 14 historic
> `in_fence = not in_fence` toggle sites have been replaced (TC-2378).

---

## Workers

### W1: RepoScout
**Goal:** clone and fingerprint the GitHub repo and the target site repo, then build `repo_inventory.json` and `frontmatter_contract.json` (site discovery).

**Inputs**
- `RUN_DIR/run_config.yaml` (or JSON equivalent; validated against `run_config.schema.json`)

**Outputs**
- `RUN_DIR/artifacts/repo_inventory.json` (schema: `repo_inventory.schema.json`)
- `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
- `RUN_DIR/artifacts/site_context.json` (schema: `site_context.schema.json`)
- `RUN_DIR/artifacts/hugo_facts.json` (schema: `hugo_facts.schema.json`)

**Binding requirements**
- MUST perform **exhaustive file inventory** (TC-1020, see `specs/02_repo_ingestion.md`):
  - MUST record ALL files in `repo_inventory.paths[]` regardless of file extension
  - MUST NOT apply extension-based filters that exclude files from the inventory
  - Extension heuristics MAY be used as scoring boosts for downstream prioritization
  - Binary files MUST be recorded in inventory with `binary: true` flag
  - Files with unknown or missing extensions MUST be recorded with `extension: ""` or `extension: null`
  - MUST support configurable scan directories via `run_config.ingestion.scan_directories` (default: repo root)
  - MUST support `.gitignore`-aware scanning via `run_config.ingestion.gitignore_mode` (default: `respect`)
  - MUST exclude `.pdf` files from `discovered_docs.json` (binary spec docs produce extraction noise)
  - MUST support configurable exclude patterns via `run_config.ingestion.exclude_patterns` for doc and example discovery
- MUST record resolved SHAs:
  - `repo_inventory.repo_sha` (for github_repo_url + github_ref)
  - `repo_inventory.site_sha` (for site_repo_url + site_ref)

- MUST clone workflows repo (see `specs/30_site_and_workflow_repos.md`) into `RUN_DIR/work/workflows/` and record resolved SHA:
  - `site_context.workflows.resolved_sha`
- MUST scan Hugo configs under `RUN_DIR/work/site/configs/` and record:
  - `site_context.hugo.config_files` + `site_context.hugo.build_matrix` (see `specs/31_hugo_config_awareness.md`)
  - `RUN_DIR/artifacts/hugo_facts.json` (normalized facts; schema: `hugo_facts.schema.json`)
- FrontmatterContract discovery (binding):
  - MUST follow `specs/examples/frontmatter_models.md` deterministic discovery algorithm.
  - Sampling MUST be deterministic (sorted paths, fixed N, pinned in config or run_config).
  - Output MUST be written before planning begins.
- MUST compute `repo_profile`:
  - language/platform hints (e.g., python/.NET/node/java)
  - doc roots, example roots, test roots, source roots
  - adapter_id (selected per `specs/26_repo_adapters_and_variability.md`)
- MUST record file tree fingerprints deterministically (stable ordering + stable hashing).

**Edge cases and failure modes** (binding):
- **Empty repository**: If cloned repo contains no files (zero file tree entries), emit telemetry `REPO_SCOUT_EMPTY_REPO`, proceed with minimal repo_inventory (only repo_url and repo_sha), open MAJOR issue with error_code `REPO_SCOUT_EMPTY_REPOSITORY`
- **No README found**: If no README file exists, emit telemetry `REPO_SCOUT_NO_README`, set `repo_inventory.readme_path` to null, proceed (not a blocker)
- **No documentation discovered**: If doc_roots is empty, emit telemetry `REPO_SCOUT_NO_DOCS`, proceed with empty doc_roots array
- **No tests discovered**: If test_roots is empty, emit telemetry `REPO_SCOUT_NO_TESTS`, set repository_health.tests_present=false
- **No examples discovered**: If example_roots is empty, emit telemetry `REPO_SCOUT_NO_EXAMPLES`, proceed (tests may be used as example candidates downstream)
- **Clone failure**: If git clone fails, emit error_code `REPO_SCOUT_CLONE_FAILED`, mark as retryable if network error (429, timeout, connection reset), otherwise fail with BLOCKER issue
- **Site repo clone failure**: If site repo clone fails, emit error_code `REPO_SCOUT_SITE_CLONE_FAILED`, mark as retryable if network error, otherwise fail with BLOCKER issue
- **Adapter selection failure**: If no adapter matches repo profile, emit error_code `REPO_SCOUT_NO_ADAPTER`, fall back to `universal` adapter (see specs/26_repo_adapters_and_variability.md)
- **Telemetry events**: MUST emit `REPO_SCOUT_STARTED`, `REPO_SCOUT_COMPLETED`, `ARTIFACT_WRITTEN` for each output artifact

---

### W2: FactsBuilder
**Goal:** build ProductFacts and EvidenceMap with stable claim IDs, including code analysis, workflow enrichment, and optional semantic claim enrichment.

**Sub-tasks** (TC-1040):
- **Claim Extraction** (TC-411): Extract claims from documentation with evidence anchors
  - `extract_claims()`: Main extraction from documentation files
  - `extract_claims_with_llm()`: LLM-assisted extraction for complex documents
  - `extract_claims_from_code_analysis()`: Extract claims from AST-parsed code structures
- **Code Analysis** (TC-1041, TC-1042): Parse source code with AST to extract `api_surface_summary`, `code_structure`, and `positioning`
  - `analyze_repository_code()`: Entry point for repository code analysis
- **LLM Code Understanding** (TC-1410): Build deep structured understanding of codebase from source files (class profiles, core concepts, usage workflows). LLM-powered with offline AST fallback. Output: `code_understanding.json`
  - `build_code_understanding()`: Generate structured code understanding from source files
- **Structured Feature Profiles** (TC-1411): Group related claims into coherent feature descriptions with capabilities, limitations, code examples. Heuristic keyword clustering with optional LLM enrichment. Output: `feature_profiles` in `product_facts.json`
  - `build_feature_profiles()`: Build feature profiles from claims with keyword clustering
- **Workflow Enrichment** (TC-1043, TC-1044): Enrich workflows with descriptions, step ordering, complexity, and time estimates
- **Semantic Enrichment** (TC-1045, TC-1046): Use LLM to add claim metadata (audience_level, complexity, prerequisites, use_cases, target_persona). Requires AG-002 approval for production use.
  - `enrich_claims_batch()`: Batch LLM enrichment of claim metadata
- **Evidence Mapping** (TC-412): Map claims to evidence citations with source priority ranking
  - `map_evidence()`: Map claims to source file evidence with Jaccard word-overlap scoring
- **Contradiction Detection** (TC-413): Detect and resolve contradictory claims
  - `detect_all_contradictions()`: Pairwise contradiction detection with Jaccard pre-filter
- **TruthLock Compilation** (TC-413): Compile minimal truth representation
- **Round 8-10 additions** (TC-1616 through TC-1641):
  - **Claim Quality Filter** (TC-1616): Reduce key_features noise from 50% to <20% via `extract_claims()` filtering
  - **Workflow Expansion** (TC-1617): Expand workflows from 2 steps to 8-12+ steps with educational context via `llm_generate_workflow_steps()`
  - **Use Case Extraction** (TC-1618): Extract 10-15 use_case and 3-5 tutorial claims via `llm_generate_use_cases()`, `llm_generate_tutorials()`, `synthesize_use_cases_from_profiles()`
  - **Troubleshooting & FAQ** (TC-1619): Extract 15-20 troubleshooting and 10-15 faq entries via `llm_generate_faq_entries()`, `llm_generate_troubleshooting_entries()`
  - **Best Practices & Performance** (TC-1620): Add 8-12 best_practice and 3-5 performance claims via `llm_generate_best_practices()`, `llm_generate_performance_claims()`
  - **Enriched Text** (TC-1622): LLM-generated marketing-ready rewrites for key_feature claims via `enrich_claim_text_batch()`
  - **Claim Groups Extension** (TC-1632): Route new claim_kinds into 12 claim_groups (was 6) in `assemble_product_facts()`

**Inputs**
- `RUN_DIR/artifacts/repo_inventory.json`
- repo worktree (read-only)
- optional: extra evidence URLs from run_config

**Outputs**
- `RUN_DIR/artifacts/product_facts.json` (schema: `product_facts.schema.json`)
  - Includes `api_surface_summary` (class/function names extracted from code)
  - Includes `code_structure` (source roots, entrypoints, package names)
  - Includes enriched `workflows` (steps, complexity, estimated_time_minutes)
  - Includes enriched `example_inventory` (descriptions, audience_level)
  - Includes `version` extracted from manifests or source code constants
  - Includes `feature_profiles` (TC-1411): Structured feature descriptions grouping related claims with capabilities, limitations, code examples, and audience level
  - **Round 8-10 additions** (TC-1616 through TC-1641):
    - `claim_groups` dict extended from 6 to 12 keys: key_features, install_steps, workflows, format_support, limitations, api_surface, use_cases, faq, best_practices, performance, tutorials, troubleshooting
    - Claims may include `enriched_text` field (LLM-generated marketing-ready rewrite)
    - New claim_kinds: use_case, tutorial, faq, troubleshooting, best_practice, performance
  - **Round 7+ additions**:
    - `positioning.audience`: Inferred from claims and manifest
    - `positioning.who_it_is_for`: Includes "both humans and AI agents"
    - `distribution`: Array format with method/identifier/install_commands
    - `runtime_requirements`: Language versions from manifest
    - `dependencies`: Runtime dependencies from manifest
    - `license`: License info from repo_inventory
    - Feature profiles use dynamic domain-specific keywords (TF-IDF extraction when corpus ≥10)
- `RUN_DIR/artifacts/code_understanding.json` (TC-1410): Deep structured understanding of the codebase
  - Contains `class_profiles`, `core_concepts`, `usage_workflows`, `api_relationships`
  - Built via LLM when available, falls back to AST-only offline profiles
  - Consumed by W5 SectionWriter to produce grounded content with real code examples
- `RUN_DIR/artifacts/evidence_map.json` (schema: `evidence_map.schema.json`)
  - Claims MAY include enrichment metadata (audience_level, complexity, prerequisites, use_cases, target_persona)
  - **Round 7+ additions**:
    - All claims have `source_type` (100% coverage)
    - Decomposed workflow claims have `step_order` field
    - Workflows include `steps[]` arrays with step-level detail

**Binding requirements**
- MUST process **all discovered documents** without count caps (TC-1020, see `specs/03_product_facts_and_evidence.md`):
  - MUST NOT apply a maximum document count that causes documents to be skipped
  - MUST NOT apply minimum word-count filters that exclude short documents from processing
  - MUST NOT apply keyword-presence filters that exclude documents lacking specific keywords
  - Word-count and keyword heuristics MAY be used as **priority scoring** to determine processing order, but MUST NOT be used as exclusion filters
  - Evidence priority ranking (manifests > source code > tests > docs > README) is for **prioritization of conflicting claims**, NOT for filtering of evidence sources
  - All evidence sources MUST be ingested and recorded in the EvidenceMap regardless of their priority level
  - Every extracted claim MUST carry `source_relevance` (from W1 `relevance_score`) and `evidence_priority` (from W1 `evidence_priority`) to propagate source quality to downstream consumers
- Claim IDs MUST be stable:
  - `claim_id = sha256(normalized_claim_text + evidence_anchor + ruleset_version)`
- All factual statements MUST be represented as claims with evidence anchors (repo path + line range or URL + fragment).
- If `run_config.allow_inference=false`:
  - MUST NOT emit speculative claims (no "likely", "probably", "supports many formats", etc.)
  - MUST open a blocker issue `EvidenceMissing` when a required claim cannot be evidenced.

**Performance requirements** (TC-1040):
- **Code analysis**: MUST complete in < 10% of W2 total runtime (target: < 3 seconds for medium repos)
- **LLM enrichment**: MUST use caching to achieve 80%+ hit rate on second run with same repo SHA
- **LLM enrichment**: MUST NOT exceed 20% of W2 total runtime when enabled
- **Total W2 runtime**: Target < 60 seconds for medium repos (100-500 files, 100-300 claims)

**Edge cases and failure modes** (binding):
- **Zero claims extracted**: If no claims can be extracted from repo (no README, docs, or meaningful code evidence), emit telemetry `FACTS_BUILDER_ZERO_CLAIMS`, proceed with empty ProductFacts (see specs/03_product_facts_and_evidence.md Edge Case Handling), force launch_tier=minimal
- **Contradictory evidence**: If contradictions are detected, apply resolution algorithm per specs/03_product_facts_and_evidence.md, emit telemetry `FACTS_BUILDER_CONTRADICTION_DETECTED`, record in evidence_map.contradictions array
- **External URL fetch failure**: If optional external evidence URLs fail to fetch, emit telemetry `FACTS_BUILDER_EXTERNAL_FETCH_FAILED`, proceed with repo-only evidence (not a blocker)
- **Evidence extraction timeout**: If evidence extraction exceeds configured timeout, emit error_code `FACTS_BUILDER_TIMEOUT`, mark as retryable, save partial ProductFacts with note
- **Sparse claims** (< 5 claims): Emit telemetry `FACTS_BUILDER_SPARSE_CLAIMS`, force launch_tier=minimal, open MAJOR issue
- **Code analysis failure**: If all code parsing fails, emit telemetry `CODE_ANALYSIS_ALL_FAILED`, proceed with documentation-only extraction (not a blocker)
- **LLM enrichment failure**: If LLM API fails, emit telemetry `CLAIM_ENRICHMENT_FAILED`, fall back to offline heuristics, proceed (not a blocker)
- **Telemetry events**: MUST emit `FACTS_BUILDER_STARTED`, `FACTS_BUILDER_COMPLETED`, `ARTIFACT_WRITTEN` for each output artifact

**Additional output artifact** (TC-2383):
- `RUN_DIR/artifacts/topic_manifest.json` — LLM-discovered topics per section
  - `topics[]`: array of `{topic_id, title, section, source_claim_ids[]}`
  - Each topic belongs to exactly one `section` (docs, kb, blog, etc.)
  - `section` field enables W4 per-section topic budgeting
  - Generated by `topic_discovery.py`; falls back to deterministic extraction when LLM unavailable
  - Used by W4 for topic-aware page planning and claim-to-topic binding

---

### W3: SnippetCurator
**Goal:** extract, normalize, and tag reusable code snippets with provenance.

**Inputs**
- `RUN_DIR/artifacts/repo_inventory.json`
- `RUN_DIR/artifacts/product_facts.json`
- repo worktree (read-only)

**Outputs**
- `RUN_DIR/artifacts/snippet_catalog.json` (schema: `snippet_catalog.schema.json`)

**Binding requirements**
- MUST discover examples from standard directories (`examples/`, `samples/`, `demo/`) PLUS any additional directories listed in `run_config.ingestion.example_directories` (TC-1020, see `specs/05_example_curation.md`)
- MUST NOT exclude files from snippet discovery based on unrecognized language; files with unknown language MUST be recorded with `language: "unknown"` (TC-1020)
- Every snippet MUST include:
  - `source_path`, `start_line`, `end_line`, `language`
  - stable `snippet_id` derived from `{path, line_range, sha256(content)}`
- Snippets MUST be normalized deterministically:
  - line endings `\n`, trailing whitespace trimmed, no reformatting that changes meaning
- Tags MUST be stable and derived from the ruleset (not ad-hoc freeform).

**Edge cases and failure modes** (binding):
- **Zero examples discovered**: If example_roots is empty and no snippets can be extracted, emit telemetry `SNIPPET_CURATOR_ZERO_SNIPPETS`, proceed with empty snippet_catalog (mark for generated snippets downstream if allowed)
- **All snippets invalid syntax**: If all extracted snippets fail syntax validation and forbid_invalid_snippets=true, emit error_code `SNIPPET_CURATOR_ALL_INVALID`, open MAJOR issue, proceed with empty catalog
- **Large snippet handling**: If snippet exceeds max_snippet_lines (from ruleset), truncate with note or skip, emit telemetry `SNIPPET_CURATOR_TRUNCATED`
- **Binary file encountered**: If snippet extraction targets binary file, skip with warning, emit telemetry `SNIPPET_CURATOR_BINARY_SKIPPED`
- **Snippet validation timeout**: If syntax validation for a snippet exceeds timeout, mark validation.syntax_ok=null, proceed, emit telemetry `SNIPPET_CURATOR_VALIDATION_TIMEOUT`
- **Telemetry events**: MUST emit `SNIPPET_CURATOR_STARTED`, `SNIPPET_CURATOR_COMPLETED`, `ARTIFACT_WRITTEN` for snippet_catalog.json

---

### W4: IAPlanner
**Goal:** produce a complete PagePlan before any writing.

**Inputs**
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- run_config
- `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
- site worktree (read-only, under allowed_paths)
- Merged page requirements from ruleset (TC-983): `mandatory_pages`, `optional_page_policies`, and `family_overrides` from `specs/rulesets/ruleset.v1.yaml` (schema: `ruleset.schema.json`). W4 reads the global section config and family_overrides, merges them using union strategy (family extends global, deduplicate by slug), and uses the merged config to determine mandatory pages and optional page policies per section.

**Outputs**
- `RUN_DIR/artifacts/page_plan.json` (schema: `page_plan.schema.json`)
  - `page_plan.evidence_volume` (TC-983): dict containing evidence volume metrics (`total_score`, `claim_count`, `snippet_count`, `api_symbol_count`, `workflow_count`, `key_feature_count`). Computed from product_facts and snippet_catalog. Used for evidence-driven page scaling.
  - `page_plan.effective_quotas` (TC-983): dict mapping section names to their computed effective `max_pages` after applying tier scaling coefficients and evidence-based targets. Used downstream by W7 for Gate 14 validation.
- `RUN_DIR/artifacts/shared_facts.json` (schema: `shared_facts.schema.json`, TC-2478)
  - Canonical fact sheet containing product-level reference data extracted during page planning.
  - Fields include: `product_name`, `min_python_version`, `top_formats[]`, `top_conversion_pairs[]`, `family_keyword`, `product_family`.
  - Consumed by W5 for evidence pack pre-computation (TC-2482) and by Gate 20 for source-of-truth validation (TC-2479).
  - Written atomically alongside `page_plan.json`.

**Binding requirements**
- MUST select templates deterministically from:
  - `specs/templates/<subdomain>/<family>/<locale>/...` (see `specs/20_rulesets_and_templates_registry.md`)
  - Templates MUST NOT include `__PLATFORM__` directory segments (V2 removed, 2026-02-09)
- MUST define for each planned page:
  - `output_path`: content file path relative to site repo root (V1 layout: no platform segment)
  - `url_path`: public canonical URL path (via resolver, see `specs/33_public_url_mapping.md`). Format: `/{family}/{slug}/` (no platform segment).
  - `cross_links`: array of **absolute URLs** to related pages across subdomains (e.g., `https://docs.aspose.org/cells/overview/`). Format: `https://<subdomain>/<family>/<slug>/`. See `specs/06_page_planning.md` "cross_links format" section.
  - template id + variant
  - required claim IDs
  - required snippet tags
  - internal link targets (using url_path, not output_path)
- MUST populate `url_path` using the public URL resolver based on hugo_facts (V1 layout only, no platform segment)
- MUST respect `run_config.required_sections`:
  - if a required section cannot be planned, open a blocker issue `PlanIncomplete`.
- MUST read `family_overrides` from ruleset and merge with global section config (TC-983):
  - Load global `sections.<section>.mandatory_pages` from `specs/rulesets/ruleset.v1.yaml`
  - If `family_overrides.<product_family>.sections.<section>.mandatory_pages` exists, UNION with global list (deduplicate by slug)
  - All mandatory pages from merged config MUST appear in page_plan.pages for the corresponding section
  - Optional page candidates MUST be generated per `optional_page_policies` from merged config
- MUST compute and record `evidence_volume` in page_plan.json (TC-983):
  - quality_score formula: `(claim_count * 2) + (snippet_count * 3) + (api_symbol_count * 1)`
  - All component counts from product_facts and snippet_catalog
- MUST compute and record `effective_quotas` in page_plan.json (TC-983):
  - Tier scaling coefficients: minimal=0.3, standard=0.7, rich=1.0
  - Per-section effective max = clamp(evidence_target, min_pages, tier_adjusted_max)
- MUST derive `page_role` from template filename prefix (TC-990, binding):
  - `_index*` -> derive from context:
    - `toc` for docs root index (e.g., `__LOCALE__/_index.md`)
    - `landing` for products/kb/reference root indices
    - `comprehensive_guide` for `developer-guide/_index.md`
  - `index*` (blog) -> `landing`
  - `feature*` (docs developer-guide) -> `workflow_page`
  - `howto*` (kb) -> `feature_showcase`
  - `reference*` (under reference.aspose.org) -> `api_reference`
  - `installation*`, `license*`, `getting-started*` -> `workflow_page`
  - See `specs/07_section_templates.md` "Target V1 Template File Structure" for the binding ground truth

**Edge cases and failure modes** (binding):
- **Insufficient claims for minimum pages**: If required section cannot meet minimum page count due to lack of claims, emit error_code `PAGE_PLANNER_INSUFFICIENT_EVIDENCE`, open BLOCKER issue, halt run (see specs/06_page_planning.md)
- **URL path collision**: If multiple pages resolve to same url_path, emit error_code `PAGE_PLANNER_URL_COLLISION`, open BLOCKER issue with conflicting page IDs (see specs/06_page_planning.md)
- **Template not found**: If required template does not exist in registry, emit error_code `PAGE_PLANNER_TEMPLATE_MISSING`, open BLOCKER issue, halt run
- **Zero pages planned**: If page_plan.pages is empty (no sections can be planned), emit error_code `PAGE_PLANNER_ZERO_PAGES`, open BLOCKER issue, halt run
- **Frontmatter contract violation**: If planned page would violate frontmatter_contract.json schema, emit error_code `PAGE_PLANNER_FRONTMATTER_VIOLATION`, open BLOCKER issue
- **Telemetry events**: MUST emit `PAGE_PLANNER_STARTED`, `PAGE_PLANNER_COMPLETED`, `ARTIFACT_WRITTEN` for page_plan.json

**Spec v1.1 Additions (Agents 41-45)**:

- **Ruleset version wiring** (Agent 41): `load_ruleset()` and `load_ruleset_quotas()` use `resolve_ruleset_path()` from `template_registry.py` instead of hardcoded paths. `ruleset_version` read from `run_config` (dict or RunConfig object).
- **Blog workflow scoring** (Agent 44): `score_blog_workflow(product_facts, snippet_catalog)` ranks workflows by conversion+snippet (+5), snippet (+3), high-intent verb (+2). Winning workflow's title → `_derive_semantic_slug()` → feature_blog slug. Result stored in `content_strategy.selected_workflow`.
- **Format evidence injection** (Agent 43): For conversion how-to pages (slug/title contains "convert"), W4 injects `is_conversion_howto`, `supported_formats`, `conversion_pairs` from `product_facts` into `content_strategy`.
- **Reference object richness boost** (Agent 45): `per_api_object` candidates receive quality boost from API surface: `+min(methods//3, 5)` for methods, `+min(properties, 3)` for properties. Priority 1 over `per_api_symbol` (priority 2).
- **Mandatory role override** (Agent 45): When ruleset specifies `page_role: "toc"` for a mandatory page (e.g., reference `_index`), W4 overrides the template-enumerated page's role to enable `child_pages` population.
- **Cross-section links** (Agent 42): `_populate_products_cross_section_links()` sets 4 absolute URLs on the products `_index` page linking to docs, reference, kb, and blog section homes.

---

### W5: SectionWriter (one per section)
**Goal:** draft Markdown for the pages assigned to that section.

**Inputs**
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/snippet_catalog.json`
- `specs/templates/**` + ruleset (read-only)

**Outputs**
- `RUN_DIR/drafts/<section>/<output_path>` (mirrors `page_plan.pages[].output_path`; see `specs/29_project_repo_structure.md`)

**Binding requirements**
- MUST embed claim markers for every factual sentence/bullet (see `specs/23_claim_markers.md`).
- MUST only use snippets referenced by `required_snippet_tags` unless the plan explicitly allows extras.
- MUST fill and then remove all template tokens:
  - all `__UPPER_SNAKE__` placeholders (except DEPRECATED V2 tokens which must not be present)
  - all `__BODY_*__` scaffolding placeholders
  - MUST NOT use or emit `__PLATFORM__`, `__PLATFORM_CAPITALIZED__`, or `__PLUGIN_PLATFORM__` tokens (DEPRECATED V2 tokens, removed 2026-02-09)
- MUST NOT:
  - modify the site worktree
  - write artifacts under `RUN_DIR/artifacts/` (writer only writes drafts)

**Prompt Templates** (New in Round 11)

W5 specialized generators now use LLM-powered content generation via prompt templates located in `src/launch/workers/w5_section_writer/prompts/`:

- `comprehensive_guide.txt` — Developer guide workflows (TC-1652)
- `troubleshooting.txt` — Troubleshooting/limitations (TC-1653)
- `faq.txt` — FAQ Q&A expansion (TC-1654)
- `best_practices.txt` — Best practices with DO/DON'T examples (TC-1655)
- `tutorial.txt` — Step-by-step tutorials (TC-1656)
- `feature_showcase.txt` — Feature deep-dives (TC-1657)

Each prompt template follows the pattern:
1. Product and audience context
2. Facts (enriched claims) as source of truth
3. Code examples (snippets) for reference
4. Task description with requirements
5. Output format specification

Generators use `_call_llm_for_content()` (TC-1658) to invoke these prompts with populated placeholders. Required placeholders: `{product_name}`, `{enriched_claims}`, `{snippets}`. Prompts explicitly forbid placeholder text ("refer to repository") and claim markers.

**LLM-Enhanced Comprehensive Guide Generator** (TC-1652)

The `generate_comprehensive_guide_content()` function has been enhanced with dual-path generation architecture:

**LLM Path** (when `llm_client` provided):
1. Loads `comprehensive_guide.txt` prompt template
2. Builds enriched claim context via `_build_enriched_claim_context()`
3. Formats workflows and snippets for prompt injection
4. Calls `_call_llm_for_content()` with min_words=200 requirement
5. Injects HTML comment claim markers via `_inject_claim_markers_as_comments()`
6. Returns substantive workflow documentation (>200 words)

**Deterministic Fallback** (when `llm_client=None` or LLM fails):
1. Uses `_generate_deterministic_comprehensive_guide()` helper
2. Generates workflow sections with:
   - Workflow name (H3 heading)
   - Description text
   - Step-by-step instructions (numbered list from `workflow.steps[]`)
   - Code snippet (matched by `workflow_id` or name tags)
   - GitHub source link (when `repo_url` and `source_path` available)
   - HTML comment claim markers

**BLOCKER-1 Elimination**: TC-1652 removes ALL placeholder text instances:
- No "Refer to repository" text when snippets missing
- No "See documentation" fallback stubs
- All workflows rendered with substantive content (name + description + steps minimum)

**BLOCKER-4 Elimination**: Workflows always have substantive content, never empty shells.

Template variable substitution uses `.replace()` instead of `.format()` to avoid conflicts with example placeholders like `{Workflow Name}` in the OUTPUT FORMAT section of the prompt template.

**LLM-Enhanced Best Practices Generator** (TC-1655)

The `generate_best_practices_content()` function has been enhanced with dual-path generation architecture to produce detailed best practices with WHY explanations, DO/DON'T code comparisons, and quantified impact. **Eliminates BLOCKER-5 for best practices**.

**LLM Path** (when `llm_client` provided):
1. Loads `best_practices.txt` prompt template from `prompts/` directory
2. Builds enriched claim context via `_build_enriched_claim_context()`
3. Formats first 5 code snippets for reference
4. Fills prompt template using `.replace()` (not `.format()` to avoid brace conflicts)
5. Calls `_call_llm_for_content()` with min_words=200 requirement
6. Validates output quality via `_validate_best_practice_quality()`:
   - Requires at least 1 code block (DO/DON'T comparison)
   - Requires explanation keywords (why, because, improves, reduces, ensures, prevents)
7. Injects HTML comment claim markers via `_inject_claim_markers_as_comments()`
8. Returns substantive best practices content (>200 words with code examples)

**Deterministic Fallback** (when `llm_client=None` or LLM fails validation):
1. Groups best practice claims by category (uses `claim.get("category", "General")`)
2. For each category, generates H2 section heading
3. Renders each practice as bullet with:
   - Claim text (sentence-boundary truncation at 200 chars if needed)
   - HTML comment claim marker
4. Returns organized content grouped by category (Performance, Security, Code Organization, etc.)

**Quality Validation**:
The `_validate_best_practice_quality()` helper ensures LLM output meets minimum standards:
- At least 1 code block present (indicates DO/DON'T examples)
- Contains explanation keywords (why, because, improves, etc.)
- Rejects output that lacks either criterion and falls back to deterministic rendering

**BLOCKER-5 Elimination**: LLM path generates complete explanations with code examples. Deterministic fallback uses sentence-boundary truncation (not hard cut with "...") to preserve readability.

**LLM-Enhanced Tutorial Generator** (TC-1656)

The `generate_tutorial_content()` function has been enhanced with dual-path generation architecture to produce complete step-by-step tutorials with runnable Python code, line-by-line explanations, expected output, and common mistakes sections. **Eliminates BLOCKER-5 for tutorials and BLOCKER-7 (no code examples)**.

**LLM Path** (when `llm_client` provided):
1. Loads `tutorial.txt` prompt template from `prompts/` directory
2. Builds enriched claim context via `_build_enriched_claim_context()` grouped by claim_kind
3. Formats first 5 code snippets for reference examples
4. Fills prompt template with product_name, enriched_claims, and snippets using `.replace()`
5. Calls `_call_llm_for_content()` with min_words=300 requirement (tutorials need comprehensive step-by-step content)
6. Validates output quality via `_validate_tutorial_quality()`:
   - Requires at least 1 step with step numbering (flexible patterns: "## Step 1:", "Step 1:", "1.", "### Step 1")
   - Requires at least 1 Python code block (```python ... ```)
   - Requires minimum 200 words (substantial content)
7. Injects HTML comment claim markers via `_inject_claim_markers_as_comments()`
8. Returns complete tutorial content (>300 words with code examples and explanations)

**Deterministic Fallback** (when `llm_client=None` or LLM fails validation):
1. Uses `_generate_deterministic_tutorial()` helper to create structured steps
2. Iterates tutorial claims as numbered steps (Step 1, Step 2, etc.)
3. Extracts step title from first sentence of claim_text
4. Uses full claim_text as description (no truncation)
5. Matches relevant code snippet via `_find_related_snippet()`:
   - Computes keyword overlap between claim text and snippet description/code
   - Returns snippet with ≥2 word overlap
   - Falls back to minimal code placeholder if no match
6. Renders each step as:
   - H2 heading: `## Step N: {title}`
   - Description paragraph (full claim text)
   - Code block (matched snippet or placeholder)
   - HTML comment claim marker
7. Returns structured tutorial with real content (no truncation or placeholders)

**Quality Validation**:
The `_validate_tutorial_quality()` helper ensures LLM output meets minimum standards:
- At least 1 step marker (various formats supported for flexibility)
- At least 1 Python code block (eliminates BLOCKER-7: no code examples)
- Minimum 200 words (ensures substantial content, eliminates BLOCKER-5: truncation)
- Rejects output that lacks any criterion and falls back to deterministic rendering

**Snippet Matching Algorithm**:
The `_find_related_snippet()` helper uses simple keyword overlap matching:
- Extracts keywords from claim text (whitespace split, lowercase)
- Extracts keywords from snippet description + code
- Computes set intersection overlap
- Returns best snippet with ≥2 word overlap
- Returns None if no meaningful match (triggers placeholder code)

**Tutorial Structure Requirements** (per prompt template):
- Step number and clear title
- What the step accomplishes
- Complete working Python code for the step
- Line-by-line explanation of the code
- Expected output or result
- Common mistakes to avoid

**BLOCKER-5 Elimination**: LLM path generates complete tutorial steps with full explanations. Deterministic fallback uses full claim text (no truncation) and provides real code snippets where available.

**BLOCKER-7 Elimination**: Every tutorial step MUST include a code block. LLM validation enforces this. Deterministic fallback provides either matched snippets or minimal placeholders (never completely absent code).

**LLM-Enhanced FAQ Generator** (TC-1654)

The `generate_faq_content()` function has been enhanced with dual-path generation architecture to produce detailed, actionable FAQ entries with 3-5 sentence answers and code examples. **Lifts FAQ quality from C/B to A grade**.

**LLM Path** (when `llm_client` provided):
1. Loads `faq.txt` prompt template from `prompts/` directory
2. Builds enriched claim context via `_build_enriched_claim_context()` grouped by claim_kind
3. Formats first 5 code snippets for reference
4. Fills prompt template with product_name, enriched_claims, and snippets
5. Calls `_call_llm_for_content()` with min_words=150 requirement (ensures substantial answers)
6. Validates output format via `_validate_faq_format()`:
   - Requires at least 1 Q&A pair in expected format (### Q: / **A:**)
   - Ensures question and answer markers are present
7. Injects HTML comment claim markers via `_inject_claim_markers_as_comments()`
8. Returns substantive FAQ content (>150 words with code examples where relevant)

**Deterministic Fallback** (when `llm_client=None` or LLM fails validation):
1. Uses `_generate_deterministic_faq()` helper to parse Q&A from claim_text
2. W2 FAQ claims are already in Q&A format (question? answer.)
3. Splits on first "?" to separate question from answer
4. Renders each FAQ as:
   - H3 heading: `### Q: {question}`
   - Answer paragraph: `**A:** {answer}`
   - HTML comment claim marker
5. Returns basic but readable FAQ content preserving original Q&A structure

**Quality Validation**:
The `_validate_faq_format()` helper ensures LLM output meets minimum standards:
- At least 1 question marker (### Q:, **Q:**, or Question:)
- At least 1 answer marker (**A:** or Answer:)
- Rejects output that lacks either criterion and falls back to deterministic rendering

**Quality Improvements**:
- Answers expanded from 1 sentence to 3-5 sentences (50+ words per FAQ)
- Code examples added for "How do I..." questions
- Caveats and limitations included where applicable
- Links to related docs where relevant
- Actionable guidance instead of simple yes/no answers

**Data Structure Serialization** (TC-1651)

W5 MUST NOT emit raw Python dict/list structures (e.g., `{'OBJ': 'GLTF'}` or `['OBJ', 'FBX']`) into user-facing markdown content. The `_serialize_workflow_data()` helper converts structured workflow metadata to natural language prose:

- `dict` → "Supports conversion: X to Y, A to B"
- `list` → "Supports formats: A, B, C"
- `scalar` → unchanged string representation

This serialization is applied in `generate_comprehensive_guide_content()` when outputting workflow descriptions and in the "Additional Workflows" section. All specialized generators MUST use prose serialization for any structured data fields to prevent backend data structures from leaking into documentation.

**Smart Truncation** (TC-1660)

W5 MUST use `_smart_truncate()` instead of hard truncation (e.g., `text[:200]`) for all claim text display. The smart truncation function eliminates BLOCKER-5 (truncated sentences ending with "...") through intelligent truncation strategies:

1. **Pass-through**: Text ≤ max_len returns unchanged
2. **LLM summarization** (when available): Calls `llm_client.generate()` for clean, professional summaries
3. **Sentence-boundary fallback**: Preserves complete sentences by splitting on `.!?` punctuation
4. **Word-boundary last resort**: Avoids mid-word cuts when no complete sentence fits

Usage locations:
- Key Capabilities section (feature claims)
- FAQ fallback content
- Best Practices recommendations
- Tutorial step descriptions

The function signature: `_smart_truncate(text: str, max_len: int = 200, llm_client: Optional[Any] = None) -> str`

Default max_len remains 200 characters per `MAX_CLAIM_TEXT_LENGTH` constant. LLM client parameter is optional; when None, deterministic sentence/word-boundary logic is used.

**Bullet Point Post-Processing** (TC-1661)

W5 MUST apply `_first_sentence_bullets()` post-processing to all generated content to prevent broken claim markers at sentence boundaries. This function:

1. **Converts bracket markers to HTML comments**: Transforms any legacy `[claim: id]` markers to `<!-- claim: id -->` format at function entry, ensuring all downstream logic works with standardized HTML comment format.
2. **Extracts first sentence**: For bullets exceeding `MAX_BULLET_LEN` (170 chars), extracts the first complete sentence instead of hard truncation with "...".
3. **Preserves claim markers**: Claim markers are preserved at the end of truncated content in HTML comment format.
4. **Falls back gracefully**: If the first sentence is still too long, falls back to word-boundary truncation.

This post-processing eliminates BLOCKER-5 (truncated sentences with "...") and prevents broken claim markers like `"This is a feature [claim: "` (truncated mid-marker). The conversion happens BEFORE sentence extraction to ensure claim markers never appear at sentence boundaries where they could be broken by truncation.

Applied to all specialized generator outputs: comprehensive_guide, troubleshooting, faq, best_practices, tutorial, feature_showcase, toc.

**Code Fence Validation** (TC-1662)

W5 MUST apply `_fix_code_fences()` post-processing to all generated content to eliminate broken code fences (SERIOUS-9 quality issue). This function:

1. **Validates matching fence pairs**: Tracks fence state (inside/outside) and ensures every opening ``` has a matching closing ```
2. **Removes orphaned opening fences**: Skips opening fences when already inside a code block (e.g., consecutive ``` with language tags)
3. **Removes orphaned closing fences**: Skips closing fences when already outside a code block (e.g., ``` with no prior opening)
4. **Converts pseudocode to python**: Transforms ```pseudocode blocks to ```python with "# Illustrative example" comment header
5. **Auto-closes unclosed fences**: Appends closing ``` if content ends with an open fence

Algorithm distinguishes opening vs closing fences by language identifier presence:
- Opening fence: ``` followed by language (e.g., ```python, ```bash, ```pseudocode)
- Closing fence: bare ``` with no language identifier

Replaces legacy `_close_unclosed_fences()` function (which only handled end-of-content unclosed fences). Applied to all page content after other markdown transformations.

**LLM Client Threading** (TC-1663)

W5 SectionWriter threads `llm_client` parameter through the entire pipeline to enable LLM-enhanced content generation while maintaining backward compatibility with deterministic fallback.

**Integration Layer**:
- `execute_section_writer()` receives optional `llm_client` parameter from orchestrator
- Threads `llm_client` through `generate_section_content()` to all specialized generators
- Each generator uses LLM-enhanced path when `llm_client` is available
- Falls back to deterministic generation when `llm_client=None`

**Supported page_role values**:
- `toc` → `generate_toc_content()` (deterministic only, no LLM)
- `comprehensive_guide` → `generate_comprehensive_guide_content(..., llm_client=llm_client)` (TC-1652)
- `troubleshooting` → `generate_troubleshooting_content(..., llm_client=llm_client)` (TC-1653)
- `faq` → `generate_faq_content(..., llm_client=llm_client)` (TC-1654)
- `best_practices` → `generate_best_practices_content(..., llm_client=llm_client)` (TC-1655)
- `tutorial` → `generate_tutorial_content(..., llm_client=llm_client)` (TC-1656)
- `feature_showcase` → `generate_feature_showcase_content(..., llm_client=llm_client)` (TC-1657)
- `landing` → LLM-based prompt generation (existing implementation)

**Backward Compatibility**:
- `llm_client` defaults to `None` in all function signatures (opt-in)
- Existing test suites pass without modification
- Production runs can enable LLM by passing `llm_client` instance
- Deterministic pipelines (tests, offline runs) unaffected

**Impact**:
- Enables all 6 LLM-enhanced specialized generators in production
- Zero impact on deterministic pipelines
- Unified threading pattern for future LLM-enhanced features

**Enriched Text Usage in LLM Prompts** (TC-1664)

W5 SectionWriter now uses `enriched_text` (marketing-ready claim text from W2) instead of raw `claim_text` (code-like extractions) when building LLM prompts. This applies to both `_build_section_prompt()` (for landing/workflow pages) and `_generate_fallback_content()` (for deterministic fallback).

**Implementation**:
- `_build_section_prompt()` calls `_get_display_text(claim)` for all claim text insertion (2 sites: regular claims + limitation claims)
- `_generate_fallback_content()` calls `_get_display_text(claim)` for fallback bullet text
- `_get_display_text()` helper (line 66) prefers `enriched_text` over `claim_text`:
  - Returns `enriched_text` if available and non-empty
  - Falls back to `claim_text` if `enriched_text` missing or empty
  - Returns empty string if neither field exists

**Examples**:
- **Before (raw extraction)**: "class WorkbookFactory(AbstractFactory)"
- **After (marketing-ready)**: "Provides advanced workbook creation with factory pattern support"

**Impact**:
- Landing pages receive higher-quality LLM input (understands context instead of raw code)
- LLM generates better prose (marketing-ready text is more descriptive)
- Aligns landing/workflow pages with specialized generators (all use enriched_text)
- Backward compatible: Falls back to `claim_text` when `enriched_text` unavailable

**Consistency**:
- Specialized generators (TC-1652-1657): Use `_build_enriched_claim_context()` → enriched_text ✅
- Landing/workflow pages (TC-1664): Use `_build_section_prompt()` → enriched_text ✅
- Fallback content (TC-1664): Use `_generate_fallback_content()` → enriched_text ✅

**Edge cases and failure modes** (binding):
- **Required claim not found**: If page requires claim_id that does not exist in evidence_map, emit error_code `SECTION_WRITER_CLAIM_MISSING`, open BLOCKER issue, halt run
- **Required snippet not found**: If page requires snippet tag that does not exist in snippet_catalog, emit warning, generate minimal snippet if allow_generated_snippets=true, otherwise open MAJOR issue
- **Template rendering failure**: If template has syntax errors or missing required fields, emit error_code `SECTION_WRITER_TEMPLATE_ERROR`, open BLOCKER issue, halt run
- **Unfilled template tokens remaining**: If draft contains unreplaced `__TOKEN__` after rendering, emit error_code `SECTION_WRITER_UNFILLED_TOKENS`, open BLOCKER issue, halt run
- **Writer timeout**: If section writing exceeds configured timeout, emit error_code `SECTION_WRITER_TIMEOUT`, mark as retryable, save partial drafts
- **LLM API failure**: If LLM provider returns error (429, 500, timeout), emit error_code `SECTION_WRITER_LLM_FAILURE`, mark as retryable
- **Telemetry events**: MUST emit `SECTION_WRITER_STARTED`, `SECTION_WRITER_COMPLETED`, `DRAFT_WRITTEN` for each page

**Priority-Weighted Token Allocation** (TC-2373, RD-04):

W5 reads `page["content_strategy"]["priority_weight"]` (float, written by W4) and uses it to compute an effective token budget for each page. High-priority sections (e.g., getting_started, tutorial) receive a larger budget; low-priority sections (e.g., toc, landing) receive a smaller one.

- **`_compute_token_budget(page, run_config) -> int`**: helper in `worker.py`
- **`SECTION_TYPE_WEIGHTS`**: module-level fallback dict keyed by `page["page_type"]`; used when `content_strategy.priority_weight` is absent
- **Base budget**: `run_config.get("token_budget", 2048)`
- **Clamp rule**: `effective = max(base × 0.5, min(base × 2.0, base × weight))`
- **Observability**: DEBUG log per page — `[W5] <slug>: base=N weight=W effective=M`
- **Manifest field**: each page's manifest entry includes `"effective_token_budget": int`
- **Backward compat**: when `priority_weight` absent and page_type unmapped, `weight = 1.0` → identical behavior

**Incremental Execution Contract** (TC-2450, binding):

W5 supports page-level incremental execution via the `page_status` field in each page plan entry
and the `WorkerCache` helper (`src/launch/workers/_shared/worker_cache.py`).

**`page_status` values**:

| Status | Meaning | LLM call |
|--------|---------|-----------|
| `new` | Generate via LLM (default) | Yes |
| `preserved` | Reuse draft from `incremental.previous_run_path` | No |
| `cache_hit` | Skip — cached hash matches input hash AND draft file exists | No |

**Activation flags** (run_config):
- `caching.enabled: true` — enables per-page hash cache; all pages check cache before generating
- `regen_failed_only: true` — reads `validation_report.json`; pages with `severity in (blocker, error)` → `new`, others → `preserved`
- `incremental.enabled: true` + `incremental.previous_run_path` — provides source for preserved-page drafts

**Default behavior**: `caching.enabled=false` → all pages generate as `new`. Pilots NEVER set this flag.

**Per-Page Timing Contract** (TC-2451, binding):

Each entry in `draft_manifest.json` MUST include a `duration_ms` field:

| Page status | `duration_ms` value |
|-------------|---------------------|
| `new` (generated) | Actual wall-clock milliseconds from LLM call start to finish |
| `cache_hit` | `0` |
| `preserved` | `0` |

After the generation loop, W5 MUST emit an aggregate timing log:
```
[W5] timing: N generated avg=Xms, M skipped (preserved+cache)
```

For full details on page input hash computation and cache storage, see
`specs/47_worker_cache_and_incremental_execution.md`.

**Evidence Pack Pre-Computation (TC-2482)**:

Before invoking the LLM draft pass, W5 multi-pass generation (`multi_pass.py`) pre-computes an evidence pack for each page via `_build_evidence_packs()`. The evidence pack aggregates:
- Relevant claims filtered by page's `required_claim_ids`
- Matched snippets from `snippet_catalog`
- Shared facts from `shared_facts.json` (product name, formats, family keyword)
- Cross-page summaries from sibling pages

This pre-computation ensures the LLM draft call receives a complete, validated context bundle rather than assembling context inline.

**Post-Draft Consistency Check (TC-2483)**:

After the LLM draft pass completes, W5 multi-pass generation runs `_check_draft_consistency()` to verify:
- All required claim IDs from the page plan appear as claim markers in the draft
- Product name references in the draft match `shared_facts.product_name`
- No hallucinated format names appear (cross-checked against `shared_facts.top_formats`)

Consistency failures emit warnings (not blockers) and are recorded in `draft_manifest.json` for downstream review by W7.

**Spec v1.1 Additions (Agents 43-46)**:

- **`_build_not_evidenced_howto(page, product_facts)`** (Agent 43): Structured fallback for mandatory how-to pages with zero supporting claims. Emits all 7 spec-mandated headings (Goal → When You'd Use This → Prerequisites → Steps → {Product Name} Code Example → Common Mistakes → See Also) with safe pseudo-code only (no real API calls). Triggered when `not_evidenced_hint: true` in page spec and `len(claims) == 0`.
- **`_build_format_evidence_text(page)`** (Agent 43): Renders format evidence block for how-to prompt injection. Reads `content_strategy.supported_formats` and `content_strategy.conversion_pairs`; returns empty string for non-conversion pages. Used in `{format_evidence}` template variable in `howto_article.txt`.
- **`_normalize_howto_code_fences(content, page)`** (Agent 43): Post-render normalizer ensuring how-to articles have a code fence under the Code Example heading. Injects placeholder fence when heading has no following fence. Only activates for `page_role == "howto_article"`.
- **`generate_reference_object_content(page, product_facts, snippet_catalog, llm_client)`** (Agent 45): Generates per-class/module/function reference pages. LLM path uses `reference_object.txt` prompt template; deterministic fallback via `_build_deterministic_reference_object()` emitting H3 sub-sections for methods and properties. Triggered for `page_role == "reference_object_page"`.
- **`_build_deterministic_reference_object(page, product_facts)`** (Agent 45): Deterministic fallback for reference object pages. Reads `object_name` and `object_kind` from page spec; looks up class in `api_surface_summary.classes`; emits H3 heading per method/property with signature, docstring, and parameter table.
- **Prompt template additions**: `howto_article.txt` updated with `{format_evidence}` variable and 7-heading order (Agent 43). `feature_blog.txt` updated with `{section_links}` variable for cross-section navigation links (Agent 44).

---

### W7: ContentReviewer

**Purpose**
Reviews generated markdown across 3 quality dimensions (Content Quality, Technical Accuracy, Usability) and applies auto-fixes or delegates to specialist agents for complex issues.

**Position in Pipeline**
```
W5 (SectionWriter) -> W7 (ContentReviewer) -> W8 (LinkerAndPatcher)
```

**Inputs (read-only)**

| Artifact | Schema | Required |
|----------|--------|----------|
| `RUN_DIR/drafts/**/*.md` | — | Yes |
| `RUN_DIR/artifacts/product_facts.json` | `product_facts.schema.json` | Yes |
| `RUN_DIR/artifacts/snippet_catalog.json` | `snippet_catalog.schema.json` | Yes |
| `RUN_DIR/artifacts/page_plan.json` | `page_plan.schema.json` | Yes |
| `RUN_DIR/artifacts/evidence_map.json` | `evidence_map.schema.json` | Yes |

**Outputs (write-only)**

| Artifact | Schema | Description |
|----------|--------|-------------|
| `RUN_DIR/artifacts/review_report.json` | `review_report.schema.json` | Quality review results |
| `RUN_DIR/drafts/**/*.md` | — | Enhanced markdown (same paths as input) |
| `RUN_DIR/artifacts/review_iterations.json` | — | Iteration history for debugging |

**Review Pipeline (TC-2360 adds Phase 0)**

```
Phase 0: LLM Format Fix (detect+fix 7 defect types, in-place, before checks)
Phase 1: 4 check dimensions (36 checks + semantic_accuracy LLM checks)
Phase 2: Deterministic auto-fixes (re-check after)
Phase 3: Scoring → routing (PASS / NEEDS_CHANGES / REJECT)
Phase 4: LLM regen specialist agents (if NEEDS_CHANGES or REJECT)
Phase 5: Post-LLM sanitization chain
```

**Phase 0: LLM Formatting Review + Fix (TC-2360, binding)**

Runs BEFORE the 36-check cycle. LLM receives each draft page and the
`format_fixer.txt` checklist. LLM simultaneously detects and fixes 7
formatting defect types in a single API call. Fixed content is written to
disk immediately so Phase 1 checks run on already-improved content.

LLM-optional: if llm_client is None, Phase 0 skips silently (no error).

Defect types:
- FQ-1 NAKED_CODE: Python/bash code outside ``` fences → error
- FQ-2 FAQ_CONCAT: FAQ answer + question on same line → warn
- FQ-3 TRUNCATED: Bullet ending mid-sentence → error
- FQ-4 DOUBLE_HEADING: H2 heading + paragraph on same line → error
- FQ-5 KEYWORD_COLON: Colon in YAML keywords array item → warn
- FQ-6 CLAIM_COMMENT: `<!-- claim: UUID -->` visible in body → warn
- FQ-7 INCOHERENT: Structurally broken sentence/bullet → error

Prompt: `src/launch/workers/w7_content_reviewer/prompts/format_fixer.txt`
Module: `src/launch/workers/w7_content_reviewer/fixes/llm_format_fix.py`
Output: `format_fix_results` appended to `review_report.json`

**Review Dimensions (36 checks)**
1. **Content Quality** (12 checks): grammar, readability, paragraph structure, bullet quality, tone, completeness, heading hierarchy, claim markers, grounding, density, frontmatter, links
2. **Technical Accuracy** (12 checks): code syntax, API validation, claim validity, snippet attribution, workflow coverage, limitations, distribution, examples, evidence linkage, terminology, forbidden topics
3. **Usability** (12 checks): navigation, user journey, example clarity, headings, CTAs, prerequisites, accessibility, search optimization, mobile readability, progressive disclosure, related links, error clarity

**Claim Marker Recognition (TC-1666)**

ContentReviewer recognizes claim markers in TWO formats:

1. **HTML Comments** (TC-1650, Round 11 standard): `<!-- claim: claim_id -->`
   - Used by W5 generators (TC-1652-1657) via `_inject_claim_markers_as_comments()`
   - Invisible to end users in rendered HTML
   - Pattern: `<!--\s*claim:\s*([a-f0-9-]+)\s*-->`

2. **Visible Brackets** (legacy, backward compatibility): `[claim: claim_id]`
   - Older format, still supported for existing content
   - Pattern: `\[claim:\s*([a-f0-9-]+)\]`

Both formats are validated by:
- Check TA-4: Claim Validity (all claim IDs must exist in product_facts)
- Check TA-10: Claim-Evidence Linkage (all claims must have evidence)

This dual-format support aligns with W9 Gate 14 behavior (TC-1665).

**Routing**

| Status | Condition | Action |
|--------|-----------|--------|
| PASS | All dimensions >=4/5, zero blockers | -> W8 |
| NEEDS_CHANGES | Any dimension = 3, fixable errors | Auto-fix + re-review (max 3 iterations) |
| REJECT | Any dimension <=2, blockers present | Escalate to human review |

**Timeout**

| Profile | Timeout |
|---------|---------|
| local | 300s |
| ci | 600s |
| prod | 600s |

**Events**
- `REVIEW_STARTED` — Worker started
- `PAGE_REVIEWED` — Each page review completed
- `FIX_APPLIED` — Each auto-fix applied
- `LLM_REGEN_REQUESTED` — LLM regeneration triggered
- `REVIEW_COMPLETED` — Worker completed

**Edge cases and failure modes** (binding):
- **No drafts found**: If RUN_DIR/drafts/ is empty, emit error_code `CONTENT_REVIEWER_NO_DRAFTS`, open BLOCKER issue, halt run
- **All pages fail review**: If all pages score <=2 in any dimension, emit error_code `CONTENT_REVIEWER_ALL_FAILED`, route to REJECT
- **Auto-fix loop**: If auto-fix iterations reach max (3) without improvement, emit error_code `CONTENT_REVIEWER_FIX_LOOP`, route to REJECT
- **LLM agent failure**: If specialist agent LLM call fails, emit error_code `CONTENT_REVIEWER_AGENT_FAILED`, mark as retryable
- **Review timeout**: If review exceeds configured timeout, emit error_code `CONTENT_REVIEWER_TIMEOUT`, save partial review_report, mark as retryable
- **Telemetry events**: MUST emit `REVIEW_STARTED`, `REVIEW_COMPLETED`, `ARTIFACT_WRITTEN` for review_report.json

---

### W8: LinkerAndPatcher
**Goal:** convert drafts into a PatchBundle and apply to the site worktree deterministically.

**Inputs**
- `RUN_DIR/drafts/**`
- `RUN_DIR/artifacts/page_plan.json`
- site worktree (writeable, restricted by allowed_paths)
- `specs/templates/**` registry + ruleset (read-only)

**Outputs**
- `RUN_DIR/artifacts/patch_bundle.json` (schema: `patch_bundle.schema.json`)
- `RUN_DIR/reports/diff_report.md` (human-readable)

**Binding requirements**
- MUST apply patches in deterministic order:
  - by section order, then by planned page path
- MUST ensure only allowed_paths are changed:
  - if a patch touches an out-of-scope path, open blocker `AllowedPathsViolation`
- MUST maintain stable frontmatter formatting per template contract.
- MUST not introduce unresolved template tokens.
- MUST NOT produce output paths containing platform directory segments (V2 layout removed, 2026-02-09). All output paths use V1 layout: `content/<subdomain>/<family>/<locale>/...`

**Edge cases and failure modes** (binding):
- **No drafts found**: If RUN_DIR/drafts/ is empty (no writers completed), emit error_code `LINKER_NO_DRAFTS`, open BLOCKER issue, halt run
- **Patch conflict detection**: If applying patch would create conflict (existing content differs from expected base), emit error_code `LINKER_PATCH_CONFLICT`, open BLOCKER issue with diff details (see specs/08_patch_engine.md)
- **Allowed paths violation**: If patch targets file outside allowed_paths, emit error_code `LINKER_ALLOWED_PATHS_VIOLATION`, open BLOCKER issue, halt run
- **Frontmatter schema violation**: If patched file frontmatter violates frontmatter_contract.json, emit error_code `LINKER_FRONTMATTER_VIOLATION`, open BLOCKER issue
- **File system write failure**: If cannot write to site worktree (permissions, disk full), emit error_code `LINKER_WRITE_FAILED`, mark as retryable
- **Telemetry events**: MUST emit `LINKER_STARTED`, `LINKER_COMPLETED`, `ARTIFACT_WRITTEN` for patch_bundle.json, `PATCH_APPLIED` for each file

---

### W9: Validator
**Goal:** run all validation gates and produce a single ValidationReport.

**Inputs**
- site worktree (current)
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- `RUN_DIR/artifacts/patch_bundle.json` (if present)
- toolchain lock (see `specs/19_toolchain_and_ci.md`)

**Outputs**
- `RUN_DIR/artifacts/validation_report.json` (schema: `validation_report.schema.json`)
  - Includes `generation_id` field (TC-2470): A deterministic identifier derived from `run_id + gate_execution_timestamp` that uniquely identifies this validation pass. Used by W10 to verify it is operating on the correct validation report version.

**Binding requirements**
- MUST run all required gates (see `specs/09_validation_gates.md`).
- MUST normalize tool outputs into stable issue objects:
  - stable ordering and stable IDs (see `specs/schemas/issue.schema.json`)
- MUST never "fix" issues (validator is read-only).
- MUST write `validation_report.json` atomically (TC-2470): temp file + atomic rename to prevent partial reads by W10.

**Edge cases and failure modes** (binding):
- **Validation tool missing**: If required validation tool (e.g., markdownlint, hugo) not found in toolchain, emit error_code `VALIDATOR_TOOL_MISSING`, open BLOCKER issue, halt run
- **Validation tool timeout**: If validation gate exceeds timeout, emit error_code `VALIDATOR_TIMEOUT`, mark gate as failed, proceed with remaining gates
- **Validation tool crash**: If validation tool exits with unexpected error, emit error_code `VALIDATOR_TOOL_CRASH`, capture stderr, mark gate as failed, proceed
- **Zero issues found**: If all gates pass with zero issues, emit telemetry `VALIDATOR_ALL_GATES_PASSED`, proceed (success case)
- **All gates fail**: If all gates fail (not just issues found, but tool failures), emit error_code `VALIDATOR_ALL_GATES_FAILED`, open BLOCKER issue
- **Telemetry events**: MUST emit `VALIDATOR_STARTED`, `VALIDATOR_COMPLETED`, `ARTIFACT_WRITTEN` for validation_report.json, `GATE_EXECUTED` for each gate

---

### W10: Fixer
**Goal:** apply the minimal change required to fix exactly one selected issue.

**Inputs**
- `RUN_DIR/artifacts/validation_report.json`
- `RUN_DIR/artifacts/page_plan.json`
- `RUN_DIR/artifacts/product_facts.json`
- `RUN_DIR/artifacts/evidence_map.json`
- site worktree (writeable, restricted by allowed_paths)
- toolchain lock + ruleset

**Outputs**
- One of:
  - updated draft(s) under `drafts/<section>/...` **and** a new `patch_bundle.json` via W8 rerun
  - or a direct patch delta: `RUN_DIR/artifacts/patch_bundle.delta.json` (optional strategy)
- a note in `reports/fix_<issue_id>.md` (optional)

**Binding requirements**
- MUST fix exactly one issue: the issue_id supplied by the Orchestrator.
- MUST obey gate-specific fix rules in `specs/08_patch_engine.md`.
- MUST NOT introduce new factual claims without evidence.
- MUST fail with blocker `FixNoOp` if it cannot produce a meaningful diff.
- MUST perform an integrity guard check on `validation_report.json` before processing (TC-2470): verify that the `gates` key and `issues` key both exist in the loaded report. If either key is absent, fail with `FIXER_INVALID_REPORT` error code rather than proceeding with a corrupted or partial report.
- MUST write output files atomically (TC-2470): temp file + atomic rename to prevent partial reads during concurrent pipeline execution.

**Edge cases and failure modes** (binding):
- **Issue not found**: If supplied issue_id does not exist in validation_report, emit error_code `FIXER_ISSUE_NOT_FOUND`, open BLOCKER issue, halt run
- **Unfixable issue**: If issue is marked as unfixable (no auto-fix rule), emit error_code `FIXER_UNFIXABLE`, open MAJOR issue requesting manual intervention
- **Fix produces no diff**: If fixer runs but produces zero changes, emit error_code `FIXER_NO_DIFF`, fail with BLOCKER issue `FixNoOp`
- **Fix introduces new validation errors**: If fix resolves target issue but introduces new issues, emit warning, record new issues in validation_report, continue
- **LLM API failure during fix**: If LLM provider fails during fix generation, emit error_code `FIXER_LLM_FAILURE`, mark as retryable
- **Telemetry events**: MUST emit `FIXER_STARTED`, `FIXER_COMPLETED`, `ISSUE_RESOLVED` if successful, `ISSUE_FIX_FAILED` if not

---

### W11: PRManager
**Goal:** open a PR via the commit service with deterministic branch naming and PR body.

**Inputs**
- site worktree diff (current)
- `RUN_DIR/reports/diff_report.md`
- `RUN_DIR/artifacts/validation_report.json`
- run_config (commit templates)

**Outputs**
- `RUN_DIR/artifacts/pr.json` (optional; includes pr_url, branch, commit_sha)

**Binding requirements**
- MUST call the GitHub commit service (`specs/17_github_commit_service.md`) in production mode.
- MUST associate the resulting commit_sha to telemetry (`specs/16_local_telemetry_api.md`).
- MUST include a PR checklist summary:
  - gates passed
  - pages created/updated
  - evidence summary / TruthLock summary

**Edge cases and failure modes** (binding):
- **No changes to commit**: If site worktree has zero uncommitted changes, emit telemetry `PR_MANAGER_NO_CHANGES`, skip PR creation, mark run as success (no-op success)
- **GitHub API authentication failure**: If GitHub commit service returns 401/403, emit error_code `PR_MANAGER_AUTH_FAILED`, open BLOCKER issue, halt run (not retryable)
- **GitHub API rate limit**: If GitHub returns 429 (rate limit), emit error_code `PR_MANAGER_RATE_LIMITED`, mark as retryable with exponential backoff
- **Branch already exists**: If target branch exists on remote, emit error_code `PR_MANAGER_BRANCH_EXISTS`, either force-push (if allowed) or fail with BLOCKER issue
- **PR already exists**: If PR for branch already exists, emit telemetry `PR_MANAGER_PR_EXISTS`, update existing PR (if allowed) or return existing pr_url
- **Commit service timeout**: If commit service call exceeds timeout, emit error_code `PR_MANAGER_TIMEOUT`, mark as retryable
- **Telemetry events**: MUST emit `PR_MANAGER_STARTED`, `PR_MANAGER_COMPLETED`, `COMMIT_CREATED`, `PR_OPENED` (or `PR_UPDATED`)

---

## W5 Multi-Pass Generation Contract (Round 12, binding)

W5 SectionWriter MAY operate in multi-pass mode when `run_config.multi_pass_generation.enabled` is true. When disabled (default), existing single-pass behavior is preserved unchanged.

### Lifecycle

Multi-pass generation executes 3 sequential LLM calls per page:

1. **Pass 1 — Outline** (temperature=0.0, response_format=json_object)
   - Input: RichContext (product profile + claims + constraints)
   - Output: JSON `{sections: [{heading, purpose, key_points, claim_ids, snippet_placements, target_words}]}`
   - Validation: required_headings present, all claim_ids valid, no forbidden topics
   - Fallback: deterministic outline from required_headings + round-robin claim assignment

2. **Pass 2 — Draft** (temperature=0.1)
   - Input: RichContext + validated outline + full claim texts + full snippets
   - Output: Raw markdown content
   - System prompt: `system/technical_writer.txt`
   - Page-role instructions: `pages/{page_role}.txt`
   - Validation: min_words met, required headings present, claim markers present, code blocks present
   - Fallback: existing deterministic generator functions (unchanged)

3. **Pass 3 — Refine** (temperature=0.0)
   - Input: draft + outline summary + cross-page summaries + product profile
   - Output: Improved markdown content
   - System prompt: `system/content_editor.txt`
   - Validation: all claim markers preserved (count match ±5%), code blocks preserved, headings preserved, word count not decreased >10%
   - Fallback: use Pass 2 draft as-is

### Cross-Page Summary Building

By default pages are processed sequentially. After each page completes Pass 3, a summary is extracted:

```
summary = "This page covers: [key topics], [key APIs], [key workflows]"
```

Summaries are accumulated in `cross_page_summaries: Dict[str, str]` and passed to subsequent pages to prevent content duplication.

### Parallel Page Writing (TC-2362, binding)

W5 MUST support parallel page writing when `run_config.max_parallel_pages > 1`.

**Snapshot-based approach**: Before dispatching pages, W5 takes a frozen snapshot of `cross_page_summaries` (empty on first run; populated from previous run in incremental mode). Each page worker receives:
- Its own `MultiPassOrchestrator` instance (no shared mutable state)
- The frozen `cross_page_summaries` snapshot (read-only)

**Isolation guarantee**: Each page writes only to `drafts/<section>/<slug>.md` — disjoint paths, no file-level contention.

**Ordering**: After all workers complete, `draft_files` MUST be sorted by `(section_order, output_path)` before manifest write (determinism per specs/10_determinism_and_caching.md).

**Quality trade-off**: Pages do not accumulate summaries from siblings in the same batch. On incremental runs (preserved pages provide summaries from the previous run), cross-page coherence is maintained. Acceptable for all production use cases.

**Constraint**: `max_parallel_pages` MUST be in range [1, 16]. Default 1 preserves sequential behavior.

### Feature Flag

- `run_config.multi_pass_generation.enabled` (boolean, default: false)
- `run_config.multi_pass_generation.skip_refine_for_thin_pages` (boolean, default: true) — skip Pass 3 if draft < 200 words
- `run_config.multi_pass_generation.min_claims_for_outline` (integer, default: 3) — skip Pass 1 if page has fewer claims
- `run_config.max_parallel_pages` (integer, default: 1) — number of pages to write concurrently; 1 = sequential

### Deterministic Fallback

If any LLM pass fails validation OR if hallucination detection (see W7 and W9 Gate 15) flags HIGH risk:
- Fall back to existing deterministic generator for that page
- Emit telemetry: `MULTI_PASS_FALLBACK` with reason
- Do NOT retry the same LLM call

---

## Prompt Library Contract (Round 12, binding)

All LLM prompts MUST be loaded via the `PromptLoader` class from `src/launch/prompts/`. Inline prompt strings in worker Python files are prohibited after Phase 1 migration.

### Prompt Format

Every prompt file uses YAML frontmatter + text body:

```yaml
---
version: "1.0"
description: "Human-readable purpose"
required_variables:
  - product_name
  - enriched_claims
optional_variables:
  - code_understanding
strategy:
  temperature: 0.1
  max_tokens: 6144
  min_words: 800
anti_hallucination:
  require_claim_markers: true
  api_whitelist_enforced: true
  code_from_snippets_only: true
---
Prompt text with {variable} placeholders...
```

### Required Frontmatter Fields

- `version` (string): Semantic version for tracking
- `description` (string): Human-readable purpose
- `required_variables` (array of strings): Variables that MUST be provided at load time

### Optional Frontmatter Fields

- `optional_variables` (array of strings): Variables that MAY be provided
- `strategy` (object): LLM call parameters (temperature, max_tokens, min_words)
- `anti_hallucination` (object): Per-prompt grounding rules

### PromptLoader API

```python
class PromptLoader:
    def load(self, name: str, **kwargs) -> PromptResult
    def load_with_fragments(self, name: str, fragments: List[str], **kwargs) -> PromptResult
    def get_version(self, name: str) -> str  # SHA-256 content hash
    def validate_variables(self, name: str, provided: Dict) -> List[str]  # Missing vars
```

### Variable Validation

- `load()` MUST raise `ValueError` if any `required_variables` are not provided in kwargs
- `optional_variables` that are not provided are silently omitted from the rendered template
- Variables use Python str.format_map() syntax: `{variable_name}`

### Folder Structure

```
src/launch/prompts/
  __init__.py          # PromptLoader class
  system/              # System role prompts (7 files)
  pages/               # Page-role prompts (11 files)
  synthesis/           # W2 synthesis prompts (13 files)
  review/              # W7 review prompts (3 files)
  fragments/           # Shared fragments (6 files)
```

### Fragment Injection

Fragments are reusable text blocks injected into prompts before variable substitution:
- `load_with_fragments("pages/comprehensive_guide", ["anti_hallucination", "product_context"])` loads the prompt AND injects the named fragments at `{fragment_name}` placeholders.

---

## W5 RichContext Contract (Round 12, binding)

When multi-pass generation is enabled, W5 MUST assemble a `RichContext` dataclass containing ALL available product data before each LLM call. This replaces the previous 3-field context (`_build_enriched_claim_context()`).

### Required Fields (15+ total)

**Product Profile** (5 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| product_name | str | product_facts.product_name | Yes |
| tagline | str | product_facts.positioning.tagline | Yes |
| short_description | str | product_facts.positioning.short_description | Yes |
| audience | str | product_facts.positioning.audience | Yes |
| license_info | str | product_facts metadata | No |

**Page Metadata** (5 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| page_role | str | page_plan.page_role | Yes |
| primary_focus | str | page_plan.content_strategy.primary_focus | Yes |
| seo_keywords | List[str] | page_plan.seo_keywords | No |
| depth_guidance | str | Computed from page_role | Yes |
| scenario_coverage | str | page_plan.content_strategy.scenario_coverage | No |

**Claims** (2 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| page_claims | List[Dict] | product_facts.claims filtered by page's claim_ids | Yes |
| workflows | List[Dict] | product_facts.workflows with steps, complexity | No |

**Code Context** (3 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| relevant_snippets | List[Dict] | snippet_catalog filtered | Yes |
| code_understanding | Dict | code_understanding.json artifact | No |
| api_surface | Dict | product_facts.api_surface_summary | No |

**Cross-Page Awareness** (2 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| sibling_pages | List[Dict] | Other pages in same section | No |
| cross_page_summaries | Dict[str, str] | Built incrementally during generation | No |

**Constraints** (3 fields):
| Field | Type | Source | Required |
|-------|------|--------|----------|
| forbidden_topics | List[str] | page_plan.forbidden_topics | Yes |
| required_headings | List[str] | page_plan.required_headings | Yes |
| claim_quota | Dict[str, int] | page_plan.content_strategy.claim_quota | No |

### Builder Function

```python
def build_rich_context(
    page: Dict, product_facts: Dict, snippet_catalog: Dict,
    evidence_map: Dict, page_plan: Dict = None,
    cross_page_summaries: Dict[str, str] = None,
    code_understanding: Dict = None,
) -> RichContext
```

Workers MUST call `build_rich_context()` instead of `_build_enriched_claim_context()` when multi-pass is enabled. The old function is preserved for backward compatibility when multi-pass is disabled.

---

## W5 Generator Context Builders (TC-2379, Binding)

Every `generate_*_content()` function in
`src/launch/workers/w5_section_writer/generators/content_generators.py` MUST have a
corresponding `build_*_context(page, product_facts, snippet_catalog) -> dict` function.

The returned dict MUST include all four keys:

| Key | Type | Description |
|-----|------|-------------|
| `claims` | `list` | Role-priority ranked claim dicts (most relevant first) |
| `snippets` | `list` | Up to 5 snippet dicts selected for this role |
| `claim_context` | `str` | Formatted claim text for LLM prompt injection |
| `snippet_text` | `str` | Formatted snippet code blocks for LLM prompt injection |

Role-to-claim-kind priority mapping (binding):

| Role | Primary claim kinds | Snippet strategy |
|------|--------------------|--------------------|
| `tutorial` | workflow → feature | demo_snippet_ids from ordered claims |
| `feature_showcase` | feature (primary claim first) | demo_snippet_ids from primary claim |
| `api_reference` | api → format (alphabetical) | demo_snippet_ids from api claims |
| `comprehensive_guide` | workflow → feature → api | demo_snippet_ids from top 5 workflow claims |
| `troubleshooting` | error → limitation → format | Snippets demonstrating fixes |
| `blog` | feature → workflow | First demo_snippet_id |
| `feature_blog` | feature → workflow | First demo_snippet_id |
| `performance` | limitation → feature | Snippets with timing/benchmark tags |
| `faq` | feature → api → format | No snippets required (return empty list) |
| `best_practices` | workflow → limitation | Step-linked snippets |
| `getting_started` | workflow (install sections first) → feature | Ordered install snippets |
| `workflow_page` | workflow in source_section order | Step-ordered snippets |
| `landing` | feature (top 5 only) | Hero snippet from demo_snippet_ids |
| `format_conversion` | format → api | Input/output format snippets |
| `howto_article` | workflow ordered | Step-linked snippets |
| `toc` | (none — structural page) | (none — return empty claims and snippets) |

The `get_context_for_role(page_role, page, product_facts, snippet_catalog) -> dict`
dispatch function MUST exist. It returns the role-appropriate context dict and falls
back to `build_tutorial_context` for unknown roles.

---

## W10 YAML Frontmatter Repair Contract (TC-3625, binding)

When gate_4 reports `frontmatter_read_error_<file>` (YAML parse error in frontmatter), W10 `fix_frontmatter_invalid_yaml()` MUST:

1. **Attempt field extraction** before falling back to minimal frontmatter. Search the raw file content (both inside and outside the frontmatter block) for `title:`, `layout:`, and `permalink:` field values using line-oriented regex.
2. **Prefer extracted values** over synthetic defaults. If `title` is found, use it; otherwise fall back to `stem.replace("-"," ").title()`. Same for `layout` and `permalink`.
3. **Trailing-field reconstruction**: If the file contains YAML-like `key: value` lines *after* the markdown body (outside any `---` block), extract `title`, `layout`, `permalink` from those lines and include them in the reconstructed frontmatter block.
4. **Write atomically**: temp-write + os.replace, as required by TC-2470.
5. **Return `fixed: True`** with `files_changed` and `diff_summary` on success; `fixed: False` with `error` on failure.

The minimal-frontmatter fallback (existing behavior) MUST be preserved for files where no extractable fields are found.

---

## write_frontmatter() YAML Serialization Contract (TC-3628, binding)

`write_frontmatter(frontmatter, body)` is the shared utility used by ALL W10 frontmatter fixers to serialize a frontmatter dict back to a markdown file. It MUST use `yaml.dump()` with `width=float('inf')` to prevent YAML string wrapping.

**Root cause**: `yaml.dump()` with the default width (80 chars) wraps long string values across lines as plain-scalar continuations (e.g., `  post` on the next line after `description: ...long text...`). When a subsequent fixer replaces the description with a double-quoted string, the orphaned continuation line becomes an invalid YAML token, causing Hugo and PyYAML to reject the file with parse errors.

**Contract** (binding):
1. `write_frontmatter()` MUST call `yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, width=float('inf'))`.
2. The `width=float('inf')` parameter MUST NOT be removed or overridden.
3. Any other YAML serialization of frontmatter dicts in W10 MUST also use `width=float('inf')`.

---

## Gate-17 FQ-1 Fence-Tracking CommonMark Contract (TC-3629, binding)

The pre-lint `lint_fq1_naked_code()` and related fence-tracking functions in `gate_17_prelints.py` MUST follow the CommonMark specification for code-fence close detection.

**Root cause**: All fence-tracking code used `if stripped.startswith("```"): in_fence = not in_fence`, which incorrectly treats ` ```python` (fence with info string) as a fence CLOSER. Per CommonMark spec, only a bare ` ``` ` line (backticks + optional whitespace, NO info string) can close an open code fence.

**Contract** (binding):
1. When `in_fence=True`, a fence line MUST close the fence only if it matches `^```+\s*$` (backticks only, no info string).
2. When `in_fence=False`, any ` ``` ` line (with or without info string) opens a new fence.
3. This rule applies to ALL four fence-tracking loops in `gate_17_prelints.py`: `lint_fq1_naked_code()`, `lint_fq4_double_heading()`, `lint_fq6_claim_comment()`, `lint_fq9_limitations_dump_shape()`.
4. A helper constant `_FENCE_CLOSER_RE = re.compile(r'^```+\s*$')` MUST be defined and used in all four loops.

---

## Acceptance
- Every worker has a complete, non-overlapping responsibility.
- All handoffs are file-based and schema-validated.
- A full dependency chain exists from RepoScout → PRManager with no hidden inputs.
