# Plan Sources Resolution
**Generated**: 2026-02-05T07:40:00Z
**Updated**: 2026-02-05T16:00:00Z (evidence-driven page scaling + configurable page requirements)

## ChatExtractedSteps

From LAST user message (orchestrator spawn directive):
> "Spawn specialist agents for repo tasks with evidence-based self-review. ANY score <4/5 -> route back for hardening until pass."

From LAST assistant plan (`C:\Users\prora\.claude\plans\spicy-floating-tome.md`):
1. **Part A**: Configurable page requirements in ruleset + family overrides
   - A1: Extend ruleset.v1.yaml with mandatory_pages + optional_page_policies per section
   - A2: Add family_overrides top-level key to ruleset
   - A3: Update ruleset.schema.json
   - A4: Add load_and_merge_page_requirements() to W4
2. **Part B**: Evidence-driven page scaling
   - B1: compute_evidence_volume() function
   - B2: compute_effective_quotas() function
   - B3: generate_optional_pages() function (spec 06 algorithm)
   - B4: Soften CI-absent tier reduction
   - B5: Integrate into execute_ia_planner()
   - B6: Add evidence_volume + effective_quotas to page_plan.json
3. **Part C**: Full spec artifact updates (schemas, gates, specs, contracts, rulesets)
   - C1: 3 schemas (ruleset, page_plan, validation_report)
   - C2: 4 specs (06, 07, 08, 09)
   - C3: 1 worker contract (21)
   - C4: 1 ruleset (ruleset.v1.yaml)
   - C5: 1 gate impl (W7 Gate 14)
4. Evidence commands: pytest tests/unit/workers/test_w4_*.py, pytest tests/, pilot runs

## ChatExtractedGapsAndFixes

**Gap 1: Hardcoded page counts (Root Cause 1+5) [CRITICAL]**
- Code: w4_ia_planner/worker.py lines 640-972
- Problem: plan_pages_for_section() uses tier-based hardcoded counts, not configurable
- Fix: Move mandatory page definitions to ruleset.v1.yaml, implement load_and_merge_page_requirements()

**Gap 2: No evidence scaling (Root Cause 2+3) [CRITICAL]**
- Code: w4_ia_planner/worker.py lines 1797-1803
- Problem: Static max_pages from ruleset, spec 06 quality_score algorithm unimplemented
- Fix: compute_evidence_volume() + compute_effective_quotas() + generate_optional_pages()

**Gap 3: Aggressive tier reduction (Root Cause 4) [HIGH]**
- Code: w4_ia_planner/worker.py lines 412-423
- Problem: CI absent alone drops standard → minimal
- Fix: Only reduce when BOTH CI and tests missing

**Gap 4: Spec artifacts inconsistent [HIGH]**
- Problem: Changes to W4 logic require updates across 11 spec artifacts
- Fix: Part C systematically updates all schemas, gates, specs, contracts

**Gap 5: No configurable family-level page overrides [MEDIUM]**
- Problem: All product families get identical mandatory page sets
- Fix: family_overrides in ruleset merges with global config

## ChatMentionedFiles

- `src/launch/workers/w4_ia_planner/worker.py` (Parts A, B)
- `src/launch/workers/w7_validator/worker.py` (Part C5)
- `specs/rulesets/ruleset.v1.yaml` (Parts A1, A2, C4)
- `specs/schemas/ruleset.schema.json` (Part C1)
- `specs/schemas/page_plan.schema.json` (Part C1)
- `specs/schemas/validation_report.schema.json` (Part C1)
- `specs/06_page_planning.md` (Part C2)
- `specs/07_section_templates.md` (Part C2)
- `specs/08_content_distribution_strategy.md` (Part C2)
- `specs/09_validation_gates.md` (Part C2)
- `specs/21_worker_contracts.md` (Part C3)
- `tests/unit/workers/test_w4_evidence_scaling.py` (new)

## SubstantialityCheck

**SUBSTANTIAL**: YES
- 15+ actionable steps derived (A1-A4, B1-B6, C1-C5)
- 5 concrete gaps with plausible fixes (code locations, line numbers, fix strategies)
- Clear acceptance criteria (page count differentiation, schema validation, test suite green)
- 6+ evidence commands (pytest suites, pilot runs, determinism checks)

