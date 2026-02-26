# Taskcards Index

- Read **Taskcards Contract** first: `plans/taskcards/00_TASKCARD_CONTRACT.md`
- Use `plans/traceability_matrix.md` to ensure every spec area has taskcard coverage.

This index maps taskcards to the worker pipeline (W1–W11) and cross-cutting concerns.

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
- TC-450 — W8 Linker and Patcher
- TC-460 — W9 Validator
- TC-470 — W10 Fixer
- TC-480 — W11 PR Manager

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
- TC-631 — Offline-safe PR manager (W11)
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
- TC-974 — W9 Validator - Gate 14 Implementation
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
- TC-985 — W9 Validator Gate 14: Mandatory Page Presence Check (Agent-B, P2, depends: TC-983, TC-984)
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
- TC-1000 — Fix W8 content_preview Double Directory Bug (Agent-B, P2, no deps) — COMPLETE
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

### Phase 4b: Deep Code Intelligence (2026-02-13)
- TC-1410 — W2 LLM-Powered Code Understanding (code_understanding.json artifact)
- TC-1411 — W2 Structured Feature Profiles (keyword clustering + LLM enrichment)

### Phase 5: Code Quality & Refinements (2026-02-08)
- TC-1050-T1 — Complete code_analyzer.py TODOs — Agent-B, depends: TC-1041
- TC-1050-T2 — Add Dedicated Unit Tests for Workflow Enrichment — Agent-C, depends: TC-1043, TC-1044
- TC-1050-T3 — Extract Stopwords to Shared Constant — Agent-B
- TC-1050-T4 — Add File Size Cap for Memory Safety — Agent-B
- TC-1050-T5 — Add Progress Events for Observability — Agent-B
- TC-1050-T6 — Run Both Pilots E2E for Verification — Agent-C, depends: TC-1050-T1..TC-1050-T5

## W7 ContentReviewer (2026-02-09)
- TC-1100 — W7 ContentReviewer Implementation (Orchestrator, P1) — Done

### Track 2: W5/W7 Contract Alignment
- TC-1101_frontmatter_field_resolution — Frontmatter Field Name Resolution (permalink vs url_path) — Agent-B, P1 — Done
- TC-1102_w4_limitations_heading — W4 Limitations Heading Integration — Agent-C, P1 — Done
- TC-1103_w5_limitations_prompt — W5 LLM Prompt Update for Limitations + W7 Check Refinement — Agent-D, P1 — Done
- TC-1104_products_index_frontmatter — Fix Products/Index.md Missing Frontmatter Blocker — Agent-F, P1 — Done
- TC-1105_track2_pilot_verification — Track 2 Final Pilot Verification — Agent-E, P1 — Done

### Track 3: ContentReviewer Final Tuning
- TC-1106_developer_guide_limitations — Developer Guide Limitations Section Gap — Agent-B, P1 — Done
- TC-1107_readability_exemptions — Readability Exemptions for Navigation/FAQ Pages — Agent-C, P1 — In-Progress
- TC-1108_workflow_coverage_investigation — Workflow Coverage Investigation (developer-guide.md) — Agent-D, P1 — Done
- TC-1109_track3_final_verification — Track 3 Final Pilot Verification — Agent-E, P1 — In-Progress

### Track 3.1: TC-1106 Regression Fix
- TC-1110_fix_tc1106_regression — Fix TC-1106 Regression (1.6MB Bullet Points) — Agent-B, P1 — Done
- TC-1111_verify_track3_1 — Verify Track 3.1 Fix — Agent-E, P1 — In-Progress

## Page Expansion Epic (2026-02-11)

Dramatically increase per-pilot page count through 7 new optional_page_policy sources,
feature sub-pages, and configurable expansion controls. All strategies are evidence-driven
and config-customizable. Locale-based expansion is explicitly out of scope.

### Phase 0: Specifications Foundation (PREREQUISITE)
- TC-1200 — Specs & Schemas: Page Expansion Policies, Sub-Page Model, Config Keys — Agent-D, P0, no deps — Draft

### Phase 1: Ruleset Configuration
- TC-1201 — Ruleset: Raise Quotas & Register 7 New Policy Sources — Agent-D, P1, depends: TC-1200 — Draft

### Phase 2: Worker Implementation (parallelizable: TC-1202 || TC-1203+TC-1204)
- TC-1202 — W2: Format-Pair Extraction & Evidence Enrichment — Agent-B, P1, depends: TC-1200 — Draft
- TC-1203 — W4: 7 New Optional Page Policy Source Handlers — Agent-B, P2, depends: TC-1200, TC-1201, TC-1202 — Draft
- TC-1204 — W4: Feature Sub-Page Generation (detail expansion) — Agent-B, P2, depends: TC-1200, TC-1203 — Draft

### Phase 3: Templates & Content Generation (parallelizable: TC-1205 || TC-1206)
- TC-1205 — Templates: 11 New Template Files for New Page Types + Sub-Pages — Agent-D, P2, depends: TC-1200 — Draft
- TC-1206 — W5: 11 Specialized Generators for New Page Types + Sub-Pages — Agent-B, P3, depends: TC-1200, TC-1203, TC-1205 — Draft

### Phase 4: Testing
- TC-1207 — Tests: Integration, Determinism, Config Permutation (26+ tests) — Agent-C, P4, depends: TC-1202, TC-1203, TC-1204, TC-1206 — Draft

### Phase 5: Verification
- TC-1208 — Pilot Config Updates & E2E Verification with Before/After Comparison — Agent-C, P5, depends: ALL above — Draft

## LLM Pipeline Hardening — Non-Optional Enrichment & Review (2026-02-11)

Make W2 LLM enrichment and W7 ContentReviewer non-optional pipeline stages.
W2 gets priority-based claim splitting (LLM for high-value, heuristics for rest).
W7 gets real LLM enhancement agents (replacing stubs) and becomes mandatory.

### Phase 1: Worker Implementation (parallelizable: TC-1300 || TC-1301 || TC-1401 || TC-1402 || TC-1405)
- TC-1300 — W2: Priority-Based LLM Enrichment (remove 500-claim auto-offline threshold) — Agent-B, P1, no deps — Draft
- TC-1301 — W7: LLM Agent Implementation (replace 3 stub agents with real LLM calls) — Agent-B, P1, no deps — Draft
- TC-1401 — W2: Code-Grounded Claim Generation (integrate extract_claims_from_code_analysis) — Agent-B, P1, no deps — Done
- TC-1402 — W2: LLM Claim Classification (filter internal_detail + developer_instruction) — Agent-B, P1, no deps — Done
- TC-1405 — W7: LLM Semantic Checks (API hallucination, licensing accuracy, content relevance) — Agent-B, P1, depends: TC-1100 — Done

### Phase 2: Enforcement
- TC-1302 — Mandatory Pipeline Enforcement (remove review_enabled flag, W7 always-on) — Agent-D, P2, depends: TC-1301 — Draft

### Phase 3: Verification
- TC-1303 — E2E Verification: Both Pilots with LLM Enrichment + Mandatory Review — Agent-C, P3, depends: TC-1300, TC-1301, TC-1302 — Draft

## W2 Content Completeness — Round 8 (2026-02-13)

Reduce key_features noise from 50% to <20% through targeted claim quality filters.
Add use cases, tutorials, FAQ, and troubleshooting content for marketing and KB articles.

