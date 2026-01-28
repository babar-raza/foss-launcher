# Specs ↔ Taskcards Traceability Matrix

This document reduces “agent guessing” by making it explicit **which taskcards implement and/or validate** each spec area.

> Rule: if a spec section has no taskcard coverage, it is a **plan gap** and must be addressed by adding a micro taskcard.

## Core contracts
- `specs/00_environment_policy.md`
  - Implement: TC-100 (.venv setup, validation enforcement)
  - Validate: Gate 0 (.venv policy validation)
- `specs/00_overview.md`
  - Implement: TC-300 (orchestrator architecture), TC-100 (repo bootstrap)
- `specs/01_system_contract.md`
  - Implement: TC-300, TC-200, TC-201
  - Validate: TC-460, TC-570, TC-571
- `specs/10_determinism_and_caching.md`
  - Implement: TC-200, TC-560, TC-401..TC-404
  - Validate: TC-560, TC-460, TC-522 (CLI determinism proof), TC-523 (MCP determinism proof)
- `specs/11_state_and_events.md`
  - Implement: TC-300, TC-200
  - Validate: TC-460
- `specs/state-graph.md`
  - **Purpose**: Defines LangGraph state machine transitions for orchestrator
  - **Implement**: TC-300 (Orchestrator graph definition, node transitions, edge conditions)
  - **Validate**: TC-300 (graph smoke tests, transition determinism tests)
  - **Status**: Spec complete, TC-300 not started
- `specs/state-management.md`
  - **Purpose**: Defines state persistence, snapshot updates, event log structure
  - **Implement**: TC-300 (state serialization, snapshot creation, event sourcing)
  - **Validate**: TC-300 (determinism tests for state serialization)
  - **Status**: Spec complete, TC-300 not started
- `specs/28_coordination_and_handoffs.md`
  - **Purpose**: Defines orchestrator-to-worker handoff contracts and coordination patterns
  - **Implement**: TC-300 (worker orchestration, handoff logic, state transitions)
  - **Validate**: TC-300 (orchestrator integration tests)
  - **Status**: Spec complete, TC-300 not started

## Inputs, repos, and site awareness
- `specs/02_repo_ingestion.md`
  - Implement: TC-401, TC-402
- `specs/18_site_repo_layout.md`
  - Implement: TC-404, TC-540, TC-430
- `specs/26_repo_adapters_and_variability.md`
  - Implement: TC-402 (repo fingerprinting, archetype detection), TC-403 (frontmatter contract discovery)
- `specs/27_universal_repo_handling.md`
  - Implement: TC-400 (RepoScout orchestration), TC-402 (universal detection strategies)
- `specs/29_project_repo_structure.md`
  - Implement: TC-100 (repo bootstrap), TC-200 (RUN_DIR layout schemas)
- `specs/30_site_and_workflow_repos.md`
  - Implement: TC-401
- `specs/31_hugo_config_awareness.md`
  - Implement: TC-404, TC-550
  - Validate: TC-460, TC-570

## Platform-aware content layout (V2)
- `specs/32_platform_aware_content_layout.md`
  - Implement: TC-540, TC-403, TC-404, TC-570
  - Validate: TC-570 (platform layout gate)

## Facts, evidence, truth lock
- `specs/03_product_facts_and_evidence.md`
  - Implement: TC-411, TC-412
- `specs/04_claims_compiler_truth_lock.md`
  - Implement: TC-413, TC-460 (truth-lock gate integration)
  - Validate: TC-460, TC-570
- `specs/23_claim_markers.md`
  - Implement: TC-413 (claim ID assignment), TC-440 (claim marker insertion in content)
  - Validate: TC-460 (claim marker validation gate)

## Snippets and page planning
- `specs/05_example_curation.md`
  - Implement: TC-421, TC-422
- `specs/06_page_planning.md`
  - Implement: TC-430
- `specs/07_section_templates.md`
  - Implement: TC-440
