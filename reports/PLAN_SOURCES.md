# PLAN_SOURCES — Orchestrator Session 20 (2026-03-24) — Evaluation Check Registry Gap Closure

## PrimaryPlanSource (Session 20)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\idempotent-crunching-sutton.md` |
| Type | Chat-derived production quality review (185 pages audited against golden) |
| Why selected | Deep structural analysis: 17/41 evaluation checks exist on disk but are NOT registered in `__init__.py`. This single integration gap explains the majority of quality failures (113/185 broken pages). `forbidden_content` check (catches `[identifier omitted]` as CRITICAL) exists but is disconnected. |
| Key sections | Part 1 (structural finding), Part 4 (what must change), Part 8 (implementation plan) |
| SelectedAsPrimary | true (session 20) |

### ChatExtractedSteps (Session 20)

1. Wire 17 disconnected evaluation checks into `checks/__init__.py` and `_run_deterministic_checks()` in `worker.py`
2. Fix identifier repair sentinel in `_identifier_repair.py` (replace `[identifier omitted]` insertion with strip/retry)
3. Create 3 missing checks: `code_platform.py`, `unsourced_metrics.py`, `content_viability.py`
4. Add deploy purge command to `phase_promoter.py` and `deploy.py` CLI
5. Regenerate and revalidate

### ChatExtractedGapsAndFixes (Session 20)

| Gap | Root Cause | Fix | Confirmed |
|-----|-----------|-----|-----------|
| 17 checks not registered | Import missing from `__init__.py` | Wire into registry + worker | YES (`__init__.py` has 24, disk has 41) |
| `[identifier omitted]` leaks | `_identifier_repair.py:384` inserts sentinel, `forbidden_content` not wired | Fix sentinel + wire check | YES (both files inspected) |
| No platform-code check | `code_platform.py` doesn't exist | Create check | YES (SR-DOW-00 confirms) |
| No fabricated-metric check | `unsourced_metrics.py` doesn't exist | Create check | YES (SR-DOW-00 confirms) |
| No content-viability check | `content_viability.py` doesn't exist | Create check | YES (SR-DOW-00 confirms) |
| Old broken pages persist | No purge mechanism | Add CLI command | YES (promoter is append-only) |

### SubstantialityCheck (Session 20)
SUBSTANTIAL — 5 phases, 6 gaps with confirmed fixes, 5372 test baseline

### ResolutionStrategy (Session 20)
Phase 1 (P0): Wire checks in 2 waves (critical then quality). Phase 2 (P0): Fix sentinel. Phase 3 (P1): Create missing checks. Phase 4 (P2): Deploy purge. Phase 5: Regenerate.

## SecondarySources (Session 20)
- `plans/healing/SR-DOW-00-consolidation-rebaseline-gap-index.md` — Confirms 3 missing checks, 5372/5372 tests pass

## MissingCandidates (Session 20)
None.

---

# PLAN_SOURCES — Orchestrator Session 19 (2026-03-24) — Java & C++ Gap Closure

## PrimaryPlanSource (Session 19)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\async-sleeping-hopcroft.md` |
| Type | Chat-derived plan (approved in plan mode) |
| Why selected | Comprehensive gap assessment for Java+C++ based on code inspection of all 4 adapters, shared extraction infrastructure, evaluate results, and phase_store contents. All bugs verified against actual code with line numbers. |
| Key sections | Gap Assessment (6 MUST FIX, 4 SHOULD FIX, 2 OPTIONAL), Phased Execution Plan (4 phases, 10 taskcards), Validation Plan, Rollout Order |
| SelectedAsPrimary | true (session 19) |

### ChatExtractedSteps (Session 19)

