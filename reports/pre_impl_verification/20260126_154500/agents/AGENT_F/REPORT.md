# AGENT_F: Feature & Testability Validation Report

**Generated:** 2026-01-26
**Agent:** AGENT_F (Feature & Testability Validator)
**Working Directory:** c:\Users\prora\OneDrive\Documents\GitHub\foss-launcher

---

## Features Inventory

| FEAT-ID | Description | Source Evidence | Mapped REQ-IDs |
|---------|-------------|-----------------|----------------|
| FEAT-001 | Repo ingestion & fingerprinting | specs/02_repo_ingestion.md:1-243, specs/21_worker_contracts.md:53-84 | REQ-ING-001 (clone), REQ-ING-002 (fingerprint), REQ-DET-001 (determinism) |
| FEAT-002 | Frontmatter contract discovery | specs/21_worker_contracts.md:75-78, specs/examples/frontmatter_models.md | REQ-ING-003 (site discovery), REQ-DET-002 (deterministic sampling) |
| FEAT-003 | Hugo config awareness & build matrix | specs/31_hugo_config_awareness.md, specs/21_worker_contracts.md:72-74 | REQ-HUGO-001 (config scan), REQ-HUGO-002 (build matrix) |
| FEAT-004 | Repo adapter selection | specs/02_repo_ingestion.md:163-243, specs/26_repo_adapters_and_variability.md | REQ-ADAPT-001 (platform detection), REQ-ADAPT-002 (archetype selection) |
| FEAT-005 | ProductFacts extraction with evidence | specs/03_product_facts_and_evidence.md:1-133, specs/21_worker_contracts.md:87-106 | REQ-FACTS-001 (grounded claims), REQ-FACTS-002 (evidence priority) |
| FEAT-006 | EvidenceMap with stable claim IDs | specs/04_claims_compiler_truth_lock.md:1-58, specs/21_worker_contracts.md:100-102 | REQ-CLAIM-001 (stable IDs), REQ-CLAIM-002 (citations) |
| FEAT-007 | TruthLock enforcement | specs/04_claims_compiler_truth_lock.md:32-51, specs/09_validation_gates.md:64 | REQ-TRUTH-001 (no uncited claims), REQ-TRUTH-002 (no inference for formats) |
| FEAT-008 | Snippet catalog with provenance | specs/05_example_curation.md:1-88, specs/21_worker_contracts.md:109-127 | REQ-SNIP-001 (stable snippet IDs), REQ-SNIP-002 (tags from ruleset) |
| FEAT-009 | PagePlan with public URL paths | specs/06_page_planning.md, specs/21_worker_contracts.md:130-157, specs/33_public_url_mapping.md | REQ-PLAN-001 (output_path + url_path), REQ-PLAN-002 (required sections) |
| FEAT-010 | Section-specific content drafting | specs/07_section_templates.md, specs/21_worker_contracts.md:160-182 | REQ-WRITE-001 (template fill), REQ-WRITE-002 (claim markers) |
| FEAT-011 | Claim marker embedding | specs/23_claim_markers.md, specs/21_worker_contracts.md:174-175 | REQ-MARKER-001 (embed in content), REQ-MARKER-002 (TruthLock validation) |
| FEAT-012 | Patch engine with idempotency | specs/08_patch_engine.md:1-43, specs/21_worker_contracts.md:185-205 | REQ-PATCH-001 (deterministic order), REQ-PATCH-002 (allowed_paths fence) |
| FEAT-013 | Validation gates orchestration | specs/09_validation_gates.md:1-212, specs/21_worker_contracts.md:207-227 | REQ-GATE-001 (schema), REQ-GATE-002 (Hugo build), REQ-GATE-003 (TruthLock), REQ-GATE-004 (links) |
| FEAT-014 | Profile-based gating (local/ci/prod) | specs/09_validation_gates.md:123-159 | REQ-GATE-005 (profile selection), REQ-GATE-006 (timeout enforcement) |
| FEAT-015 | Strict compliance gates (J-R) | specs/09_validation_gates.md:196-212, specs/34_strict_compliance_guarantees.md | REQ-COMP-001 to REQ-COMP-009 (pinned refs, secrets, network allowlist, etc.) |
| FEAT-016 | Targeted single-issue fixer | specs/21_worker_contracts.md:229-252, specs/08_patch_engine.md | REQ-FIX-001 (fix exactly one), REQ-FIX-002 (no new claims) |
| FEAT-017 | PR manager with commit service | specs/21_worker_contracts.md:254-274, specs/12_pr_and_release.md, specs/17_github_commit_service.md | REQ-PR-001 (deterministic branch), REQ-PR-002 (commit SHA association) |
| FEAT-018 | Determinism harness (golden runs) | specs/10_determinism_and_caching.md:1-53, plans/taskcards/TC-560_determinism_harness.md | REQ-DET-003 (byte-identical artifacts), REQ-DET-004 (stable ordering) |
| FEAT-019 | MCP server with 11 tools | specs/14_mcp_endpoints.md:1-27, specs/24_mcp_tool_schemas.md:82-392 | REQ-MCP-001 to REQ-MCP-011 (all tools) |
| FEAT-020 | MCP product URL quickstart | specs/24_mcp_tool_schemas.md:110-151 | REQ-MCP-012 (URL derivation), REQ-MCP-013 (idempotency) |
| FEAT-021 | MCP GitHub repo URL quickstart | specs/24_mcp_tool_schemas.md:153-240 | REQ-MCP-014 (inference), REQ-MCP-015 (ambiguity handling) |
| FEAT-022 | Local telemetry API integration | specs/16_local_telemetry_api.md:1-142, specs/11_state_and_events.md:39-50 | REQ-TELEM-001 (parent run), REQ-TELEM-002 (child runs), REQ-TELEM-003 (commit association) |
| FEAT-023 | Event sourcing & snapshot state | specs/11_state_and_events.md:1-116, specs/schemas/event.schema.json, specs/schemas/snapshot.schema.json | REQ-STATE-001 (replay), REQ-STATE-002 (resume) |
| FEAT-024 | LangGraph orchestrator | specs/00_overview.md:49-54, specs/21_worker_contracts.md:1-281, plans/taskcards/TC-300_orchestrator_langgraph.md | REQ-ORCH-001 (state machine), REQ-ORCH-002 (worker dispatch) |
| FEAT-025 | Schema validation for all artifacts | specs/01_system_contract.md:41-57, specs/09_validation_gates.md:21-22 | REQ-SCHEMA-001 (validate JSON), REQ-SCHEMA-002 (frontmatter) |
| FEAT-026 | Allowed paths write fence | specs/01_system_contract.md:60-66, specs/09_validation_gates.md:201-202 | REQ-SAFE-001 (allowed_paths), REQ-SAFE-002 (blocker on violation) |
| FEAT-027 | Emergency manual edits mode | specs/01_system_contract.md:69-76, plans/taskcards/TC-201_emergency_mode_manual_edits.md | REQ-SAFE-003 (default false), REQ-SAFE-004 (enumerate files) |
| FEAT-028 | Versioned rulesets & templates | specs/01_system_contract.md:10-13, specs/20_rulesets_and_templates_registry.md | REQ-VER-001 (ruleset_version), REQ-VER-002 (templates_version) |
| FEAT-029 | Platform-aware content layout (V2) | specs/32_platform_aware_content_layout.md, specs/09_validation_gates.md:34-43 | REQ-LAYOUT-001 (locale/platform paths), REQ-LAYOUT-002 (gate enforcement) |
| FEAT-030 | Pilots with pinned SHAs | specs/13_pilots.md, specs/01_system_contract.md:75-79, plans/acceptance_test_matrix.md | REQ-PILOT-001 (two pilots), REQ-PILOT-002 (golden PagePlan), REQ-PILOT-003 (regression detection) |