- TC-1616 — Claim Quality Filter: Reduce key_features Noise (50%→<20%) — Agent-TC1616, P0, no deps — In-Progress
- TC-1617 — W2 Workflow Enrichment: Expand from 2 steps to 8-12+ steps — agent_workflow_enrichment, P0, deps: TC-1616 — In-Progress
- TC-1618 — Use Case & Tutorial Extraction: 10-15 use cases, 3-5 tutorials — agent_narrative_extractor, P1, deps: TC-1617 — In-Progress
- TC-1619 — Troubleshooting & FAQ Extraction: 15-20 troubleshooting, 10-15 FAQ — agent_tc1619, P1, deps: TC-1617, TC-1618 — In-Progress

## W2 Production Readiness — Round 4 (2026-02-13)

Fix 5 systemic issues: code-as-claims leakage, class profile coverage, claim group contamination, empty critical fields, feature profile misclassification.

- TC-1508 — Harden Claim Quality Filters (code-as-claims 38%→<5%) — Agent-B, P1, no deps — In-Progress
- TC-1509 — Fix Claim Grouping and Add Compatibility Routing — Agent-B, P1, depends: TC-1508 — Draft
- TC-1510 — Expand Code Understanding Class Coverage (10→30+ profiles) — Agent-B, P1, no deps — Draft
- TC-1511 — Fix Feature Profile Topic Assignment — Agent-B, P1, no deps — Draft
- TC-1512 — Populate Example Inventory from Code — Agent-B, P1, no deps — Draft

## Content Quality Hardening — Round 8: W2 Content Completeness (2026-02-13)

Add educational and marketing content extraction for blog posts and tutorials.

- TC-1617 — W2: Code-Grounded Claims for Quickstart/Workflows — Agent-B, P1, no deps — Done
- TC-1618 — W2: Use Case & Tutorial Extraction — Agent-B, P1, depends: TC-1617 — Done
- TC-1619 — W2: FAQ & Troubleshooting Extraction — Agent-B, P1, depends: TC-1618 — Draft
- TC-1620 — W2: Best Practices & Performance Extraction — agent_round8_w2, P2, depends: TC-1410, TC-1411, TC-1501, TC-1510 — Done

## Content Quality Hardening — Round 3: Remaining Gaps (2026-02-13)

Fix quickstart synthesis, feature profile code examples, and LLM truncation handling.

- TC-1505 — Synthesize Claims from Code-Only README Sections — Agent-B, P1, no deps — Done
- TC-1506 — Fix Feature Profile Code Example Lookup — Agent-B, P1, no deps — Done
- TC-1507 — Handle LLM Response Truncation in Code Understanding — Agent-B, P1, no deps — Done

## Content Quality Hardening — Round 2: W2 Pipeline Enhancement (2026-02-13)

Comprehensive W2 pipeline improvements to increase claim volume and quality.
AST enrichment, claim filter tuning, offline understanding quality, and LLM diagnostics.

- TC-1501 — Enrich AST Extraction with Docstrings, Signatures, Inheritance — Agent-B, P1, no deps — Done
- TC-1502 — Improve Claim Extraction Quality and Coverage — Agent-B, P1, depends: TC-1501 — Done
- TC-1503 — Improve Offline Code Understanding Quality — Agent-B, P1, depends: TC-1501 — Done
- TC-1504 — Ensure LLM is Used + Diagnostic Logging — Agent-B, P1, no deps — Done

## Content Quality Hardening — Round 1 (2026-02-12)

- TC-1401 — W2: Code-Grounded Claim Generation (integrate extract_claims_from_code_analysis) — Agent-B, P1, no deps — Done
- TC-1402 — W2: LLM Claim Classification (filter internal_detail + developer_instruction) — Agent-B, P1, no deps — Done
- TC-1403 — W5: Snippet-Anchored Generation (restructure prompts for grounding) — Agent-B, P1, depends: TC-1401 — Done
- TC-1404 — W5: Deterministic Post-Processing Fixes (inline claims, unclosed fences, collapsed frontmatter, token expansion) — Agent-B, P1, no deps — Done
- TC-1405 — W7: LLM Semantic Checks (API hallucination, licensing accuracy, content relevance) — Agent-B, P1, depends: TC-1100 — Done
- TC-1406 — W7: Factual Verifier Agent (rewrite pages with semantic issues) — Agent-B, P1, depends: TC-1405 — Done
- TC-1407 — W7: Deterministic Defense-in-Depth (severity bumps, collapsed frontmatter) — Agent-B, P1, no deps — Done
- TC-1408 — Pilot Verification (Final Gate for Round 1 Content Quality Hardening) — Agent-B, P1, depends: TC-1401..TC-1407 — FAILED (3 blockers raised)

## Round 10: Pipeline Wiring — W2→W4→W5→W9 Integration (2026-02-14)

Fix dead data problem: W2 generates 55 LLM-synthesized claims (use_case, faq, best_practice, performance, tutorial, troubleshooting) but zero reach end users because claim_groups only has 6 hardcoded keys. Wire W2→W4→W5→W9 to consume all new content types.

### Workstream 0: Specs & Schema Updates (MUST GO FIRST)
- TC-1627 — Schema Extensibility Fix for claim_groups — Agent-D, P0, no deps — Draft
- TC-1628 — Ruleset Updates for New Page Policies — Agent-D, P0, depends: TC-1627 — Draft

### Workstream 1: Bug Fixes (Independent, Parallelizable)
- TC-1629 — W9 Gate 8 Data Structure Fix — Agent-B, P1, no deps — Draft
- TC-1630 — TC-1622 Offline Threshold Fix — Agent-B, P1, no deps — Draft
- TC-1631 — Use Case Deduplication Fix — Agent-B, P1, no deps — Draft

### Workstream 2: W2 Claim Groups Wiring
- TC-1632 — Extend claim_groups with 6 New Keys — Agent-B, P1, depends: TC-1627 — Draft

### Workstream 3: W4 IAPlanner Routing
- TC-1633 — Update page_role Assignment for New Content Types — Agent-B, P2, depends: TC-1627, TC-1628, TC-1632 — Draft
- TC-1634 — Route New claim_groups to Pages — Agent-B, P2, depends: TC-1632, TC-1633 — Draft
- TC-1635 — Add per_claim_group Optional Page Policy — Agent-B, P2, depends: TC-1628, TC-1632, TC-1633 — Draft

### Workstream 4: W5 SectionWriter Renderers
- TC-1636 — FAQ Q&A Renderer — Agent-B, P3, depends: TC-1632, TC-1634, TC-1633 — Draft
- TC-1637 — Best Practices Renderer — Agent-B, P3, depends: TC-1632, TC-1635, TC-1633 — Draft
- TC-1638 — Tutorial Step-by-Step Renderer — Agent-B, P3, depends: TC-1632, TC-1635, TC-1633 — Draft
- TC-1639 — Enhance Troubleshooting Renderer with Dedicated Claims — Agent-B, P3, depends: TC-1632, TC-1634 — Draft

### Workstream 5: Validation Alignment
- TC-1640 — W7 Density Tuning for New Page Types (if needed) — Agent-B, P4, depends: TC-1636, TC-1637, TC-1638 — Done
- TC-1641 — W9 Gate 14 Page Role Awareness (if needed) — Agent-B, P4, depends: TC-1633 — Done