- `specs/20_rulesets_and_templates_registry.md`
  - Implement: TC-100 (ruleset/template versioning in repo), TC-440 (template selection), TC-200 (ruleset schema validation)
  - Validate: Gate A1 (spec pack validation includes ruleset validation)

## Patch engine and safety
- `specs/08_patch_engine.md`
  - Implement: TC-450, TC-540
  - Validate: TC-571
- `specs/22_navigation_and_existing_content_update.md`
  - **Purpose**: Defines navigation planning and existing content update strategies
  - **Implement**: TC-430 (navigation planning), TC-450 (content linking and updates)
  - **Validate**: TC-460 (link validation gate)
  - **Status**: Spec complete, implementation coverage via TC-430 and TC-450
- `plans/policies/no_manual_content_edits.md`
  - Implement/Validate: TC-201, TC-571

## Validation and release
- `specs/09_validation_gates.md`
  - Implement: TC-460, TC-570, TC-571
- `specs/12_pr_and_release.md`
  - Implement: TC-480
- `specs/13_pilots.md`
  - Implement: TC-520
  - Validate: TC-522 (CLI E2E), TC-523 (MCP E2E)

## Services and integrations
- `specs/14_mcp_endpoints.md`, `specs/24_mcp_tool_schemas.md`
  - Implement: TC-510, TC-511 (product URL quickstart), TC-512 (GitHub repo URL quickstart)
  - Validate: TC-523 (MCP E2E)
- `specs/15_llm_providers.md`
  - Implement: TC-500
- `specs/16_local_telemetry_api.md`
  - Implement: TC-500
- `specs/17_github_commit_service.md`
  - Implement: TC-500, TC-480
- `specs/19_toolchain_and_ci.md`
  - Implement: TC-100 (toolchain.lock.yaml), TC-530 (CLI entrypoints), TC-560 (determinism harness)
  - Validate: Gate A1 (toolchain lock validation), Gate Q (CI parity)
- `specs/25_frameworks_and_dependencies.md`
  - Implement: TC-100 (dependency pinning), TC-300 (LangGraph orchestrator)
  - Validate: Gate K (supply chain pinning)

## Worker Contracts

- `specs/21_worker_contracts.md`
  - **Purpose**: Defines input/output contracts for all 9 workers (W1-W9)
  - **Implement**: TC-400 (W1 RepoScout), TC-410 (W2 FactsBuilder), TC-420 (W3 SnippetCurator), TC-430 (W4 IAPlanner), TC-440 (W5 SectionWriter), TC-450 (W6 Linker/Patcher), TC-460 (W7 Validator), TC-470 (W8 Fixer), TC-480 (W9 PRManager)
  - **Validate**: TC-522 (CLI E2E), TC-523 (MCP E2E)
  - **Status**: ✅ Spec complete, each worker taskcard implements its contract

## Strict compliance guarantees
- `specs/34_strict_compliance_guarantees.md`
  - Implement: Multiple taskcards implement specific guarantees (see STRICT_COMPLIANCE_GUARANTEES.md for mapping)
  - Validate: Gates J, K, L, M, N, O, R, S (guarantee-specific validation gates)

## Schemas and their governing specs
### Schema → Spec → Gate Mapping

- `specs/schemas/run_config.schema.json`
  - Governed by: specs/01_system_contract.md, specs/34_strict_compliance_guarantees.md
  - Validated by: Gate 1 (schema validation), Gate J (pinned refs), Gate O (budgets), Gate P (version locks)
  - Required fields enforce: budgets (Guarantees F, G), version locks (Guarantee K), allowed_paths (Guarantee B)