1. TC-CPP-410: Add C++ to install recipe dispatch (`_deterministic.py:944`)
2. TC-CPP-411: Platform-aware verification fence (`section_prompt.py:1181`)
3. TC-CPP-412: Fix api_allowlist `::` splitting (`api_allowlist.py:134`)
4. TC-CPP-413: Canonical import enforcement for C++ in generation prompt
5. TC-CPP-414: Re-run C++ slides pilot end-to-end
6. TC-JAVA-410: Run full Java pipeline (3d-java or slides-java)
7. TC-JAVA-411: Overloaded method docstring matching
8. TC-CPP-415: Tree-sitter hard dep or improved regex fallback
9. TC-CPP-416: vcpkg/conan detection for install command
10. TC-JAVA-412: Optional Gradle multi-module + install recipe

### ChatExtractedGapsAndFixes (Session 19)

| Gap ID | Root Cause | Fix | Confirmed |
|--------|-----------|-----|-----------|
| GAP-C1 | `"cpp"` missing from `_NON_PYTHON_PLATFORMS` | Add to frozenset + `_CACHED_CMD_TPL` + `_CACHED_LABEL` | YES (line 944) |
| GAP-C2 | Hardcoded `` ```python `` fence | Use `_PLATFORM_DEFAULT_LANG` | YES (line 1181) |
| GAP-C3 | LLM hallucinates `Aspose::Slides::Foss` | Prompt enforcement | YES (evaluate.json) |
| GAP-C4 | `ident.split(".")` ignores `::` | Split on both `.` and `::` | YES (line 134) |
| GAP-J1 | Java pipeline never completed past understand | Run full pipeline | YES (phase_store) |
| GAP-J2 | Name-only method matching for Javadoc | Parameter-count matching | YES (lines 268-282) |

### ChatMentionedFiles (Session 19)

- `src/launcher/workers/understand/extract/_deterministic.py` (lines 944, 951, 963, 1043)
- `src/launcher/workers/generate/section_prompt.py` (line 1181)
- `src/launcher/workers/evaluate/checks/api_allowlist.py` (line 134)
- `src/launcher/workers/generate/worker.py` (line 2045)
- `src/launcher/workers/understand/adapters/_java.py` (lines 268-282)
- `phase_store/slides/cpp/evaluate.json`
- `phase_store/3d/java/` (only scout.json + understand.json)

### SubstantialityCheck (Session 19)

SUBSTANTIAL: 10 steps, 6 gaps with confirmed fixes, acceptance criteria per taskcard.

### ResolutionStrategy (Session 19)

Phase A: 4 bug fixes (TC-CPP-410..413) — parallelizable
Phase B: 2 pilot runs (TC-CPP-414, TC-JAVA-410) — blocked on Phase A
Phase C: 3 quality hardening (TC-JAVA-411, TC-CPP-415/416) — blocked on Phase B
Phase D: 1 optional (TC-JAVA-412)

## SecondarySources (Session 19)
- `agents.md` — operational guide
- `CLAUDE.md` — taskcard-first workflow
- `.claude_code_rules` — governance AG-001..AG-020

## MissingCandidates (Session 19)
None.

---

# PLAN_SOURCES — Orchestrator Session 16 (2026-03-20) — Pipeline Audit Hardening (Self-Review Remediation)

## PrimaryPlanSource (Session 16)

| Field | Value |
|-------|-------|
| Path | `reports/from_chat/20260320_pipeline_audit_hardening.md` |
| Type | chat-derived (self-review remediation) |
| Why selected | Self-review of TC-PA-01..05 identified 5 code patches, 17+ missing tests, and taskcard closure gaps. All items concrete, scoped within existing taskcards. |
| Key sections | 3 workstreams, acceptance criteria, evidence commands |
| SelectedAsPrimary | true (session 16) |

### ChatExtractedSteps (Session 16)

1. Patch A: Fix `_compute_claim_coverage` denominator (remove buggy `or` fallback)
2. Patch B: Remove dead `factual_accuracy` from `_PROMOTED_LLM_CHECKS`
3. Patch C: Import `_CLAIM_CONFIDENCE_THRESHOLD` instead of hardcoding 0.5
4. Patch D: Add orphan claim ID warning log
5. Patch E: Strengthen type hint `"list"` → `"list[Any]"`
6. Write 13+ new tests for TC-PA-01..04 new behavior
7. Update 5 taskcards to Done status

### ChatExtractedGapsAndFixes (Session 16)

| Gap | Root Cause | Fix |
|-----|-----------|-----|
| Buggy denominator fallback | `or len(...)` treats 0 as falsy | Remove fallback; 0-case handled separately |
| Dead promotion code | TC-PA-04 removed from `_LLM_CHECK_NAMES` but not `_PROMOTED_LLM_CHECKS` | Clean up dead entry |
| Hardcoded threshold | 0.5 duplicated from section_prompt constant | Import shared constant |
| Silent orphan claims | Claim IDs not in `claims_by_id` produce silent mismatch | Add WARNING log |
| Zero new tests | Plan specified 17+ tests; only 1 existing test updated | Write all specified tests |

### ChatMentionedFiles (Session 16)

- `src/launcher/workers/evaluate/worker.py` (Patches A, E)
- `src/launcher/workers/evaluate/grader.py` (Patch B)
- `src/launcher/workers/generate/worker.py` (Patches C, D)
- `tests/unit/workers/evaluate/checks/test_claim_coverage.py`
- `tests/unit/workers/test_evaluate.py`
- `tests/unit/workers/generate/test_section_prompt.py`
- `tests/unit/workers/generate/test_section_prompt_evidence.py`

### SubstantialityCheck (Session 16)

SUBSTANTIAL: 7 steps, 5 gaps with fixes, 5 evidence commands.

### ResolutionStrategy (Session 16)

3 parallel workstreams: B (patches), C (tests), D (taskcard closure).
All within existing TC-PA-01..05 scope. No new taskcards needed.

## SecondarySources (Session 16)
- `C:\Users\prora\.claude\plans\refactored-soaring-sonnet.md` (master plan for TC-PA-01..05)
- `plans/taskcards/TC-PA-01..05*.md` (taskcard definitions)

## MissingCandidates (Session 16)
None — all sources resolved.

---

# PLAN_SOURCES — Orchestrator Session 15 (2026-03-18) — Production Fix: Linking, Claims, Determinism

## PrimaryPlanSource (Session 15)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\merry-fluttering-perlis.md` |
| Type | plan-mode artifact (approved) |
| Why selected | Deep investigation of Part 7 "not fixable without deeper changes" problems. Traced actual runtime execution paths for snippet-claim linking, claim authenticity, and LLM determinism. Identified structural weakness: pipeline uses lexical surface proxies at boundaries where structural data exists but isn't wired in. |
| Key sections | 4 phases, 10 files, honest limits section |
| SelectedAsPrimary | true (session 15) |

