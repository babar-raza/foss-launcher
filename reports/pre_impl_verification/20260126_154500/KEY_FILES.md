# Key Files Inventory

**Timestamp:** 2026-01-26 15:45:00
**Purpose:** Authoritative starting points for pre-implementation verification

## Authority Order (Established)

1. **Specs** (Primary authority)
2. **Requirements** (derived from README/docs/specs)
3. **Schemas/Contracts** (enforce specs)
4. **Gates/Validators** (enforce schemas/specs)
5. **Plans/Taskcards** (operationalize specs)

---

## Root Documentation
- README.md
- ASSUMPTIONS.md
- CODE_OF_CONDUCT.md
- CONTRIBUTING.md
- SECURITY.md
- GLOSSARY.md

## Specifications (Primary Authority)
Located in `specs/`:
- 00_overview.md
- 01_system_contract.md
- 02_repo_ingestion.md
- 03_product_facts_and_evidence.md
- 04_claims_compiler_truth_lock.md
- 05_example_curation.md
- 08_patch_engine.md
- 10_determinism_and_caching.md
- 11_state_and_events.md
- 12_pr_and_release.md
- 13_pilots.md
- 15_llm_providers.md
- 16_local_telemetry_api.md
- 17_github_commit_service.md
- 18_site_repo_layout.md
- 19_toolchain_and_ci.md
- 20_rulesets_and_templates_registry.md
- 23_claim_markers.md
- 25_frameworks_and_dependencies.md
- 26_repo_adapters_and_variability.md
- 27_universal_repo_handling.md
- 28_coordination_and_handoffs.md
- 30_site_and_workflow_repos.md
- 32_platform_aware_content_layout.md
- blueprint.md
- state-graph.md
- state-management.md

## Schemas/Contracts (Enforcement Artifacts)
Located in `specs/schemas/`:
- api_error.schema.json
- commit_request.schema.json
- commit_response.schema.json
- event.schema.json
- evidence_map.schema.json
- frontmatter_contract.schema.json
- hugo_facts.schema.json
- issue.schema.json
- open_pr_request.schema.json
- open_pr_response.schema.json
- page_plan.schema.json
- patch_bundle.schema.json
- pr.schema.json
- product_facts.schema.json
- repo_inventory.schema.json
- ruleset.schema.json
- run_config.schema.json
- site_context.schema.json
- snapshot.schema.json
- snippet_catalog.schema.json
- truth_lock_report.schema.json
- validation_report.schema.json

## Plans & Taskcards (Operational Artifacts)
Located in `plans/`:
- 00_README.md
- 00_orchestrator_master_prompt.md
- acceptance_test_matrix.md
- implementation_master_checklist.md
- swarm_coordination_playbook.md
- traceability_matrix.md
- policies/no_manual_content_edits.md

Located in `plans/taskcards/`:
- 00_TASKCARD_CONTRACT.md
- INDEX.md
- STATUS_BOARD.md
- TC-100 through TC-602 (56 taskcard files identified)

## Documentation
Located in `docs/`:
- architecture.md
- cli_usage.md
- reference/local-telemetry-api.md
- reference/local-telemetry.md

## Gates/Validators
Located in `src/launch/validators/`:
- cli.py (identified from git status)

Additional validation scripts:
- scripts/validate_spec_pack.py

## Reports (Evidence Storage)
Located in `reports/`:
- Templates: agent_report.md, orchestrator_master_review.md, self_review_12d.md
- Previous phases: phase-0 through phase-5
- sanity_checks.md
- swarm_readiness_review.md
- swarm_allowed_paths_audit.md

## Templates
Located in `specs/templates/`:
- Multiple Hugo site templates (blog.aspose.org, docs.aspose.org, kb.aspose.org, products.aspose.org, reference.aspose.org)

---

## Evidence Collection Commands Used
- Python-based tree generation (depth 6)
- ripgrep pattern search for: specs/, schemas/, taskcards, plans, validator, gate, contract, mcp

**Next Stage:** Agent swarm deployment (Stage 1)