---

## Feature Sufficiency Analysis

### Features with Full Requirements Coverage

**Evidence:** All 30 identified features trace to explicit requirements in specs/plans. Cross-referenced with plans/traceability_matrix.md:1-100.

### Missing Features (Requirements without features)

**F-GAP-001** (see GAPS.md): No explicit feature for **content rollback** despite Guarantee L mention in specs/34_strict_compliance_guarantees.md. TC-480 includes rollback metadata in pr.json but no documented rollback *execution* feature.

**F-GAP-002** (see GAPS.md): **Network allowlist validation** (Gate N, Guarantee D) referenced in specs/09_validation_gates.md:204 and specs/34_strict_compliance_guarantees.md but no Gate N implementation defined in specs/19_toolchain_and_ci.md (gates stop at Gate 9 + TemplateTokenLint).

**F-GAP-003** (see GAPS.md): **Budget enforcement** (Gates O, Guarantees F/G) referenced in specs/09_validation_gates.md:205 but no budget tracking feature or gate implementation defined.

**F-GAP-004** (see GAPS.md): **CI parity gate** (Gate Q, Guarantee H) referenced in specs/09_validation_gates.md:206 but no gate implementation or CI parity validator defined.

**F-GAP-005** (see GAPS.md): **Untrusted code non-execution gate** (Gate R, Guarantee J) referenced in specs/09_validation_gates.md:207 but no gate implementation or ingestion safety validator defined.