- `specs/schemas/validation_report.schema.json`
  - Governed by: specs/09_validation_gates.md, specs/01_system_contract.md
  - Produced by: TC-460 (Validator W7), TC-570 (validation gates extensions)
  - Required fields: ok, profile, gates[], issues[]
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/issue.schema.json`
  - Governed by: specs/09_validation_gates.md, specs/01_system_contract.md (error handling)
  - Used by: All gates and validators
  - Required error_code for error/blocker severity (per specs/01_system_contract.md:87-93)
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/repo_inventory.schema.json`
  - Governed by: specs/02_repo_ingestion.md, specs/26_repo_adapters_and_variability.md
  - Produced by: TC-401, TC-402 (W1 RepoScout)
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/frontmatter_contract.schema.json`
  - Governed by: specs/18_site_repo_layout.md, specs/31_hugo_config_awareness.md
  - Produced by: TC-403 (W1 frontmatter discovery)
  - Validated by: Gate 1 (schema validation), Gate 2 (frontmatter validation)

- `specs/schemas/site_context.schema.json`
  - Governed by: specs/18_site_repo_layout.md, specs/30_site_and_workflow_repos.md, specs/31_hugo_config_awareness.md
  - Produced by: TC-404 (W1 Hugo site context)
  - Validated by: Gate 1 (schema validation), Gate 3 (hugo_config)

- `specs/schemas/product_facts.schema.json`
  - Governed by: specs/03_product_facts_and_evidence.md, specs/04_claims_compiler_truth_lock.md
  - Produced by: TC-411 (W2 FactsBuilder)
  - Validated by: Gate 1 (schema validation), Gate 9 (TruthLock)

- `specs/schemas/evidence_map.schema.json`
  - Governed by: specs/03_product_facts_and_evidence.md, specs/04_claims_compiler_truth_lock.md
  - Produced by: TC-412 (W2 EvidenceMap linking)
  - Validated by: Gate 1 (schema validation), Gate 9 (TruthLock)

- `specs/schemas/truth_lock_report.schema.json`
  - Governed by: specs/04_claims_compiler_truth_lock.md
  - Produced by: TC-413 (W2 truth lock compile)
  - Validated by: Gate 1 (schema validation), Gate 9 (TruthLock)

- `specs/schemas/snippet_catalog.schema.json`
  - Governed by: specs/05_example_curation.md
  - Produced by: TC-421, TC-422 (W3 SnippetCurator)
  - Validated by: Gate 1 (schema validation), Gate 8 (snippet checks)

- `specs/schemas/page_plan.schema.json`
  - Governed by: specs/06_page_planning.md, specs/32_platform_aware_content_layout.md
  - Produced by: TC-430 (W4 IAPlanner)
  - Validated by: Gate 1 (schema validation), Gate 4 (content_layout_platform)

- `specs/schemas/patch_bundle.schema.json`
  - Governed by: specs/08_patch_engine.md, specs/34_strict_compliance_guarantees.md (Guarantee G)
  - Produced by: TC-450 (W6 LinkerAndPatcher)
  - Validated by: Gate 1 (schema validation), Gate O (change budgets)

- `specs/schemas/event.schema.json`
  - Governed by: specs/11_state_and_events.md, state-management.md
  - Produced by: All workers (event emission)
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/snapshot.schema.json`
  - Governed by: specs/11_state_and_events.md, state-management.md
  - Produced by: Orchestrator (TC-300)
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/pr.schema.json`
  - Governed by: specs/12_pr_and_release.md, specs/34_strict_compliance_guarantees.md (Guarantee L)
  - Produced by: TC-480 (W9 PRManager)
  - Validated by: Gate 1 (schema validation)
  - Required rollback fields (Guarantee L): base_ref, run_id, rollback_steps, affected_paths

- `specs/schemas/ruleset.schema.json`
  - Governed by: specs/20_rulesets_and_templates_registry.md
  - Validated by: Gate A1 (spec pack validation includes ruleset validation)

- `specs/schemas/commit_request.schema.json`, `commit_response.schema.json`
  - Governed by: specs/17_github_commit_service.md
  - Used by: TC-480, TC-500
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/open_pr_request.schema.json`, `open_pr_response.schema.json`
  - Governed by: specs/12_pr_and_release.md, specs/17_github_commit_service.md
  - Used by: TC-480
  - Validated by: Gate 1 (schema validation)