## Round 11: LLM-Powered Content Quality Hardening (2026-02-14)

Transform W5 SectionWriter from deterministic claim-wrapper into LLM-powered content generator. Addresses 9 publication blockers identified in Round 10 manual audit. W2 produces A-grade content but W5 destroys quality through truncation, placeholder text, and missing LLM enhancement.

**Publication Status**: NO-GO (D+ content quality across 45 pages)
**Blockers**: "Refer to repository" placeholders, visible claim markers, 0 real troubleshooting solutions, empty developer guide workflows, truncated sentences, raw data leaks, broken code fences

### Phase 0: Quick Wins (Independent)
- TC-1650 — Strip Visible Claim Markers from User-Facing Output — Agent-B, P1, no deps — Draft
- TC-1651 — Fix Raw Data Structure Leakage in Comprehensive Guide — Agent-B, P1, no deps — Draft

### Phase 2: LLM Infrastructure (Foundation for Phase 1)
- TC-1658 — W5 LLM Integration Layer (3 helper functions) — Agent-B, P0, no deps — Draft
- TC-1659 — Prompt Templates for Specialized Generators (6 files) — Agent-B, P0, no deps — Draft

### Phase 1: LLM-Enhanced Specialized Generators (Depends on Phase 2)
- TC-1652 — LLM-Enhanced Comprehensive Guide Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft
- TC-1653 — LLM-Enhanced Troubleshooting Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft
- TC-1654 — LLM-Enhanced FAQ Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft
- TC-1655 — LLM-Enhanced Best Practices Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft
- TC-1656 — LLM-Enhanced Tutorial Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft
- TC-1657 — LLM-Enhanced Feature Showcase Generator — Agent-B, P2, depends: TC-1658, TC-1659 — Draft

### Phase 3: Truncation & Post-Processing Fixes (Independent)
- TC-1660 — Replace Hard Truncation with LLM Summarization — Agent-B, P2, no deps — Draft
- TC-1661 — Fix _first_sentence_bullets Post-Processor — Agent-B, P2, no deps — Draft
- TC-1662 — Fix Broken Code Fences and Orphaned Blocks — Agent-B, P2, no deps — Draft

### Phase 4: W5 Integration (Depends on Phase 1+2)
- TC-1663 — Thread LLM Client Through W5 Specialized Generators — Agent-B, P3, depends: TC-1652..TC-1657 — Draft
- TC-1664 — Use enriched_text in LLM Prompts (line 2771 fix) — Agent-B, P3, depends: TC-1658 — Draft

### Phase 5: Validation Alignment (Depends on Phase 0)
- TC-1665 — Update W9 Gate 14 for HTML Comment Claim Markers — Agent-B, P3, depends: TC-1650 — Draft
- TC-1666 — W7 ContentReviewer Skip Claim Marker Checks on HTML Comments — Agent-B, P3, depends: TC-1650 — Draft

### Phase 6: VFV & Publication Readiness (Depends on ALL)
- Acceptance: Zero "Refer to repository", zero visible claim markers, substantive troubleshooting solutions (>50 words), real code examples on all pages, all pages ≥3/5 quality dimensions

## Round 12: Publication-Ready Content Pipeline (2026-02-15)

Full pipeline enhancement: centralized prompt library, multi-pass LLM generation (outline→draft→refine),
8-layer hallucination prevention, incremental update support, W5 refactoring.
Baseline: 3619 tests passing.

### Phase 0: Specs & Schema Foundation (PREREQUISITE)
- TC-1700 — Spec Updates: Prompt Library, Multi-Pass, Incremental, Hallucination — Agent-D, P0, no deps — Draft
- TC-1701 — Shared Model Extensions (run_config, claim_registry) — Agent-D, P0, no deps — Draft
- TC-1702 — Schema Updates (product_facts, page_plan, prompt_frontmatter) — Agent-D, P0, depends: TC-1700 — Draft
- TC-1703 — Ruleset Updates (multi_pass, incremental, claims config) — Agent-D, P0, depends: TC-1700 — Draft

### Phase 1: Prompt Library Infrastructure
- TC-1710 — PromptLoader Class + Folder Structure — Agent-B, P1, depends: TC-1700, TC-1702 — Draft
- TC-1711 — Create Prompt Templates (40+ files) — Agent-B, P1, depends: TC-1710 — Draft
- TC-1712 — Migrate W2 Prompts (13 inline → loader) — Agent-B, P1, depends: TC-1710, TC-1711 — Draft
- TC-1713 — Migrate W5 Prompts (9 inline + 6 files → loader) — Agent-B, P1, depends: TC-1710, TC-1711 — Draft
- TC-1714 — Migrate W7 Prompts (7 inline + 4 .md → loader) — Agent-B, P1, depends: TC-1710, TC-1711 — Draft

### Phase 2: Rich Context + Multi-Pass Engine
- TC-1720 — RichContext Dataclass + Builder — Agent-B, P2, depends: TC-1700, TC-1701 — Draft
- TC-1721 — MultiPassOrchestrator (Outline → Draft → Refine) — Agent-B, P2, depends: TC-1710, TC-1711, TC-1720 — Draft
- TC-1722 — Hallucination Detection Module — Agent-B, P2, depends: TC-1720 — Draft
- TC-1723 — Integrate Multi-Pass into W5 Generator Dispatch — Agent-B, P2, depends: TC-1721, TC-1722, TC-1713 — Draft

### Phase 3: W2 Claim Quality
- TC-1730 — Chunked LLM Enrichment (Replace 500-Claim Cutoff) — Agent-B, P3, depends: TC-1700, TC-1701 — Draft
- TC-1731 — Implementation Detail Filter — Agent-B, P3, no deps — Draft
- TC-1732 — Richer Offline Enrichment Fallbacks — Agent-B, P3, depends: TC-1730 — Draft
- TC-1733 — Ensure All Critical Claim Groups Populated — Agent-B, P3, depends: TC-1730, TC-1731 — Draft

### Phase 4: W4 Distribution + W6 Linking
- TC-1740 — Missing page_role Mappings + min_claims — Agent-B, P4, depends: TC-1701 — Draft
- TC-1741 — Replace Positional Slicing with Semantic Selection — Agent-B, P4, depends: TC-1701, TC-1740 — Draft
- TC-1742 — Cross-Page Claim Overlap Detection — Agent-B, P4, depends: TC-1741 — Draft
- TC-1743 — W8 See Also Injection + Link Validation — Agent-B, P4, depends: TC-1742 — Draft

### Phase 5: W7 Review Fixes + LLM Regen
- TC-1750 — Remove Synthetic Claim ID Injection — Agent-B, P5, no deps — Draft
- TC-1751 — Complete LLM Regen Agents (3 specialists) — Agent-B, P5, depends: TC-1710, TC-1714 — Draft
- TC-1752 — Per-Page Scoring + Publication Readiness Checks — Agent-B, P5, depends: TC-1750 — Draft

### Phase 6: Incremental Update Support
- TC-1760 — RunConfig + RunLayout: Previous Run Reference — Agent-B, P6, depends: TC-1701, TC-1702 — Draft
- TC-1761 — W1 SHA Comparison — Agent-B, P6, depends: TC-1760 — Draft
- TC-1762 — W2 Claim Merging — Agent-B, P6, depends: TC-1760 — Draft
- TC-1763 — W4 Page Preservation — Agent-B, P6, depends: TC-1760, TC-1762 — Draft
- TC-1764 — W5 Draft Reuse + W8 Delete + W11 Delta Summary — Agent-B, P6, depends: TC-1763 — Draft

