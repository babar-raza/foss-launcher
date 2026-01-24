# Aspose Product Launch Agent - Specification

## Overview

This specification defines an agent system that takes a public GitHub repository and launches the product on Hugo-based aspose.org sites. The system is designed to handle **hundreds of products** with **diverse repository structures**.

## Spec Classification

All specifications are classified as either **BINDING** or **REFERENCE**:

- **BINDING**: Specs that require taskcards, tests, and full implementation. These define system contracts, workflows, and runtime behavior that must be enforced.
- **REFERENCE**: Documentation, blueprints, and informational specs that guide implementation but do not require dedicated taskcards.

### BINDING Specifications

The following specs are binding and require taskcard coverage + tests:
- 00_environment_policy.md (venv policy enforcement)
- 00_overview.md (system goals and architecture)
- 01_system_contract.md (binding rules and guarantees)
- 02_repo_ingestion.md (clone, profile, discover)
- 03_product_facts_and_evidence.md (facts extraction)
- 04_claims_compiler_truth_lock.md (claim ID stability)
- 05_example_curation.md (snippet extraction)
- 06_page_planning.md (page inventory, launch tiers)
- 07_section_templates.md (template selection)
- 08_patch_engine.md (safe file modification)
- 09_validation_gates.md (quality gates, fix loops)
- 10_determinism_and_caching.md (reproducibility rules)
- 11_state_and_events.md (state machine, telemetry)
- 12_pr_and_release.md (PR creation, deployment)
- 13_pilots.md (pilot project specifications)
- 14_mcp_endpoints.md (MCP server interface)
- 15_llm_providers.md (OpenAI-compatible LLM usage)
- 16_local_telemetry_api.md (event logging API)
- 17_github_commit_service.md (commit/PR service)
- 18_site_repo_layout.md (Hugo site structure)
- 19_toolchain_and_ci.md (required tools)
- 20_rulesets_and_templates_registry.md (template versioning)
- 23_claim_markers.md (inline claim attribution)
- 24_mcp_tool_schemas.md (MCP tool definitions)
- 25_frameworks_and_dependencies.md (LangChain, LangGraph)
- 26_repo_adapters_and_variability.md (platform adapters)
- 27_universal_repo_handling.md (universal handling guidelines)
- 29_project_repo_structure.md (launcher repo + RUN_DIR layout)
- 30_site_and_workflow_repos.md (hardcoded repo defaults)
- 31_hugo_config_awareness.md (Hugo config scanning)
- 32_platform_aware_content_layout.md (platform-aware content layout)
- 34_strict_compliance_guarantees.md (strict compliance guarantees)

### REFERENCE Specifications

