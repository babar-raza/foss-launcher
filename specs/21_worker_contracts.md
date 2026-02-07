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
- **Code Analysis** (TC-1041, TC-1042): Parse source code with AST to extract `api_surface_summary`, `code_structure`, and `positioning`
- **Workflow Enrichment** (TC-1043, TC-1044): Enrich workflows with descriptions, step ordering, complexity, and time estimates
- **Semantic Enrichment** (TC-1045, TC-1046): Use LLM to add claim metadata (audience_level, complexity, prerequisites, use_cases, target_persona). Requires AG-002 approval for production use.
- **Evidence Mapping** (TC-412): Map claims to evidence citations with source priority ranking
- **TruthLock Compilation** (TC-413): Compile minimal truth representation

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
- `RUN_DIR/artifacts/evidence_map.json` (schema: `evidence_map.schema.json`)
  - Claims MAY include enrichment metadata (audience_level, complexity, prerequisites, use_cases, target_persona)

**Binding requirements**
- MUST process **all discovered documents** without count caps (TC-1020, see `specs/03_product_facts_and_evidence.md`):
  - MUST NOT apply a maximum document count that causes documents to be skipped
  - MUST NOT apply minimum word-count filters that exclude short documents from processing
  - MUST NOT apply keyword-presence filters that exclude documents lacking specific keywords
  - Word-count and keyword heuristics MAY be used as **priority scoring** to determine processing order, but MUST NOT be used as exclusion filters
  - Evidence priority ranking (manifests > source code > tests > docs > README) is for **prioritization of conflicting claims**, NOT for filtering of evidence sources
  - All evidence sources MUST be ingested and recorded in the EvidenceMap regardless of their priority level
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

**Binding requirements**
- MUST select templates deterministically from:
  - `specs/templates/<subdomain>/<family>/<locale>/...` (see `specs/20_rulesets_and_templates_registry.md`)
- MUST define for each planned page:
  - `output_path`: content file path relative to site repo root
  - `url_path`: public canonical URL path (via resolver, see `specs/33_public_url_mapping.md`)
  - `cross_links`: array of **absolute URLs** to related pages across subdomains (e.g., `https://docs.aspose.org/cells/python/overview/`). Format: `https://<subdomain>/<family>/<platform>/<slug>/`. See `specs/06_page_planning.md` "cross_links format" section.
  - template id + variant
  - required claim IDs
  - required snippet tags
  - internal link targets (using url_path, not output_path)
- MUST populate `url_path` using the public URL resolver based on hugo_facts
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
    - `toc` for docs root index (e.g., `__LOCALE__/__PLATFORM__/_index.md`)
    - `landing` for products/kb/reference root indices
    - `comprehensive_guide` for `developer-guide/_index.md`
  - `index*` (blog) -> `landing`
  - `feature*` (docs developer-guide) -> `workflow_page`
  - `howto*` (kb) -> `feature_showcase`
  - `reference*` (under reference.aspose.org) -> `api_reference`
  - `installation*`, `license*`, `getting-started*` -> `workflow_page`
  - See `specs/07_section_templates.md` "Target V2 Template File Structure" for the binding ground truth

**Edge cases and failure modes** (binding):
- **Insufficient claims for minimum pages**: If required section cannot meet minimum page count due to lack of claims, emit error_code `PAGE_PLANNER_INSUFFICIENT_EVIDENCE`, open BLOCKER issue, halt run (see specs/06_page_planning.md)
- **URL path collision**: If multiple pages resolve to same url_path, emit error_code `PAGE_PLANNER_URL_COLLISION`, open BLOCKER issue with conflicting page IDs (see specs/06_page_planning.md)
- **Template not found**: If required template does not exist in registry, emit error_code `PAGE_PLANNER_TEMPLATE_MISSING`, open BLOCKER issue, halt run
- **Zero pages planned**: If page_plan.pages is empty (no sections can be planned), emit error_code `PAGE_PLANNER_ZERO_PAGES`, open BLOCKER issue, halt run
- **Frontmatter contract violation**: If planned page would violate frontmatter_contract.json schema, emit error_code `PAGE_PLANNER_FRONTMATTER_VIOLATION`, open BLOCKER issue
- **Telemetry events**: MUST emit `PAGE_PLANNER_STARTED`, `PAGE_PLANNER_COMPLETED`, `ARTIFACT_WRITTEN` for page_plan.json

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
  - all `__UPPER_SNAKE__` placeholders
  - all `__BODY_*__` scaffolding placeholders
- MUST NOT:
  - modify the site worktree
  - write artifacts under `RUN_DIR/artifacts/` (writer only writes drafts)