## ResolutionStrategy

**PREVIOUS PRIMARY**: `plans/from_chat/20260205_160000_evidence_driven_page_scaling.md` (COMPLETED)
**PREVIOUS SECONDARY**: `C:\Users\prora\.claude\plans\spicy-floating-tome.md` (raw plan, COMPLETED)

---

## Session 3: Template Audit & Restructuring (2026-02-05)

### ChatExtractedSteps

From LAST assistant plan (`C:\Users\prora\.claude\plans\melodic-nibbling-shore.md`):
1. **TC-990**: Update specs 06, 07, 21, schemas to reflect correct template structure per subdomain
2. **TC-991**: Delete ~72 wrong-hierarchy template files (converter, section_path, format_slug, misplaced blog)
3. **TC-992**: Create ~51 new templates for full family parity (3d, cells, note)
4. **TC-993**: Update W4 enumerate_templates() for new structure + page_role derivation
5. **TC-994**: Update W5 to follow templates for all page types (feature, howto, reference)
6. **TC-995**: Update/add tests for template enumeration and page roles
7. **TC-996**: Audit validation gates for template path references
8. **TC-997**: Run pilot, verify template discovery, produce evidence bundle

### ChatExtractedGapsAndFixes

**Gap 1: Wrong-hierarchy templates (CRITICAL)**
- 30 files under `__CONVERTER_SLUG__/` — hierarchy doesn't exist in reality
- 10 files under `__SECTION_PATH__/` — too abstract, real sections are concrete
- Fix: Delete all, replace with concrete section templates (developer-guide, getting-started)

**Gap 2: Blog templates with __PLATFORM__ (HIGH)**
- Blog has NO platform segment per real site structure
- 9 V2 blog templates + 14 misplaced blog templates in docs
- Fix: Delete all, keep V1 blog templates (no platform, no locale)

**Gap 3: Missing templates (HIGH)**
- No getting-started section templates for any family
- No feature/howto/reference repeatable variants
- No family parity (cells has templates, 3d/note partially)
- Fix: Create ~51 new templates with correct frontmatter

**Gap 4: Spec contradictions (MEDIUM)**
- spec 07 claims blog V2 uses `__PLATFORM__` — WRONG per ground truth
- specs reference `__CONVERTER_SLUG__`, `__FORMAT_SLUG__`, `__SECTION_PATH__` as valid
- Fix: Correct specs before any file operations

**Gap 5: W4 doesn't derive page_role from template filename (MEDIUM)**
- New concrete filenames (feature.*, howto.*, reference.*) need page_role mapping
- Fix: Add derivation logic in enumerate_templates()

### ChatMentionedFiles

- `specs/07_section_templates.md` (TC-990)
- `specs/06_page_planning.md` (TC-990)
- `specs/21_worker_contracts.md` (TC-990)
- `specs/schemas/page_plan.schema.json` (TC-990)
- `specs/templates/**` (TC-991, TC-992)
- `src/launch/workers/w4_ia_planner/worker.py` (TC-993)
- `src/launch/workers/w5_section_writer/worker.py` (TC-994)
- `tests/unit/workers/test_w4_template_enumeration*.py` (TC-995)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 8 actionable taskcards with 40+ implementation steps
- 5 concrete gaps with plausible fixes (exact file counts, line numbers)
- Clear acceptance criteria per taskcard + pilot verification
- Evidence commands: pytest, pilot runs, tree diffs

### ResolutionStrategy

**PRIMARY**: `plans/from_chat/20260205_200000_template_audit_restructuring.md`
**SECONDARY**: `C:\Users\prora\.claude\plans\melodic-nibbling-shore.md` (detailed plan)
**NEXT**: Create taskcards, spawn agents per dependency graph: TC-990 → (TC-991 || TC-996) → TC-992 → (TC-993 || TC-994) → TC-995 → TC-997

**STATUS**: TC-990 through TC-997 COMPLETE (2026-02-05). All template audit tasks executed.

---

