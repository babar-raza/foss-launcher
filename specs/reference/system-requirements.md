# FOSS Launcher System Requirements (extracted)

**Generated**: 2026-01-23  
**Scope**: This document extracts the system requirements that must be built, based on the repository's binding specifications (`specs/`).  
**Primary sources**: `specs/` (binding), `plans/` (LLM-ready implementation coverage), `specs/schemas/` (authoritative contracts).

## System definition

The FOSS Launcher is an agentic system that takes:
- a public GitHub product repository, and
- the target Hugo site repository (aspose.org content repo),

and produces deterministic, evidence-grounded content updates across site sections (products, docs, reference, kb, blog), validated by stop-the-line gates, delivered via a centralized commit/PR service, and fully operable through MCP tools.

## High-level requirements (root-level)

### REQ-001: Launch hundreds of products deterministically
- **Binding specs**:
  - `specs/00_overview.md`
  - `specs/10_determinism_and_caching.md`
  - `specs/01_system_contract.md`
- **Implementation coverage**:
  - `plans/00_orchestrator_master_prompt.md`
- **Acceptance (from traceability matrix)**: Deterministic hashing, stable ordering, idempotent patches

### REQ-002: Adapt to diverse repository structures
- **Binding specs**:
  - `specs/02_repo_ingestion.md`
  - `specs/26_repo_adapters_and_variability.md`
  - `specs/27_universal_repo_handling.md`
- **Implementation coverage**:
  - `plans/taskcards/INDEX.md`
- **Acceptance (from traceability matrix)**: Correct platform detection, archetype classification, adapter selection

### REQ-003: All claims must trace to evidence
- **Binding specs**:
  - `specs/03_product_facts_and_evidence.md`
  - `specs/04_claims_compiler_truth_lock.md`
  - `specs/23_claim_markers.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-410_facts_builder_w2.md`
- **Acceptance (from traceability matrix)**: EvidenceMap complete, TruthLock gate passes, claim markers present

### REQ-004: MCP endpoints for all features
- **Binding specs**:
  - `specs/14_mcp_endpoints.md`
  - `specs/24_mcp_tool_schemas.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-510_mcp_server.md`
- **Acceptance (from traceability matrix)**: MCP server runs, tools exposed, schemas valid

### REQ-005: OpenAI-compatible LLM providers only
- **Binding specs**:
  - `specs/15_llm_providers.md`
  - `specs/25_frameworks_and_dependencies.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-500_clients_services.md`
- **Acceptance (from traceability matrix)**: No provider-specific APIs, configurable endpoint/model

### REQ-006: Centralized telemetry for all events
- **Binding specs**:
  - `specs/16_local_telemetry_api.md`
  - `specs/11_state_and_events.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-500_clients_services.md`
  - `plans/taskcards/TC-580_observability_and_evidence_bundle.md`
- **Acceptance (from traceability matrix)**: All events logged via HTTP API, event schemas valid

### REQ-007: Centralized GitHub commit service
- **Binding specs**:
  - `specs/17_github_commit_service.md`
  - `specs/12_pr_and_release.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-480_pr_manager_w9.md`
- **Acceptance (from traceability matrix)**: All commits go through service, templates applied

### REQ-008: Hugo config awareness
- **Binding specs**:
  - `specs/31_hugo_config_awareness.md`
  - `specs/18_site_repo_layout.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-404_hugo_site_context_build_matrix.md`
  - `plans/taskcards/TC-550_hugo_config_awareness_ext.md`
- **Acceptance (from traceability matrix)**: Build matrix created, validation config-aware

### REQ-009: Validation gates with profiles
- **Binding specs**:
  - `specs/09_validation_gates.md`
  - `specs/19_toolchain_and_ci.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-460_validator_w7.md`
  - `plans/taskcards/TC-570_validation_gates_ext.md`

