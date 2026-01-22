# Phase 0: Documentation Inventory

**Date**: 2026-01-22
**Phase**: Discovery & Gap Report
**Purpose**: Complete inventory of repo documentation structure

---

## Entry Points

### Primary Entry Points
1. **Root README** ([README.md](../../README.md))
   - Status: EXISTS ✓
   - Quality: Good - clear structure, implementation guidance
   - Coverage: Spec pack overview, quickstart, implementation guidance
   - Missing: Documentation navigation map for specs/plans/taskcards (minimal)

2. **Specs Entry Point** ([specs/README.md](../../specs/README.md))
   - Status: EXISTS ✓
   - Quality: Excellent - comprehensive table with descriptions
   - Coverage: All 36 spec files with categorization
   - Missing: None significant

3. **Plans Entry Point** ([plans/00_README.md](../../plans/00_README.md) and [plans/00_orchestrator_master_prompt.md](../../plans/00_orchestrator_master_prompt.md))
   - Status: EXISTS ✓
   - Quality: Good - clear orchestrator instructions
   - Coverage: Workflow phases, implementation rules
   - Missing: Quick navigation to key plan files

4. **Taskcards Entry Point** ([plans/taskcards/INDEX.md](../../plans/taskcards/INDEX.md))
   - Status: EXISTS ✓
   - Quality: Excellent - clear organization by worker
   - Coverage: All taskcards with landing order
   - Missing: Status tracking (which are draft vs ready)

---

## Specs Documentation (36 files)

### Core System (2 files)
- [x] [00_overview.md](../../specs/00_overview.md) - Goals, requirements, architecture
- [x] [01_system_contract.md](../../specs/01_system_contract.md) - Binding rules and guarantees

### Ingestion & Evidence (5 files)
- [x] [02_repo_ingestion.md](../../specs/02_repo_ingestion.md) - Clone, profile, discover
- [x] [03_product_facts_and_evidence.md](../../specs/03_product_facts_and_evidence.md) - Facts extraction
- [x] [04_claims_compiler_truth_lock.md](../../specs/04_claims_compiler_truth_lock.md) - Claim stability
- [x] [05_example_curation.md](../../specs/05_example_curation.md) - Snippet extraction
- [x] [27_universal_repo_handling.md](../../specs/27_universal_repo_handling.md) - Universal handling

### Planning & Writing (3 files)
- [x] [06_page_planning.md](../../specs/06_page_planning.md) - Page inventory, tiers
- [x] [07_section_templates.md](../../specs/07_section_templates.md) - Template selection
- [x] [08_patch_engine.md](../../specs/08_patch_engine.md) - Safe file modification

### Validation & Release (4 files)
- [x] [09_validation_gates.md](../../specs/09_validation_gates.md) - Quality gates
- [x] [10_determinism_and_caching.md](../../specs/10_determinism_and_caching.md) - Reproducibility
- [x] [11_state_and_events.md](../../specs/11_state_and_events.md) - State machine
- [x] [12_pr_and_release.md](../../specs/12_pr_and_release.md) - PR creation

### Infrastructure (11 files)
- [x] [13_pilots.md](../../specs/13_pilots.md) - Pilot specifications
- [x] [14_mcp_endpoints.md](../../specs/14_mcp_endpoints.md) - MCP server interface
- [x] [15_llm_providers.md](../../specs/15_llm_providers.md) - OpenAI-compatible LLM
- [x] [16_local_telemetry_api.md](../../specs/16_local_telemetry_api.md) - Event logging API
- [x] [17_github_commit_service.md](../../specs/17_github_commit_service.md) - Commit/PR service
- [x] [18_site_repo_layout.md](../../specs/18_site_repo_layout.md) - Hugo site structure
- [x] [19_toolchain_and_ci.md](../../specs/19_toolchain_and_ci.md) - Required tools
- [x] [29_project_repo_structure.md](../../specs/29_project_repo_structure.md) - Launcher layout
- [x] [30_site_and_workflow_repos.md](../../specs/30_site_and_workflow_repos.md) - Hardcoded repos
- [x] [31_hugo_config_awareness.md](../../specs/31_hugo_config_awareness.md) - Hugo config scanning
- [x] [state-management.md](../../specs/state-management.md) - State handling details
- [x] [state-graph.md](../../specs/state-graph.md) - State graph visualization

