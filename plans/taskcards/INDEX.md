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
- TC-1102 (TC-CREV-C-TRACK2) — W4 Limitations Heading Integration (Agent C)
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
- TC-967 — Filter W4 template files with placeholder filenames
- TC-970 — Extend W4 token generation for docs/products/reference/kb templates
- TC-971 — Content Distribution Strategy - Specs and Schemas
- TC-972 — W4 IAPlanner - Content Distribution Implementation
- TC-973 — W5 SectionWriter - Specialized Content Generators
- TC-974 — W7 Validator - Gate 14 Implementation
- TC-975 — Content Distribution Templates

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

## Gate Fixes (2026-02-05)
- TC-976 — Fix Gate 13 (Hugo Build) - Copy Hugo Configuration Files
- TC-977 — Fix Gate 14 (Content Distribution) - Forbidden Topic and Claim Quota Violations
- TC-978 — Fix Gate T (Test Determinism) - Configure PYTHONHASHSEED=0

## Pilot Content Quality Fixes (2026-02-05)
- TC-980 — Fix W4 claim_group field mismatch in plan_pages_for_section (RC-1: CRITICAL)
- TC-981 — Fix W4 template page claims and product-specific token generation (RC-2, RC-3, RC-5)
- TC-982 — Fix W5 fallback content generation - claim distribution and snippet matching (RC-4)

## Evidence-Driven Page Scaling + Configurable Page Requirements (2026-02-05)
- TC-983 — Specs & Schemas: Evidence-Driven Page Scaling + Configurable Page Requirements (Agent-D, P0, no deps)
- TC-984 — W4 IAPlanner: Evidence-Driven Page Scaling + Configurable Page Requirements (Agent-B, P1, depends: TC-983)
- TC-985 — W7 Validator Gate 14: Mandatory Page Presence Check (Agent-B, P2, depends: TC-983, TC-984)
- TC-986 — Tests: Evidence-Driven Page Scaling + Configurable Page Requirements (Agent-C, P3, depends: TC-984, TC-985)

## Template Audit & Restructuring (2026-02-05)
- TC-990 — Specs & Schemas: Template Structure Ground Truth (Agent-D, P0, no deps)
- TC-991 — Delete Wrong-Hierarchy Templates (Agent-B, P1, depends: TC-990)
- TC-992 — Create Missing Templates: Full Family Parity (Agent-B, P2, depends: TC-990, TC-991)
- TC-993 — W4 IAPlanner: Template Enumeration for New Structure (Agent-B, P3, depends: TC-990, TC-992)
- TC-994 — W5 SectionWriter: Template-Driven Content for All Page Types (Agent-B, P3, depends: TC-990, TC-992)
- TC-995 — Tests: Template Structure Verification (Agent-C, P4, depends: TC-993, TC-994)
- TC-996 — Validation Gates: Template Path Consistency (Agent-B, P3, depends: TC-990)
- TC-997 — Pilot Verification & Evidence Bundle (Agent-C, P5, depends: ALL above)

## Stale Fixtures + cross_links Absolute + content_preview Bug (2026-02-06)
- TC-998 — Fix Stale expected_page_plan.json url_path Values (Agent-B, P1, no deps) — COMPLETE
- TC-999 — Fix Stale Test Fixture url_path in test_tc_450 (Agent-C, P2, depends: TC-998) — COMPLETE
- TC-1000 — Fix W6 content_preview Double Directory Bug (Agent-B, P2, no deps) — COMPLETE
- TC-1001 — Make cross_links Absolute URLs in W4 (Agent-B, P2, no deps) — COMPLETE
- TC-1002 — Document Absolute cross_links in Specs/Schemas (Agent-D, P3, depends: TC-1001) — COMPLETE
- TC-1003 — Verification: All Fixes + Pilots (Agent-C, P4, depends: TC-998..TC-1002) — COMPLETE

## Comprehensive Healing — System Completion (2026-02-07)

### Phase 0: Critical Fixes
- TC-1010 — Fix W4 claim_group data model bugs (3 locations)
- TC-1011 — Add cells/note family_overrides to ruleset.v1.yaml
- TC-1012 — Fix expected_page_plan.json cross_links to ABSOLUTE URLs
- TC-1013 — Remove/configure W2 evidence mapping caps

### Phase 1: Design Artifacts
- TC-1020 — Update specs for exhaustive ingestion (02, 03, 05, 21)
- TC-1021 — Update run_config schema + model for configurable ingestion