### ChatExtractedSteps (Session 15)

1. Phase 1 (TC-5133): Cache default-on — flip `FOSS_LAUNCHER_LLM_CACHE` default to `"1"`, add bust mode, enable fallback caching
2. Phase 4 (TC-5134): Sort stability — add tiebreakers to plan.py, section_prompt.py sorts; add content fingerprinting to generate worker
3. Phase 2 (TC-5135): Structural linking — three-tier linker (API identity → TF-IDF → word-overlap fallback), move linking to bulk post-extraction step
4. Phase 3 (TC-5136): Claim depth — add TF-IDF Pass 2 to claim_coverage.py, extract context windows around keyword matches

### ChatExtractedGapsAndFixes (Session 15)

| Gap | Root Cause | Fix |
|-----|-----------|-----|
| Cross-run divergence | LLM cache disabled by default | Default-on + bust mode (TC-5133) |
| Sort instability | Missing tiebreakers in plan.py, section_prompt.py | Deterministic total-order keys (TC-5134) |
| False snippet-claim links | Word overlap ignores API identity, timing problem | Three-tier structural linker (TC-5135) |
| Hollow claim coverage | 3-of-5 keyword-only check | TF-IDF depth verification (TC-5136) |

### ChatMentionedFiles (Session 15)

- `src/launcher/clients/llm_cache.py` (TC-5133)
- `src/launcher/clients/llm_provider.py` (TC-5133)
- `src/launcher/workers/planner/plan.py` (TC-5134)
- `src/launcher/workers/generate/section_prompt.py` (TC-5134)
- `src/launcher/workers/generate/worker.py` (TC-5134)
- `src/launcher/workers/understand/extract/_linking.py` (TC-5135)
- `src/launcher/workers/understand/extract/_snippets.py` (TC-5135)
- `src/launcher/workers/understand/extract/_entry.py` (TC-5135)
- `src/launcher/workers/evaluate/checks/claim_coverage.py` (TC-5136)
- `src/launcher/shared/embeddings.py` (TC-5135, TC-5136)