### Extensibility (11 files)
- [x] [20_rulesets_and_templates_registry.md](../../specs/20_rulesets_and_templates_registry.md) - Template versioning
- [x] [21_worker_contracts.md](../../specs/21_worker_contracts.md) - Worker I/O definitions
- [x] [22_navigation_and_existing_content_update.md](../../specs/22_navigation_and_existing_content_update.md) - Site navigation
- [x] [23_claim_markers.md](../../specs/23_claim_markers.md) - Inline claim attribution
- [x] [24_mcp_tool_schemas.md](../../specs/24_mcp_tool_schemas.md) - MCP tool definitions
- [x] [25_frameworks_and_dependencies.md](../../specs/25_frameworks_and_dependencies.md) - LangChain, LangGraph
- [x] [26_repo_adapters_and_variability.md](../../specs/26_repo_adapters_and_variability.md) - Platform adapters
- [x] [28_coordination_and_handoffs.md](../../specs/28_coordination_and_handoffs.md) - Worker coordination
- [x] [blueprint.md](../../specs/blueprint.md) - Blueprint overview
- [x] [pilot-blueprint.md](../../specs/pilot-blueprint.md) - Pilot blueprint

### Supporting Specs
- [x] Schemas (15 JSON schema files in [specs/schemas/](../../specs/schemas/))
- [x] Templates (Hugo templates in [specs/templates/](../../specs/templates/))
- [x] Rulesets (YAML rulesets in [specs/rulesets/](../../specs/rulesets/))
- [x] Pilots (2 pilot configs in [specs/pilots/](../../specs/pilots/))
- [x] Reference (Hugo configs in [specs/reference/hugo-configs/](../../specs/reference/hugo-configs/))
- [x] Examples (frontmatter models, ruleset examples in [specs/examples/](../../specs/examples/))
- [x] Patches (patch specs in [specs/patches/](../../specs/patches/))

---

## Plans Documentation

### Master Plans (3 files)
- [x] [00_README.md](../../plans/00_README.md) - Plans overview
- [x] [00_orchestrator_master_prompt.md](../../plans/00_orchestrator_master_prompt.md) - Orchestrator instructions
- [x] [README.md](../../plans/README.md) - Plans readme

### Traceability & Acceptance (2 files)
- [x] [traceability_matrix.md](../../plans/traceability_matrix.md) - Spec to taskcard mapping
- [x] [acceptance_test_matrix.md](../../plans/acceptance_test_matrix.md) - Test matrix

### Policies (1 file)
- [x] [policies/no_manual_content_edits.md](../../plans/policies/no_manual_content_edits.md) - Manual edit policy

### Templates (1 file)
- [x] [_templates/taskcard.md](../../plans/_templates/taskcard.md) - Taskcard template

---

## Taskcards Documentation (33 files)

### Contract & Index (2 files)
- [x] [00_TASKCARD_CONTRACT.md](../../plans/taskcards/00_TASKCARD_CONTRACT.md) - Taskcard binding rules
- [x] [INDEX.md](../../plans/taskcards/INDEX.md) - Taskcard index

### Bootstrap (3 files)
- [x] TC-100 — Bootstrap repo
- [x] TC-200 — Schemas and IO
- [x] TC-201 — Emergency mode flag
- [x] TC-300 — Orchestrator graph

### W1 RepoScout (5 files - 4 micro + 1 epic)
- [x] TC-401 — Clone and resolve SHAs
- [x] TC-402 — Repo fingerprint and inventory
- [x] TC-403 — Frontmatter contract discovery
- [x] TC-404 — Hugo site context build matrix
- [x] TC-400 — W1 epic wrapper

### W2 FactsBuilder (4 files - 3 micro + 1 epic)
- [x] TC-411 — Facts extract catalog
- [x] TC-412 — Evidence map linking
- [x] TC-413 — Truth lock compile
- [x] TC-410 — W2 epic wrapper

### W3 SnippetCurator (3 files - 2 micro + 1 epic)
- [x] TC-421 — Snippet inventory tagging
- [x] TC-422 — Snippet selection rules
- [x] TC-420 — W3 epic wrapper

### W4-W9 Workers (6 epic files)
- [x] TC-430 — W4 IA Planner
- [x] TC-440 — W5 SectionWriter
- [x] TC-450 — W6 Linker and Patcher
- [x] TC-460 — W7 Validator
- [x] TC-470 — W8 Fixer
- [x] TC-480 — W9 PR Manager

### Cross-cutting (4 files)
- [x] TC-500 — Clients and services
- [x] TC-510 — MCP server
- [x] TC-520 — Pilots and regression
- [x] TC-530 — CLI entrypoints and runbooks

### Additional Hardening (7 files)
- [x] TC-540 — Content Path Resolver
- [x] TC-550 — Hugo Config Awareness
- [x] TC-560 — Determinism harness
- [x] TC-570 — Validation gates ext
- [x] TC-571 — Policy gate: No manual edits
- [x] TC-580 — Observability and evidence bundle
- [x] TC-590 — Security and secrets
- [x] TC-600 — Failure recovery and backoff

---

## Reports Infrastructure

