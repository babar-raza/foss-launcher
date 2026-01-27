# Key Files Inventory

This document lists the authoritative starting points for pre-implementation verification.

## Primary Authority Sources (Specs)

### Core Specifications
- `specs/README.md` — Spec overview and entry point
- `specs/00_overview.md` — System overview
- `specs/01_system_contract.md` — Top-level system contract
- `specs/02_repo_ingestion.md` — Repository ingestion
- `specs/03_product_facts_and_evidence.md` — Product facts collection
- `specs/04_claims_compiler_truth_lock.md` — Claims compilation
- `specs/05_example_curation.md` — Example curation
- `specs/06_page_planning.md` — Page planning
- `specs/08_patch_engine.md` — Patch application engine
- `specs/09_validation_gates.md` — Validation gates
- `specs/10_determinism_and_caching.md` — Determinism requirements
- `specs/11_state_and_events.md` — State management and events
- `specs/12_pr_and_release.md` — PR creation and release
- `specs/13_pilots.md` — Pilot configurations
- `specs/14_mcp_endpoints.md` — MCP endpoints
- `specs/15_llm_providers.md` — LLM provider interfaces
- `specs/16_local_telemetry_api.md` — Local telemetry API
- `specs/17_github_commit_service.md` — GitHub commit service
- `specs/18_site_repo_layout.md` — Site repository layout
- `specs/19_toolchain_and_ci.md` — Toolchain and CI requirements
- `specs/20_rulesets_and_templates_registry.md` — Template registry
- `specs/21_worker_contracts.md` — Worker contracts
- `specs/22_navigation_and_existing_content_update.md` — Navigation handling
- `specs/23_claim_markers.md` — Claim markers
- `specs/24_mcp_tool_schemas.md` — MCP tool schemas
- `specs/25_frameworks_and_dependencies.md` — Framework dependencies
- `specs/26_repo_adapters_and_variability.md` — Repository adapters
- `specs/27_universal_repo_handling.md` — Universal repo handling
- `specs/28_coordination_and_handoffs.md` — Coordination between workers
- `specs/30_site_and_workflow_repos.md` — Site and workflow repos
- `specs/32_platform_aware_content_layout.md` — Platform-aware layout
- `specs/33_public_url_mapping.md` — URL mapping
- `specs/34_strict_compliance_guarantees.md` — Compliance guarantees
- `specs/blueprint.md` — System blueprint
- `specs/state-graph.md` — State graph model
- `specs/state-management.md` — State management details

### Specifications with Patches
- `specs/patches/16_local_telemetry_api.patch.md` — Telemetry API patch
- `specs/patches/event.schema.json` — Event schema patch

## Schemas and Contracts

### JSON Schemas (specs/schemas/)
- `api_error.schema.json` — API error format
- `commit_request.schema.json` — Commit request
- `commit_response.schema.json` — Commit response
- `event.schema.json` — Event format
- `evidence_map.schema.json` — Evidence map
- `frontmatter_contract.schema.json` — Frontmatter contract
- `hugo_facts.schema.json` — Hugo facts
- `issue.schema.json` — Issue format
- `open_pr_request.schema.json` — Open PR request
- `open_pr_response.schema.json` — Open PR response
- `page_plan.schema.json` — Page plan
- `patch_bundle.schema.json` — Patch bundle
- `pr.schema.json` — PR schema
- `product_facts.schema.json` — Product facts
- `repo_inventory.schema.json` — Repository inventory
- `ruleset.schema.json` — Ruleset
- `run_config.schema.json` — Run configuration
- `site_context.schema.json` — Site context
- `snapshot.schema.json` — Snapshot
- `snippet_catalog.schema.json` — Snippet catalog
- `truth_lock_report.schema.json` — Truth lock report
- `validation_report.schema.json` — Validation report

## Gates and Validators

### Validators
- `src/launch/validators/__init__.py` — Validators package
- `src/launch/validators/__main__.py` — CLI entry point
- `src/launch/validators/cli.py` — Validation CLI implementation