### REQ-010: Platform-aware content layout (V2)
- **Binding specs**:
  - `specs/32_platform_aware_content_layout.md`
  - `specs/18_site_repo_layout.md`
  - `specs/20_rulesets_and_templates_registry.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-540_content_path_resolver.md`
  - `plans/taskcards/TC-403_frontmatter_contract_discovery.md`
  - `plans/taskcards/TC-404_hugo_site_context_build_matrix.md`
  - `plans/taskcards/TC-570_validation_gates_ext.md`
- **Acceptance (from traceability matrix)**: - Products use `/{locale}/{platform}/` paths in V2 (NOT `/{platform}/` alone)

### REQ-011: Idempotent patch engine
- **Binding specs**:
  - `specs/08_patch_engine.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-450_linker_and_patcher_w6.md`
- **Acceptance (from traceability matrix)**: Patches apply cleanly, re-run produces same result, minimal diffs

### REQ-011a: Two pilot projects for regression
- **Binding specs**:
  - `specs/13_pilots.md`
  - `specs/pilots/README.md`
- **Implementation coverage**:
  - `plans/taskcards/TC-520_pilots_and_regression.md`
- **Acceptance (from traceability matrix)**: Both pilots produce golden outputs matching expectations

### REQ-012: No manual content edits
- **Binding specs**:
  - `specs/01_system_contract.md`
- **Implementation coverage**:
  - `plans/policies/no_manual_content_edits.md`
  - `plans/taskcards/TC-201_emergency_mode_manual_edits.md`
  - `plans/taskcards/TC-571_policy_gate_no_manual_edits.md`
  - `plans/traceability_matrix.md`
  - `plans/taskcards/INDEX.md`
- **Acceptance (from traceability matrix)**: Policy gate enforces, emergency mode flag required for manual edits


## System-wide non-negotiables
These requirements are explicitly called out as binding in `specs/01_system_contract.md`:

- 1) **Scale**: designed to launch and maintain hundreds of products with diverse repo structures.
- 2) **LLM provider**: MUST use OpenAI-compatible APIs (example: Ollama OpenAI-compatible endpoint).
- 3) **MCP**: MUST expose MCP endpoints/tools for all features (not CLI-only).
- 4) **Telemetry**: MUST use centralized local-telemetry via HTTP API for all run events and all LLM operations.
- 5) **Commits**: MUST commit to aspose.org via a centralized GitHub commit service with configurable message/body templates.
- 6) **Adaptation**: MUST adapt to different repo structures and product platform/language via repo profiling and adapters.
- 7) **Change control + versioning**:


## Run configuration (input contract)
The runtime is driven by a `run_config` artifact that MUST validate against `specs/schemas/run_config.schema.json`.

### Required fields
- `schema_version`
- `product_slug`
- `product_name`
- `family`
- `github_repo_url`
- `github_ref`
- `required_sections`
- `site_layout`
- `allowed_paths`
- `llm`
- `mcp`
- `telemetry`
- `commit_service`
- `templates_version`
- `ruleset_version`
- `allow_inference`
- `max_fix_attempts`

### Key override and control fields
- `site_repo_url`
- `site_ref`
- `workflows_repo_url`
- `workflows_ref`
- `canonical_urls`
- `platform_hints`
- `target_platform`
- `layout_mode`
- `allow_manual_edits`


## Required artifacts and outputs
All runs are persisted under `RUN_DIR = runs/<run_id>/` (see `specs/29_project_repo_structure.md`).
At minimum, the system MUST write the following JSON artifacts under `RUN_DIR/artifacts/` (validated by schemas):

- `repo_inventory.json` (schema: `repo_inventory.schema.json`): Inventory of repo tree, fingerprints, language/platform signals
- `frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`): Discovered frontmatter fields per section/family
- `site_context.json` (schema: `site_context.schema.json`): Resolved site/workflows refs, content roots, build matrix
- `hugo_facts.json` (schema: `hugo_facts.schema.json`): Normalized Hugo configuration facts
- `product_facts.json` (schema: `product_facts.schema.json`): Extracted facts about product, features, formats, APIs
- `evidence_map.json` (schema: `evidence_map.schema.json`): Evidence anchors mapping claim IDs to repo paths and line ranges
- `snippet_catalog.json` (schema: `snippet_catalog.schema.json`): Curated code snippets with provenance and tags
- `truth_lock_report.json` (schema: `truth_lock_report.schema.json`): TruthLock compilation results and uncited-claim enforcement
- `page_plan.json` (schema: `page_plan.schema.json`): Exact pages to create/update per section, with requirements
- `patch_bundle.json` (schema: `patch_bundle.schema.json`): Idempotent patch operations against site repo
- `validation_report.json` (schema: `validation_report.schema.json`): Gate results, issues, and overall ok flag
- `snapshot.json` (schema: `snapshot.schema.json`): Event-sourced snapshot for resume (written at key steps)

