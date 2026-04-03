# Task Backlog — Session 23 (2026-03-27) — Architectural Revamp: Canonical Evidence Architecture

**Plan**: `C:\Users\prora\.claude\plans\bright-nibbling-elephant.md`
**From_chat**: `plans/from_chat/20260327_120000_from_chat_arch-revamp-canonical-evidence.md`

## Phase 0 — Fix Broken Metrics + Annotate Side-Load (P0, Very Low Risk)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5304 | Fix `evaluate/worker.py:547` claim_coverage always-1.0 bug | P0 | Agent-B | `src/launcher/workers/evaluate/worker.py` | `claim_coverage` < 1.0 when pages have uncovered claims; test proves it | **Done** |
| TC-5305 | Wire verify worker in `graph_builder._resolve_input_model()` | P0 | Agent-B | `src/launcher/orchestrator/graph_builder.py` | `_resolve_input_model("verify")` returns `ScoutBundle` not `None` | **Done** |
| TC-5306 | Annotate generate side-load + `understanding_checkpoint_run_id` in ContentManifest | P0 | Agent-B | `src/launcher/workers/generate/worker.py`, `models/content.py`, `evaluate/worker.py` | Side-load logs WARNING with checkpoint path; ContentManifest carries run_id; stale cross-run load warns in evaluate | **Done** |

## Phase 1 — Platform Config Unification (P0, Low Risk, 2 sessions)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5307 | Create `shared/families_loader.py`; replace 3 platform lookup tables | P0 | Agent-B | `src/launcher/shared/families_loader.py`, `section_prompt.py`, `acquisition.py`, `configs/families.yaml` | All 3 tables removed; 59 new tests pass; 5731 total pass | **Done** |

## Phase 2 — Extraction Quality Observability (P0, Low Risk, 1 session)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5308 | Add extraction_quality check; wire into evaluate as MEDIUM/HIGH finding | P0 | Agent-B | `src/launcher/models/content.py`, `evaluate/checks/extraction_quality.py`, `evaluate/worker.py` | check fires MEDIUM when overall_completeness<0.35; HIGH when classes=0; 9 new tests; 5740 total pass | **Done** |

## Phase 3 — Fix Claim Binding (P1, Medium Risk, 2 sessions)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5309 | Remove `llm_sparse_grounding` bypass in `_entry.py:535-540` | P1 | Agent-B | `src/launcher/workers/understand/extract/_entry.py`, LLM claim extraction prompt | Zero `llm_sparse_grounding` claims in UnderstandingBundle; claim count ≥5 for pilot repos | Pending |

## Phase 4 — C++ Tree-Sitter Extraction (P1, High Risk, 3-4 sessions)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5310 | `_cpp_ast.py` using `shared/ts_analyzer.py`; C++ full AST extraction | P1 | Agent-B | `src/launcher/workers/understand/adapters/_cpp_ast.py`, `_cpp.py` | api_allowlist failures <5/18 (from 13/18); `[identifier omitted]` = 0; class_count ≥10 | Pending |

## Phase 5 — Deterministic Routing (P1, Low Risk, 1 session)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5311 | Replace LLM advisor with deterministic `route_after_evaluate()`; add `heal_understand` path | P1 | Agent-B | `src/launcher/orchestrator/pipeline_advisor.py`, `configs/pipeline.yaml`, `graph_builder.py`, `models/evaluation.py` | All routing branches tested without LLM; C++ failures route to `heal_understand` | **Draft — next session** |

---

# Task Backlog — Session 22 (2026-03-27) — Production-Grade A+B 100% Redesign

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-5301 | Remove skeleton directive paragraph from `fallback.py` | P0 | Agent-B | `src/launcher/workers/generate/fallback.py` | No fallback section ever emits `"{display_name} -- "` pattern; 4 new tests pass | Pending |
| TC-5303 | Normalize internal links in generate worker post-processor + prompt instruction | P0 | Agent-B | `src/launcher/workers/generate/worker.py`, `section_prompt.py` | link_validity HIGH count drops to 0 on re-eval; 4 new tests pass | Pending |
| TC-5300 | Diagnose and fix intake worker silent failure (10/11 pilots blocked) | P0 | Agent-B | `src/launcher/workers/intake/worker.py` | All 11 pilots produce `intake_checkpoint.json`; failed runs write structured error event | Pending |
| TC-5302 | Fix output token budget + handle `finish_reason="length"` + JSON healing | P0 | Agent-B | `src/launcher/workers/generate/worker.py`, `llm_provider.py` | No `finish_reason: length` truncation in 3D DotNet; fallback rate < 20% | Pending |
| TC-HEAL-003 | Class-grouped relevance-ranked api_surface_block in `section_prompt.py` | P1 | Agent-B | `src/launcher/workers/generate/section_prompt.py` | Input prompt token count ≤3000 for 3D DotNet sections; tests pass | Pending |

