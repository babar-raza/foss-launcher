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
- TC-900 — Fix Pilot Configs and YAML Truncation
- TC-901 — Ruleset Schema: Add max_pages and Per-Section Style Configuration
- TC-902 — W4 Template Enumeration with Quotas
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
- TC-630 — Golden capture for pilot-aspose-3d-foss-python
- TC-631 — Offline-safe PR manager (W9)
- TC-632 — Pilot 3D config truth verification
- TC-633 — Taskcard hygiene for TC-630/631/632 (Gate A2/B fixes)
- TC-681 — W4 template-driven page enumeration (3D pilot)
- TC-700 — Template packs for 3D and NOTE families
- TC-701 — W4 family-aware path construction
- TC-702 — Validation report determinism
- TC-703 — Pilot VFV harness (determinism + goldenize)
- TC-709 — Fix time-sensitive test in test_tc_523_metadata_endpoints
- TC-903 — VFV harness - strict 2-run determinism with goldenization
- TC-910 — Taskcard Hygiene: Fix TC-901, TC-902, TC-903
- TC-920 — VFV diagnostics: capture stderr/stdout tail for failed runs
- TC-921 — TC-401 fix: Clone SHA used by pilots (not latest)
- TC-922 — Fix Gate D UTF-8 docs audit
- TC-923 — Fix Gate Q AI governance workflow
- TC-924 — Add legacy FOSS pattern to repo URL validator
- TC-925 — Fix W4 IAPlanner load_and_validate_run_config signature
- TC-926 — Fix W4 path construction: blog format + empty product_slug handling
- TC-928 — Taskcard hygiene for TC-924 and TC-925
- TC-930 — Fix Pilot-1 (3D) placeholder SHAs with real pinned refs
- TC-931 — Fix taskcard structure, INDEX entries, and version locks (Gates A2/B/P/C)
- TC-932 — Fix Gate E critical path overlaps
- TC-934 — Fix Gate R: Replace unsafe subprocess call with approved wrapper
- TC-935 — Make validation_report.json deterministic (fix TC-702 regression)
- TC-936 — Stabilize Gate L secrets scan to avoid timeout
- TC-937 — Taskcard compliance for TC-935 and TC-936
- TC-938 — Absolute cross-subdomain links (content quality)
- TC-939 — Storage model audit and documentation
- TC-940 — Page inventory policy (mandatory vs optional)
- TC-961 — Fix blog template README subdomain references
- TC-962 — Delete obsolete blog template __LOCALE__ files
- TC-963 — Fix IAPlanner blog template validation (missing title field)
- TC-964 — Fix W5 SectionWriter blog template token rendering
- TC-965 — Fix Gate 11 template token lint JSON metadata false positives
- TC-966 — Fix W4 template enumeration to search placeholder directories

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
# TC-920
# TC-924