- `specs/schemas/hugo_facts.schema.json`
  - Governed by: specs/31_hugo_config_awareness.md
  - Produced by: TC-404 (Hugo site context)
  - Validated by: Gate 1 (schema validation), Gate 3 (hugo_config)

- `specs/schemas/api_error.schema.json`
  - Governed by: specs/24_mcp_tool_schemas.md (standard error shape)
  - Used by: TC-510, TC-511, TC-512 (MCP endpoints)
  - Validated by: Gate 1 (schema validation)

---

## Gates and their implementing validators
### Gate → Validator → Spec Mapping

**Preflight Gates** (run before orchestration):

- **Gate 0**: .venv policy validation
  - Validator: tools/validate_dotvenv_policy.py
  - Spec: specs/00_environment_policy.md
  - Guarantee: (foundational, not lettered)
  - Status: ✅ IMPLEMENTED

- **Gate A1**: Spec pack validation
  - Validator: scripts/validate_spec_pack.py
  - Specs: All schemas, specs/20_rulesets_and_templates_registry.md
  - Validates: All schemas valid, rulesets valid, toolchain lock present
  - Status: ✅ IMPLEMENTED

- **Gate B**: Taskcard contract validation
  - Validator: tools/validate_taskcards.py
  - Spec: plans/taskcards/00_TASKCARD_CONTRACT.md, specs/34_strict_compliance_guarantees.md (Guarantee K)
  - Validates: All taskcards have required fields, version locks present
  - Status: ✅ IMPLEMENTED

- **Gate E**: Allowed paths overlap detection
  - Validator: tools/audit_allowed_paths.py
  - Spec: specs/18_site_repo_layout.md, specs/34_strict_compliance_guarantees.md (Guarantee B)
  - Validates: Taskcard allowed_paths do not overlap (critical paths have single ownership)
  - Status: ✅ IMPLEMENTED

- **Gate J**: Pinned refs policy (Guarantee A)
  - Validator: tools/validate_pinned_refs.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee A)
  - Validates: All *_ref fields in run_config use commit SHAs (no floating branches/tags)
  - Status: ✅ IMPLEMENTED

- **Gate K**: Supply chain pinning (Guarantee C)
  - Validator: tools/validate_supply_chain_pinning.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee C), specs/00_environment_policy.md
  - Validates: Lock file exists (uv.lock or poetry.lock), .venv exists
  - Status: ✅ IMPLEMENTED

- **Gate L**: Secrets hygiene (Guarantee E)
  - Validator: tools/validate_secrets_hygiene.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee E)
  - Validates: No secrets in repository files (scans for patterns)
  - Status: ✅ IMPLEMENTED (preflight scan only; runtime redaction PENDING)

- **Gate M**: No placeholders in production paths (Guarantee E)
  - Validator: tools/validate_no_placeholders_production.py
  - Spec: specs/34_strict_compliance_guarantees.md (production paths definition)
  - Validates: No NOT_IMPLEMENTED, TODO, FIXME in production code paths
  - Status: ✅ IMPLEMENTED

- **Gate N**: Network allowlist validation (Guarantee D)
  - Validator: tools/validate_network_allowlist.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee D)
  - Validates: config/network_allowlist.yaml exists, run_config hosts allowlisted
  - Status: ✅ IMPLEMENTED

- **Gate O**: Budget validation (Guarantees F, G)
  - Validator: tools/validate_budgets_config.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantees F, G), specs/schemas/run_config.schema.json
  - Validates: Budgets present in prod configs (runtime, LLM calls, tokens, file writes, patch attempts, change budgets)
  - Status: ✅ IMPLEMENTED