---

# Task Backlog — .NET Pilot Publishability

**Created**: 2026-03-25
**Plan**: snuggly-painting-widget.md

## Workstream 1 — Core generate fixes (P0)

| ID | Scope | Owner | Impacted Paths | Acceptance | Risk |
|----|-------|-------|----------------|------------|------|
| TC-NET-001 | `_identifier_repair.py` + `worker.py` | Agent B | `src/launcher/workers/generate/` | 0 `[identifier omitted]` in regenerated .NET pages | LOW — additive param to existing function |
| TC-NET-002 | `section_validator.py` | Agent B | `src/launcher/workers/generate/` | `using Aspose.Slides.Foss;` → `using Aspose.Slides;` | MEDIUM — new code branch for csharp fences |

## Workstream 2 — Evaluate + forbidden pattern fixes (P1)

| ID | Scope | Owner | Impacted Paths | Acceptance | Risk |
|----|-------|-------|----------------|------------|------|
| TC-NET-003 | `code_platform.py` | Agent B | `src/launcher/workers/evaluate/checks/` | HIGH finding for Python imports in csharp blocks | LOW — additive check |
| TC-NET-005 | `forbidden_patterns.py` | Agent B | `src/launcher/shared/` | Bare CLM IDs + template stubs flagged as CRITICAL/HIGH | LOW — additive patterns |

## Workstream 3 — SEO + api_allowlist (P1/P2)

| ID | Scope | Owner | Impacted Paths | Acceptance | Risk |
|----|-------|-------|----------------|------------|------|
| TC-NET-004 | `seo_metadata.py` | Agent B | `src/launcher/workers/generate/` | No Python keywords in .NET frontmatter | LOW — post-filter function |
| TC-NET-006 | `api_allowlist.py` | Agent B | `src/launcher/workers/evaluate/checks/` | No false HIGH for .NET stdlib types | LOW — additive exempt set |

## Status

| ID | Status | Notes |
|----|--------|-------|
| TC-NET-001 | Pending | |
| TC-NET-002 | Pending | |
| TC-NET-003 | Pending | |
| TC-NET-004 | Pending | |
| TC-NET-005 | Pending | |
| TC-NET-006 | Pending | |

---

# Task Backlog — Java & C++ Gap Closure (Session 19, 2026-03-24)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-CPP-410 | Add C++ to install recipe dispatch | P0 | Agent-B | `_deterministic.py` | `extract_install_recipe(platform="cpp")` returns CMake cmd | **Done** |
| TC-CPP-411 | Platform-aware verification fence | P0 | Agent-B | `section_prompt.py`, `worker.py` | Fence uses correct lang tag per platform | **Done** |
| TC-CPP-412 | Fix api_allowlist `::` splitting | P0 | Agent-B | `api_allowlist.py` | `Aspose::Slides::Presentation` correctly split | **Done** |
| TC-CPP-413 | Canonical import enforcement for C++ | P1 | Agent-B | `section_prompt.py`, `section_writer.txt` | C++ prompt includes `#include`/`using namespace` rules | **Done** |
| TC-JAVA-411 | Overloaded method docstring matching | P2 | Agent-B | `_java.py` | Correct Javadoc for overloaded methods | **Done** |
| TC-CPP-416 | vcpkg/conan detection | P2 | Agent-B | `scout.py`, `_deterministic.py` | Detects vcpkg.json/conanfile | **Done** |
| TC-CPP-414 | C++ slides pilot re-run | P1 | Agent-C | pilot execution | A+B >= 30%, no pip install | Ready (next session) |
| TC-JAVA-410 | Java full pipeline run | P1 | Agent-C | pilot execution | All 5 phase JSONs, A+B >= 40% | Ready (next session) |
| TC-CPP-415 | Tree-sitter hard dep / fallback | P2 | Agent-B | `ts_analyzer.py` | Clear error or improved regex | Pending |
| TC-JAVA-412 | Gradle multi-module + recipe | P3 | Agent-B | `_java.py`, `_deterministic.py` | Optional | Optional |

---