## Session 4: VFV Loop + Content Quality + Dual-Pilot Verification (2026-02-05)

### ChatExtractedSteps

From plan file (`C:\Users\prora\.claude\plans\melodic-nibbling-shore.md`):
1. **Phase 0**: Delete stale `nul` file from repo root (DONE)
2. **Phase 1**: Fix W4 `generate_content_tokens()` — add 42 missing tokens (TC-998)
3. **Phase 2**: Wire LLM client auto-construction in W5 `execute_section_writer()` + update pilot configs to `qwen3:14b` (TC-999, DONE)
4. **Phase 3**: Fix 15 pre-existing test failures (VFV:4, SectionWriter:2, PRManager:8, nul:1) (TC-1000)
5. **Phase 4**: Run full test suite — target 0 failures
6. **Phase 5**: Run both pilots E2E with real Ollama LLM (`qwen3:14b`)
7. **Phase 6**: VFV determinism verification for both pilots
8. **Phase 7**: Final evidence bundle + 12D self-review

### ChatExtractedGapsAndFixes

**Gap 1: 42 missing tokens in W4 (CRITICAL, pilot blocker)**
- Products: 9 tokens (`__FEATURES_*__`, `__CODE_EXAMPLES_*__`, `__FORMATS_*__`)
- Docs: 6 installation + 4 licensing + 5 structural
- Reference: 7 API tokens (`__BODY_CONSTRUCTORS__`, `__BODY_PROPERTIES__`, etc.)
- Navigation: 8 URL tokens (`__URL_DEVELOPER_GUIDE__`, etc.)
- KB: 3 howto tokens
- Fix: Add all to `generate_content_tokens()` in section-conditional block

**Gap 2: W5 never gets LLM client (CRITICAL, content quality blocker)**
- `WorkerInvoker.invoke_worker()` calls `executor(run_dir, run_config)` — no llm_client
- W5 always falls back to template-based content (no real synthesis)
- Fix: Auto-construct `LLMProviderClient` from `run_config["llm"]` inside W5 (DONE)

**Gap 3: Pilot configs point to nonexistent model (HIGH)**
- `model: "gpt-4o-mini"` — not available via local Ollama
- Fix: Change to `model: "qwen3:14b"` (DONE)

**Gap 4: 15 pre-existing test failures (MEDIUM)**
- VFV tests: ERROR vs FAIL status confusion
- Section writer: old claim marker format
- PR manager: offline mode auto-enabled on default profile
- Fix: Update assertions and test configs

### ChatMentionedFiles

- `src/launch/workers/w4_ia_planner/worker.py` (Phase 1)
- `src/launch/workers/w5_section_writer/worker.py` (Phase 2, DONE)
- `specs/pilots/pilot-aspose-3d-foss-python/run_config.pinned.yaml` (Phase 2, DONE)
- `specs/pilots/pilot-aspose-note-foss-python/run_config.pinned.yaml` (Phase 2, DONE)
- `tests/e2e/test_tc_903_vfv.py` (Phase 3)
- `tests/unit/workers/test_tc_440_section_writer.py` (Phase 3)
- `tests/unit/workers/test_tc_480_pr_manager.py` (Phase 3)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 8 phases with 42+ actionable items
- 4 concrete gaps with evidence-backed fixes
- 18-item verification checklist
- Multiple evidence commands (pytest, pilot runs, VFV harness)

### ResolutionStrategy

**PRIMARY**: `C:\Users\prora\.claude\plans\melodic-nibbling-shore.md`
**AGENTS**: Phase 1 (Agent-B, a4eb37b), Phase 3 (Agent-C, a816ee7), Phase 2 (direct, DONE)
**NEXT**: Wait for agents → Phase 4 (test suite) → Phase 5 (pilots) → Phase 6 (VFV)

---

## Session 5: Exhaustive Repo Ingestion Plan (2026-02-06)

### ChatExtractedSteps