### Phase 2: W1/W2 Exhaustive Ingestion
- TC-1022 — Exhaustive documentation discovery (remove extension filters)
- TC-1023 — Configurable scan directories for code/example discovery
- TC-1024 — .gitignore support + phantom path detection
- TC-1025 — Fingerprinting improvements (configurable ignores, size tracking)
- TC-1026 — Remove all W2 extraction limits (caps, filters, thresholds)

### Phase 3: Infrastructure
- TC-1030 — Typed artifact models — foundation
- TC-1031 — Typed artifact models — worker models
- TC-1032 — Centralized ArtifactStore class
- TC-1033 — Write-time validation + worker migration to ArtifactStore

### Phase 4: Integration
- TC-1034 — W1 stub artifact enrichment (frontmatter, site_context, hugo_facts)
- TC-1035 — Testing coverage expansion (edge cases, integration, golden files)

### Phase 5: Verification
- TC-1036 — Create cells pilot (pilot-aspose-cells-foss-python)
- TC-1037 — Final verification — all 3 pilots E2E + VFV determinism

---

## W2 Intelligence — Deep Code Understanding for Content Generation (2026-02-07)

### Phase 0: Specifications Foundation (PREREQUISITE)
- TC-1040 — Update specifications for W2 intelligence (specs 03, 07, 08, 21, 30, schemas) — Agent-D

### Phase 1: Code Analysis (AST + Manifest Parsing)
- TC-1041 — Implement code analyzer module (AST parsing, manifest parsing) — Agent-B, depends: TC-1040
- TC-1042 — Integrate code analysis into W2 worker (api_surface, code_structure, positioning) — Agent-B, depends: TC-1041

### Phase 2: Workflow & Example Enrichment
- TC-1043 — Implement workflow enrichment (step ordering, descriptions, complexity) — Agent-B, depends: TC-1042
- TC-1044 — Implement example enrichment (metadata extraction from docstrings) — Agent-B, depends: TC-1042

### Phase 3: Semantic Understanding (MANDATORY)
- TC-1045 — Implement LLM claim enrichment (audience, complexity, prerequisites) — Agent-B, depends: TC-1040, TC-1044
- TC-1046 — Implement semantic embeddings for evidence mapping — Agent-B, depends: TC-1045

### Phase 4: Integration & Verification
- TC-1047 — Integration testing (unit + integration tests for all phases) — Agent-C, depends: TC-1041..TC-1046
- TC-1048 — Update pilot configs and expected outputs — Agent-B, depends: TC-1047
- TC-1049 — Run pilots E2E to verify no regression and compare content quality — Orchestrator, depends: TC-1048

### Phase 5: Code Quality & Refinements (2026-02-08)
- TC-1050-T1 — Complete code_analyzer.py TODOs — Agent-B, depends: TC-1041
- TC-1050-T2 — Add Dedicated Unit Tests for Workflow Enrichment — Agent-C, depends: TC-1043, TC-1044
- TC-1050-T3 — Extract Stopwords to Shared Constant — Agent-B
- TC-1050-T4 — Add File Size Cap for Memory Safety — Agent-B
- TC-1050-T5 — Add Progress Events for Observability — Agent-B
- TC-1050-T6 — Run Both Pilots E2E for Verification — Agent-C, depends: TC-1050-T1..TC-1050-T5

## W5.5 ContentReviewer (2026-02-09)
- TC-1100 — W5.5 ContentReviewer Implementation (Orchestrator, P1) — Done

### Track 2: W5/W5.5 Contract Alignment
- TC-1101_frontmatter_field_resolution — Frontmatter Field Name Resolution (permalink vs url_path) — Agent-B, P1 — Done
- TC-1102_w4_limitations_heading — W4 Limitations Heading Integration — Agent-C, P1 — Done
- TC-1103_w5_limitations_prompt — W5 LLM Prompt Update for Limitations + W5.5 Check Refinement — Agent-D, P1 — Done
- TC-1104_products_index_frontmatter — Fix Products/Index.md Missing Frontmatter Blocker — Agent-F, P1 — Done
- TC-1105_track2_pilot_verification — Track 2 Final Pilot Verification — Agent-E, P1 — Done

### Track 3: ContentReviewer Final Tuning
- TC-1106_developer_guide_limitations — Developer Guide Limitations Section Gap — Agent-B, P1 — In-Progress
- TC-1107_readability_exemptions — Readability Exemptions for Navigation/FAQ Pages — Agent-C, P1 — In-Progress
- TC-1108_workflow_coverage_investigation — Workflow Coverage Investigation (developer-guide.md) — Agent-D, P1 — In-Progress