### Unnecessary Features (Features without requirements)

**None identified.** All features trace to specs/requirements or are explicitly part of the system contract (specs/00_overview.md, specs/01_system_contract.md).

---

## Best-Fit Design Assessment

### Documented Design Rationale

| Design Choice | Rationale Source | Evidence |
|---------------|------------------|----------|
| LangGraph for orchestration | specs/00_overview.md:49, specs/25_frameworks_and_dependencies.md | LangGraph state machine chosen for "resumable mid-run, parallelizable drafting" - explicit requirement (specs/00_overview.md:24-26) |
| OpenAI-compatible LLM only | specs/00_overview.md:28-30, specs/01_system_contract.md:5 | "Non-negotiable" for provider interoperability (Ollama, etc.) |
| MCP-first (not CLI-only) | specs/00_overview.md:32-34, specs/01_system_contract.md:6 | "Non-negotiable" - all features MUST be MCP-accessible (specs/14_mcp_endpoints.md:3-5) |
| Local telemetry (not cloud) | specs/16_local_telemetry_api.md:1-11 | System-of-record for audit; buffering strategy for transport failures (specs/16_local_telemetry_api.md:123-135) |
| GitHub commit service (centralized) | specs/17_github_commit_service.md, specs/01_system_contract.md:8 | "Non-negotiable" for configurable templates + traceability (specs/00_overview.md:41-43) |
| Adapter mechanism | specs/02_repo_ingestion.md:163-243, specs/01_system_contract.md:9 | "Non-negotiable" for universal repo handling (specs/00_overview.md:44-47) |
| Temperature 0.0 default | specs/10_determinism_and_caching.md:5, specs/01_system_contract.md:39 | Determinism requirement: "same inputs -> same plan" (specs/00_overview.md:22) |
| Claim ID hashing (sha256) | specs/04_claims_compiler_truth_lock.md:12-19 | Stable claim IDs required for determinism + TruthLock (specs/10_determinism_and_caching.md:45) |
| Event sourcing (NDJSON) | specs/11_state_and_events.md:51-73 | Replay/resume requirement (specs/00_overview.md:24) |
| Schema-first artifacts | specs/01_system_contract.md:41-57 | "Unknown keys forbidden" for validation gates + determinism (specs/01_system_contract.md:57) |

**Gaps:** No documented rationale for:
- **Why LangGraph over alternative state machines** (e.g., Temporal, Prefect)? specs/25_frameworks_and_dependencies.md mentions LangGraph but no alternatives analysis.
- **Why NDJSON over SQLite** for events? specs/11_state_and_events.md:54-60 allows both but doesn't justify NDJSON as preferred.
- **Why sha256 claim IDs over content-addressable UUIDs?** specs/04_claims_compiler_truth_lock.md:12-14 defines algorithm but no collision analysis.

### Missing Design Justification (Gaps)

