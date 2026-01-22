# Overview

## Goal
Build an agent or workforce of agents that can take a public GitHub repo and launch the product on a Hugo-based aspose.org site.

"Launch" means:
- Update existing aspose.org content to announce the product where appropriate.
- Create multiple new pages across sections (products, docs, reference, kb, blog).
- Each section describes the same product in a different way.
- Every section contains code, with priority on code extracted from the repo.

## Scale requirement (non-negotiable)
This system is intended to launch and maintain **hundreds of products** over time.
Therefore:
- Runs must be isolated (no shared mutable global state).
- The system must support batch execution (queue many runs) with bounded concurrency.
- Telemetry, artifacts, and commit operations must be robust at high volume.
- Idempotence is required: re-running does not duplicate pages or navigation.

## Deterministic reusable system
This must be production-grade and repeatable:
- Same inputs -> same plan -> near-identical diffs.
- Replayable decisions (prompt hashes + input hashes).
- Resumable mid-run.
- Parallelizable drafting.
- Fully auditable: every claim traces to evidence.

## LLM provider requirement (non-negotiable)
The system MUST use **OpenAI-compatible** LLM APIs (for example Ollama OpenAI-compatible server).
No provider-specific assumptions that break OpenAI-compatible servers.

## MCP requirement (non-negotiable)
All features MUST be exposed via MCP endpoints/tools (not only CLI).
See 14_mcp_endpoints.md.

## Telemetry requirement (non-negotiable)
All run events and all LLM operations MUST be logged via a centralized local-telemetry HTTP API endpoint.
See 16_local_telemetry_api.md.

## Commit requirement (non-negotiable)
All commits/PR actions against aspose.org MUST go through a centralized GitHub commit service with configurable message/body templates.
See 17_github_commit_service.md.

## Adaptation requirement (non-negotiable)
The system MUST adapt to different repo structures and product platforms/languages through a repo profiling + adapter mechanism.
See 02_repo_ingestion.md and repo_inventory schema.

## Architecture
- Orchestrator (LangGraph state machine / graph) coordinates everything.
- Specialized workers produce typed artifacts (LLM-facing workers use LangChain; see 25_frameworks_and_dependencies.md).
- Patch engine applies changes safely.
- Validation harness enforces gates.
- PR manager creates commits and opens PR with evidence and checklists (via commit service).

## Project repository structure
The launcher implementation repo layout and the runtime run directory layout are defined in:
- `specs/29_project_repo_structure.md`

## Site + workflows repos (hardcoded defaults)
Agents MUST not guess where to write content or how to run workflows:
- `specs/30_site_and_workflow_repos.md`

## Hugo config awareness
Hugo configs decide what is built; planning and validation MUST be config-aware:
- `specs/31_hugo_config_awareness.md`

## Single source of truth
All content must derive from:
- ProductFacts (facts, features, supported formats, workflows, APIs)
- EvidenceMap (citations to repo paths and line ranges)
- PagePlan (exact page inventory and per-page requirements)
- SnippetCatalog (tagged code samples and their provenance)

## Two pilots
The system must be developed against two pilot projects:
- Each pilot must be pinned to repo SHA and site SHA.
- Each pilot produces a golden PagePlan and a golden ValidationReport.
- Golden runs are used to measure determinism and regression.