From plan file (`C:\Users\prora\.claude\plans\rustling-pondering-seahorse.md`):
1. **Phase 0**: Update specs for exhaustive ingestion (specs 02, 03, 05, 21) + run_config schema
2. **Phase 1**: W1 exhaustive discovery (doc discovery, configurable scan dirs, .gitignore, fingerprinting)
3. **Phase 2**: W2 exhaustive extraction (remove 10-doc cap, 4-word min, keyword filter, 10-example cap)
4. **Phase 3**: Infrastructure (typed artifact models, centralized ArtifactStore)
5. **Phase 4**: Integration (write-time validation, testing, W1 stub enrichment)

### ChatExtractedGapsAndFixes

**Gap 1: Selective doc discovery (CRITICAL)**
- Code: w1_repo_scout/discover_docs.py lines 250, 262-263, 38-49
- Problem: Only .md/.rst/.txt scanned, hidden dirs skipped, pattern matching filters
- Fix: Record ALL files, use patterns for SCORING only

**Gap 2: Hardcoded scan directories (HIGH)**
- Code: w1_repo_scout/discover_examples.py line 41
- Problem: Only examples/, samples/, demo/ scanned
- Fix: Configurable list including src/, config/, tests/, tools/, docker/, etc.

**Gap 3: W2 extraction limits (CRITICAL)**
- Code: w2_facts_builder/extract_claims.py lines 419, 370, 372-377; worker.py line 314
- Problem: 10-doc cap, 4-word minimum, keyword filter, 10-example cap
- Fix: Remove ALL limits - everything discovered must be ingested

**Gap 4: Unused .gitignore support (MEDIUM)**
- Code: w1_repo_scout/fingerprint.py line 162
- Problem: `respect_gitignore=True` parameter exists but is NOT implemented
- Fix: Implement using pathspec library

**Gap 5: No phantom path detection (MEDIUM)**
- Spec: specs/02_repo_ingestion.md lines 103-141
- Problem: Spec requires detecting paths referenced in docs but absent from repo
- Fix: Implement cross-reference after discovery

### ChatMentionedFiles

- `specs/02_repo_ingestion.md` (Phase 0)
- `specs/03_product_facts_and_evidence.md` (Phase 0)
- `specs/05_example_curation.md` (Phase 0)
- `specs/21_worker_contracts.md` (Phase 0)
- `specs/schemas/run_config.schema.json` (Phase 0)
- `src/launch/models/run_config.py` (Phase 0)
- `src/launch/workers/w1_repo_scout/discover_docs.py` (Phase 1)
- `src/launch/workers/w1_repo_scout/discover_examples.py` (Phase 1)
- `src/launch/workers/w1_repo_scout/fingerprint.py` (Phase 1)
- `src/launch/workers/w2_facts_builder/extract_claims.py` (Phase 2)
- `src/launch/workers/w2_facts_builder/worker.py` (Phase 2)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 13 taskcards with 50+ implementation steps
- 5 concrete gaps with exact code locations and line numbers
- Clear acceptance criteria (exhaustive discovery, no limits, configurable dirs)
- Evidence commands: pytest, pilot runs, diff analysis

### ResolutionStrategy

**PRIMARY**: `C:\Users\prora\.claude\plans\rustling-pondering-seahorse.md`
**CONFLICT**: Taskcard IDs TC-980 through TC-992 in plan conflict with existing taskcards
**RESOLUTION**: Re-number exhaustive ingestion taskcards to TC-1000+ series
**STATUS**: Plan exists, taskcards need re-numbering, then implementation

**CURRENT PRIORITY**: Superseded by Session 7 comprehensive healing plan

---

## Session 6: Stale Fixtures + cross_links Absolute + content_preview Bug (2026-02-06)

### ChatExtractedSteps

From plan file (`C:\Users\prora\.claude\plans\joyful-swinging-rainbow.md`):
1. **TC-998**: Fix expected_page_plan.json stale url_path values (remove section names from paths)
2. **TC-999**: Fix test_tc_450_linker_and_patcher.py stale fixture url_path
3. **TC-1000**: Fix W6 content_preview double-dir bug (line 867)
4. **TC-1001**: Make cross_links absolute in W4 add_cross_links()
5. **TC-1002**: Document absolute cross_links in specs/schemas
6. **TC-1003**: Verification - all fixes + pilots

### ChatExtractedGapsAndFixes

