# Taskcards Index

- Read **Taskcards Contract** first: `plans/taskcards/00_TASKCARD_CONTRACT.md`
- Use `plans/traceability_matrix.md` to ensure every spec area has taskcard coverage.

This index maps taskcards to the worker pipeline (W1–W9) and cross-cutting concerns.

## Bootstrap
- TC-100 — Bootstrap repo, toolchain, minimal skeleton
- TC-200 — Schemas and IO foundations
- TC-201 — Emergency mode flag (allow_manual_edits) and policy plumbing
- TC-250 — Shared library governance and data models
- TC-300 — Orchestrator graph wiring and run loop

## W1 RepoScout (micro)
- TC-401 — Clone inputs and resolve SHAs deterministically
- TC-402 — Repo fingerprint and inventory
- TC-403 — Frontmatter contract discovery
- TC-404 — Hugo config scan and site_context build matrix

(Epic wrapper: TC-400 — W1 RepoScout end-to-end integration)

## W2 Facts/Evidence/TruthLock (micro)
- TC-411 — Extract ProductFacts catalog deterministically
- TC-412 — Build EvidenceMap linking facts and sources
- TC-413 — TruthLock compile (minimal claim groups + report)

(Epic wrapper: TC-410 — W2 FactsBuilder end-to-end integration)

## W3 Snippets (micro)
- TC-421 — Snippet inventory and tagging
- TC-422 — Snippet selection and normalization rules

(Epic wrapper: TC-420 — W3 SnippetCurator end-to-end integration)

## Workers (epics)
- TC-430 — W4 IA Planner
- TC-440 — W5 SectionWriter
- TC-450 — W6 Linker and Patcher
- TC-460 — W7 Validator
- TC-470 — W8 Fixer
- TC-480 — W9 PR Manager

## Cross-cutting
- TC-500 — Clients and services
- TC-510 — MCP server
- TC-511 — MCP quickstart from product URL (launch_start_run_from_product_url)
- TC-512 — MCP quickstart from GitHub repo URL (launch_start_run_from_github_repo_url)
- TC-520 — Pilots and regression
- TC-522 — Pilot E2E CLI execution and determinism verification
- TC-523 — Pilot E2E MCP execution and determinism verification
- TC-530 — CLI entrypoints and runbooks

## Additional critical hardening
- TC-540 — Content Path Resolver
- TC-550 — Hugo Config Awareness
- TC-560 — Determinism harness
- TC-570 — Validation gates
- TC-571 — Policy gate: No manual content edits
- TC-580 — Observability and evidence bundle
- TC-590 — Security and secrets handling
- TC-600 — Failure recovery and backoff
- TC-601 — Windows Reserved Names Validation Gate
- TC-602 — Specs README Navigation Update
- TC-603 — Taskcard status hygiene - correct TC-520 and TC-522 status
- TC-604 — Taskcard closeout for TC-520 and TC-522
- TC-709 — Fix time-sensitive test in test_tc_523_metadata_endpoints

## Suggested landing order (micro-first)
1) TC-100, TC-200
2) TC-401..TC-404
3) TC-411..TC-413
4) TC-421..TC-422
5) TC-540, TC-550
6) TC-460, TC-570, TC-571
7) TC-500, TC-510, TC-530
8) TC-470, TC-480, TC-520
9) TC-580, TC-590, TC-600