# Task Backlog — FPRPS Healing Sprint (Session 18, 2026-03-24)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| FPRPS-01 | Fix PascalCase regex false positives | P0 | Agent-B1 | `extract/_linking.py`, `test_confidence_bucketing.py` | CSV/JSON NOT matched, Workbook IS matched, 2 new tests pass | **Done** |
| FPRPS-03 | Add _SOURCE_PRIORITY dedup regression test | P1 | Agent-B1 | `test_confidence_bucketing.py` | 2 dedup tests pass | **Done** |
| FPRPS-05 | Add DEBUG logging for promoted claims | P1 | Agent-B1 | `extract/_linking.py` | DEBUG log per promoted claim | **Done** |
| FPRPS-04 | Remove unused `call` import | P2 | Agent-B2 | `test_clone.py` | Import removed, tests pass | **Done** |
| FPRPS-02 | TC-UND-209 spec/impl alignment | P2 | Agent-B2 | TC-UND-209 taskcard, `worker.py` | Taskcard updated, comment added | **Done** |
| FPRPS-06 | Evaluate promotion wiring architecture | P3 | Agent-B2 | `_entry.py`, `worker.py` | Decision documented, inline import hoisted | **Done** |
| VERIFY | Full test suite — 0 regressions | Final | Orchestrator | All | 275 pass, 2 pre-existing fail | **Done** |

---

# Task Backlog — Pipeline Audit Hardening (Session 16)

| ID | Scope | Priority | Owner | Impacted Paths | Status |
|----|-------|----------|-------|---------------|--------|
| PA-H01 | Patch A: Fix _compute_claim_coverage denominator | P0 | Agent-B | `evaluate/worker.py` | **Done** |
| PA-H02 | Patch B: Clean dead _PROMOTED_LLM_CHECKS entry | P0 | Agent-B | `evaluate/grader.py` | **Done** |
| PA-H03 | Patch C: Import confidence threshold | P0 | Agent-B | `generate/worker.py` | **Done** |
| PA-H04 | Patch D: Add orphan claim warning | P1 | Agent-B | `generate/worker.py` | **Done** |
| PA-H05 | Patch E: Strengthen type hint | P2 | Agent-B | `evaluate/worker.py` | **Done** |
| PA-T01 | Write TC-PA-01 tests (4 tests) | P0 | Agent-C | `tests/unit/workers/` | **Done** |
| PA-T02 | Write TC-PA-02 tests (grader interaction) | P1 | Agent-C | `tests/unit/workers/` | **Done** |
| PA-T03 | Write TC-PA-03 tests (evidence + filtering) | P1 | Agent-C | `tests/unit/workers/` | **Done** |
| PA-T04 | Write TC-PA-04 tests (uncap verification) | P0 | Agent-C | `tests/unit/workers/` | **Done** |
| PA-D01 | Update 5 taskcards to Done | P1 | Agent-D | `plans/taskcards/TC-PA-*.md` | **Done** |
| PA-V01 | Full test suite verification | Final | Orchestrator | All | **Done** (5923 pass, 5 pre-existing fail) |

---

# Task Backlog — Email Pilot Healing (prior session)

| ID | Scope | Priority | Owner | Impacted Paths | Status |
|----|-------|----------|-------|---------------|--------|
| EH-03 | Add stdlib types to identifier repair exempt | P0 | Agent-B | `_identifier_repair.py`, `section_validator.py` | Not Started |
| EH-02 | Fix import pattern in verification_code + reminder | P0 | Agent-B | `_deterministic.py`, `section_prompt.py` | Not Started |
| EH-01 | Fix snippet extraction cascade for example files | P0 | Agent-B | `_snippets.py`, `_linking.py` | Not Started |
| EH-05 | Propagate python_requires to generate context | P1 | Agent-B | `understanding.py`, `worker.py`, `section_prompt.py` | Not Started |
| EH-06 | Fix runtime_import_tpl in families.yaml | P1 | Agent-B | `families.yaml`, pilot configs | Not Started |
| EH-04 | Format detection domain fallback | P1 | Agent-B | `_entry.py`, `_deterministic.py` | Not Started |
| VERIFY | E2E email pilot re-run | Final | Agent-C | All | Not Started |

---

## 2026-03-25 Backlog — Unified Quality Fix