- **Gate P**: Taskcard version locks (Guarantee K)
  - Validator: tools/validate_taskcard_version_locks.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee K), plans/taskcards/00_TASKCARD_CONTRACT.md
  - Validates: All taskcards have spec_ref, ruleset_version, templates_version
  - Status: ✅ IMPLEMENTED

- **Gate Q**: CI parity (Guarantee H)
  - Validator: tools/validate_ci_parity.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee H), specs/19_toolchain_and_ci.md
  - Validates: CI workflows use canonical commands (make install-uv, pytest, validate_swarm_ready.py)
  - Status: ✅ IMPLEMENTED

- **Gate R**: Untrusted code non-execution (Guarantee J)
  - Validator: tools/validate_untrusted_code_policy.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee J), specs/02_repo_ingestion.md
  - Validates: Ingestion is parse-only (no subprocess execution from RUN_DIR/work/repo/)
  - Status: ✅ IMPLEMENTED

**Runtime Gates** (run during validation phase):

- **Gate 1**: Schema validation
  - Validator: src/launch/validators/cli.py (launch_validate schema command)
  - Spec: specs/09_validation_gates.md, all schemas in specs/schemas/
  - Validates: All JSON artifacts validate against schemas
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 2**: Markdown lint + frontmatter validation
  - Validator: src/launch/validators/cli.py (launch_validate lint command)
  - Spec: specs/09_validation_gates.md, specs/18_site_repo_layout.md
  - Validates: markdownlint rules, frontmatter contract compliance
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 3**: Hugo config compatibility
  - Validator: src/launch/validators/cli.py (launch_validate hugo_config command)
  - Spec: specs/09_validation_gates.md, specs/31_hugo_config_awareness.md
  - Validates: Planned (subdomain, family) pairs enabled by Hugo configs, output_path matches content root contract
  - Fails with: HugoConfigMissing (blocker)
  - Taskcards: TC-460, TC-550, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-550)

- **Gate 4**: Platform layout compliance (content_layout_platform)
  - Validator: tools/validate_platform_layout.py OR src/launch/validators/cli.py (launch_validate content_layout_platform command)
  - Spec: specs/09_validation_gates.md, specs/32_platform_aware_content_layout.md
  - Validates: V2 sections use /{locale}/{platform}/ paths, no unresolved __PLATFORM__ tokens, allowed_paths correct
  - Fails with: BLOCKER (no acceptable warnings)
  - Taskcards: TC-540, TC-570
  - Status: ✅ IMPLEMENTED (preflight tool exists; runtime gate integration PENDING - See TC-570)

- **Gate 5**: Hugo build
  - Validator: src/launch/validators/cli.py (launch_validate hugo_build command)
  - Spec: specs/09_validation_gates.md, specs/19_toolchain_and_ci.md
  - Validates: hugo build succeeds in production mode
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 6**: Internal links
  - Validator: src/launch/validators/cli.py (launch_validate internal_links command)
  - Spec: specs/09_validation_gates.md
  - Validates: No broken internal links or anchors
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 7**: External links (optional by config)
  - Validator: src/launch/validators/cli.py (launch_validate external_links command)
  - Spec: specs/09_validation_gates.md
  - Validates: External links reachable (lychee or equivalent)
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 8**: Snippet checks
  - Validator: src/launch/validators/cli.py (launch_validate snippets command)
  - Spec: specs/09_validation_gates.md, specs/05_example_curation.md
  - Validates: Snippet syntax, optionally runs snippets in container
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate 9**: TruthLock
  - Validator: src/launch/validators/cli.py (launch_validate truthlock command)
  - Spec: specs/09_validation_gates.md, specs/04_claims_compiler_truth_lock.md
  - Validates: All claims in content link to EvidenceMap, no uncited facts
  - Taskcards: TC-413, TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-413, TC-460)