Additional required output surfaces include:
- A deterministic local event log plus snapshots to support replay and resume (`specs/state-management.md`).
- Human-readable reports under `RUN_DIR/reports/` (diff reports, master review, gate logs).
- Draft markdown content under `RUN_DIR/drafts/<section>/...` that mirrors final site paths (`specs/29_project_repo_structure.md`).


## Worker set (W1 to W9)
Workers are the unit of work coordinated by the orchestrator. The minimum worker set is defined in `specs/21_worker_contracts.md`.

### W1: RepoScout
- **Goal**: clone and fingerprint the GitHub repo and the target site repo, then build `repo_inventory.json` and `frontmatter_contract.json` (site discovery).
- **Inputs**:
  - `RUN_DIR/run_config.yaml` (or JSON equivalent; validated against `run_config.schema.json`)
- **Outputs**:
  - `RUN_DIR/artifacts/repo_inventory.json` (schema: `repo_inventory.schema.json`)
  - `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
  - `RUN_DIR/artifacts/site_context.json` (schema: `site_context.schema.json`)
  - `RUN_DIR/artifacts/hugo_facts.json` (schema: `hugo_facts.schema.json`)

### W2: FactsBuilder
- **Goal**: build ProductFacts and EvidenceMap with stable claim IDs.
- **Inputs**:
  - `RUN_DIR/artifacts/repo_inventory.json`
  - repo worktree (read-only)
  - optional: extra evidence URLs from run_config
- **Outputs**:
  - `RUN_DIR/artifacts/product_facts.json` (schema: `product_facts.schema.json`)
  - `RUN_DIR/artifacts/evidence_map.json` (schema: `evidence_map.schema.json`)

### W3: SnippetCurator
- **Goal**: extract, normalize, and tag reusable code snippets with provenance.
- **Inputs**:
  - `RUN_DIR/artifacts/repo_inventory.json`
  - `RUN_DIR/artifacts/product_facts.json`
  - repo worktree (read-only)
- **Outputs**:
  - `RUN_DIR/artifacts/snippet_catalog.json` (schema: `snippet_catalog.schema.json`)

### W4: IAPlanner
- **Goal**: produce a complete PagePlan before any writing.
- **Inputs**:
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - `RUN_DIR/artifacts/snippet_catalog.json`
  - run_config
  - `RUN_DIR/artifacts/frontmatter_contract.json` (schema: `frontmatter_contract.schema.json`)
  - site worktree (read-only, under allowed_paths)
- **Outputs**:
  - `RUN_DIR/artifacts/page_plan.json` (schema: `page_plan.schema.json`)

### W5: SectionWriter (one per section)
- **Goal**: draft Markdown for the pages assigned to that section.
- **Inputs**:
  - `RUN_DIR/artifacts/page_plan.json`
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - `RUN_DIR/artifacts/snippet_catalog.json`
  - `specs/templates/**` + ruleset (read-only)
- **Outputs**:
  - `RUN_DIR/drafts/<section>/<output_path>` (mirrors `page_plan.pages[].output_path`; see `specs/29_project_repo_structure.md`)

### W6: LinkerAndPatcher
- **Goal**: convert drafts into a PatchBundle and apply to the site worktree deterministically.
- **Inputs**:
  - `RUN_DIR/drafts/**`
  - `RUN_DIR/artifacts/page_plan.json`
  - site worktree (writeable, restricted by allowed_paths)
  - `specs/templates/**` registry + ruleset (read-only)
- **Outputs**:
  - `RUN_DIR/artifacts/patch_bundle.json` (schema: `patch_bundle.schema.json`)
  - `RUN_DIR/reports/diff_report.md` (human-readable)

### W7: Validator
- **Goal**: run all validation gates and produce a single ValidationReport.
- **Inputs**:
  - site worktree (current)
  - `RUN_DIR/artifacts/page_plan.json`
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - `RUN_DIR/artifacts/patch_bundle.json` (if present)
  - toolchain lock (see `specs/19_toolchain_and_ci.md`)
- **Outputs**:
  - `RUN_DIR/artifacts/validation_report.json` (schema: `validation_report.schema.json`)

### W8: Fixer
- **Goal**: apply the minimal change required to fix exactly one selected issue.
- **Inputs**:
  - `RUN_DIR/artifacts/validation_report.json`
  - `RUN_DIR/artifacts/page_plan.json`
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - site worktree (writeable, restricted by allowed_paths)
  - toolchain lock + ruleset
- **Outputs**:
  - One of:
  - updated draft(s) under `drafts/<section>/...` **and** a new `patch_bundle.json` via W6 rerun
  - or a direct patch delta: `RUN_DIR/artifacts/patch_bundle.delta.json` (optional strategy)
  - a note in `reports/fix_<issue_id>.md` (optional)

### W9: PRManager
- **Goal**: open a PR via the commit service with deterministic branch naming and PR body.
- **Inputs**:
  - site worktree diff (current)
  - `RUN_DIR/reports/diff_report.md`
  - `RUN_DIR/artifacts/validation_report.json`
  - run_config (commit templates)
- **Outputs**:
  - `RUN_DIR/artifacts/pr.json` (optional; includes pr_url, branch, commit_sha)



## Orchestrator workflow model
The orchestrator workflow is defined by `specs/state-graph.md` and `specs/11_state_and_events.md`.

### Authoritative run state progression
```
CREATED → CLONED_INPUTS → INGESTED → FACTS_READY → PLAN_READY → DRAFTING
→ DRAFT_READY → LINKING → VALIDATING → (FIXING → VALIDATING)* → READY_FOR_PR
→ PR_OPENED → DONE

Failure: any state → FAILED  
Cancel: any state → CANCELLED (optional; see MCP tools)

## Required artifacts by state
- CLONED_INPUTS:
  - resolved repo_sha and site_sha recorded in `repo_inventory.json`
  - `RUN_DIR/artifacts/frontmatter_contract.json`
- INGESTED:
  - `RUN_DIR/artifacts/repo_inventory.json`
- FACTS_READY:
  - `RUN_DIR/artifacts/product_facts.json`
  - `RUN_DIR/artifacts/evidence_map.json`
  - `RUN_DIR/artifacts/snippet_catalog.json`
- PLAN_READY:
  - `RUN_DIR/artifacts/page_plan.json`
- DRAFT_READY:
  - drafts exist for all required sections under `RUN_DIR/drafts/<section>/`
- LINKING:
  - `RUN_DIR/artifacts/patch_bundle.json` exists
  - `RUN_DIR/reports/diff_report.md` exists
- VALIDATING:
  - `RUN_DIR/artifacts/validation_report.json` exists
- READY_FOR_PR:
  - last `validation_report.json` has `ok=true`

## Orchestrator nodes (graph nodes)
Each node corresponds to (one or more) workers and emits `RUN_STATE_CHANGED` on transition.

### Node 1: clone_inputs
**Entry state:** CREATED  
**Worker:** W1 RepoScout  
**Outputs:** `RUN_DIR/artifacts/repo_inventory.json`, `RUN_DIR/artifacts/frontmatter_contract.json`, `RUN_DIR/artifacts/site_context.json`, `RUN_DIR/artifacts/hugo_facts.json`  
**Exit state:** CLONED_INPUTS

**Failure:** missing config → FAILED (blocker)

---

### Node 2: ingest_repo
**Entry state:** CLONED_INPUTS  
**Worker:** none (optional placeholder)  
**Purpose:** reserved for future steps that materialize extra sources (e.g., download external docs).  
**Exit state:** INGESTED

**Binding rule:** if unused, this node is a no-op that still records state transition deterministically.

---

### Node 3: build_facts
**Entry state:** INGESTED  
**Workers:** W2 FactsBuilder → W3 SnippetCurator (ordered)  
**Outputs:** `RUN_DIR/artifacts/product_facts.json`, `RUN_DIR/artifacts/evidence_map.json`, `RUN_DIR/artifacts/snippet_catalog.json`  
**Exit state:** FACTS_READY

**Failure rules:**
- missing evidence for required claims with `allow_inference=false` → FAILED (blocker)

---

### Node 4: build_plan
**Entry state:** FACTS_READY  
**Worker:** W4 IAPlanner  
**Outputs:** `RUN_DIR/artifacts/page_plan.json`  
**Exit state:** PLAN_READY

---

### Node 5: draft_sections (fan-out)
**Entry state:** PLAN_READY  
**Workers:** W5 SectionWriter per section (parallel)  
**Outputs:** drafts under `RUN_DIR/drafts/<section>/...`  
**Exit state:** DRAFT_READY

**Parallel safety rule (binding):**
- writers write only to `drafts/<section>/`
- writers never touch the site worktree

---

### Node 6: merge_and_link
**Entry state:** DRAFT_READY  
**Worker:** W6 LinkerAndPatcher  
**Outputs:** `RUN_DIR/artifacts/patch_bundle.json`, `RUN_DIR/reports/diff_report.md`  
**Exit state:** LINKING

---

### Node 7: validate
**Entry state:** LINKING or FIXING  
**Worker:** W7 Validator  
**Outputs:** `RUN_DIR/artifacts/validation_report.json`  
**Exit state:** VALIDATING

---

### Node 8: fix_next (single-issue)
**Entry state:** VALIDATING  
**Condition:** `validation_report.ok == false`  
**Worker:** W8 Fixer  
**Exit state:** FIXING

**Selection rule (binding):**
- the Orchestrator selects exactly one issue:
  - first by stable ordering in `specs/10_determinism_and_caching.md`
  - must be severity blocker/error (warning-only does not enter fix loop)

**Stop rules (binding):**
- attempts >= `run_config.max_fix_attempts` → FAILED
- FixNoOp → FAILED
- AllowedPathsViolation → FAILED

After FIXING, the graph MUST route to Node 7 validate.

---

### Node 9: open_pr
**Entry state:** VALIDATING  
**Condition:** `validation_report.ok == true`  
**Worker:** W9 PRManager  
**Exit state:** PR_OPENED → DONE

---

### Node 10: finalize
**Entry state:** DONE  
**Worker:** none  
**Outputs:** optional summary report under `reports/`  
**Exit state:** DONE (idempotent)

## Deterministic routing rules (binding)
- Sections order: products, docs, reference, kb, blog
- Pages order: `(section_order, output_path)`
- Issues order: `(severity, gate, path, line, issue_id)`
- Fix loop always selects the first issue under the above ordering.

## Acceptance
- Every node maps cleanly to a worker contract with explicit inputs/outputs.
- The fan-out drafting node is parallel-safe by construction.
- The fix loop is explicit and capped, with deterministic issue selection.
```

Key binding properties:
- Runs MUST be replayable and resumable via event sourcing + snapshots.
- Completed work items MUST NOT be re-run unless explicitly forced or invalidated by upstream artifact changes.


## MCP tool surface (mandatory)
All system features MUST be available via MCP tools (CLI is optional but not sufficient). Source: `specs/14_mcp_endpoints.md`.

Minimum required MCP tools:
- `launch_start_run(run_config) -> { run_id }`
- `launch_start_run_from_product_url(url) -> { run_id, derived_config } — quickstart: derives run_config from Aspose product page URL`
- `launch_start_run_from_github_repo_url(github_repo_url) -> { run_id, derived_config } — quickstart: derives run_config from public GitHub repo URL`
- `launch_get_status(run_id) -> { state, section_states, open_issues, artifacts }`
- `launch_get_artifact(run_id, artifact_name) -> { content, content_type, sha256 }`
- `launch_validate(run_id) -> { validation_report }`
- `launch_fix_next(run_id) -> { applied_patch_ids, remaining_issues }`
- `launch_resume(run_id) -> { state }`
- `launch_cancel(run_id) -> { cancelled: true }`
- `launch_open_pr(run_id) -> { pr_url, branch }`
- `launch_list_runs(filter?) -> { runs[] }`

Binding behavior:
- MCP calls MUST emit telemetry events for every call.
- MCP tools MUST enforce `run_config.allowed_paths` and forbid out-of-scope edits.
- MCP tools MUST be deterministic with respect to identical inputs, within the nondeterminism limits defined by the specs.


## Binding implementation framework choices
`specs/25_frameworks_and_dependencies.md` constrains the implementation choices to remove architectural ambiguity:

- The orchestrator MUST be implemented using **LangGraph** (LangChain is allowed for prompt composition, but MUST NOT own orchestration).
- The MCP HTTP server surface MUST use **FastAPI** (dev/prod via **uvicorn**).
- The CLI (if implemented) MAY use **Typer**, but MUST call the same internal services as MCP.
- The runtime language is **Python 3.12+**.


## Development and CI environment policy
`specs/00_environment_policy.md` is binding for this repo:

- All Python work MUST use exactly one virtual environment named `.venv` at the repo root.
- No alternate venvs are permitted anywhere in the repository tree.
- Scripts and Makefile targets MUST use explicit `.venv` interpreter paths.


## Additional binding constraints (selected)

### Evidence and truth locking
- All factual statements in generated content MUST map to claim IDs and evidence anchors (see `specs/03_product_facts_and_evidence.md`, `specs/04_claims_compiler_truth_lock.md`, `specs/23_claim_markers.md`).
- `allow_inference` exists as an explicit control; inference must be labeled and constrained (see `specs/03_product_facts_and_evidence.md`).

### Change control and versioning
- Every run MUST pin `ruleset_version` and `templates_version`.
- Schema versions MUST be explicit in artifacts via `schema_version` fields.
- Behavior changes MUST be recorded by bumping versions (no silent drift). Source: `specs/01_system_contract.md`, `specs/20_rulesets_and_templates_registry.md`.

### Repo adaptation
- The system MUST adapt to diverse product repos and site layouts via profiling and adapters. Source: `specs/26_repo_adapters_and_variability.md`, `specs/27_universal_repo_handling.md`.

### Validation gates
- Gates are stop-the-line; a run is only successful when required artifacts exist and gates pass (`validation_report.ok=true`). Source: `specs/09_validation_gates.md`.

### PR and release
- Commits and PRs MUST be performed via a centralized GitHub commit service; the launcher must not directly commit to production targets. Source: `specs/17_github_commit_service.md`, `specs/12_pr_and_release.md`.

### No manual content edits by default
- Manual edits are prohibited by default, with a tightly-controlled emergency mode requiring explicit listing, diff evidence, and reporting. Source: `specs/01_system_contract.md`, `plans/policies/no_manual_content_edits.md`.

## Open questions and TBDs
For any ambiguity that would otherwise force implementation guesswork, the repo maintains:

- `OPEN_QUESTIONS.md` (must be resolved or explicitly accepted as TBD)
- `DECISIONS.md` (records resolved questions and binding architecture decisions)

Implementation SHOULD treat unresolved items as blockers and produce a blocker issue artifact as defined in `plans/taskcards/00_TASKCARD_CONTRACT.md`.


## Definition of done (run-level)

A run is considered successful when:
- All required artifacts exist and validate against schemas.
- All required validation gates pass and `validation_report.ok=true`.
- Telemetry contains a complete event trail and LLM operation logs.
- A PR is opened with a summary of pages created/updated, evidence summary, and attached validation results.