The following specs are reference/informational and do not require dedicated taskcards:
- 21_worker_contracts.md (worker I/O definitions - informational for implementers)
- 22_navigation_and_existing_content_update.md (navigation strategy - guidance for W4/W6)
- 28_coordination_and_handoffs.md (worker coordination - informational)
- 33_public_url_mapping.md (URL mapping - informational reference)
- blueprints/* (design blueprints - informational)

## Spec Documents

### Core System
| # | Document | Description |
|---|----------|-------------|
| 00 | [environment_policy.md](00_environment_policy.md) | Virtual environment policy |
| 00 | [overview.md](00_overview.md) | Goals, requirements, architecture |
| 01 | [system_contract.md](01_system_contract.md) | Binding rules and guarantees |

### Ingestion & Evidence
| # | Document | Description |
|---|----------|-------------|
| 02 | [repo_ingestion.md](02_repo_ingestion.md) | Clone, profile, discover (enhanced with phantom paths) |
| 03 | [product_facts_and_evidence.md](03_product_facts_and_evidence.md) | Facts extraction, evidence priority ranking |
| 04 | [claims_compiler_truth_lock.md](04_claims_compiler_truth_lock.md) | Claim ID stability, truth locking |
| 05 | [example_curation.md](05_example_curation.md) | Snippet extraction and validation |

### Planning & Writing
| # | Document | Description |
|---|----------|-------------|
| 06 | [page_planning.md](06_page_planning.md) | Page inventory, launch tiers (enhanced with CI signals) |
| 07 | [section_templates.md](07_section_templates.md) | Template selection by tier/type |
| 08 | [patch_engine.md](08_patch_engine.md) | Safe file modification |

### Validation & Release
| # | Document | Description |
|---|----------|-------------|
| 09 | [validation_gates.md](09_validation_gates.md) | Quality gates, fix loops |
| 10 | [determinism_and_caching.md](10_determinism_and_caching.md) | Reproducibility rules |
| 11 | [state_and_events.md](11_state_and_events.md) | State machine, telemetry |
| 12 | [pr_and_release.md](12_pr_and_release.md) | PR creation, deployment |

### Infrastructure
| # | Document | Description |
|---|----------|-------------|
| 13 | [pilots.md](13_pilots.md) | Pilot project specifications |
| 14 | [mcp_endpoints.md](14_mcp_endpoints.md) | MCP server interface |
| 15 | [llm_providers.md](15_llm_providers.md) | OpenAI-compatible LLM usage |
| 16 | [local_telemetry_api.md](16_local_telemetry_api.md) | Event logging API |
| 17 | [github_commit_service.md](17_github_commit_service.md) | Commit/PR service |
| 18 | [site_repo_layout.md](18_site_repo_layout.md) | Hugo site structure |
| 19 | [toolchain_and_ci.md](19_toolchain_and_ci.md) | Required tools |
| 29 | [project_repo_structure.md](29_project_repo_structure.md) | Launcher repo + RUN_DIR layout |
| 30 | [site_and_workflow_repos.md](30_site_and_workflow_repos.md) | Hardcoded repo defaults + where agents write/run |
| 31 | [hugo_config_awareness.md](31_hugo_config_awareness.md) | Hugo config scanning + build-matrix gating |

### Extensibility
| # | Document | Description |
|---|----------|-------------|
| 20 | [rulesets_and_templates_registry.md](20_rulesets_and_templates_registry.md) | Template versioning |
| 21 | [worker_contracts.md](21_worker_contracts.md) | Worker I/O definitions |
| 22 | [navigation_and_existing_content_update.md](22_navigation_and_existing_content_update.md) | Site navigation |
| 23 | [claim_markers.md](23_claim_markers.md) | Inline claim attribution |
| 24 | [mcp_tool_schemas.md](24_mcp_tool_schemas.md) | MCP tool definitions |
| 25 | [frameworks_and_dependencies.md](25_frameworks_and_dependencies.md) | LangChain, LangGraph |
| 26 | [repo_adapters_and_variability.md](26_repo_adapters_and_variability.md) | Platform adapters, product type inference (enhanced) |
| 27 | [universal_repo_handling.md](27_universal_repo_handling.md) | Universal handling guidelines |
| 28 | [coordination_and_handoffs.md](28_coordination_and_handoffs.md) | Worker coordination and decision loops |
| 32 | [platform_aware_content_layout.md](32_platform_aware_content_layout.md) | Platform-aware content layout contract |
| 33 | [public_url_mapping.md](33_public_url_mapping.md) | Public URL mapping contract |
| 34 | [strict_compliance_guarantees.md](34_strict_compliance_guarantees.md) | Strict compliance guarantees (binding) |

## Key Enhancements (v1.1)

This version includes enhancements for universal product handling:

1. **Root-level doc discovery** - Implementation docs at repo root are now detected
2. **Phantom path detection** - Claims about non-existent paths are recorded
3. **Evidence priority ranking** - Explicit 7-level priority for contradiction resolution
4. **Product type auto-inference** - Automatic detection of cli/library/service/etc.
5. **Launch tier quality signals** - CI presence and other signals adjust tier selection
6. **Contradiction recording** - EvidenceMap now tracks resolved contradictions
7. **Complete pilot configs** - Fully specified, schema-valid pilot configurations

## Pilots

Two pilot projects validate the specification:

| Pilot | Repo | Archetype | Expected Tier |
|-------|------|-----------|---------------|
| [Aspose.3D FOSS](pilots/pilot-aspose-3d-foss-python/) | Sparse, flat, no CI | `python_flat_setup_py` | `minimal` |
| [Aspose.Note FOSS](pilots/pilot-aspose-note-foss-python/) | Rich, src-layout, CI | `python_src_pyproject` | `rich` |

## Schemas

All JSON artifacts are validated against schemas in `schemas/`:
- `run_config.schema.json` - Run configuration
- `repo_inventory.schema.json` - Repository analysis (enhanced)
- `product_facts.schema.json` - Product facts
- `evidence_map.schema.json` - Claim citations (enhanced with contradictions)
- `page_plan.schema.json` - Page inventory
- `validation_report.schema.json` - Gate results
- `truth_lock_report.schema.json` - TruthLock attribution report (claim markers ↔ evidence)
- `site_context.schema.json` - Site/workflow SHAs + Hugo config fingerprints/build matrix

## Quick Start

1. Review [00_overview.md](00_overview.md) for system goals
2. Review [27_universal_repo_handling.md](27_universal_repo_handling.md) for handling diverse repos
3. Check pilot notes for expected behavior on different repo types
4. Use `specs/examples/launch_config.example.yaml` as a starting point for new products (then pin refs and allowed_paths)