## Plans and Taskcards

### Master Planning Documents
- `plans/00_README.md` — Plans overview
- `plans/README.md` — Plans entry point
- `plans/acceptance_test_matrix.md` — Acceptance test matrix
- `plans/swarm_coordination_playbook.md` — Swarm coordination playbook
- `plans/traceability_matrix.md` — Traceability matrix

### Policies
- `plans/policies/no_manual_content_edits.md` — No manual edits policy

### Taskcards
- `plans/taskcards/INDEX.md` — Taskcard index
- `plans/taskcards/00_TASKCARD_CONTRACT.md` — Taskcard contract
- `plans/taskcards/STATUS_BOARD.md` — Status board
- `plans/taskcards/TC-480_pr_manager_w9.md` — PR manager taskcard
- `plans/taskcards/TC-530_cli_entrypoints_and_runbooks.md` — CLI entrypoints taskcard
- `plans/taskcards/TC-570_validation_gates_ext.md` — Validation gates extension

## Requirements Sources

### Top-Level Documentation
- `README.md` — Repository overview and quick start
- `CONTRIBUTING.md` — Contribution guidelines
- `GLOSSARY.md` — Terminology definitions
- `ASSUMPTIONS.md` — Documented assumptions
- `TRACEABILITY_MATRIX.md` — High-level requirement tracing

### Reference Documentation
- `docs/architecture.md` — Architecture reference
- `docs/cli_usage.md` — CLI usage reference
- `docs/reference/local-telemetry-api.md` — Telemetry API reference
- `docs/reference/local-telemetry.md` — Telemetry overview

## Templates

### Template Registry (specs/templates/)
Multiple site templates under:
- `specs/templates/blog.aspose.org/cells/` — Blog templates
- `specs/templates/docs.aspose.org/cells/` — Docs templates
- `specs/templates/kb.aspose.org/cells/` — KB templates
- `specs/templates/products.aspose.org/cells/` — Products templates
- `specs/templates/reference.aspose.org/cells/` — Reference templates

## Pilot Configurations

### Pilots (specs/pilots/)
- `specs/pilots/README.md` — Pilots overview
- `specs/pilots/pilot-aspose-3d-foss-python/` — 3D pilot
- `specs/pilots/pilot-aspose-note-foss-python/` — Note pilot

## Reports and Evidence

### Report Templates
- `reports/templates/agent_report.md` — Agent report template
- `reports/templates/orchestrator_master_review.md` — Master review template
- `reports/templates/self_review_12d.md` — 12-dimension self-review template

### Previous Phases
- `reports/phase-0_discovery/` — Phase 0 discovery
- `reports/phase-1_spec-hardening/` — Phase 1 spec hardening
- `reports/phase-2_plan-taskcard-hardening/` — Phase 2 plan/taskcard hardening
- `reports/phase-3_final-readiness/` — Phase 3 final readiness
- `reports/phase-4_swarm-hardening/` — Phase 4 swarm hardening
- `reports/phase-5_swarm-hardening/` — Phase 5 swarm hardening
- `reports/phase-6_platform-layout/` — Phase 6 platform layout

## Configurations

### Config Files
- `configs/` — Run configurations (pilots + real products)
- `config/` — Toolchain pins and lint/link configs

## Authority Order Declaration

Per orchestrator contract:

1. **Specs are primary authority** (`specs/**/*.md`, `specs/**/*.json`)
2. **Requirements may be in** README, CONTRIBUTING, GLOSSARY, ASSUMPTIONS, docs, specs
3. **Schemas/contracts enforce specs** (`specs/schemas/*.schema.json`)
4. **Gates/validators enforce schemas/specs** (`src/launch/validators/**/*.py`)
5. **Plans/taskcards operationalize specs** (`plans/**/*.md`, `plans/taskcards/**/*.md`)

Any contradiction between these layers is a **GAP** requiring resolution.