- **Gate 10**: Consistency
  - Validator: src/launch/validators/cli.py (launch_validate consistency command)
  - Spec: specs/09_validation_gates.md
  - Validates: product_name, repo_url, canonical URL consistent; required headings present; required sections present
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate: TemplateTokenLint** (required per specs/19_toolchain_and_ci.md)
  - Validator: src/launch/validators/cli.py (launch_validate template_tokens command) OR integrated into Gate 2
  - Spec: specs/19_toolchain_and_ci.md, specs/20_rulesets_and_templates_registry.md
  - Validates: No unresolved template tokens (__UPPER_SNAKE__, __PLATFORM__, etc.) in generated content
  - Fails with: BLOCKER (file path + line number + token found)
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-570)

- **Gate: Tier compliance** (universality gate)
  - Validator: Integrated into Gate 10 (consistency) or separate gate
  - Spec: specs/09_validation_gates.md (universality gates section)
  - Validates: launch_tier=minimal pages don't include exhaustive API lists; launch_tier=rich demonstrates grounding
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate: Limitations honesty** (universality gate)
  - Validator: Integrated into Gate 10 (consistency) or separate gate
  - Spec: specs/09_validation_gates.md (universality gates section)
  - Validates: If ProductFacts.limitations non-empty, docs/reference include Limitations section
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate: Distribution correctness** (universality gate)
  - Validator: Integrated into Gate 10 (consistency) or separate gate
  - Spec: specs/09_validation_gates.md (universality gates section)
  - Validates: Install commands match ProductFacts.distribution.install_commands exactly
  - Taskcards: TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-460)

- **Gate: No hidden inference** (universality gate)
  - Validator: Integrated into Gate 9 (TruthLock) or separate gate
  - Spec: specs/09_validation_gates.md (universality gates section)
  - Validates: Even with allow_inference=true, capabilities must be grounded in EvidenceMap
  - Taskcards: TC-413, TC-460, TC-570
  - Status: NOT YET IMPLEMENTED (See TC-413)

**Runtime Enforcers** (enforce policies during execution):

- **Path validation runtime enforcer**
  - Enforcer: src/launch/util/path_validation.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee B), specs/18_site_repo_layout.md
  - Enforces: All file operations confined to RUN_DIR and allowed_paths; blocks path escapes (.., absolute paths, symlink resolution)
  - Tests: tests/unit/util/test_path_validation.py
  - Status: ✅ IMPLEMENTED

- **Budget tracking runtime enforcer**
  - Enforcer: src/launch/util/budget_tracker.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantees F, G)
  - Enforces: Runtime, LLM calls, tokens, file writes, patch attempts within budgets; fails fast with BUDGET_EXCEEDED_* error codes
  - Tests: tests/unit/util/test_budget_tracker.py, tests/integration/test_gate_o_budgets.py
  - Taskcards: TC-300 (orchestrator integration)
  - Status: ✅ IMPLEMENTED (orchestrator integration ready)

- **Diff analyzer runtime enforcer**
  - Enforcer: src/launch/util/diff_analyzer.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee G), specs/08_patch_engine.md
  - Enforces: Change budgets (max_lines_per_file, max_files_changed); detects formatting-only diffs; fails with POLICY_CHANGE_BUDGET_EXCEEDED
  - Tests: tests/unit/util/test_diff_analyzer.py, tests/integration/test_gate_o_budgets.py
  - Taskcards: TC-450 (patch bundle analysis integration)
  - Status: ✅ IMPLEMENTED

- **Network allowlist runtime enforcer**
  - Enforcer: src/launch/clients/http.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee D)
  - Enforces: All HTTP requests to allowlisted hosts only; blocks unauthorized hosts with POLICY_NETWORK_UNAUTHORIZED_HOST
  - Tests: tests/unit/clients/test_http.py
  - Taskcards: TC-500 (clients/services)
  - Status: ✅ IMPLEMENTED