**Gap 1: Stale expected_page_plan.json (MEDIUM)**
- Files: specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json, specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json
- Problem: url_path contains section names like `/3d/python/kb/faq/` instead of `/3d/python/faq/`
- Fix: Remove section names from url_path (section = subdomain, not path segment)

**Gap 2: Stale test fixture (MEDIUM)**
- File: tests/unit/workers/test_tc_450_linker_and_patcher.py line ~78
- Problem: url_path `/test-product/python/docs/getting-started/` has section in path
- Fix: Change to `/test-product/python/getting-started/`

**Gap 3: W6 content_preview double-dir bug (LOW)**
- File: src/launch/workers/w6_linker_and_patcher/worker.py line 867
- Problem: `content_preview_dir = run_layout.run_dir / "content_preview" / "content"` causes double content/content
- Fix: Remove extra "content" → `run_layout.run_dir / "content_preview"`

**Gap 4: cross_links relative (USER REQUIREMENT)**
- File: src/launch/workers/w4_ia_planner/worker.py add_cross_links() lines 1536-1572
- Problem: cross_links stores relative url_path, user wants absolute URLs
- Fix: Use build_absolute_public_url() from src/launch/resolvers/public_urls.py

**Gap 5: Spec/schema not documenting cross_links format (MEDIUM)**
- Files: specs/schemas/page_plan.schema.json, specs/06_page_planning.md, specs/21_worker_contracts.md
- Problem: cross_links format not specified as absolute URLs
- Fix: Update specs and schema to document absolute URL format

### ChatMentionedFiles

- `specs/pilots/pilot-aspose-3d-foss-python/expected_page_plan.json` (TC-998)
- `specs/pilots/pilot-aspose-note-foss-python/expected_page_plan.json` (TC-998)
- `tests/unit/workers/test_tc_450_linker_and_patcher.py` (TC-999)
- `src/launch/workers/w6_linker_and_patcher/worker.py` (TC-1000)
- `tests/unit/workers/test_w6_content_export.py` (TC-1000)
- `src/launch/workers/w4_ia_planner/worker.py` (TC-1001)
- `src/launch/resolvers/public_urls.py` (TC-1001, read-only)
- `specs/schemas/page_plan.schema.json` (TC-1002)
- `specs/06_page_planning.md` (TC-1002)
- `specs/21_worker_contracts.md` (TC-1002)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 6 taskcards with clear scope and dependencies
- 5 concrete gaps with file paths and line numbers
- Clear acceptance criteria (tests pass, pilots pass, cross_links absolute)
- Evidence commands: pytest, pilot runs

### ResolutionStrategy

**PRIMARY**: `C:\Users\prora\.claude\plans\joyful-swinging-rainbow.md`
**TASKCARDS**: TC-998 through TC-1003
**PARALLEL EXECUTION**:
- Phase 1: TC-998, TC-1000, TC-1001 (no dependencies)
- Phase 2: TC-999 (after TC-998), TC-1002 (after TC-1001)
- Phase 3: TC-1003 (verification after all)

**STATUS**: COMPLETE (2026-02-06). All 6 taskcards executed, all self-reviews pass.

---

## Session 7: Comprehensive Healing Plan — Complete the System (2026-02-07)

### ChatExtractedSteps

From comprehensive healing plan (`C:\Users\prora\.claude\plans\atomic-herding-hopcroft.md`):

**Phase 0 — Critical Fixes (4 TCs, immediate, parallel)**:
1. TC-1010: Fix W4 claim_group data model bugs (3 locations: lines 858, 1302, 1334)
2. TC-1011: Add cells/note family_overrides to ruleset.v1.yaml
3. TC-1012: Fix expected_page_plan.json cross_links to ABSOLUTE URLs
4. TC-1013: Remove/configure W2 evidence mapping caps

**Phase 1 — Design Artifacts (2 TCs, blocks Phase 2)**:
5. TC-1020: Update specs (02, 03, 05, 21) for exhaustive ingestion
6. TC-1021: Update run_config schema + model for configurable ingestion