### Phase 7: W5 Refactoring
- TC-1770 — Decompose W5 worker.py Monolith — Agent-B, P7, depends: TC-1721, TC-1723 — Draft

### Phase 8: Testing
- TC-1780 — Unit Tests: Prompt Library + Rich Context + Multi-Pass (30+ tests) — Agent-C, P8, depends: TC-1710, TC-1720, TC-1721 — Draft
- TC-1781 — Unit Tests: W2 Quality + W4 Distribution + W7 Fixes (23+ tests) — Agent-C, P8, depends: TC-1730-TC-1752 — Draft
- TC-1782 — Unit Tests: Incremental + Refactoring (18+ tests) — Agent-C, P8, depends: TC-1760-TC-1770 — Draft
- TC-1783 — Integration Tests: Full Pipeline Smoke (3+ tests) — Agent-C, P8, depends: ALL Phase 1-7 — Draft

### Phase 9: Calibration & Verification
- TC-1790 — Prompt Calibration Sprint (Iterative Tuning) — Agent-E, P9, depends: ALL Phase 1-7 — Draft
- TC-1791 — Full E2E Pilot Verification — Agent-E, P9, depends: TC-1790 — Draft
- TC-1792 — Publication Readiness Audit — Agent-E, P9, depends: TC-1791 — Draft

## Round 14 — Score Improvement (96 → 100) (2026-02-16)

6 targeted fixes to reach UNCONDITIONAL GO (100/100) from CONDITIONAL GO (96/100).
Baseline: 3,791 tests passing, 23/23 gates PASS on both pilots.

- TC-1900 — Gate 15: Merge code_analysis.json into API allowlist — Alpha, P0, no deps — Draft
- TC-1901 — W4: quality_score minimum for per_key_feature — Bravo, P0, no deps — Draft
- TC-1902 — Sanitizer: Fix FAQ doubled Q: prefix — Charlie, P0, no deps — Draft
- TC-1903 — Sanitizer: Normalize excess backtick fences — Charlie, P0, no deps — Draft
- TC-1904 — Prompt: Strengthen landing anti-hallucination — Bravo, P1, no deps — Draft
- TC-1905 — Gate 14: Cross-section overlap threshold — Alpha, P0, no deps — Draft

## Round 15 — Publication Path & Content Quality Fix (2026-02-16)

Fix Hugo path placement (97.4% wrong) and content quality (broken code fences, doubled A: prefix).
Baseline: 3,802 tests passing, 23/23 gates PASS on both pilots.

- TC-2000 — W4: Remove section subdirectory from output paths — Alpha, P0, no deps — Draft
- TC-2001 — W4: Fix products locale/family order per Hugo config — Alpha, P0, depends TC-2000 — Draft
- TC-2002 — W4: Generate _index.md for non-blog section pages — Alpha, P0, depends TC-2000 — Draft
- TC-2003 — Sanitizer: Extract language tag from single-backtick code fences — Bravo, P0, no deps — Draft
- TC-2004 — Sanitizer: Fix FAQ doubled A: answer prefix — Bravo, P1, no deps — Draft
- TC-2005 — SiteConfig: Remove {section} from output_path_template — Alpha, P2, depends TC-2000,TC-2001 — Draft

## Round 16 — File Placement, W7 Activation, Links, Content Quality (2026-02-16)

Deploy generated content to Hugo repo, fix W7 LLM client, revert incorrect products path ordering,
absolutize all injected links, fix broken single-backtick code fences, strip trailing periods in code.

- TC-2100 — Deploy generated files to Hugo site repository — Orchestrator, P0, no deps — Draft
- TC-2101 — Fix W7 LLM client initialization (endpoint → api_base_url) — Orchestrator, P0, no deps — Draft
- TC-2102 — Revert products locale-first path ordering (TC-2001 was wrong) — Orchestrator, P0, no deps — Draft
- TC-2103 — Absolutize all injected links (relative → absolute with subdomain) — Orchestrator, P0, depends TC-2102 — Draft
- TC-2104 — Rewrite fix_single_backtick_code_blocks() with state machine — Orchestrator, P1, no deps — Done
- TC-2105 — Add fix_trailing_periods_in_code() sanitizer — Orchestrator, P1, no deps — Done

## Round 17 — Publication Readiness (Content Quality) (2026-02-16)

Resolve 15 remaining content quality issues preventing publication: sanitizer bugs, prompt quality,
page planning improvements, unique titles/descriptions, content deduplication, and SEO optimization.
Baseline: 3,938 tests passing, all Round 16 fixes complete.

- TC-2200 — Sanitizer Deterministic Fixes (R17-001, R17-002, R17-005) — Orchestrator, P0, no deps — Done
- TC-2201 — W4 Page Planning Improvements (R17-007, R17-010, R17-011) — Orchestrator, P1, no deps — Done
- TC-2202 — Prompt & Generator Quality (R17-003, R17-004, R17-008, R17-009, R17-012) — Orchestrator, P1, no deps — Done
- TC-2203 — Unique Titles & Descriptions (R17-014) — Orchestrator, P1, no deps — Done
- TC-2204 — Cross-Section Deduplication (R17-006) — Orchestrator, P2, depends: TC-2203 — Done
- TC-2205 — W6 SEO Optimizer Worker (R17-015) — Orchestrator, P1, no deps — Done

## Round 3 — Content Quality + Quality Gate + Aspose.net Alignment (2026-02-17)

Fix 14/19 Cells pages REJECT. 5 tracks: W5 generators, W7 quality gate, W2 claim quality,
configuration, aspose.net content alignment. 19 TCs across 6 parallel agent groups.

### Track A: W5 Content Generation
- TC-2330 — Register workflow_page generator + prompt — Agent-F, P1, no deps — Done
- TC-2331 — Register landing generator + prompt — Agent-F, P1, no deps — Done
- TC-2332 — Register api_reference generator + prompt — Agent-F, P1, no deps — Done
- TC-2333 — Fix comprehensive guide claim_text → _get_display_text() — Agent-F, P0, no deps — Done
- TC-2337 — Getting-started code consolidation — Agent-F, P1, no deps — Done
- TC-2340 — W5 silent fallback warning + generic prompt hardening — Agent-C, P0, no deps — In-Progress

### Track B: W7 Quality Gate Hardening
- TC-2338 — Fix W7 scoring crash (defensive str()) — Agent-A, P0, no deps — In-Progress
- TC-2339 — LLM score verification layer — Agent-A, P1, depends: TC-2338 — In-Progress
- TC-2341 — Post-LLM re-scoring — Agent-A, P1, depends: TC-2338 — In-Progress

### Track C: W2 Claim Quality
- TC-2334 — Parameter description filter — Agent-B, P0, no deps — In-Progress
- TC-2335 — best_practice claim classification — Agent-B, P0, no deps — In-Progress
- TC-2342 — W2 format conversion detection — Agent-B, P1, no deps — In-Progress

### Track D: Configuration
- TC-2336 — Rich launch tier for Cells — Agent-E, P0, no deps — In-Progress
- TC-2348 — Ruleset update (quotas + policies) — Agent-E, P0, no deps — In-Progress