### SubstantialityCheck (Session 15)

SUBSTANTIAL: 4 phases, 10+ steps, 4 gaps with concrete fixes, acceptance criteria per phase.

### ResolutionStrategy (Session 15)

Execute via 4 taskcards (TC-5133..TC-5136). Phases 1+4 first (low risk, independent).
Phase 2 (core rewrite) after. Phase 3 last (depends on correct linking).

---

# PLAN_SOURCES — Orchestrator Session 14 (2026-03-16) — Post-Execution State Audit

## PrimaryPlanSource (Session 14)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\keen-yawning-pretzel.md` |
| Type | plan-mode artifact (post-execution audit) |
| Why selected | Honest audit of enchanted-noodling-lemur.md and optimized-chasing-music.md execution. Verified ground truth (A+B=23% from eval report 260312), identified unverified claims (35.2%), two unaddressed root causes (Python syntax errors, return type extraction), three code-complete but unverified fixes (TC-HT-008/009/010). |
| Key sections | Current Ground Truth, Executed Plan Audit, Divergence from Master Plan, Reevaluated Master Plan (Phases 0-3), Exact Next Steps |
| SelectedAsPrimary | true (session 14) |

### ChatExtractedSteps (Session 14)

1. Phase 0: Run E2E baseline on cells/python — establish verified current state
2. Close TC-HT-008 (prose floor): verify CRITICAL=0 in new run
3. Close TC-HT-009 (scaffold strip): verify template_echo CRITICAL ≤1/N
4. Close TC-HT-010 (keyword gate): verify keyword stuffing HIGH ≤2/N
5. TC-NEW-001: Add ast.parse() Python syntax check to section_validator.py
6. TC-NEW-002: Audit _api_surface.py for Python return type extraction
7. TC-NEW-003: Create 3-4 authentic golden exemplar sections from best deployed pages
8. E2E verification run — measure against GO criteria

### ChatExtractedGapsAndFixes (Session 14)

1. 35.2% A+B claim unverified — no evaluation_report.json backs it → need fresh E2E run
2. Option B (platform-native golden files) was NOT executed — 3 template files got extra headings, not real Python code patterns
3. Python syntax errors in generated code → add ast.parse() gate in section_validator
4. Reference page return types all → None → fix _api_surface.py Python type extraction
5. TC-HT-008/009/010 taskcards never closed despite code being present

### ChatMentionedFiles (Session 14)

- C:\Users\prora\.claude\plans\keen-yawning-pretzel.md (master audit plan)
- C:\Users\prora\.claude\plans\enchanted-noodling-lemur.md (executed: corpus generalization)
- C:\Users\prora\.claude\plans\optimized-chasing-music.md (executed: post-generalization)
- src/launcher/workers/generate/section_validator.py (TC-NEW-001 target)
- src/launcher/workers/understand/extract/_api_surface.py (TC-NEW-002 target)
- src/launcher/workers/generate/worker.py (TC-HT-008 code confirmed)
- src/launcher/workers/evaluate/checks/artifacts.py (TC-HT-009 code confirmed)
- src/launcher/shared/golden_loader.py (heading matcher, _VARIANT_RE fixed)
- src/launcher/workers/generate/section_prompt.py (_RUBRIC_SUPPLEMENTS confirmed)
- runs/260312_221338_cells_python_9afc/evaluation_report.json (latest verified result)

### SubstantialityCheck (Session 14)

SUBSTANTIAL: 8 steps, 5 gaps with fixes, 4 GO criteria thresholds as acceptance.