| ID | Scope | Owner-Agent | Files | Acceptance | Status |
|----|-------|-------------|-------|------------|--------|
| GOV-1 | Commit 152 working tree files | Agent-A | all modified tracked files | git status clean | In-Progress |
| EVL-1 | Syntax gate enforcement in generate worker | Agent-B/D | worker.py:1266-1273 | invalid code stripped after retries | Pending |
| EVL-2 | String-aware class instantiation scan | Agent-B | api_verification.py | formula names not flagged | Pending |
| EVL-3 | Enum member recognition in evaluate | Agent-B | api_verification.py | enum members not flagged | Pending |
| EVL-4 | Generic Test class filter | Agent-B | api_verification.py | TestFoo() not flagged | Pending |
| GEN-1 | Model routing: generate:standard→reasoning | Agent-C | configs/pilots/*.yaml | pilot runs use recommended model | Pending |
| GEN-2 | Anti-echo guard in section_writer.txt | Agent-C | section_writer.txt | no content_hint echo in output | Pending |
| GEN-3 | Identifier repair softening | Agent-C | _identifier_repair.py | case-insensitive match, property-path | Pending |
| GEN-4 | Strip-and-replace for code blocks | Agent-D | worker.py, section_validator.py | code block count stable | Pending |
| GEN-5 | Cross-section context injection | Agent-E | worker.py, section_prompt.py | no 4-8x repetition in installation.md | Pending |
| GEN-6 | Deterministic See Also | Agent-D | worker.py, section_prompt.py | all See Also links in manifest | Pending |
| UND-1 | Snippet extraction from test files | Agent-F | _snippets.py, _entry.py | snippets>=3 per page | Pending |
| ARC-1 | Code synthesis (stub→real) | Agent-F | _code_synthesis.py | synthesized snippets pass ast.parse | Pending |
| GOV-2 | agents.md __pycache__ guidance | Agent-A | agents.md | cleanup note present | Pending |
| GOV-3 | scripts/check_tc_evidence.py | Agent-A | scripts/ | script runs, finds gaps | Pending |

---

## Session 17 Backlog — 2026-03-22 (Understand Runs + Extraction Regression Fixes)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| UEX-01 (TC-5174) | Fix 3d/java 94% claim regression | P0 | Agent-B | `extract/_validation.py`, `extract/_entry.py` | 3d/java claims>=100, tier=A, completeness>=0.95 | **Investigating** |
| UEX-02 (TC-5175) | Fix email/python API extraction failure | P0 | Agent-B | `adapters/_python.py`, `extract/_api_surface.py` | email methods>=50, tier>=B, completeness>=0.70 | **Investigating** |
| UEX-03 (TC-5176) | Auto-recover corrupt clone cache | P1 | Agent-B | `workers/intake/acquisition.py` | No clone failure when .git-only dir exists | Pending |
| TC-5172 | Implement intake sync command | P1 | Agent-B | `cli/intake.py`, `phase1/onboarding.py` | `intake sync` generates missing configs from scan_state.json | Pending |
| TC-5173 | intake onboard → scan_state.json persistence | P2 | Agent-B | `cli/intake.py`, `phase1/onboarding.py` | onboard run updates scan_state.json | Pending |
| TC-5177 | --force flag for intake generate | P2 | Agent-B | `cli/intake.py` | `intake generate --force` bypasses needs_review | Pending |
| TC-5178 | Fix garbled product_name in config_generator | P2 | Agent-B | `intake/config_generator.py` | product_name = "Aspose.X FOSS for Platform" | Pending |

---

## Session 21 Backlog — 2026-03-26 (Healing Investigation: Pilot Quality Gap Analysis)

| ID | Scope | Priority | Owner | Impacted Paths | Acceptance | Status |
|----|-------|----------|-------|----------------|------------|--------|
| TC-HEAL-001 | grader.py skeleton HIGH → Grade D | P0 | Agent-B | `src/launcher/workers/evaluate/grader.py` | Skeleton-directive HIGH yields Grade D; 2 non-skeleton HIGHs still Grade C | **Done** |
| TC-HEAL-005 | seo_metadata.py keyword relevance filter | P1 | Agent-B | `src/launcher/workers/generate/seo_metadata.py` | "is .net 3.5 safe", "shapr 3d cost", "3d symptoms" rejected; "dotnet 3d library" accepted | **Done** |
| TC-HEAL-006 | section_prompt.py _foss import NEVER rule | P1 | Agent-B | `src/launcher/workers/generate/section_prompt.py` | aspose_email_foss rule explicitly names `import aspose.email` as NEVER + ImportError reason | **Done** |
| TC-HEAL-002 | Generate phase anti-echo / fallback guard | P0 | Agent-B | `src/launcher/workers/generate/worker.py` | Skeleton fallback produces CRITICAL finding, never silently promotes | Pending |
| TC-HEAL-003 | Understand api_surface_block class context | P1 | Agent-B | `src/launcher/workers/understand/`, `src/launcher/workers/generate/section_prompt.py` | C++/Java prompts include class membership in api_surface_block | Pending |
| TC-HEAL-004 | Re-evaluate old C++/Java content with [identifier omitted] | P0 | Agent-B | `deploy/` (slides/cpp, 3d/java) | All pages with [identifier omitted] re-graded F and excluded from deploy | Pending |
| TC-5179 | Fix evaluate/checks import errors | P2 | Agent-C | `tests/unit/workers/evaluate/checks/` | pytest tests/unit/ -x passes | Pending |