### Track E: Aspose.net Content Alignment
- TC-2343 — W4 new optional page sources — Agent-D, P1, depends: TC-2342 — In-Progress
- TC-2344 — W4 content strategy + headings alignment — Agent-D, P0, no deps — In-Progress
- TC-2345 — Format conversion generator + prompt — Agent-F, P2, depends: TC-2343 — Done
- TC-2346 — How-to article generator + prompt — Agent-F, P2, depends: TC-2343 — Done
- TC-2347 — Feature blog generator + prompt — Agent-F, P2, depends: TC-2343 — Done

## Pipeline Quality Improvement — Architectural Fixes (2026-02-18)

Systemic fixes to pipeline content quality: multi-pass generation, citation excerpts,
pre-generation sufficiency check, acceptance criteria with re-prompt, sanitizer audit.

- TC-2350 — Enable multi-pass generation (fix 2 bugs) — Orchestrator, P0, no deps — Done
- TC-2351 — Add citation excerpts to W2 claims — Orchestrator, P0, no deps — Done
- TC-2352 — Pre-generation sufficiency check — Orchestrator, P1, depends: TC-2350 — Done
- TC-2353 — Post-generation acceptance criteria with re-prompt — Orchestrator, P1, depends: TC-2350 — Done
- TC-2354 — Sanitizer instrumentation and audit — Orchestrator, P2, depends: TC-2350..TC-2353 — In-Progress

## LLM Formatting Quality — W7 Fix + W9 Gate (2026-02-19)

Defense-in-depth for 7 formatting defect types (FQ-1..FQ-7). W7 Phase 0
detects and fixes proactively via LLM; W9 Gate 17 enforces no defects survived.

- TC-2360 — W7 Phase 0: LLM formatting review and fix — Orchestrator, P1, no deps — Done
- TC-2361 — W9 Gate 17: LLM formatting quality verification — Orchestrator, P1, depends: TC-2360 — Done

## Agentic Architecture Gaps (2026-02-19)

Addresses two structural gaps in the pipeline: sequential W5 page writing and missing W7→W5
feedback loop.

- TC-2362 — W5 Parallel Page Writing (snapshot-based, max_parallel_pages) — Orchestrator, P1, no deps — Done
- TC-2363 — W7 → W5 Selective Re-Draft Routing (redraft_enabled) — Orchestrator, P1, depends: TC-2362 — Done

## RCA Short-Term Fixes (2026-02-19)

Implements structural improvements from RCA plan (reactive-weaving-clock.md): content-signal role
assignment, claim source tracking, similarity-based claim assignment, and pre-generation context
validation.

- TC-2364 — W4 Content-Signal Role Assignment (claim-kind inference replaces slug matching) — Orchestrator, P1, no deps — Done
- TC-2365 — W2 source_section on Claims (Markdown heading parser) — Orchestrator, P1, no deps — Done
- TC-2366 — W4 Similarity-Based Claim Assignment (embeddings.py cosine similarity) — Orchestrator, P1, depends: TC-2365 — Done
- TC-2367 — W5 Pre-Generation Context Sufficiency Gate — Orchestrator, P1, no deps — Done (pre-existing as TC-2352 context_validator.py)
- TC-2368 — W4 Claim-to-Snippet Binding (demo_snippet_ids via TF-IDF) — Orchestrator, P1, depends: TC-2366 — Done
- TC-2369 — W5 Generator-Specific Context Builders (tutorial, feature_showcase, api_reference) — Orchestrator, P1, depends: TC-2368 — Done

## RCA Gate Upgrades (2026-02-19)

Implements gate enhancements from RCA plan Part 4-E: method signature validation,
code-prose balance, and cross-page redundancy detection. All warn-only.

- TC-2370 — Gate 15 Upgrade: Method Signature Validation — Orchestrator, P2, no deps — Done
- TC-2371 — Gate 18: Code-Prose Balance Check — Orchestrator, P2, no deps — Done
- TC-2372 — Gate 19: Cross-Page Redundancy Check — Orchestrator, P2, no deps — Done

## Healing Round Improvements (2026-02-19)

Pipeline quality improvements from the RD healing plan: priority-weighted token allocation
and cross-page consistency gate.

- TC-2373 — RD-04: Priority-Weighted Token Allocation in W5 — Orchestrator, P1, no deps — Done
- TC-2374 — RD-07: Gate 20 Cross-Page Consistency Check — Orchestrator, P2, no deps — Done
- TC-2375 — RD-02: Zone-Aware AST Content Parser for content_sanitizer.py — Orchestrator, P2, no deps — In-Progress

## Content Quality Master Plan (2026-02-20)

Comprehensive pipeline upgrade importing proven patterns from content-generator (UCOP) reference implementation.
Addresses Grade D+/D- pilot output through tone control, LLM response validation, code-first assembly,
JSON structured output, SEO hardening, topic discovery, and incremental ingestion.

### Phase 0: Rename Documentation Gaps (prereq)
- TC-2380 — Rename Documentation Gap Fixes (graph.py comment + spec verification) — DOC_AGENT, P0, no deps — Done

### Tier 1: High-ROI Quality Improvements
- TC-2392 — Layer 1 LLM Response Validator (fence/truncation/frontmatter at call time + retry with error context) — SHARED_AGENT, P1, no deps — Done
- TC-2391 — Tone Control System: declarative voice/formality/structure per section type — W5_AGENT, P1, no deps — Done
- TC-2378 — Content Sanitizer Robust Fence Parser (replace 14 toggle→counter sites) — CONTENT_AGENT, P1, no deps — Done
- TC-2379 — W5 Generator Context Builders + Precedence for 13 Missing Roles — CONTENT_AGENT, P1, no deps — Done
- TC-2393 — Code-First Assembly: separate code model + validation + code-first order — W5_AGENT, P1, no deps — Done
- TC-2376 — W5 Structured Output Envelope (JSON draft + per-section calls) — W5_AGENT, P1, no deps — Done
- TC-2382 — W5 Section Templates YAML (role-specific required sections) — W5_AGENT, P1, no deps — Done

### Tier 2: Additive Improvements
- TC-2395 — SEO Hardening: keyword extraction + injection (1.5% density) + 3-provider metadata fallback — W6_AGENT, P2, no deps — Done
- TC-2394 — Topic Discovery: LLM extracts new article ideas from FOSS repo docs + vector dedup gate — W2_AGENT, P2, no deps — Done
- TC-2381 — Graph Reorder: SEO Before ContentReviewer — GRAPH_AGENT, P2, no deps — Done
- TC-2383 — W2 KB Source Chunking + W5 Retrieval (paragraph-aware + overlap) — W2_AGENT, P2, no deps — Done
- TC-2396 — Three-Layer Quality Gate: severity weights + PASS/FAIL/REVIEW scoring in W7 — W7_AGENT, P2, no deps — Done
- TC-2397 — Incremental Ingestion: hash-based skip for unchanged files (~70% speedup) — W1_AGENT, P2, no deps — Done
- TC-2389 — JSON Contracts: JSON Schema per LLM call + worker I/O validation — ORCH_AGENT, P2, no deps — Done
- TC-2377 — Quality Feedback Loop W9→W2/W4 + prompt enhancement on redraft — W9_AGENT, P1, depends: TC-2376, TC-2378, TC-2379 — Done