### ResolutionStrategy (Session 14)

Primary plan is the post-execution audit. Phases 0-3 mapped. Phase 0 requires E2E run (blocked on litellm_key).
TC-NEW-001 and TC-NEW-002 are implementable immediately. TC-HT-008/009/010 closure requires E2E evidence.

## PrimaryPlanSource
`C:\Users\prora\.claude\plans\keen-yawning-pretzel.md`

## SecondarySources
- `C:\Users\prora\.claude\plans\enchanted-noodling-lemur.md` (executed, audited)
- `C:\Users\prora\.claude\plans\optimized-chasing-music.md` (executed, audited)
- `C:\Users\prora\.claude\plans\dazzling-puzzling-kahn.md` (original golden corpus plan)
- `runs/260312_221338_cells_python_9afc/evaluation_report.json` (ground truth)

## MissingCandidates
None — all sources resolved.

---

# PLAN_SOURCES — Orchestrator Session 13 (2026-03-15) — Skill System + AGENTS.md

## PrimaryPlanSource (Session 13)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\bubbly-cooking-moonbeam.md` |
| Type | plan-mode artifact (2-pass deep analysis) |
| Why selected | Root-cause analysis from actual source code (worker.py, section_prompt.py, section_validator.py, pilot_quality_report.md). Identifies specific failure (LLM training priors override prompt guards), specific fix (snippet-injection + prose-only LLM call), and complete persistence architecture (knowledge/ projection from phase_store). |
| Key sections | Problem A (quality), Problem B (persistence), Root Cause, 2-phase generation fix, 27 skills S-01..S-26, AGENTS.md template, 9-phase impl plan, 12 verification criteria |
| SelectedAsPrimary | true (session 13) |

### ChatExtractedSteps (Session 13)

1. Phase 1 (CRITICAL): Modify generate/worker.py — snippet-selection pre-step + prose-only LLM call + deterministic assembly
2. Phase 1: Modify section_prompt.py — prose-only prompt template (no code block generation)
3. Phase 1: Modify section_validator.py — reject LLM code blocks entirely; narrow identifier scan to backtick-wrapped only
4. Phase 2: Foundation schemas (`configs/knowledge_model.schema.json`, `configs/allowed_paths.yaml`), S-01 path-guard, `AGENTS.md` in aspose.org
5. Phase 3: S-10 knowledge-project (understand.json → knowledge/ tree); run for 5 products
6. Phase 4: S-16 rubric-extract, S-17 rubric-align, `knowledge/rubrics/`
7. Phase 5: S-18 page-plan, S-19 page-draft wrapper, S-22 faq-generate, S-23 ground-check, S-24 citation-attach
8. Phase 6: Maintenance skills S-12..S-14, S-20, S-21, S-25, S-26
9. Phase 7: S-15 sync-vector
10. Phase 9: Integration verification — pilot on cells/python

### ChatExtractedGapsAndFixes (Session 13)

1. LLM training priors > prompt guards → never generate code; inject snippets deterministically
2. HG-16 false positives from broad regex repair → reject LLM code blocks; narrow scan to backtick-wrapped only
3. understand.json blobs not inspectable → S-10 JSON→Markdown projection
4. No diff/stale detection → S-12 (git diff vs repo_sha), S-13 (claim fingerprint scan)
5. Golden corpus fact leakage risk → S-16 post-scan strips product-specific tokens

### SubstantialityCheck (Session 13)

SUBSTANTIAL: 10 phases, 27 skills, 9-phase implementation plan, 12 verification criteria.

---

# PLAN_SOURCES — Orchestrator Session 12 (2026-03-15)

## PrimaryPlanSource

Plan-mode artifact: `C:\Users\prora\.claude\plans\luminous-floating-token.md`
Title: Master Plan — .NET FOSS Pipeline: End-to-End Fix and Quality Baseline
Chat-derived materialization: Plan merged from two prior plan files
  (luminous-floating-token Scout/Understand analysis + federated-dancing-peacock quality audit)

## SubstantialityCheck