### Templates (3 files)
- [x] [reports/templates/agent_report.md](../../reports/templates/agent_report.md) - Agent report template
- [x] [reports/templates/self_review_12d.md](../../reports/templates/self_review_12d.md) - 12-dimension self-review
- [x] [reports/templates/orchestrator_master_review.md](../../reports/templates/orchestrator_master_review.md) - Orchestrator review

### Report Folders
- [x] [reports/](../../reports/) - Implementation evidence folder (exists)
- [x] [reports/agents/](../../reports/agents/) - Agent reports (exists)
- [x] [reports/forensics/](../../reports/forensics/) - Forensics outputs (exists)
- [x] [reports/templates/](../../reports/templates/) - Report templates (exists)
- [ ] [reports/phase-0_discovery/](../../reports/phase-0_discovery/) - Phase 0 reports (CREATED)
- [ ] [reports/phase-1_spec-hardening/](../../reports/phase-1_spec-hardening/) - Phase 1 reports (CREATED)
- [ ] [reports/phase-2_plan-taskcard-hardening/](../../reports/phase-2_plan-taskcard-hardening/) - Phase 2 reports (CREATED)
- [ ] [reports/phase-3_final-readiness/](../../reports/phase-3_final-readiness/) - Phase 3 reports (CREATED)

---

## Root Documentation Files

### Existing (8 files)
- [x] [README.md](../../README.md) - Main readme
- [x] [CODE_OF_CONDUCT.md](../../CODE_OF_CONDUCT.md) - Code of conduct
- [x] [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contributing guidelines
- [x] [SECURITY.md](../../SECURITY.md) - Security policy
- [x] [LICENSE](../../LICENSE) - License file
- [x] [Makefile](../../Makefile) - Build automation
- [x] [pyproject.toml](../../pyproject.toml) - Python project config
- [x] [.gitignore](../../.gitignore) - Git ignore rules

### Created in Phase 0 (5 files)
- [x] [OPEN_QUESTIONS.md](../../OPEN_QUESTIONS.md) - Unresolved questions (CREATED)
- [x] [ASSUMPTIONS.md](../../ASSUMPTIONS.md) - Documented assumptions (CREATED)
- [x] [DECISIONS.md](../../DECISIONS.md) - Design decisions (CREATED)
- [x] [GLOSSARY.md](../../GLOSSARY.md) - Terminology definitions (CREATED)
- [x] [TRACEABILITY_MATRIX.md](../../TRACEABILITY_MATRIX.md) - High-level traceability (CREATED)

---

## Other Documentation

### Docs Folder (3 files)
- [x] [docs/architecture.md](../../docs/architecture.md) - Architecture reference (non-binding)
- [x] [docs/reference/local-telemetry-api.md](../../docs/reference/local-telemetry-api.md) - Telemetry API reference
- [x] [docs/reference/local-telemetry.md](../../docs/reference/local-telemetry.md) - Telemetry docs

### Config Folder
- [x] [config/](../../config/) - Toolchain pins and lint configs

### Scripts Folder
- [x] [scripts/](../../scripts/) - Dev utilities (forensics, validation)

---

## Summary Statistics

- **Total Specs**: 36 files
- **Total Plans**: 7 files (master plans, traceability, policies)
- **Total Taskcards**: 33 files
- **Total Report Templates**: 3 files
- **Total Root Documentation**: 13 files (8 existing + 5 created)
- **Total Schemas**: 15 JSON schema files
- **Total Templates**: ~100+ Hugo template files
- **Total Pilot Configs**: 2 pilots with configs

---

## Documentation Quality Assessment

### Strengths
1. **Comprehensive spec coverage** - All major areas well-documented
2. **Clear entry points** - README files provide good navigation
3. **Structured taskcards** - Well-organized by worker pipeline
4. **Traceability exists** - Spec-to-taskcard mapping present
5. **Templates provided** - Report and taskcard templates available

### Weaknesses
1. **Missing root scaffolding** - No GLOSSARY, OPEN_QUESTIONS, ASSUMPTIONS, DECISIONS (NOW CREATED)
2. **No master documentation map** - README doesn't clearly direct to all key files
3. **Status tracking absent** - Taskcards don't indicate Draft vs Ready status
4. **Cross-references incomplete** - Some specs/plans don't link to related files
5. **Acceptance criteria vary** - Some taskcards have detailed checks, others are sparse

---

## Next Steps (Phase 1)

1. Enhance README.md with clear documentation navigation map
2. Add cross-references between related specs/plans/taskcards
3. Standardize acceptance criteria across all taskcards
4. Add status metadata to taskcards (Draft/Ready)
5. Populate GLOSSARY with all key terms from specs
6. Ensure all specs have complete sections per Phase 1 requirements
