# Task Backlog
**Generated from**: plans/from_chat/20260205_160000_evidence_driven_page_scaling.md
**Generated**: 2026-02-05T16:00:00Z

## Execution Order (strict dependency chain)

```
TC-983 (Agent D, Specs) ──► TC-984 (Agent B, W4) ──► TC-985 (Agent B, W7) ──► TC-986 (Agent C, Tests)
      P0 (first)                  P1                       P2                       P3 (last)
```

**Rule**: Specs/schemas/gates/contracts MUST complete before implementation begins.

---

## Workstream 1: Specs & Schemas (PRIORITY — runs first)

**ID**: TC-983
**Owner**: Agent-D (Docs & Specs)
**Scope**: Update all 9 spec artifacts for evidence-driven page scaling + configurable page requirements
**Impacted Paths**:
- specs/rulesets/ruleset.v1.yaml
- specs/schemas/ruleset.schema.json
- specs/schemas/page_plan.schema.json
- specs/schemas/validation_report.schema.json
- specs/06_page_planning.md
- specs/07_section_templates.md
- specs/08_content_distribution_strategy.md
- specs/09_validation_gates.md
- specs/21_worker_contracts.md

**Acceptance Criteria**:
- [ ] ruleset.v1.yaml has mandatory_pages + optional_page_policies + family_overrides
- [ ] All schemas validate updated configs
- [ ] Gate 14 spec includes GATE14_MANDATORY_PAGE_MISSING (1411)
- [ ] W4 contract documents evidence_volume + effective_quotas outputs
- [ ] No orphan cross-references

**Tests**: Schema validation against updated configs
**Risk**: LOW — spec-only changes, no code execution

---

## Workstream 2: W4 Implementation (runs after Workstream 1)

**ID**: TC-984
**Owner**: Agent-B (Implementation)
**Depends on**: TC-983
**Scope**: Implement evidence-driven page scaling + configurable page requirements in W4 IAPlanner
**Impacted Paths**:
- src/launch/workers/w4_ia_planner/worker.py

**Acceptance Criteria**:
- [ ] 5 new functions implemented
- [ ] execute_ia_planner() uses config-driven mandatory pages
- [ ] evidence_volume + effective_quotas in page_plan output
- [ ] CI-absent alone doesn't force minimal tier

**Tests**: Existing W4 tests must pass
**Risk**: MEDIUM — refactors core planning logic

---

## Workstream 3: W7 Gate 14 Mandatory Page Check (runs after Workstream 2)

**ID**: TC-985
**Owner**: Agent-B (Implementation)
**Depends on**: TC-983, TC-984
**Scope**: Add mandatory page presence validation to Gate 14
**Impacted Paths**:
- src/launch/workers/w7_validator/worker.py

**Acceptance Criteria**:
- [ ] Gate 14 validates mandatory page presence from merged config
- [ ] GATE14_MANDATORY_PAGE_MISSING emitted for absent mandatory pages
- [ ] Profile-based severity applied

**Tests**: Existing Gate 14 tests must pass
**Risk**: LOW — additive change to existing gate

---

## Workstream 4: Tests & Verification (runs after Workstreams 2+3)

**ID**: TC-986
**Owner**: Agent-C (Tests & Verification)
**Depends on**: TC-984, TC-985
**Scope**: Comprehensive test suite + regression verification
**Impacted Paths**:
- tests/unit/workers/test_w4_evidence_scaling.py (new)

**Acceptance Criteria**:
- [ ] All new tests pass
- [ ] Existing test suite green (no regressions)
- [ ] Determinism verified
- [ ] Large repo produces more pages than small repo

**Tests**: Full pytest suite
**Risk**: LOW — testing only

---

# Template Audit & Restructuring (TC-990 through TC-997)
**Generated from**: plans/from_chat/20260205_200000_template_audit_restructuring.md
**Generated**: 2026-02-05

## Execution Order

```
TC-990 (Agent D, Specs) ──► TC-991 + TC-996 (parallel) ──► TC-992 ──► TC-993 + TC-994 (parallel) ──► TC-995 ──► TC-997
      P0                           P1                          P2              P3                        P4          P5
```

---

## WS-5: Specs & Schemas — Template Ground Truth (P0)

**ID**: TC-990
**Owner**: Agent-D
**Depends on**: []
**Scope**: Update specs 06, 07, 21 and page_plan schema for correct template structure
**Impacted Paths**: specs/07_section_templates.md, specs/06_page_planning.md, specs/21_worker_contracts.md, specs/schemas/page_plan.schema.json
**Acceptance**: No converter/format/section_path refs in specs; blog has no __PLATFORM__; page_role derivation documented
**Tests**: Schema validation
**Risk**: LOW

---

## WS-6: Template File Cleanup (P1, parallel)