SUBSTANTIAL: 6 phases, 14 implementation steps, 5 taskcards (TC-4306..TC-4310).
Root causes fully code-traced (RC-S1, RC-S2, RC-U1..U5, RC-G1..G5, RC-P1).
All acceptance criteria verified against actual cloned repo artifacts.

## ChatExtractedSteps

Phase 1 — Unblock API Extraction:
1. Fix multi-project .csproj selection (scout.py + _dotnet.py)
2. Wire adapter.extract_class_details() into _api_surface.py main loop
3. Add .NET to build_systems detection (scout.py)
4. Capture all .NET namespaces in import_allowlist (_dotnet.py)
5. Propagate api_extraction_status to understand bundle

Phase 2 — Fix Generation Failures:
6. Identifier repair guard when public_classes=[] (generate/worker.py)
7. Route 0-claim pages to render_minimal_stub() (generate/worker.py)
8. Route thin-evidence FAQ to deterministic generation (generate/worker.py)
9. Fix class_briefs serialization in prompt (section_prompt.py)
10. Add keyword density constraint to generation prompt (section_prompt.py)

Phase 4 — Planner Evidence Gating:
11. Add evidence_minimum to ruleset schema
12. WIP claim detection for mandatory pages (planner/plan.py)

Phase 5 — Minor Improvements:
13. Surface AGENTS.md in doc_paths (scout.py)
14. Categorize Converter CLI as example material (understand adapters)

## ChatExtractedGapsAndFixes

- RC-S1: Wrong .csproj selection → wrong package_name ("Aspose.3D.Converter"), version
- RC-U1: Wrong detect_package_root → main library files excluded from API scan → public_classes=[]
- RC-U2: adapter.extract_class_details() unreachable (dead code) in _api_surface.py
- RC-G1: Identifier repair with empty allowlist destroys multi-hump PascalCase
- RC-G2: 0-claim mandatory pages routed to LLM → hollow output
- RC-G3: FAQ with 2 claims → LLM produces empty H3 headings
- RC-G4: class_briefs serialization → raw JSON in API reference tables

## ChatMentionedFiles

- C:\Users\prora\.claude\plans\luminous-floating-token.md (master plan)
- src/launcher/workers/scout/scout.py
- src/launcher/workers/understand/adapters/_dotnet.py
- src/launcher/workers/understand/extract/_api_surface.py
- src/launcher/workers/understand/worker.py
- src/launcher/workers/generate/worker.py
- src/launcher/workers/generate/section_prompt.py
- src/launcher/workers/generate/fallback.py
- src/launcher/workers/planner/plan.py
- phase_store/3d/dotnet/scout.json
- phase_store/3d/dotnet/understand.json

## ResolutionStrategy

Primary plan is the merged master plan. All 5 taskcards (TC-4306..TC-4310) created
from master plan steps. Implementation split across 3 parallel workstreams (Agent B1:
Scout/Understand, Agent B2: Generate/Prompt, Agent B3: Planner/Minor). Tests must pass
for all existing test suites before merge.

## PrimaryPlanSource
`C:\Users\prora\.claude\plans\luminous-floating-token.md`

## SecondarySources
- `C:\Users\prora\.claude\plans\federated-dancing-peacock.md` (merged into primary)
- `phase_store/3d/dotnet/scout.json` (evidence)
- `phase_store/3d/dotnet/understand.json` (evidence)

## MissingCandidates
None — all sources resolved.

---

# PLAN_SOURCES — Orchestrator Session 17 (2026-03-22) — Understand Phase Runs + Extraction Regression Fixes

## PrimaryPlanSource (Session 17)

| Field | Value |
|-------|-------|
| Path | `C:\Users\prora\.claude\plans\sequential-foraging-plum.md` |
| Type | Disk plan (master) |
| Status | Thread A COMPLETE; Thread B in-progress; UEX healing index active |

## SecondarySources

| Source | Role |
|--------|------|
| `plans/healing/UEX-00-upstream-extraction-gap-index.md` | 6 extraction gaps, 2 critical regressions |
| `plans/taskcards/TC-5172..TC-5173` | Thread B — intake sync + scan_state persistence |