### Tier 3: Infrastructure / Maintenance
- TC-2386 — W4 Pre-Generation Duplication Check (D-4) — W4_AGENT, P3, no deps — Done
- TC-2387 — SEO Gate 4 Upgrade (seoTitle/description/keywords checks) — W9_AGENT, P3, no deps — Done
- TC-2384 — MCP HTTP Server (parent TC; child plan: mellow-hugging-shell.md) — MCP_AGENT, P3, no deps — Draft
- TC-2385 — MCP-1 Source Reader Tool in W5 Per-Section Loop — MCP_AGENT, P3, depends: TC-2376 — Draft
- TC-2390 — Link Liveness + Semantic Link Recommendations — MCP_AGENT, P3, no deps — Draft

## Resumable Pipeline Execution (2026-02-21)
- TC-2398 — Spec 43: Resumable Pipeline Execution (AGENT_D, P0, no deps) — Done
- TC-2399 — Implement `launch resume` command with dynamic graph entry point (AGENT_B, P1, depends: TC-2398) — In-Progress

## LLM Performance Optimization (2026-02-21)

Reduce pipeline wall-clock time 2–3× through HTTP connection reuse, rate-limit header parsing,
concurrency control, within-page section parallelization, and artifact dedup.

- TC-2409 — LLM Disk Cache: Opt-In Response Cache for Reruns and Resume Cycles (CACHE_AGENT, P2, depends: TC-500) — In-Progress
- TC-2410 — LLM Cache Observability: Structured Telemetry, Maintenance CLI, and Safety Rails (OBS_AGENT, P2, depends: TC-2409) — In-Progress
- TC-2400 — LLM HTTP Client Performance: Session Pool, Retry-After, max_concurrency Semaphore (PERF_AGENT, P1, no deps) — In-Progress
- TC-2401 — W5 Within-Page Section Parallelization (max_parallel_sections) (PERF_AGENT, P1, depends: TC-2400) — In-Progress
- TC-2402 — W9 Gate 17 System Prompt Dedup (PERF_AGENT, P2, no deps) — Done
- TC-2403 — W7 Parallel Check Execution + Semantic Caching (max_parallel_workers_w7) (PERF_AGENT, P1, no deps) — In-Progress
- TC-2404 — W9 Gate 17 Per-File LLM Parallelization (max_parallel_files_g17) (PERF_AGENT, P2, no deps) — In-Progress
- TC-2405 — W2 Workflow + Example Enrichment Parallelization (reuses max_parallel_batches) (PERF_AGENT, P2, no deps) — In-Progress
- TC-2406 — W7 Phase 0 Format Fix: Per-Call Timeout (120s) + Parallel Loop (reuses max_parallel_workers_w7) (PERF_AGENT, P1, depends: TC-2403) — In-Progress
- TC-2407 — W7 Phase 4 Regen: Per-Call Timeout (120s) + Parallel Per-File Loop (reuses max_parallel_workers_w7) (PERF_AGENT, P1, depends: TC-2403) — In-Progress
- TC-2408 — W2 Enrichment enrich_timeout_s Per-Call Timeout Override (PERF_AGENT, P2, depends: TC-2400) — In-Progress

## Post-Merge Verification & Import Fix (2026-02-22)
- TC-2411 — Fix W2 embeddings import regression (topic_discovery + chunk_sources) (AGENT_11, P0, no deps) — Done
- TC-2412 — E2E mandatory-sections regression test harness (AGENT_12, P1, depends: TC-2411) — Done
- TC-2415 — Round-3 polish: fix stale rationale variable + chunk logging (AGENT_23, P1, no deps) — Done

## Validation Gate Registry Migration (2026-02-22)
- TC-2420 — Gate Registry Engine MVP (registry + runner + adapters + golden test) (Orchestrator, P1, no deps) — Done
- TC-2421 — Gate Test Consolidation (move scattered tests to w9/gates/) (Orchestrator, P1, depends: TC-2420) — Done
- TC-2422 — Gate Registry Spec Update (document registry in specs/09) (Orchestrator, P2, depends: TC-2420) — Done

## Next-Stage Improvements: Quality, Policy, Profiling, Caching, Structured Gen (2026-02-22)
### Phase 0 — Baseline
- TC-2430 — Phase 0: Baseline Re-Verification — Pilot Runs + Equivalence Capture (Orchestrator, P0, no deps) — In-Progress

### Agent A — Gate Engine Hardening
- TC-2431 — Callable Validation at Load Time (registry_loader.py) (Agent_A, P1, depends: TC-2430) — In-Progress
- TC-2432 — Pilot-Scale Golden Comparison Tests + Env-Gated Equivalence Test (Agent_A, P1, depends: TC-2431) — In-Progress
- TC-2433 — Legacy Engine DeprecationWarning (Agent_A, P2, depends: TC-2432) — In-Progress

### Agent B — Mandatory vs Optional Policy Engine
- TC-2436 — Spec Update: specs/06_page_planning.md Policy Layer Section (Agent_B, P1, depends: TC-2431) — In-Progress
- TC-2434 — content_policy.py Module (Agent_B, P1, depends: TC-2436) — In-Progress
- TC-2435 — W4 + W5 Integration: Policy Check in generate_optional_pages() (Agent_B, P1, depends: TC-2434) — In-Progress
- TC-2447 — Evidence-Based Content Policy Engine v2 (Agent_B, P2, depends: TC-2435) — In-Progress

### Agent C — Repo Profiling + Evidence Scoring
- TC-2437 — repo_profiler.py Deterministic Module (Agent_C, P1, depends: TC-2431) — In-Progress
- TC-2438 — W1+W2 Integration: Write repo_profile.json + citation_quality_score (Agent_C, P1, depends: TC-2437) — In-Progress
- TC-2439 — W4 Optional Page Score: Tier Multiplier from repo_profile (Agent_C, P2, depends: TC-2438, TC-2435) — In-Progress
- TC-2448 — Enrich repo_profiler.py with Full Signal Set + W1 Always-On Write (Agent_C, P1, depends: TC-2437, TC-2438) — Done
- TC-2449 — W2 Example Weight Boost + W4 Page Role Eligibility (Agent_C, P2, depends: TC-2448) — Done

### Agent D — Incremental Caching + Performance
- TC-2440 — worker_cache.py Hash-Based Worker Skip Cache (Agent_D, P2, depends: TC-2439) — In-Progress
- TC-2441 — W5 Page-Level Regeneration Cache (Agent_D, P2, depends: TC-2440) — In-Progress
- TC-2442 — run_cache.json Artifact Schema Documentation (Agent_D, P3, depends: TC-2440) — In-Progress
- TC-2443 — Orchestrator Pre/Post Worker Cache Hooks (Agent_D, P2, depends: TC-2441, TC-2442) — In-Progress
- TC-2450 — W5 Page Hash Cache + regen_failed_only (Agent_D, P1, depends: TC-2440, TC-2441) — Done
- TC-2451 — W5 Per-Page Timing Metrics + INCREMENTAL.md (Agent_D, P2, depends: TC-2450) — Done

### Agent E — Structured Generation: Limitations Section
- TC-2444 — limitations_renderer.py Structured Renderer Module (Agent_E, P2, depends: TC-2431) — In-Progress
- TC-2445 — W5 Integration: Structured LLM Call for Limitations (Agent_E, P2, depends: TC-2444) — In-Progress
- TC-2446 — Feature Flag Verification + Freeform Fallback Integration Test (Agent_E, P2, depends: TC-2445) — In-Progress