**Phase 2 — W1/W2 Exhaustive Ingestion (5 TCs, parallel after Phase 1)**:
7. TC-1022: Exhaustive doc discovery (remove extension filters)
8. TC-1023: Configurable scan directories for code/example discovery
9. TC-1024: .gitignore support + phantom path detection
10. TC-1025: Fingerprinting improvements (configurable ignores, size tracking)
11. TC-1026: Remove all W2 extraction limits

**Phase 3 — Infrastructure (4 TCs, parallel with Phases 1-2)**:
12. TC-1030: Typed artifact models — foundation
13. TC-1031: Typed artifact models — worker models
14. TC-1032: Centralized ArtifactStore class
15. TC-1033: Write-time validation + worker migration

**Phase 4 — Integration (2 TCs)**:
16. TC-1034: W1 stub artifact enrichment
17. TC-1035: Testing coverage expansion

**Phase 5 — Verification (2 TCs)**:
18. TC-1036: Create cells pilot
19. TC-1037: Final verification all pilots E2E + VFV

### ChatExtractedGapsAndFixes

**Gap 1: 3 claim_group bugs in W4 (CRITICAL)**
- Code: w4_ia_planner/worker.py lines 858, 1302, 1334
- Problem: `c.get("claim_group", "")` reads per-claim field that doesn't exist
- Fix: Use `product_facts.get("claim_groups", {})` top-level dict

**Gap 2: Missing family_overrides (HIGH)**
- File: specs/rulesets/ruleset.v1.yaml lines 117-128
- Problem: Only "3d" has family_overrides, missing "cells" and "note"
- Fix: Add cells/note overrides with product-appropriate mandatory pages