**ID**: TC-991
**Owner**: Agent-B
**Depends on**: TC-990
**Scope**: Delete ~72 wrong-hierarchy template files
**Impacted Paths**: specs/templates/**
**Acceptance**: No converter/section/format/misplaced blog templates remain
**Risk**: LOW

**ID**: TC-996
**Owner**: Agent-B
**Depends on**: TC-990
**Scope**: Audit validation gates for template path references
**Impacted Paths**: src/launch/workers/w7_validator/gates/**
**Acceptance**: No gates reference old template patterns
**Risk**: LOW

---

## WS-7: Template Creation (P2)

**ID**: TC-992
**Owner**: Agent-B
**Depends on**: TC-990, TC-991
**Scope**: Create ~51 new templates for full family parity
**Impacted Paths**: specs/templates/**
**Acceptance**: All 3 families have identical template tree structure
**Risk**: MEDIUM

---

## WS-8: Code Changes (P3, parallel)

**ID**: TC-993
**Owner**: Agent-B
**Depends on**: TC-990, TC-992
**Scope**: Update W4 enumerate_templates() for new structure + page_role
**Impacted Paths**: src/launch/workers/w4_ia_planner/worker.py
**Acceptance**: page_role assigned to all templates; blog __PLATFORM__ filtered
**Risk**: MEDIUM

**ID**: TC-994
**Owner**: Agent-B
**Depends on**: TC-990, TC-992
**Scope**: Update W5 template loading for feature/howto/reference types
**Impacted Paths**: src/launch/workers/w5_section_writer/worker.py
**Acceptance**: Templates loaded for all page types
**Risk**: MEDIUM

---

## WS-9: Tests & Verification (P4-P5)

**ID**: TC-995
**Owner**: Agent-C
**Depends on**: TC-993, TC-994
**Scope**: Update/add tests for template enumeration and page roles
**Impacted Paths**: tests/unit/workers/test_w4_*.py
**Acceptance**: All tests pass with PYTHONHASHSEED=0
**Risk**: LOW

**ID**: TC-997
**Owner**: Agent-C
**Depends on**: ALL
**Scope**: Pilot verification and evidence bundle
**Impacted Paths**: reports/**
**Acceptance**: Pilot W4 discovers correct templates; family parity verified
**Risk**: LOW

---

# TC-1050 W2 Intelligence Refinements (2026-02-08)
**Generated from**: C:\Users\prora\.claude\plans\floofy-drifting-finch.md (lines 971-1207)
**Generated**: 2026-02-08T01:15:00Z

## Execution Order (sequential for low-risk incremental changes)

```
TC-1050-T3 (Agent-B) ──► TC-1050-T4 (Agent-B) ──► TC-1050-T5 (Agent-B) ──► TC-1050-T1 (Agent-B) ──► TC-1050-T2 (Agent-C) ──► TC-1050-T6 (Agent-C)
    stopwords DRY            file size cap           progress events          code_analyzer TODOs      workflow tests          pilot E2E
```

**Rule**: Low-risk foundational changes first (stopwords, safety, observability), then enhancements (TODOs, tests), then verification.

---

## Task 3: Extract Stopwords to Shared Constant (P0)

**ID**: TC-1050-T3
**Owner**: Agent-B (Implementation)
**Priority**: P0 (Foundational, low risk)
**Scope**: DRY refactor - extract STOPWORDS to _shared.py, import from embeddings.py and map_evidence.py
**Impacted Paths**:
- src/launch/workers/w2_facts_builder/_shared.py (NEW)
- src/launch/workers/w2_facts_builder/embeddings.py (EDIT - line ~38)
- src/launch/workers/w2_facts_builder/map_evidence.py (EDIT - line ~38)

**Acceptance Criteria**:
- [ ] _shared.py created with STOPWORDS frozenset
- [ ] embeddings.py imports from _shared
- [ ] map_evidence.py imports from _shared
- [ ] Both modules work correctly (imports verified)
- [ ] No duplication (single source of truth)
- [ ] Tests pass (2531+)

**Tests**: Verify imports work, existing tests still pass
**Docs**: No spec changes needed (internal refactor)
**Risk**: LOW — DRY refactor, no behavior change

---

## Task 4: Add File Size Cap for Memory Safety (P1)

**ID**: TC-1050-T4
**Owner**: Agent-B (Implementation)
**Priority**: P1 (Safety improvement)
**Scope**: Add MAX_FILE_SIZE_MB check in _load_and_tokenize_files() to skip large files (>5MB default)
**Impacted Paths**:
- src/launch/workers/w2_facts_builder/map_evidence.py (EDIT - _load_and_tokenize_files function)
- tests/unit/workers/test_tc_412_map_evidence.py (ADD test_map_evidence_skips_large_files)

**Acceptance Criteria**:
- [ ] MAX_FILE_SIZE_MB constant added (default: 5)
- [ ] File size check before reading in _load_and_tokenize_files()
- [ ] Warning logged for skipped large files
- [ ] Configurable via W2_MAX_FILE_SIZE_MB env var
- [ ] Test coverage for file size filtering
- [ ] Tests pass (2531+)

**Tests**: test_map_evidence_skips_large_files()
**Docs**: No spec changes (internal safety mechanism)
**Risk**: LOW — additive, graceful skip

---

## Task 5: Add Progress Events for Observability (P2)

**ID**: TC-1050-T5
**Owner**: Agent-B (Implementation)
**Priority**: P2 (Observability improvement)
**Scope**: Add emit_event callback to _load_and_tokenize_files() for per-document progress
**Impacted Paths**:
- src/launch/workers/w2_facts_builder/map_evidence.py (EDIT - _load_and_tokenize_files, find_supporting_evidence_in_docs, find_supporting_evidence_in_examples)
- tests/unit/workers/test_tc_412_map_evidence.py (ADD test_map_evidence_emits_progress_events)

**Acceptance Criteria**:
- [ ] emit_event callback parameter added to _load_and_tokenize_files()
- [ ] Progress emitted every 10 files or on completion
- [ ] Event format: {"event_type": "WORK_PROGRESS", "label": "doc_tokenization", "progress": {"current": N, "total": M}}
- [ ] Integrated into find_supporting_evidence_in_docs/examples
- [ ] Test coverage for progress emission
- [ ] Tests pass (2531+)

**Tests**: test_map_evidence_emits_progress_events()
**Docs**: No spec changes (internal observability)
**Risk**: LOW — additive, optional callback

---

## Task 1: Complete code_analyzer.py TODOs (P3)

**ID**: TC-1050-T1
**Owner**: Agent-B (Implementation)
**Priority**: P3 (Functional enhancement)
**Scope**: Implement _extract_modules_from_init() and _detect_public_entrypoints() to remove TODOs at lines 303, 307
**Impacted Paths**:
- src/launch/workers/w2_facts_builder/code_analyzer.py (EDIT - lines 303, 307)
- tests/unit/workers/test_w2_code_analyzer.py (ADD 3 new tests)

**Acceptance Criteria**:
- [ ] _extract_modules_from_init() implemented (AST __all__ extraction, fallback to imports)
- [ ] _detect_public_entrypoints() implemented (detect __init__.py, __main__.py, setup.py entry_points)
- [ ] TODOs removed from lines 303, 307
- [ ] test_extract_modules_from_init_with_all()
- [ ] test_extract_modules_from_imports()
- [ ] test_detect_public_entrypoints_main_py()
- [ ] Tests pass (2531+)

**Tests**: 3 new tests in test_w2_code_analyzer.py
**Docs**: No spec changes (internal enhancement)
**Risk**: LOW — enhances existing functionality, graceful fallback

---

## Task 2: Add Dedicated Unit Tests for Workflow Enrichment (P4)

**ID**: TC-1050-T2
**Owner**: Agent-C (Tests & Verification)
**Priority**: P4 (Test coverage expansion)
**Scope**: Create test_w2_workflow_enrichment.py with 15-20 tests for enrich_workflow() and enrich_example()
**Impacted Paths**:
- tests/unit/workers/test_w2_workflow_enrichment.py (NEW)

**Acceptance Criteria**:
- [ ] test_enrich_workflow_step_ordering() — install → setup → config → basic → advanced
- [ ] test_enrich_workflow_complexity_simple() — 1-3 steps marked as 'simple'
- [ ] test_enrich_workflow_complexity_complex() — 8+ steps marked as 'complex'
- [ ] test_enrich_workflow_time_estimation() — estimated_time_minutes based on step count
- [ ] test_enrich_example_description_from_docstring() — description extraction
- [ ] test_enrich_example_audience_level_inference() — beginner/intermediate/advanced classification
- [ ] 15-20 total tests covering all code paths
- [ ] 100% coverage for enrich_workflows.py and enrich_examples.py
- [ ] Tests pass (2531+)

**Tests**: 15-20 new tests
**Docs**: No spec changes (test expansion)
**Risk**: LOW — testing only

---

## Task 6: Run Both Pilots E2E for Verification (P5)

**ID**: TC-1050-T6
**Owner**: Agent-C (Verification)
**Priority**: P5 (Final verification)
**Depends on**: ALL (T1-T5)
**Scope**: Run both pilots (3D, Note) end-to-end to verify no regression and all features working
**Impacted Paths**: None (verification only)

**Acceptance Criteria**:
- [ ] pilot-aspose-3d-foss-python: PASS, exit code 0
- [ ] pilot-aspose-note-foss-python: PASS, exit code 0
- [ ] Full test suite: 2531+ passed, 0 failed
- [ ] Performance: Note ~7.3 min, 3D ~6 min (no regression)
- [ ] Quality: 96+ classes, 357+ functions, enriched claims, real positioning
- [ ] Evidence bundle with timing, outputs, validation reports

**Tests**: run_pilot.py for both pilots, full pytest suite
**Docs**: Update CHANGELOG.md with TC-1050 summary
**Risk**: NONE — verification only

---

## Summary

**Total tasks**: 6 (5 implementation + 1 verification)
**Estimated effort**: 5-7 hours
**Priority**: P2 (Enhancement, not blocking)
**Parallelization**: Sequential execution (low-risk incremental changes)
**Agents**: Agent-B (T1, T3, T4, T5), Agent-C (T2, T6)
**Taskcard requirement**: Each agent MUST create taskcard + register in plans/taskcards/INDEX.md