### Spec v1.1 Compliance (Agents 41-46, retroactive)
- TC-2460 — Version Wiring: template_registry.py + RunConfig object-path fix (Agent_41, P1) — Done
- TC-2461 — Mandatory Page Catalog: ruleset.v1_1 expansion + gate_kb_howto 5-slug update (Agent_42, P1, depends: TC-2460) — Done
- TC-2462 — KB How-To Contract: heading order, not-evidenced fallback, format evidence flow (Agent_43, P1, depends: TC-2461) — Done
- TC-2463 — Blog v1.1: workflow-derived feature_blog slug + cross-section links (Agent_44, P1, depends: TC-2461) — Done
- TC-2464 — Reference Object Pages: per_api_object priority swap + richness boost + role override (Agent_45, P1, depends: TC-2461) — Done
- TC-2465 — Validation Gates 32-33: KB how-to structure + format evidence checking (Agent_46, P1, depends: TC-2462) — Done

### Slug Pipeline Hardening (Agent 47, 2026-02-24)
- TC-2470 — Slug Pipeline Hardening: W6 metadata-only contract + slug_rewrite_enabled flag + regression tests (Agent_47, P1, no deps) — Done

## Quality & Reliability Upgrade (Agent 48, 2026-02-24)

### Atomic Writes & Handoff Contracts
- TC-2470 — W9/W10 atomic write + handoff contract (Agent_48, P1, no deps) — Done
- TC-2471 — W5 draft write atomic migration (Agent_48, P1, no deps) — Done

### Structured Run Results
- TC-2472 — Add run_summary.json artifact to orchestrator (Agent_48, P1, no deps) — Done
- TC-2473 — Update run_pilot.py for structured results (Agent_48, P1, depends: TC-2472) — Done

### Template & Config Hardening
- TC-2474 — Template version hardening (Agent_48, P1, no deps) — Done

### Gate 17 Two-Phase Architecture
- TC-2475 — Gate 17 deterministic pre-lints (Agent_48, P1, no deps) — Done
- TC-2476 — Gate 17 two-phase integration (Agent_48, P1, depends: TC-2475) — Done
- TC-2477 — FQ-3 fixer in W10 (Agent_48, P1, depends: TC-2476) — Done

### Shared Facts & Evidence Pipeline
- TC-2478 — Shared fact sheet artifact (W4) (Agent_48, P1, no deps) — Done
- TC-2479 — W5 fact consumption + Gate 20 strengthening (Agent_48, P1, depends: TC-2478) — Done
- TC-2480 — Family capability extraction (W4) (Agent_48, P1, depends: TC-2478) — Done

### Evidence-Aware Slug Derivation
- TC-2481 — Evidence-aware how-to slug derivation (Agent_48, P1, depends: TC-2480) — Done
- TC-2481b — Gate 30+32 role-based mandatory how-to validation (Agent_48, P1, depends: TC-2481) — Done

### W5 Evidence & Consistency
- TC-2482 — Evidence pack stage (pre-Draft) (Agent_48, P1, depends: TC-2478) — Done
- TC-2483 — Post-draft consistency check (Agent_48, P1, depends: TC-2482) — Done

## Deep-Dive: Phased Execution, Handoff Integrity, Template Versioning (Agent 49, 2026-02-25)

Plan: `soft-orbiting-blossom.md` | Audit: `reports/orchestrator/r_phase0/research_audit.md`

### Phase 1 — Phased Pilot Execution Runner
- TC-2500 — Phase group executor (compose resume calls sequentially) (Agent_49, P1, no deps) — Draft
- TC-2501 — Phase artifact verifier (schema + existence checks) (Agent_49, P1, no deps) — Draft
- TC-2502 — CLI `launch phase` subcommand (Agent_49, P1, depends: TC-2500, TC-2501) — Draft
- TC-2503 — `run_pilot.py` phase-mode integration (Agent_49, P1, depends: TC-2502) — Draft
- TC-2504 — Phase integrity report artifact `phase_report.json` (Agent_49, P1, depends: TC-2500) — Draft

### Phase 2 — W9/W10 Handoff Integrity
- TC-2505 — W9 content hash computation + emission (Agent_49, P2, no deps) — Draft
- TC-2506 — W10 generation_id + content_hash verification (Agent_49, P2, depends: TC-2505) — Draft
- TC-2507 — Orchestrator generation_id propagation through fix loop (Agent_49, P2, depends: TC-2506) — Draft
- TC-2508 — Deterministic tests: stale artifact, mismatched hash, missing generation_id (Agent_49, P2, depends: TC-2505, TC-2506) — Draft

### Phase 3 — Template Versioning Hardening
- TC-2509 — Create `specs/templates/templates.v1/` with current template content (Agent_49, P2, no deps) — Draft
- TC-2510 — Add deprecation warning on legacy fallback + `template_root_used` diagnostic (Agent_49, P2, depends: TC-2509) — Draft
- TC-2511 — Tests: versioned dir exists, versioned dir missing + strict mode, diagnostic emission (Agent_49, P2, depends: TC-2509, TC-2510) — Draft

### Phase 4 — Family Capability Registry + Slug Architecture
- TC-2512 — Family capabilities schema + spec update (Agent_49, P1, no deps) — Draft
- TC-2513 — W2 family capabilities extraction (deterministic) (Agent_49, P1, depends: TC-2512) — Draft
- TC-2514 — W4 slug generation refactor — read registry instead of hardcoded maps (Agent_49, P1, depends: TC-2512, TC-2513) — Draft
- TC-2515 — Slug collision detection (uniqueness within section namespace) (Agent_49, P1, depends: TC-2514) — Draft
- TC-2516 — W6 registry-validated slug refinement (Agent_49, P1, depends: TC-2512, TC-2513, TC-2514) — Draft
- TC-2517 — Conversion-pair extraction bugfix investigation (Agent_49, P1, no deps) — Draft
- TC-2518 — Multi-family slug tests (3D, Cells, Note collision matrix) (Agent_49, P1, depends: TC-2513, TC-2515) — Draft

### Phase 5 — LLM Contract Hardening
- TC-2519 — LLM contract module — output schema validator + failure classifier (Agent_49, P2, no deps) — Draft
- TC-2520 — W5 micro-task schema contracts (draft + refine outputs) (Agent_49, P2, depends: TC-2519) — Draft
- TC-2521 — Rule checklist injection per W5 micro-task (Agent_49, P2, depends: TC-2520) — Draft
- TC-2522 — Gate 17 FQ-7 stability — split + deterministic sub-checks + retry (Agent_49, P2, depends: TC-2519) — Draft
- TC-2523 — Heading hierarchy validator (deterministic) (Agent_49, P2, no deps) — Draft
- TC-2524 — Bounded output length enforcement (Agent_49, P2, no deps) — Draft

### Phase 6 — Cross-Page Consistency & Contradiction Prevention
- TC-2525 — G20-005/006/007 cross-page consistency checks (Agent_49, P2, no deps) — Draft
- TC-2526 — W10 contradiction resolver (shared_facts as source of truth) (Agent_49, P2, depends: TC-2525) — Draft
- TC-2527 — W5 canonical facts enforcement (reject draft if contradicts facts) (Agent_49, P2, no deps) — Draft
- TC-2528 — Synthetic contradiction fixtures + tests (Agent_49, P2, depends: TC-2525, TC-2526, TC-2527) — Draft