- **Subprocess execution blocker**
  - Enforcer: src/launch/util/subprocess.py
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee J), specs/02_repo_ingestion.md
  - Enforces: No subprocess execution from ingested repo (RUN_DIR/work/repo/); fails with SECURITY_UNTRUSTED_EXECUTION
  - Tests: tests/unit/util/test_subprocess.py
  - Taskcards: TC-400, TC-401, TC-402 (RepoScout must be parse-only)
  - Status: ✅ IMPLEMENTED

- **Secret redaction runtime enforcer**
  - Enforcer: Logging utilities (location TBD - likely src/launch/util/logging.py or src/launch/util/redaction.py)
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee E)
  - Enforces: All secret-like patterns redacted from logs/artifacts/reports (show ***REDACTED***)
  - Taskcards: TC-590 (security and secrets)
  - Status: PENDING IMPLEMENTATION (See TC-590)

- **Floating ref rejection (runtime)**
  - Enforcer: Integrated into launch_validate or orchestrator startup
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee A)
  - Enforces: Rejects run_config with floating branches/tags in prod profile
  - Taskcards: TC-300 (orchestrator), TC-460 (validator)
  - Status: PENDING IMPLEMENTATION (See TC-300, TC-460)

- **Rollback metadata validation (runtime)**
  - Enforcer: Integrated into launch_validate
  - Spec: specs/34_strict_compliance_guarantees.md (Guarantee L), specs/12_pr_and_release.md
  - Enforces: PR artifacts include rollback metadata in prod profile (base_ref, run_id, rollback_steps, affected_paths)
  - Taskcards: TC-480 (PRManager)
  - Status: PENDING IMPLEMENTATION (See TC-480 - TC not started)

---

## Additional binding specs not yet in detailed traceability

- `specs/04_claims_compiler_truth_lock.md`
  - Implement: TC-413 (truth lock compile minimal)
  - Validate: TC-460, TC-570 (Gate 9: TruthLock)
  - Enforces: Claim stability, no uncited facts, inference constraints

- `specs/33_public_url_mapping.md` (binding)
  - Implement: TC-430 (IAPlanner uses URL mapping contract), TC-540 (content path resolver)
  - Validate: TC-460 (URL consistency checks)
  - Used by: Planning and patching stages to compute canonical public URLs

- `specs/templates/` (all template READMEs reference binding contract)
  - Governed by: specs/20_rulesets_and_templates_registry.md, specs/32_platform_aware_content_layout.md
  - Implement: TC-440 (SectionWriter template rendering), TC-540 (path resolution)
  - Validate: Gate: TemplateTokenLint (no unresolved tokens)

---

## Summary of Implementation Status

**Preflight Gates (all ✅ IMPLEMENTED)**:
- Gate 0, A1, B, E, J, K, L, M, N, O, P, Q, R

**Runtime Gates (all PENDING - See TC-460, TC-570)**:
- Gates 1-10, TemplateTokenLint, Universality gates (tier compliance, limitations honesty, distribution correctness, no hidden inference)

**Runtime Enforcers**:
- ✅ IMPLEMENTED: path_validation, budget_tracker, diff_analyzer, network allowlist (http.py), subprocess blocker
- PENDING: secret redaction, floating ref rejection (runtime), rollback metadata validation

**Key Gaps**:
1. Runtime validation gates (TC-460, TC-570 not started)
2. Secret redaction utilities (TC-590 not started)
3. PRManager with rollback metadata (TC-480 not started)

---

## Plan gaps policy
If you add or change a spec, you MUST:
1) update this matrix, and
2) create/adjust taskcards so there is at least one implementing taskcard (and usually one validating taskcard).

---

**Traceability Matrix Updated**: 2026-01-27T14:00:00Z (Wave 3 Hardening - Agent D)
**Changes**: Added comprehensive schema→spec→gate mappings, gate→validator→spec mappings, runtime enforcer details, implementation status for all compliance guarantees (A-L)