## ChatExtractedSteps (Session 17)
1. ✅ Run all 11 FOSS pilots through --stop-after understand
2. ✅ Compare before/after metrics (3 infra bugs found + fixed)
3. ⏳ Fix UEX-01: 3d/java 94% claim regression (TC-5174)
4. ⏳ Fix UEX-02: email/python API extraction failure (TC-5175)
5. ⏳ Fix UEX-03: corrupt clone cache auto-recovery (TC-5176)
6. ⏳ Implement intake sync command (TC-5172)
7. ⏳ intake onboard → scan_state.json persistence (TC-5173)
8. ⏳ Low-priority: product_name fix (TC-5178), import errors (TC-5179)

## SubstantialityCheck
SUBSTANTIAL — 8 steps, 6 gaps with fixes, acceptance criteria in UEX-00

## ResolutionStrategy
P0: UEX-01/02 (critical regressions) → P1: TC-5176 + TC-5172 → P2: TC-5173/5177/5178/5179

---

# PLAN_SOURCES — Orchestrator Session 18 (2026-03-24) — FPRPS Healing Sprint

## PrimaryPlanSource (Session 18)

| Field | Value |
|-------|-------|
| Path | `plans/healing/SR-FPRPS-00-post-sprint-gap-index.md` |
| Type | healing gap index (self-review remediation) |
| Why selected | Self-review of TC-5175, TC-UND-209, TC-UND-210 identified 6 gaps: regex false positives (HIGH), spec misalignment (MED), missing dedup test (MED), unused import (LOW), missing logging (LOW), architectural fit (LOW) |
| Key sections | Gap table, execution order, 6 healing plans FPRPS-01..06 |
| SelectedAsPrimary | true (session 18) |

### ChatExtractedSteps (Session 18)

1. FPRPS-01: Fix PascalCase regex from `r"\b[A-Z][a-zA-Z0-9]+\b"` to `r"\b[A-Z][a-z][a-zA-Z0-9]*\b"` + 2 tests
2. FPRPS-02: Update TC-UND-209 taskcard to clarify raise ValueError is intentional
3. FPRPS-03: Add `_SOURCE_PRIORITY` dedup regression test for `llm_corroborated`
4. FPRPS-04: Remove unused `call` import in `test_clone.py`
5. FPRPS-05: Add DEBUG logging for individual promoted claims in `_linking.py`
6. FPRPS-06: Evaluate moving promote_corroborated_claims wiring to `_entry.py`

### SubstantialityCheck (Session 18)

SUBSTANTIAL — 6 steps, 6 gaps with fixes, pytest evidence commands.

### ResolutionStrategy (Session 18)

P0: FPRPS-01 (correctness) → P1: FPRPS-03+05 (test+observability) → P2: FPRPS-02+04+06 (docs/cleanup)

## SecondarySources (Session 18)
- `plans/healing/SR-FPRPS-01-pascal-regex-false-positives.md`
- `plans/healing/SR-FPRPS-02-tc-und-209-spec-misalignment.md`
- `plans/healing/SR-FPRPS-03-source-priority-dedup-regression-test.md`
- `plans/healing/SR-FPRPS-04-unused-call-import.md`
- `plans/healing/SR-FPRPS-05-promotion-debug-logging.md`
- `plans/healing/SR-FPRPS-06-promotion-wiring-architecture.md`

## MissingCandidates (Session 18)
None.

---

## 2026-03-25 — Unified Quality Fix Plan

PrimaryPlanSource: C:\Users\prora\.claude\plans\elegant-spinning-blanket.md
SecondarySources:
  - C:\Users\prora\.claude\plans\toasty-whistling-abelson.md (quality audit)
  - C:\Users\prora\.claude\plans\playful-floating-cosmos.md (governance debt)
  - C:\Users\prora\.claude\plans\kind-wondering-lake.md (structural diagnosis)
ResolutionStrategy: SUBSTANTIAL chat — 12 actionable steps, 3+ concrete gaps, evidence commands