**Gap 3: VFV cross_links mismatch (HIGH)**
- Files: specs/pilots/*/expected_page_plan.json
- Problem: cross_links RELATIVE but W4 produces ABSOLUTE (after TC-1001)
- Fix: Update expected files to match W4 ABSOLUTE format

**Gap 4: W2 evidence mapping caps (MEDIUM)**
- Code: map_evidence.py lines 152, 184, 195, 202, 234
- Problem: max_evidence_per_claim=5/3, relevance_score thresholds 0.2/0.25
- Fix: Make configurable, raise defaults

**Gap 5: Exhaustive ingestion at 0% (CRITICAL)**
- Code: W1 discover_docs.py (extension filter), discover_examples.py (hardcoded dirs), W2 extract_claims.py (caps/filters), worker.py (10-example cap)
- Fix: Remove all filters/caps, make configurable via run_config

**Gap 6: No typed artifact models or ArtifactStore (MEDIUM)**
- Problem: 14+ duplicated load functions, 9+ duplicated emit_event
- Fix: Typed models + centralized ArtifactStore + worker migration

### ChatMentionedFiles

- `C:\Users\prora\.claude\plans\atomic-herding-hopcroft.md` (comprehensive plan)
- `src/launch/workers/w4_ia_planner/worker.py` (TC-1010)
- `specs/rulesets/ruleset.v1.yaml` (TC-1011)
- `specs/pilots/*/expected_page_plan.json` (TC-1012)
- `src/launch/workers/w2_facts_builder/map_evidence.py` (TC-1013)
- `specs/02_repo_ingestion.md` (TC-1020)
- `specs/03_product_facts_and_evidence.md` (TC-1020)
- `specs/05_example_curation.md` (TC-1020)
- `specs/21_worker_contracts.md` (TC-1020)
- `specs/schemas/run_config.schema.json` (TC-1021)
- `src/launch/models/run_config.py` (TC-1021)
- `src/launch/workers/w1_repo_scout/discover_docs.py` (TC-1022)
- `src/launch/workers/w1_repo_scout/discover_examples.py` (TC-1023)
- `src/launch/workers/w1_repo_scout/fingerprint.py` (TC-1024, TC-1025)
- `src/launch/workers/w2_facts_builder/extract_claims.py` (TC-1026)
- `src/launch/workers/w2_facts_builder/worker.py` (TC-1026)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 18 taskcards across 5 phases with 100+ implementation steps
- 6 concrete gaps with exact code locations and line numbers
- Clear acceptance criteria per taskcard + E2E pilot verification
- Evidence commands: pytest, pilot runs, VFV determinism, taskcard validation

### ResolutionStrategy

**PRIMARY**: `C:\Users\prora\.claude\plans\atomic-herding-hopcroft.md`
**SECONDARY**: `C:\Users\prora\.claude\plans\rustling-pondering-seahorse.md` (exhaustive ingestion detail)
**EXECUTION**: Phase 0 (4 parallel agents) → Phase 1 (specs) → Phase 2+3 (parallel) → Phase 4 → Phase 5
**STATUS**: Executing — Phase 0 agents spawning

---

## Session 8: W2 Intelligence — Deep Code Understanding for Content Generation (2026-02-07)

### ChatExtractedSteps

From plan file (`C:\Users\prora\.claude\plans\floofy-drifting-finch.md`):
1. **Phase 0**: Update specifications (specs 03, 07, 08, 21, 30, schemas) — FOUNDATION
2. **Phase 1**: Implement code analyzer (AST parsing, manifest parsing, constant extraction)
3. **Phase 2**: Implement workflow enrichment (step ordering, descriptions, complexity)
4. **Phase 3**: Implement semantic understanding (LLM claim enrichment, embeddings) — MANDATORY
5. **Phase 4**: Integration testing + pilot verification

### ChatExtractedGapsAndFixes

**Gap 1: W2 treats code as text, no structural understanding (CRITICAL)**
- Code: w2_facts_builder/worker.py lines 294-299, 324-326
- Problem: api_surface_summary empty, positioning hardcoded placeholders
- Fix: AST parsing for Python/JS/C# to extract classes, functions, constants

**Gap 2: W2 outputs minimal workflow metadata (HIGH)**
- Code: w2_facts_builder/worker.py lines 278-293
- Problem: Workflows just grouped claim IDs, no descriptions/step ordering
- Fix: Enrich workflows with descriptions, step ordering, complexity estimates

**Gap 3: Claims lack semantic context (HIGH)**
- Problem: No audience level, complexity, prerequisites, use cases
- Fix: LLM-based claim enrichment (MANDATORY) with caching + offline fallbacks

**Gap 4: W5 gets insufficient data for quality content (HIGH)**
- Code: w5_section_writer/worker.py lines 750-849
- Problem: Only uses claim_id + claim_text, missing context metadata
- Fix: Enrich claims → W5 filters by audience, sorts by complexity, orders by prerequisites

### ChatMentionedFiles

- `C:\Users\prora\.claude\plans\floofy-drifting-finch.md` (PRIMARY PLAN)
- `specs/03_product_facts_and_evidence.md` (Phase 0)
- `specs/schemas/product_facts.schema.json` (Phase 0)
- `specs/schemas/evidence_map.schema.json` (Phase 0)
- `specs/21_worker_contracts.md` (Phase 0)
- `specs/30_ai_agent_governance.md` (Phase 0)
- `specs/07_code_analysis_and_enrichment.md` (NEW, Phase 0)
- `specs/08_semantic_claim_enrichment.md` (NEW, Phase 0)
- `src/launch/workers/w2_facts_builder/code_analyzer.py` (NEW, Phase 1)
- `src/launch/workers/w2_facts_builder/enrich_workflows.py` (NEW, Phase 2)
- `src/launch/workers/w2_facts_builder/enrich_claims.py` (NEW, Phase 3)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 9 taskcards (TC-1040 through TC-1048) + pilot verification
- 4 concrete gaps with exact code locations
- Clear acceptance criteria (api_surface populated, workflows enriched, LLM enrichment working)
- Evidence commands: pytest, pilot runs, VFV determinism, jq queries

### ResolutionStrategy

**PRIMARY**: `C:\Users\prora\.claude\plans\floofy-drifting-finch.md`
**EXECUTION**: Sequential phases (Phase 0 → 1 → 2 → 3 → 4)
**AGENTS**: Agent D (specs), Agent B (implementation), Agent C (tests), Orchestrator (pilot verification)
**STATUS**: TC-1040 through TC-1049 COMPLETE (2026-02-08). W2 Intelligence fully implemented and verified.

---

## Session 9: TC-1050 W2 Intelligence Refinements (2026-02-08)

### ChatExtractedSteps

From verification results and TC-1050 gap remediation plan:
1. Task 3: Extract stopwords to shared constant (_shared.py NEW, embeddings.py EDIT, map_evidence.py EDIT)
2. Task 4: Add file size cap for memory safety (map_evidence.py EDIT, MAX_FILE_SIZE_MB=5)
3. Task 5: Add progress events for observability (map_evidence.py EDIT, emit_event callback)
4. Task 1: Complete code_analyzer.py TODOs (module extraction from __init__.py, dynamic entrypoint detection)
5. Task 2: Add dedicated unit tests (test_w2_workflow_enrichment.py NEW, 15-20 tests)
6. **FINAL**: Run both pilots E2E for verification (no regression, all features working)

### ChatExtractedGapsAndFixes

**Gap 1: TODOs in code_analyzer.py (Enhancement, not blocking)**
- Lines 303, 307: modules returns [], public_entrypoints hardcoded ["__init__.py"]
- Fix: AST-based extraction from __all__ or imports, detect __main__.py/setup.py entry_points
- Impact: Better API surface understanding

**Gap 2: Missing dedicated unit tests (Nice-to-have)**
- Current: enrich_workflow() and enrich_example() tested indirectly via integration
- Fix: Create test_w2_workflow_enrichment.py with step ordering, complexity, time estimation tests
- Impact: 100% test coverage for W2 enrichment modules

**Gap 3: Stopwords duplication (Code quality)**
- Current: STOPWORDS defined identically in embeddings.py and map_evidence.py
- Fix: Extract to _shared.py, import from both
- Impact: DRY principle, maintainability

**Gap 4: No file size cap (Memory safety)**
- Current: 3.3MB PDFs processed without limit
- Fix: Add MAX_FILE_SIZE_MB check before reading files in _load_and_tokenize_files()
- Impact: Prevent memory issues with very large documents

**Gap 5: No progress events (Observability)**
- Current: No per-document progress in events.ndjson for evidence mapping
- Fix: Add emit_event callback to _load_and_tokenize_files(), emit progress every 10 files
- Impact: Better monitoring and debugging

### ChatMentionedFiles

- C:\Users\prora\.claude\plans\floofy-drifting-finch.md (lines 971-1207, TC-1050 plan)
- src/launch/workers/w2_facts_builder/_shared.py (NEW)
- src/launch/workers/w2_facts_builder/embeddings.py (EDIT - import from _shared)
- src/launch/workers/w2_facts_builder/map_evidence.py (EDIT - import from _shared, file size cap, progress events)
- src/launch/workers/w2_facts_builder/code_analyzer.py (EDIT - TODOs lines 303, 307)
- tests/unit/workers/test_w2_code_analyzer.py (ADD tests for module extraction, entrypoint detection)
- tests/unit/workers/test_w2_workflow_enrichment.py (NEW)

### SubstantialityCheck

**SUBSTANTIAL**: YES
- 5 concrete actionable tasks with implementation details + 1 pilot verification
- 5 minor gaps with specific fixes (line numbers, function names, file paths)
- Clear acceptance criteria: tests pass (2531+), pilots pass, no regression, code quality improved
- Evidence commands: pytest tests/, run_pilot.py for both pilots

### ResolutionStrategy

**PRIMARY**: C:\Users\prora\.claude\plans\floofy-drifting-finch.md (TC-1050, lines 971-1207)
**EXECUTION**: Sequential (Tasks 3→4→5→1→2→6)
- Agent-B handles Tasks 1, 3, 4, 5 (implementation)
- Agent-C handles Task 2 (testing)
- Agent-C handles Task 6 (pilot verification)
**AGENTS**:
- Agent-B-T3 (stopwords extraction)
- Agent-B-T4 (file size cap)
- Agent-B-T5 (progress events)
- Agent-B-T1 (code_analyzer TODOs)
- Agent-C-T2 (unit tests)
- Agent-C-T6 (pilot verification)
**TASKCARDS**: Each agent MUST create taskcard and register in plans/taskcards/INDEX.md
**STATUS**: STARTING — orchestrator spawning agents
