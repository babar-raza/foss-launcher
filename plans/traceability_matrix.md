# Specs ↔ Taskcards Traceability Matrix

This document reduces “agent guessing” by making it explicit **which taskcards implement and/or validate** each spec area.

> Rule: if a spec section has no taskcard coverage, it is a **plan gap** and must be addressed by adding a micro taskcard.

## Core contracts
- `specs/01_system_contract.md`
  - Implement: TC-300, TC-200, TC-201
  - Validate: TC-460, TC-570, TC-571
- `specs/10_determinism_and_caching.md`
  - Implement: TC-200, TC-560, TC-401..TC-404
  - Validate: TC-560, TC-460, TC-522 (CLI determinism proof), TC-523 (MCP determinism proof)
- `specs/11_state_and_events.md`
  - Implement: TC-300, TC-200
  - Validate: TC-460

## Inputs, repos, and site awareness
- `specs/02_repo_ingestion.md`
  - Implement: TC-401, TC-402
- `specs/18_site_repo_layout.md`
  - Implement: TC-404, TC-540, TC-430
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

## Snippets and page planning
- `specs/05_example_curation.md`
  - Implement: TC-421, TC-422
- `specs/06_page_planning.md`
  - Implement: TC-430
- `specs/07_section_templates.md`
  - Implement: TC-440

## Patch engine and safety
- `specs/08_patch_engine.md`
  - Implement: TC-450, TC-540
  - Validate: TC-571
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

## Plan gaps policy
If you add or change a spec, you MUST:
1) update this matrix, and
2) create/adjust taskcards so there is at least one implementing taskcard (and usually one validating taskcard).