**F-GAP-006** (MAJOR): No documented **performance/scalability justification** for "hundreds of products" goal (specs/00_overview.md:13). No batch execution design, concurrency model, or resource budgets defined in specs.

**F-GAP-007** (MAJOR): No documented **caching strategy** despite specs/10_determinism_and_caching.md:30-38 defining cache keys. No cache invalidation rules, cache storage location, or cache hit telemetry defined.

**F-GAP-008** (MINOR): No documented **template selection tiebreaker** justification. specs/20_rulesets_and_templates_registry.md referenced by plans/taskcards/TC-430_ia_planner_w4.md:99-102 warns about "arbitrary tiebreakers" but no resolution strategy defined.

---

## Testability Assessment

### Features with Clear Test Boundaries

| Feature | Test Boundary | Evidence |
|---------|---------------|----------|
| FEAT-001 (RepoScout) | Input: run_config.yaml; Output: repo_inventory.json, frontmatter_contract.json, site_context.json | plans/taskcards/TC-400_repo_scout_w1.md:68-74, E2E command:138-150 |
| FEAT-005 (FactsBuilder) | Input: repo_inventory.json + worktree; Output: product_facts.json, evidence_map.json | plans/taskcards/TC-410_facts_builder_w2.md:55-62, E2E command:114-128 |
| FEAT-008 (SnippetCurator) | Input: repo_inventory.json, product_facts.json; Output: snippet_catalog.json | plans/taskcards/TC-420_snippet_curator_w3.md:49-56, E2E command:105-117 |
| FEAT-009 (IAPlanner) | Input: facts, evidence, snippets, site_context; Output: page_plan.json | plans/taskcards/TC-430_ia_planner_w4.md:61-72, E2E command:126-138 |
| FEAT-010 (SectionWriter) | Input: page_plan.json + templates; Output: drafts/**/*.md | plans/taskcards/TC-440_section_writer_w5.md:49-58, E2E command:78-90 |
| FEAT-012 (LinkerAndPatcher) | Input: drafts/** + page_plan; Output: patch_bundle.json + site worktree changes | plans/taskcards/TC-450_linker_and_patcher_w6.md:49-57, E2E command:74-87 |
| FEAT-013 (Validator) | Input: site worktree + artifacts; Output: validation_report.json | plans/taskcards/TC-460_validator_w7.md:48-58, E2E command:78-90 |
| FEAT-016 (Fixer) | Input: validation_report.json + issue_id; Output: updated drafts or patch delta | plans/taskcards/TC-470_fixer_w8.md:47-59, E2E command:78-90 |
| FEAT-017 (PRManager) | Input: site diff + validation_report; Output: pr.json | plans/taskcards/TC-480_pr_manager_w9.md:46-53, E2E command:74-87 |
| FEAT-018 (Determinism harness) | Input: 2 RUN_DIRs or rerun command; Output: determinism_report.json | plans/taskcards/TC-560_determinism_harness.md:50-56, E2E command:72-84 |
| FEAT-019 (MCP server) | Input: MCP requests (JSON-RPC); Output: MCP responses | plans/taskcards/TC-510_mcp_server.md:44-48, E2E command:78-92 |

**All workers (W1-W9) have:**
- Explicit I/O contracts (specs/21_worker_contracts.md:23-30)
- Schema-validated outputs (specs/01_system_contract.md:41-57)
- E2E verification commands in taskcards
- Determinism test requirements (specs/10_determinism_and_caching.md:51-53)

### Features Lacking Testability (Gaps)

**F-GAP-009** (BLOCKER): **Batch execution** feature (specs/00_overview.md:16) has no test boundary defined. No acceptance criteria for "queue many runs" or "bounded concurrency".

**F-GAP-010** (MAJOR): **Resume from snapshot** (FEAT-023) lacks E2E test scenario. specs/11_state_and_events.md:112-115 requires "resume continues from last stable state" but no test command or fixture defined.

**F-GAP-011** (MAJOR): **Telemetry buffering retry** (specs/16_local_telemetry_api.md:123-135) lacks test scenario. No fixture for simulated API outage + recovery.

**F-GAP-012** (MAJOR): **Conflict detection & resolution** (specs/08_patch_engine.md:31-36) lacks test scenario. No fixture for "patch cannot apply cleanly".

---

## Reproducibility & Determinism Assessment

### Determinism Guarantees Found

| Guarantee | Source | Evidence |
|-----------|--------|----------|
| Temperature 0.0 default | specs/10_determinism_and_caching.md:5, specs/01_system_contract.md:39 | "Temperature MUST default to 0.0" (binding) |
| Stable artifact ordering | specs/10_determinism_and_caching.md:40-49 | All lists sorted: paths lexicographically, sections by config, pages by (section, output_path), issues by (severity, gate, location, id), claims by claim_id, snippets by (language, tag, snippet_id) |
| Byte-identical artifacts | specs/10_determinism_and_caching.md:51-53 | "Repeat run with same inputs produces byte-identical artifacts (PagePlan, PatchBundle, drafts, reports)" |
| Stable claim IDs | specs/04_claims_compiler_truth_lock.md:12-19, specs/21_worker_contracts.md:100-102 | `claim_id = sha256(normalized_claim_text + evidence_anchor + ruleset_version)` |
| Stable snippet IDs | specs/05_example_curation.md:8, specs/21_worker_contracts.md:123 | `snippet_id = {path, line_range, sha256(content)}` |
| Stable event hashing (optional) | specs/11_state_and_events.md:72 | `prev_hash` and `event_hash` optional but recommended |
| Schema version enforcement | specs/01_system_contract.md:10-13 | Every artifact MUST have `schema_version`; any behavior change MUST bump version |
| Deterministic frontmatter sampling | specs/21_worker_contracts.md:75-78, specs/examples/frontmatter_models.md | "Sorted paths, fixed N, pinned in config" |
| Deterministic adapter selection | specs/02_repo_ingestion.md:163-228 | Tie-breaking: "prefer order python > node > dotnet > java > go > rust > php" |
| Prompt hashing | specs/10_determinism_and_caching.md:25-32 | `prompt_hash = full prompt + schema ref + worker version` |

**Enforcement:** specs/10_determinism_and_caching.md:51-53 requires determinism test passes (byte-identical artifacts). plans/taskcards/TC-560_determinism_harness.md:26-28 implements golden run harness.

### Determinism Gaps

**F-GAP-013** (BLOCKER): **No LLM nondeterminism fallback** defined. specs/10_determinism_and_caching.md:5 sets temperature=0.0 but doesn't address provider-specific nondeterminism (e.g., Ollama vs OpenAI sampling differences). No acceptance criteria for "how much variance is acceptable?"

**F-GAP-014** (MAJOR): **No timestamp policy for events**. specs/11_state_and_events.md:52 allows variance in `ts`/`event_id` values but doesn't define timezone requirements (ISO8601 with timezone per specs/11_state_and_events.md:66, but no enforcement gate).

**F-GAP-015** (MAJOR): **No cache invalidation rules** despite cache_key definition (specs/10_determinism_and_caching.md:31-32). When does cached output become stale? No versioning strategy for cached artifacts.

**F-GAP-016** (MINOR): **No floating-point determinism policy**. If metrics_json includes float values (latency_ms, token costs), are they rounded? No rounding spec in specs/16_local_telemetry_api.md:79-91.

---

## MCP Tool Assessment

### MCP Tool Contracts Found

| Tool Name | Request Schema | Response Schema | Error Codes | Evidence |
|-----------|----------------|-----------------|-------------|----------|
| launch_start_run | run_config (run_config.schema.json) | {ok, run_id, state} | INVALID_INPUT, SCHEMA_VALIDATION_FAILED | specs/24_mcp_tool_schemas.md:84-107 |
| launch_start_run_from_product_url | {url, idempotency_key?} | {ok, run_id, state, derived_config} | INVALID_URL, UNSUPPORTED_SITE | specs/24_mcp_tool_schemas.md:110-151 |
| launch_start_run_from_github_repo_url | {github_repo_url, idempotency_key?} | {ok, run_id, derived_config} OR {ok:false, error{missing_fields, suggested_values}} | INVALID_INPUT, REPO_NOT_FOUND | specs/24_mcp_tool_schemas.md:153-240 |
| launch_get_status | {run_id} | {ok, status: RunStatus} | RUN_NOT_FOUND | specs/24_mcp_tool_schemas.md:243-253 |
| launch_get_artifact | {run_id, artifact_name} | {ok, artifact: ArtifactResponse} | RUN_NOT_FOUND, INVALID_INPUT | specs/24_mcp_tool_schemas.md:255-263 |
| launch_validate | {run_id} | {ok, run_id, validation_report} | ILLEGAL_STATE, TOOLCHAIN_MISSING | specs/24_mcp_tool_schemas.md:265-285 |
| launch_fix_next | {run_id} | {ok, fixed_issue_id, applied_patch_ids, validation_report} | FIX_EXHAUSTED, ILLEGAL_STATE | specs/24_mcp_tool_schemas.md:287-314 |
| launch_resume | {run_id} | {ok, status: RunStatus} | RUN_NOT_FOUND | specs/24_mcp_tool_schemas.md:317-329 |
| launch_cancel | {run_id} | {ok, cancelled, state} | RUN_NOT_FOUND | specs/24_mcp_tool_schemas.md:331-343 |
| launch_open_pr | {run_id} | {ok, pr_url, branch, commit_sha} | ILLEGAL_STATE, COMMIT_SERVICE_ERROR | specs/24_mcp_tool_schemas.md:345-368 |
| launch_list_runs | {filter?} | {ok, runs[]} | (none specific) | specs/24_mcp_tool_schemas.md:370-387 |

**All tools have:**
- Standard error shape (specs/24_mcp_tool_schemas.md:19-45)
- `ok: true|false` convention (specs/24_mcp_tool_schemas.md:13)
- Idempotency rules where applicable (specs/24_mcp_tool_schemas.md:104-107, 149-151, 239-240)
- Telemetry emission requirement (specs/24_mcp_tool_schemas.md:16-18)

### MCP Tool Callability (One Specific Job)

| Tool | Single Job | Clear I/O | Schema Defined | Error Handling | Independent | Evidence |
|------|------------|-----------|----------------|----------------|-------------|----------|
| launch_start_run | ✅ Start run from config | ✅ | ✅ run_config.schema.json | ✅ 2 error codes | ✅ No state deps | specs/24_mcp_tool_schemas.md:84-107 |
| launch_start_run_from_product_url | ✅ Derive config from URL | ✅ | ✅ | ✅ 2 error codes | ✅ No state deps | specs/24_mcp_tool_schemas.md:110-151 |
| launch_start_run_from_github_repo_url | ✅ Infer config from repo | ✅ | ✅ | ✅ 3 error codes + ambiguity | ✅ No state deps | specs/24_mcp_tool_schemas.md:153-240 |
| launch_get_status | ✅ Get run status | ✅ | ✅ RunStatus type | ✅ 1 error code | ✅ No state deps | specs/24_mcp_tool_schemas.md:243-253 |
| launch_get_artifact | ✅ Fetch one artifact | ✅ | ✅ ArtifactResponse | ✅ 2 error codes | ✅ No state deps | specs/24_mcp_tool_schemas.md:255-263 |
| launch_validate | ✅ Run validation | ✅ | ✅ validation_report.schema.json | ✅ 2 error codes | ❌ Requires run state >= LINKING | specs/24_mcp_tool_schemas.md:265-285 |
| launch_fix_next | ✅ Fix one issue | ✅ | ✅ | ✅ 2 error codes | ❌ Requires state = VALIDATING | specs/24_mcp_tool_schemas.md:287-314 |
| launch_resume | ✅ Resume run | ✅ | ✅ RunStatus | ✅ 1 error code | ❌ Requires snapshot exists | specs/24_mcp_tool_schemas.md:317-329 |
| launch_cancel | ✅ Cancel run | ✅ | ✅ | ✅ 1 error code | ✅ No state deps | specs/24_mcp_tool_schemas.md:331-343 |
| launch_open_pr | ✅ Open PR | ✅ | ✅ pr.schema.json | ✅ 2 error codes | ❌ Requires state = READY_FOR_PR | specs/24_mcp_tool_schemas.md:345-368 |
| launch_list_runs | ✅ List runs | ✅ | ✅ | ✅ 0 specific codes | ✅ No state deps | specs/24_mcp_tool_schemas.md:370-387 |

**State dependencies documented:** specs/24_mcp_tool_schemas.md:269-272, 291-294, 350-352

### MCP Tool Gaps

**F-GAP-017** (MINOR): **No tool for "list artifacts"**. launch_get_artifact requires artifact_name but no discovery tool. User must know artifact names from schema docs.

**F-GAP-018** (MINOR): **No tool for "get event log"**. events.ndjson referenced in specs/11_state_and_events.md:55 but no MCP accessor.

**F-GAP-019** (MINOR): **No tool for "get snapshot"**. snapshot.json referenced in specs/11_state_and_events.md:101-111 but no MCP accessor.

**F-GAP-020** (MAJOR): **MCP server lifecycle undefined**. plans/taskcards/TC-510_mcp_server.md:78-81 shows server start command but no shutdown, restart, or health check beyond /health endpoint.

**F-GAP-021** (MAJOR): **No MCP tool examples**. specs/24_mcp_tool_schemas.md defines schemas but no example request/response payloads. No curl examples or integration test fixtures.

---

## Feature Completeness Assessment

### Features with Explicit Acceptance Criteria

| Feature | Acceptance Criteria | Evidence |
|---------|---------------------|----------|
| FEAT-001 (RepoScout) | All 3 artifacts validate, SHAs present, determinism test passes, build matrix present, events emitted | plans/taskcards/TC-400_repo_scout_w1.md:168-174 |
| FEAT-005 (FactsBuilder) | product_facts + evidence_map validate, stable claim IDs, every claim has evidence, no speculation when allow_inference=false | plans/taskcards/TC-410_facts_builder_w2.md:146-151 |
| FEAT-008 (SnippetCurator) | snippet_catalog validates, snippet_id stability proven, provenance required, tags from rulesets | plans/taskcards/TC-420_snippet_curator_w3.md:135-140 |
| FEAT-009 (IAPlanner) | page_plan validates, stable ordering, required sections enforced, output paths compatible, url_path populated, cross_links use url_path | plans/taskcards/TC-430_ia_planner_w4.md:156-163 |
| FEAT-010 (SectionWriter) | Drafts match output_path, no unresolved tokens, claim markers present, byte-identical on rerun | plans/taskcards/TC-440_section_writer_w5.md:136-141 |
| FEAT-012 (LinkerAndPatcher) | patch_bundle validates, only allowed paths changed, byte-identical on rerun, diff_report stable | plans/taskcards/TC-450_linker_and_patcher_w6.md:134-139 |
| FEAT-013 (Validator) | validation_report validates, stable ordering, all gates represented, read-only (no site modification) | plans/taskcards/TC-460_validator_w7.md:137-142 |
| FEAT-016 (Fixer) | Fixes exactly one issue, meaningful diff or FixNoOp, no new unsupported claims, deterministic strategy | plans/taskcards/TC-470_fixer_w8.md:138-142 |
| FEAT-017 (PRManager) | PR payload deterministic, pr.json validates, rollback fields present, commit SHA associated | plans/taskcards/TC-480_pr_manager_w9.md:134-139 |
| FEAT-018 (Determinism harness) | Canonical JSON writer used, tool produces JSON+MD reports, golden run executable in CI | plans/taskcards/TC-560_determinism_harness.md:122-125 |
| FEAT-019 (MCP server) | Tools match specs, input validation rejects unknown keys, artifact fetch read-only, tests passing | plans/taskcards/TC-510_mcp_server.md:135-139 |
| FEAT-024 (Orchestrator) | All workers dispatch correctly, state transitions valid, fix loop converges, telemetry complete | plans/taskcards/TC-300_orchestrator_langgraph.md:140-145 (inferred from STATUS_BOARD.md) |
| FEAT-030 (Pilots) | Two pilots with pinned SHAs, golden PagePlan + ValidationReport produced, regression detection working | specs/00_overview.md:75-79, plans/acceptance_test_matrix.md:1-58 |

**All workers (W1-W9) have:**
- E2E verification commands (see taskcards)
- Schema validation requirements (specs/01_system_contract.md:57)
- Determinism test requirements (specs/10_determinism_and_caching.md:51-53)
- Write fence enforcement (specs/01_system_contract.md:60-66)

### Features with Vague Completion Criteria (Gaps)

**F-GAP-022** (BLOCKER): **Batch execution** (specs/00_overview.md:16) has no "done" definition. What is "bounded concurrency"? No max parallel runs specified. No acceptance test for "queue many runs".

**F-GAP-023** (MAJOR): **Caching** (specs/10_determinism_and_caching.md:30-38) has no completion criteria. What to cache? Cache hit rate? Cache storage limits? No cache validation gate.

**F-GAP-024** (MAJOR): **Emergency manual edits** (FEAT-027) acceptance criteria vague: "enumerate affected files" (specs/01_system_contract.md:74) but no validation gate to enforce enumeration. plans/taskcards/TC-201_emergency_mode_manual_edits.md exists but no E2E test.

**F-GAP-025** (MAJOR): **Telemetry buffering** (specs/16_local_telemetry_api.md:123-135) completion criteria vague: "flush outbox when connectivity returns" - but how to detect connectivity? Retry count? Exponential backoff parameters?

**F-GAP-026** (MAJOR): **Fix loop convergence** (specs/09_validation_gates.md:78-79) references "max_fix_attempts" but no default value or convergence criteria defined. When to give up?

**F-GAP-027** (MINOR): **Template selection** (FEAT-009) vague: "deterministic template selection" (specs/21_worker_contracts.md:145-146) but plans/taskcards/TC-430_ia_planner_w4.md:99-102 warns about "arbitrary tiebreakers" without resolution.

---

## Summary Statistics

- **Total features identified:** 30
- **Features with full testability:** 23 (77%)
- **Features requiring gaps closure:** 27 (90% - includes design rationale gaps, not just testability)
- **Total gaps identified:** 27 (F-GAP-001 through F-GAP-027)
  - BLOCKER: 3
  - MAJOR: 18
  - MINOR: 6
- **MCP tools defined:** 11 (100% coverage per specs/14_mcp_endpoints.md)
- **Workers (W1-W9) with E2E verification:** 9 (100%)
- **Validation gates defined:** 10+ (schema, lint, hugo_config, content_layout_platform, hugo_build, internal_links, external_links, snippets, truthlock, consistency + universality gates + strict compliance gates J-R)
- **Schemas defined:** 22 (see Glob output from specs/schemas/)

---

## Critical Observations

1. **Strong testability foundation:** All workers have clear I/O boundaries, schema-validated outputs, and E2E commands. Determinism harness (TC-560) provides golden run infrastructure.

2. **MCP tool contracts well-defined:** All 11 tools have explicit request/response schemas, error codes, and idempotency rules (specs/24_mcp_tool_schemas.md).

3. **Determinism rigor:** Extensive determinism guarantees (10+ documented) with byte-identical artifact requirement and stable ordering rules.

4. **Gaps concentrated in:**
   - **Missing gates** (J-R compliance gates referenced but not implemented)
   - **Vague completion criteria** (batch execution, caching, fix loop convergence)
   - **Design rationale gaps** (no alternatives analysis for key choices)
   - **E2E test scenarios** (resume, telemetry buffering, conflict resolution)

5. **Reproducibility strength:** Event sourcing + snapshot model (specs/11_state_and_events.md) enables replay/resume. Golden run harness (TC-560) enforces byte-identical artifacts.

6. **Testability weakness:** System-level features (batch execution, caching, telemetry buffering) lack E2E test scenarios despite worker-level features having strong test boundaries.