**Edge cases and failure modes** (binding):
- **Required claim not found**: If page requires claim_id that does not exist in evidence_map, emit error_code `SECTION_WRITER_CLAIM_MISSING`, open BLOCKER issue, halt run
- **Required snippet not found**: If page requires snippet tag that does not exist in snippet_catalog, emit warning, generate minimal snippet if allow_generated_snippets=true, otherwise open MAJOR issue
- **Template rendering failure**: If template has syntax errors or missing required fields, emit error_code `SECTION_WRITER_TEMPLATE_ERROR`, open BLOCKER issue, halt run
- **Unfilled template tokens remaining**: If draft contains unreplaced `__TOKEN__` after rendering, emit error_code `SECTION_WRITER_UNFILLED_TOKENS`, open BLOCKER issue, halt run
- **Writer timeout**: If section writing exceeds configured timeout, emit error_code `SECTION_WRITER_TIMEOUT`, mark as retryable, save partial drafts
- **LLM API failure**: If LLM provider returns error (429, 500, timeout), emit error_code `SECTION_WRITER_LLM_FAILURE`, mark as retryable
- **Telemetry events**: MUST emit `SECTION_WRITER_STARTED`, `SECTION_WRITER_COMPLETED`, `DRAFT_WRITTEN` for each page

---

### W6: LinkerAndPatcher
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

**Edge cases and failure modes** (binding):
- **No drafts found**: If RUN_DIR/drafts/ is empty (no writers completed), emit error_code `LINKER_NO_DRAFTS`, open BLOCKER issue, halt run
- **Patch conflict detection**: If applying patch would create conflict (existing content differs from expected base), emit error_code `LINKER_PATCH_CONFLICT`, open BLOCKER issue with diff details (see specs/08_patch_engine.md)
- **Allowed paths violation**: If patch targets file outside allowed_paths, emit error_code `LINKER_ALLOWED_PATHS_VIOLATION`, open BLOCKER issue, halt run
- **Frontmatter schema violation**: If patched file frontmatter violates frontmatter_contract.json, emit error_code `LINKER_FRONTMATTER_VIOLATION`, open BLOCKER issue
- **File system write failure**: If cannot write to site worktree (permissions, disk full), emit error_code `LINKER_WRITE_FAILED`, mark as retryable
- **Telemetry events**: MUST emit `LINKER_STARTED`, `LINKER_COMPLETED`, `ARTIFACT_WRITTEN` for patch_bundle.json, `PATCH_APPLIED` for each file

---

### W7: Validator
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

**Binding requirements**
- MUST run all required gates (see `specs/09_validation_gates.md`).
- MUST normalize tool outputs into stable issue objects:
  - stable ordering and stable IDs (see `specs/schemas/issue.schema.json`)
- MUST never "fix" issues (validator is read-only).

**Edge cases and failure modes** (binding):
- **Validation tool missing**: If required validation tool (e.g., markdownlint, hugo) not found in toolchain, emit error_code `VALIDATOR_TOOL_MISSING`, open BLOCKER issue, halt run
- **Validation tool timeout**: If validation gate exceeds timeout, emit error_code `VALIDATOR_TIMEOUT`, mark gate as failed, proceed with remaining gates
- **Validation tool crash**: If validation tool exits with unexpected error, emit error_code `VALIDATOR_TOOL_CRASH`, capture stderr, mark gate as failed, proceed
- **Zero issues found**: If all gates pass with zero issues, emit telemetry `VALIDATOR_ALL_GATES_PASSED`, proceed (success case)
- **All gates fail**: If all gates fail (not just issues found, but tool failures), emit error_code `VALIDATOR_ALL_GATES_FAILED`, open BLOCKER issue
- **Telemetry events**: MUST emit `VALIDATOR_STARTED`, `VALIDATOR_COMPLETED`, `ARTIFACT_WRITTEN` for validation_report.json, `GATE_EXECUTED` for each gate

---

### W8: Fixer
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
  - updated draft(s) under `drafts/<section>/...` **and** a new `patch_bundle.json` via W6 rerun
  - or a direct patch delta: `RUN_DIR/artifacts/patch_bundle.delta.json` (optional strategy)
- a note in `reports/fix_<issue_id>.md` (optional)

**Binding requirements**
- MUST fix exactly one issue: the issue_id supplied by the Orchestrator.
- MUST obey gate-specific fix rules in `specs/08_patch_engine.md`.
- MUST NOT introduce new factual claims without evidence.
- MUST fail with blocker `FixNoOp` if it cannot produce a meaningful diff.

**Edge cases and failure modes** (binding):
- **Issue not found**: If supplied issue_id does not exist in validation_report, emit error_code `FIXER_ISSUE_NOT_FOUND`, open BLOCKER issue, halt run
- **Unfixable issue**: If issue is marked as unfixable (no auto-fix rule), emit error_code `FIXER_UNFIXABLE`, open MAJOR issue requesting manual intervention
- **Fix produces no diff**: If fixer runs but produces zero changes, emit error_code `FIXER_NO_DIFF`, fail with BLOCKER issue `FixNoOp`
- **Fix introduces new validation errors**: If fix resolves target issue but introduces new issues, emit warning, record new issues in validation_report, continue
- **LLM API failure during fix**: If LLM provider fails during fix generation, emit error_code `FIXER_LLM_FAILURE`, mark as retryable
- **Telemetry events**: MUST emit `FIXER_STARTED`, `FIXER_COMPLETED`, `ISSUE_RESOLVED` if successful, `ISSUE_FIX_FAILED` if not

---

### W9: PRManager
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

## Acceptance
- Every worker has a complete, non-overlapping responsibility.
- All handoffs are file-based and schema-validated.
- A full dependency chain exists from RepoScout → PRManager with no hidden inputs.