### Phase 7 — Quality Feedback Loop (Spec 42)
- TC-2529 — W2 feedback wiring (call existing function from main path) (Agent_49, P1, no deps) — Draft
- TC-2530 — Feedback delta artifact emission (W2 + W4) (Agent_49, P1, depends: TC-2529) — Draft
- TC-2531 — Pilot config update + two-run verification for feedback loop (Agent_49, P1, depends: TC-2529, TC-2530) — Draft
- TC-2532 — Tests proving feedback changes selection outcomes (Agent_49, P1, depends: TC-2529, TC-2530) — Draft

### Phase 8 — Manual Review Agent
- TC-2533 — Review rubric schema + dimensions specification (Agent_49, P2, no deps) — Draft
- TC-2534 — Deterministic dimension checkers (RD-02,03,04,05,06,07,08,10,12) (Agent_49, P2, depends: TC-2533) — Draft
- TC-2535 — LLM dimension checkers (RD-01, RD-09, RD-11) (Agent_49, P2, depends: TC-2533) — Draft
- TC-2536 — Review report aggregator + summary generator (Agent_49, P2, depends: TC-2534, TC-2535) — Draft
- TC-2537 — Orchestrator integration (review -> taskcard creation) (Agent_49, P2, depends: TC-2536) — Draft
- TC-2538 — Review all 3 pilot outputs, log baseline scores (Agent_49, P2, depends: TC-2536, TC-2537) — Draft

### Phase 9 — GitHub Organization Monitoring & Pilot Intake
- TC-2539 — Intake config schema + spec for GitHub org monitoring (Agent_49, P3, no deps) — Done
- TC-2540 — Org scanner (GitHub API, pagination, rate limiting, state persistence) (Agent_49, P3, depends: TC-2539) — Done
- TC-2541 — Repo classifier (heuristics, deterministic decisions) (Agent_49, P3, depends: TC-2539) — Done
- TC-2542 — Config generator (YAML template, dedup against existing pilots) (Agent_49, P3, depends: TC-2539, TC-2541) — Done
- TC-2543 — Scheduler (priority queue, batch mode, dry-run) (Agent_49, P3, depends: TC-2539) — Done
- TC-2544 — CLI entrypoints (launch intake scan/classify/generate) (Agent_49, P3, depends: TC-2540, TC-2541, TC-2542, TC-2543) — Done
- TC-2545 — Integration tests (mocked GitHub API responses) (Agent_49, P3, depends: TC-2540, TC-2541, TC-2542, TC-2543, TC-2544) — Done

## Slug Architecture Hardening (Agent 50, 2026-02-25)

Plan: `warm-floating-hickey.md` | 7 phases, 15 taskcards | Tests: +168 new (6178 total)

### Phase 0 — Baseline Capture
- TC-2600 — Baseline slug inventory and spec-code discrepancy report (Agent_50, P0, no deps) — Done

### Phase 1 — Shared Slug Infrastructure
- TC-2601 — Shared slug constants module (slug_constants.py) (Agent_50, P1, no deps) — Done
- TC-2602 — W4 slug format validation at plan time (Agent_50, P1, depends: TC-2601) — Done

### Phase 2 — Platform-Aware Slug Templates
- TC-2604 — Platform-aware slug templates in W4 (Agent_50, P2, depends: TC-2601) — Done
- TC-2605 — Thread platform through load_and_merge_page_requirements (Agent_50, P2, depends: TC-2604) — Done
- TC-2606 — Pilot re-baseline for Phase 2 (Agent_50, P2, depends: TC-2605) — Done

### Phase 3 — Blog Slug Evidence Enhancement
- TC-2607 — Blog evidence-aware slug generation (Agent_50, P3, depends: TC-2601) — Done
- TC-2608 — Pilot re-baseline for Phase 3 (Agent_50, P3, depends: TC-2607) — Done

### Phase 4 — W6 Slug Refinement Production-Readiness
- TC-2609 — Schema-constrain W6 LLM slug refinement (Agent_50, P4, depends: TC-2601) — Done
- TC-2610 — Deterministic validation for slug refinement candidates (Agent_50, P4, depends: TC-2609) — Done
- TC-2611 — Test suite for W6 slug refinement pipeline (Agent_50, P4, depends: TC-2609, TC-2610) — Done

### Phase 5 — Gate Alignment & Topic Category Cleanup
- TC-2612 — Deprecate slug-based inference in Gate 30 (Agent_50, P5, depends: TC-2601) — Done
- TC-2613 — Add G20-008 slug-evidence consistency check (Agent_50, P5, no deps) — Done
- TC-2614 — Derive REQUIRED_TOPIC_CATEGORIES from canonical map (Agent_50, P5, depends: TC-2601) — Done

### Phase 6 — Quality Pass
- TC-2615 — Reviewer-driven quality pass (3D pilot 30/33) (Agent_50, P6, depends: ALL) — Done

## CLI Monitoring Enhancement (2026-02-26)

- TC-2700 — Document launch monitor and launch phase commands in CLI reference (Agent_51, P1, no deps) — Draft

## Truth Enforcement Layer (2026-02-26)

Epic: make hallucination, name corruption, broken links, and slug corruption impossible to publish.

### Phase 0 — Baseline + Governance
- TC-2800 — Baseline RCA + evidence pack for truth enforcement (Orchestrator, P0, no deps) — Draft

### Phase 1 — API Inventory + Code Fence Validation
- TC-2810 — Extend W2 code_analysis into api_inventory.json artifact (Agent_52, P0, depends: TC-2800) — Draft
- TC-2811 — Gate 15b: code fence API validation blocker (Agent_52, P0, depends: TC-2810) — Draft
- TC-2812 — W5 evidence-gated code generation with API symbol injection (Agent_52, P0, depends: TC-2810) — Draft

### Phase 2 — Sanitizer Product Name Fix
- TC-2820 — Sanitizer product name allowlist (Agent_52, P1, depends: TC-2800) — Draft
- TC-2821 — Gate: product name integrity blocker (Agent_52, P1, depends: TC-2820) — Draft

### Phase 3 — Link Resolution Upgrade
- TC-2830 — Gate 5 upgrade: absolute link + placeholder + domain validation (Agent_52, P1, depends: TC-2800) — Draft

### Phase 4 — Slug Safety
- TC-2840 — Fix conversion_pairs type handling in W4 (Agent_52, P1, depends: TC-2800) — Draft
- TC-2841 — Gate: slug/path safety validation (Agent_52, P1, depends: TC-2840) — Draft

### Phase 5 — Scaffold Leak Gate
- TC-2850 — Gate: scaffold/prompt leak detection blocker (Agent_52, P2, depends: TC-2800) — Draft

### Phase 6 — Dedup Severity Upgrade
- TC-2860 — Gate 19 dedup severity upgrade with profile-aware thresholds (Agent_52, P2, depends: TC-2800) — Draft

## Prevention Engine Activation (2026-02-26)

### Schema↔Config Alignment
- TC-2870 — Enable multi-pass generation prevention engine: schema-config alignment (Agent_b, P0, no deps) — In-Progress
