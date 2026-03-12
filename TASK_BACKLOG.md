# TASK_BACKLOG — Scout + Plan + Generate Quality Fixes (COMPLETE — 2026-03-12)

## Live TODO — Orchestrator Protocol Execution (2026-03-12 15:16:43)

- [x] ORCH-01: Materialize current plan sources and preserve prior backlog/report history
- [x] ORCH-02: Run fresh `aspose-3d-foss-python` pilot and capture run/evaluation evidence
- [x] ORCH-03: Compare pilot metrics against the two most recent prior runs and identify active root causes
- [x] ORCH-04: If pilot exposes unresolved defects, create/activate taskcards and implement protected-path fixes with tests/docs/evidence
- [ ] ORCH-05: Close the loop with self-reviews, hardening tickets if needed, `reports/STATUS.md`, `reports/CHANGELOG.md`, and final E2E verification

### ORCH-04 progress note - 2026-03-12

- `TC-4256` is complete for the property/method duplication sub-issue.
- `understand` no longer emits `root_node()`, `child_nodes()`, or `name()` as callable property evidence.
- Latest full pilot `runs/260312_151758_3d_python_3513` still ends `NO_GO`; the active upstream `understand` blocker is now undefined option-class/settings evidence (`ObjLoadOptions`, `ObjSaveOptions`, `flip_coordinate_system`, `scale`).
- Once that upstream leak is isolated or accepted, the next dominant lane is `generate` (`content_density`, `structure`, `completeness`, `route_consistency`).

## Orchestrator Protocol Execution (IN PROGRESS — 2026-03-12)

Primary plan: `plans/from_chat/20260312_151643_from_chat_orchestrator_protocol_refactored-watching-kahn.md`
Secondary plan: `C:\Users\prora\.claude\plans\refactored-watching-kahn.md`
Mission: Refresh Scout/Understand execution evidence, then harden only the still-active root causes until the pilot either passes or is blocked with evidence.

| ID | Scope | Owner-Agent | Impacted Paths | Acceptance Criteria | Risk | Tests / Evidence | Docs |
|----|-------|-------------|----------------|---------------------|------|------------------|------|
| ORCH-01 | Plan-source resolution, stale-step verification, backlog refresh | A_discovery | `reports/PLAN_SOURCES.md`, `reports/PLAN_INDEX.md`, `plans/from_chat/**`, `TASK_BACKLOG.md` | Primary plan materialized, source rationale recorded, stale plan items marked with repo evidence | Low | File inspection, `git status`, `rg` verification | `reports/*` only |
| ORCH-02 | Full 3D Python pilot execution and evidence capture | E_ops | `configs/pilots/aspose-3d-foss-python.yaml`, `runs/**`, `phase_store/3d/python/**`, `phase_store/trend.md` | Successful run or blocker evidence captured; evaluate + events + generated-page evidence collected | Medium | `launch run`, run artifacts, page reads | `phase_store/trend.md` append |
| ORCH-03 | Regression review and active root-cause diagnosis | A_discovery | `phase_store/3d/python/evaluate.json`, `runs/**/events.ndjson`, `reports/agents/A_discovery/ORCH-03/**` | A+B / D+F / CRITICAL compared to two prior runs; root causes mapped to producing modules | Medium | Artifact diff, `rg`, direct JSON inspection | `reports/STATUS.md` update |
| ORCH-04 | Protected-path implementation sprint if pilot still fails | B_implementation | `plans/taskcards/**`, `src/launcher/**`, `configs/**`, `specs/**`, `tests/**` | Taskcard-first fixes only; regression tests added; docs updated; self-review >=4/5 all dims | High | `pytest`, targeted pilot re-run, evidence files | taskcards + specs/docs as needed |
| ORCH-05 | Final verification, self-reviews, hardening routing, and release-style reporting | C_tests + D_docs + E_ops | `reports/STATUS.md`, `reports/CHANGELOG.md`, `reports/HARDENING_TICKETS/**`, `reports/agents/**` | No open known gaps for passing tasks; hardening tickets written for any failing review; final pilot status recorded | Medium | Self-review files, status report, pilot summary | `reports/*` only |

Plan: `C:\Users\prora\.claude\plans\kind-rolling-whale.md`
Run analyzed: `260311_164147_3d_python_3f6f`
Goal: Partial A+B improvement from 27% (full ≥50% also requires Understand fixes)
Final test count: 3844/3844 PASS

## Workstream A: Scout (P0 BLOCKER)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4217 | Fix `_extract_package_metadata`: add `_parse_setup_py()` fallback | **DONE** (2026-03-12) | `src/launcher/workers/scout/scout.py` |

## Workstream B: Plan (P0 BLOCKER)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4218 | Fix `_generate_evidence_aware_title`: dedup + slug fallback + fragment rejection | **DONE** (2026-03-12) | `src/launcher/workers/planner/plan.py` |

## Workstream C: Generate (P0 BLOCKER + P1 SECONDARY)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4219 | Inject claim text into section writer prompt + populate GeneratedPage.claim_texts | **DONE** (2026-03-12) | `src/launcher/workers/generate/section_prompt.py`, `generate/worker.py` |
| TC-4220 | Enforce min-prose retry (30 words) for non-optional sections | **DONE** (2026-03-12) | `src/launcher/workers/generate/worker.py` |
| TC-4221 | FAQ min answer depth: 3 sentences + ≥1 code block | **DONE** (2026-03-12) | `src/launcher/workers/generate/section_prompt.py` |

## Outcome
All 5 taskcards done. Pipeline re-run required to verify E2E A+B rate improvement.
Remaining gap: Understand phase (94.7% LLM hallucination → factual_accuracy + api_consistency HIGH) — separate sprint.

---

# TASK_BACKLOG — Understand/Generate Quality Sprint (IN PROGRESS — 2026-03-11)

Plan: `C:\Users\prora\.claude\plans\hidden-enchanting-puppy.md`
Goal: A+B ≥ 90% (baseline: 31.8% — 7/22 pages on 3D Python pilot)
Dominant findings: `factual_accuracy HIGH` (14/22) + `api_consistency HIGH` (11/22)

## Workstream A: Evidence Pipeline (CRITICAL PATH)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4040 | Evidence completeness: wire format_matrix + prefer extract-level formats | **ACTIVE** | `src/launcher/workers/understand/extract/_entry.py`, `src/launcher/workers/understand/worker.py` |
| TC-4041 | Evidence injection: workflow_examples + format_matrix → section_prompt | **NEXT** | `src/launcher/workers/generate/section_prompt.py`, `src/launcher/workers/generate/worker.py` |

## Workstream B: API Surface Quality

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4042 | API surface allowlist-first: fix inverted _is_internal_class logic | **QUEUED** | `src/launcher/workers/understand/extract/_api_surface.py` |

## Workstream C: Readability

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4043 | Readability calibration: FK 12-16 section in section_writer.txt | **QUEUED** | `src/launcher/prompts/section_writer.txt` |

## STOP Gate
If A+B ≥ 90% after TC-4040+4041+4042+4043 → declare sprint DONE. Remaining TCs (4044-4047) go to backlog.

---

# TASK_BACKLOG — Intake + Understand Hardening Swarm (IN PROGRESS — 2026-03-11)

Plan: `C:\Users\prora\.claude\plans\reflective-finding-lark.md`
Mission: Strengthen Phase 1 (Intake) + Phase 2 (Understand) until downstream agents can trust outputs.

## Phase A — Intake Hardening (Active)

| ID | Title | Owner | Status | Files |
|----|-------|-------|--------|-------|
| TC-A03 | Write intake acquisition artifact | Agent-B | **IN-PROGRESS** | `src/launcher/workers/intake/worker.py` |
| TC-A04 | Harden platform assumptions | Agent-B | **IN-PROGRESS** | `src/launcher/intake/repo_classifier.py` |
| TC-A05 | Harden clone failure + tests | Agent-B+C | **IN-PROGRESS** | `src/launcher/workers/intake/clone.py`, `tests/unit/workers/intake/test_clone.py` |
| TC-A07 | Phase 1 test run | Agent-C | **PENDING** | (after A03/A04/A05) |
| TC-A08 | Phase 1 GO/NO-GO | Orchestrator | **PENDING** | (after A07) |

## Phase B — Understand Hardening (Blocked until Phase A GO)

| ID | Title | Owner | Status | Files |
|----|-------|-------|--------|-------|
| TC-B03 | Content selection + scout visibility | Agent-B | **PENDING** | `src/launcher/workers/understand/scout.py`, `src/launcher/shared/surface_classifier.py` |
| TC-B04 | Strengthen manifest parsing | Agent-B | **PENDING** | `src/launcher/workers/understand/scout.py` |
| TC-B05 | Claim provenance tracking | Agent-B | **PENDING** | `src/launcher/models/claims.py`, `src/launcher/workers/understand/extract/_entry.py` |
| TC-B06 | Contradiction detection + semantic self-review | Agent-B+C | **PENDING** | `src/launcher/workers/understand/extract/_contradiction_resolver.py`, `src/launcher/workers/understand/worker.py` |
| TC-B07 | Isolate nondeterministic side work | Agent-B | **PENDING** | `src/launcher/workers/understand/worker.py` |
| TC-B08 | Inspectable understanding artifacts | Agent-B | **PENDING** | `src/launcher/workers/understand/worker.py`, `src/launcher/workers/understand/scout.py` |
| TC-B09 | Phase 2 test run | Agent-C | **PENDING** | (after B03-B08) |
| TC-B10 | Phase 2 GO/NO-GO | Orchestrator | **PENDING** | (after B09) |

---

# TASK_BACKLOG — Evidence Model Upgrade Sprint + Deploy Remediation (IN PROGRESS — 2026-03-11)

## Deploy Remediation Sprint — ACTIVE (Plan: plans/from_chat/20260311_000428_from_chat_deploy-remediation.md)

| ID | Scope | Status |
|----|-------|--------|
| DEPLOY-01 | Phase A: Delete irredeemable Cells (10 files) + Note LLM-batch (20 files) + ALL Slides (19 files) = 49 deleted | **DONE** (2026-03-11) |
| DEPLOY-02 | Phase B Cells: Fix `add_column()` → `add_bar()` (26 occurrences, 7 files) + import corrections (16 files) | **DONE** (2026-03-11) |
| DEPLOY-03 | Phase B 3D: Fix license placeholder + `_iter_nodes` code bug + fabricated testimonial — all 3 blockers fixed | **DONE** (2026-03-11) |
| DEPLOY-04 | Phase C Structural: Hugo `{{ }}` = all valid shortcodes (no rogue artifacts); relative links OK; no doubled URLs | **DONE** (2026-03-11) |
| DEPLOY-05 | Phase C Products: Both products pages have substantial content (100+ words) — no action needed | **DONE** (2026-03-11) |
| DEPLOY-06 | Phase D: Rebuilt `deploy/manifest.json` — 94 pages, all SHA256 correct (spot-check 5/5 PASS) | **DONE** (2026-03-11) |

---

# Evidence Model Upgrade Sprint (IN PROGRESS — 2026-03-10)

Plan: `C:\Users\prora\.claude\plans\abundant-wibbling-wadler.md` (hybrid: iterative-frolicking-river + bubbly-brewing-tulip)
Target: A+B rate from 23% → 70%+ | eliminate hallucinated API calls, broken imports, wrong format capabilities

## Phase 0: Immediate Critical Fix — COMPLETE

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-01 | Split canonical_import → add runtime_import for Python code generation | Agent-B | **DONE** (3325 tests) |

Result: Python code generation now uses `aspose.threed` not `aspose_3d_foss`. All 4 Python pilot configs updated.

---

## Phase 1: Rich API Surface Extraction — UNBLOCKED

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-02 | Typed method signatures (params + return types) + property types + enum members in ApiSurface | Agent-B | **DONE** (2963 tests, 9/9 targeted PASS) |
| TC-HYBRID-03 | Format matrix extraction (FormatRecord: can_import, can_export, test_count) | Agent-B | **DONE** (2963 tests, 9/9 targeted PASS) |

Execution: TC-HYBRID-02 and TC-HYBRID-03 are PARALLELIZABLE (both extend ApiSurface/ProductEvidence; coordinate on model field names).

---

## Phase 2: Structured Product Facts — AFTER PHASE 1

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-04 | StructuredProductFacts: InstallRecipe + LimitationEntry + WorkflowExample | Agent-B | **PENDING** |

Execution: After Phase 1 (models must be stable first).

---

## Phase 3: Factual Accuracy Gates — AFTER PHASE 1

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-05 | API identifier verification gate (flag unknown method/class calls) | Agent-B | **PENDING** |
| TC-HYBRID-06 | Contradiction detection + format truth gate (README vs source facts) | Agent-B | **PENDING** |

Execution: TC-HYBRID-05 and TC-HYBRID-06 are PARALLELIZABLE. Both depend on Phase 1 (need typed ApiSurface + FormatRecord).

---

## Phase 4: Context + Consistency + Planning — AFTER PHASE 3

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-07 | Holistic API context injection into generate worker | Agent-B | **PENDING** |
| TC-HYBRID-08 | Cross-page consistency review (runs on NO-GO verdict only) | Agent-B | **PENDING** |
| TC-HYBRID-09 | Scenario-aware planning (light: detect primary scenario for blog variant) | Agent-B | **PENDING** |

Execution: TC-HYBRID-07/08 PARALLELIZABLE after Phase 3. TC-HYBRID-09 can start after Phase 0 (independent of Phase 1-3).

---

## Phase 5: LLM Review Enhancement — AFTER PHASES 3-4

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-HYBRID-10 | Enhanced LLM review prompts + evidence quality metrics | Agent-D | **PENDING** |

---

## Acceptance Gate (Evidence Model Upgrade Sprint)

| Criterion | Target | Status |
|-----------|--------|--------|
| Python code uses aspose.threed not aspose_3d_foss | PASS | **DONE (TC-HYBRID-01)** |
| runtime_import populated for all Python pilots | PASS | **DONE (TC-HYBRID-01)** |
| ApiSurface has typed method signatures | PASS | PENDING |
| Format matrix extracted (can_import, can_export) | PASS | PENDING |
| API identifier verification gate fires on unknown class | PASS | PENDING |
| Contradiction detection fires on format capability mismatch | PASS | PENDING |
| A+B rate (Python) | ≥70% | PENDING |
| D+F rate (Python) | ≤15% | PENDING |

---

# TASK_BACKLOG — Thin Repo Parity Sprint (IN PROGRESS — 2026-03-09)

Plan: `plans/from_chat/20260309_175440_from_chat_thin-repo-parity.md` | `silly-yawning-sifakis.md`
Target: Fix 3D TypeScript 16%→>50% A+B with zero regression on rich repos

## Workstream 0: Breaking Point Fix (TC-3901) — UNBLOCKED

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3901 | AST-based TypeScript import normalization — replaces regex `\w+` hyphen-blindness | Agent-B | **IN PROGRESS** |

Root cause: `ts_analyzer.py:428-429` regex `(@aspose/\w+)` truncates `@aspose/3d-foss` → `@aspose/3d`, then replaces → `@aspose/3d-foss-foss`. Fix: `normalize_imports_ast()` using tree-sitter byte positions.

## Workstream 1: Evidence Guards (TC-3902, TC-3903) — PARALLELIZABLE after TC-3901

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3902 | SKIP markers: conditional "EVIDENCE ABSENT" injection in section_prompt.py | Agent-B | **PENDING** |
| TC-3903 | `code_evidence_sparse` flag in RichnessResult + surface_classifier + product model | Agent-B | **PENDING** |

Execution: TC-3902 and TC-3903 are independent — can run in parallel.

## Workstream 2: Regression Tests (TC-3904) — AFTER TC-3901+3902+3903

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3904 | 15 regression tests across test_ts_analyzer, test_section_prompt, test_surface_classifier | Agent-C | **PENDING** |

## Acceptance Gate

| Criterion | Target | Status |
|-----------|--------|--------|
| `normalize_imports_ast` handles `@aspose/3d-foss-foss` → `@aspose/3d-foss` | Pass | PENDING |
| Python code blocks: no change from normalize_imports_ast | Pass | PENDING |
| section_prompt with empty snippets + code_required: "EVIDENCE ABSENT" injected | Pass | PENDING |
| section_prompt with snippets present: no injection | Pass | PENDING |
| 3D TypeScript equivalent → code_evidence_sparse=True | Pass | PENDING |
| Cells Python equivalent → code_evidence_sparse=False | Pass | PENDING |
| All 15 new regression tests pass | Pass | PENDING |
| Full test suite: 0 regressions | Pass | PENDING |

---

# TASK_BACKLOG — Quality Upgrade Sprint (IN PROGRESS — 2026-03-09)

Plan: `plans/from_chat/20260309_quality_upgrade_sprint.md` | `curious-juggling-dream.md`
Target: 100% A+B grade on all published pages

---

## Workstream 0: Wave 0 — Foundation (TC-3870, TC-3871)

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3870 | Multi-language AST extraction + canonical import per platform | Agent-B | **DONE** (3118 tests) |
| TC-3871 | Richness tier multi-signal + mandatory/optional page budget | Agent-B | **DONE** (3118 tests) |

Execution: TC-3870 first (AST dispatch), then TC-3871 (tier scoring uses API surface count from TC-3870)

---

## Workstream 1: Wave 1 — Engineering Fixes (TC-3872, TC-3873, TC-3874) — PARALLELIZABLE

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3872 | Prompt hardening: template-label headings + artifact phrases + spec vocab | Agent-B | **DONE** (3102 tests) |
| TC-3873 | Post-LLM fixes: dict-literal + SEO completeness + canonical import | Agent-B | **DONE** (3102 tests) |
| TC-3874 | Snippet quality ranking (section_prompt.py) | Agent-B | **DONE** (3102 tests) |

Execution: TC-3872, TC-3873, TC-3874 all parallelizable (no shared state)

---

## Workstream 2: Wave 2 — Generation Control Flow (TC-3875 through TC-3878)

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3875 | Sandwich architecture audit across all LLM call sites | Agent-A | **DONE** (15 sites: 12 PASS, 3 PARTIAL) |
| TC-3876 | Evidence anchoring + claim saturation + tier in prompts | Agent-B | **DONE** (3118 tests) |
| TC-3877 | Per-section quality gate with inline retry | Agent-B | **DONE** (3120 tests) |
| TC-3878 | Golden corpus mandatory + code block completeness | Agent-B | **DONE** (3120 tests) |

Execution: TC-3875 first (audit informs TC-3876 scope); TC-3876/3877/3878 parallelizable after TC-3875

---

## Workstream 3: Wave 3 — Adaptive Healing (TC-3879, TC-3880)

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3879 | Structured heal actions schema + 3-tier escalation policy | Agent-B | **PENDING** |
| TC-3880 | Golden corpus expansion (all platforms) + quality-annotated examples | Agent-D | **PENDING** |

Execution: TC-3879 first; TC-3880 parallelizable after golden format defined in TC-3879

---

## Acceptance Gate

| Criterion | Target | Status |
|-----------|--------|--------|
| A+B rate on published pages | 100% | PENDING |
| D+F rate on published pages | 0% | PENDING |
| heal_failed rate | ≤5% | PENDING |
| Zero CRITICAL findings | 0 | PENDING |
| Zero spec_leakage HIGH | 0 | PENDING |
| Zero dict-literal HIGH | 0 | PENDING |
| Zero template-label HIGH | 0 | PENDING |
| All reference pages have code | Yes | PENDING |
| Heal convergence ≤2 steps | Yes | PENDING |
| Sandwich audit compliance | 100% | PENDING |
| Golden coverage | all platforms × mandatory roles | PENDING |

---

# TASK_BACKLOG — TC-3868 Self-Review Healing Sprint (COMPLETE)

Generated: 2026-03-08 (updated by orchestrator)
Active plans: `plans/healing/TC-3868-gap-index.md` — 6 healing TCs

---

## Workstream 0: TC-3868 Self-Review Healing (NEW — HIGH PRIORITY)

| ID | Scope | Owner | Status |
|----|-------|-------|--------|
| TC-3868-H4 | Verify execute_run() kwargs: ADD doc comment + test (result: VERIFIED correct) | Agent-B | DONE |
| TC-3868-H1 | Fix current_metrics never updating in run_heal() loop — Critical bug | Agent-B | DONE |
| TC-3868-H2 | Rename _restore_rollback_snapshot → _remove_rollback_snapshot + scope contract | Agent-B | DONE |
| TC-3868-H3 | Add executed_mode field to HealStep; change _execute_worker_rerun to 4-tuple | Agent-B | DONE |
| TC-3868-H5 | Code hygiene: dead Literal + atomic_write_json + token constant + dup HealResult | Agent-B | DONE |
| TC-3868-H6 | 7 new tests: cross-step metrics update, worker→full fallback, CLI diagnose E2E | Agent-C | DONE |

Execution order: H4 → {H1, H2 sequential (same file)} → {H3, H5 sequential (same file)} → H6

---

# TASK_BACKLOG — Plan Complete (HL-01 + H5 DONE)

Generated: 2026-03-08 (updated)
Active plans: None — all plan tasks from quirky-mapping-mccarthy.md, twinkly-beaming-wren.md, sparkling-discovering-walrus.md are closed.
Discovery report: `reports/agents/A/HL-01-discovery/report.md`

---

## Workstream 1: Heal Loop Architecture — COMPLETE

| ID | Scope | Status |
|----|-------|--------|
| HL-01 | Pipeline re-execution via `execute_run()` | DONE via TC-3868 |
| HL-02 | HealDecision schema_failure type mismatch | DONE |
| HL-04 | Module-level constants + session timeout + prompt fix | DONE |
| HL-03 | `emit_event` at 4 heal session points | DEFERRED (low priority) |

---

## Workstream 2: Optimization Phase — COMPLETE (H5-06/H5-07 deferred by design)

| ID | Scope | TC | Status |
|----|-------|-------|--------|
| H5-01 | Selective page regen — `heal_target_pages` in WorkerContext | TC-3853 | DONE |
| H5-02 | Generate worker page-skip + `generate_page_skipped` event | TC-3853 | DONE |
| H5-03 | `eval_fast_path` — skip LLM review for A/B pages | TC-3854 | DONE |
| H5-04 | Cache doc — LLM disk cache enable/restore in `run_heal` | TC-3855 | DONE |
| H5-05 | `remaining_for_step()` in BudgetTracker | TC-3854 | DONE |
| H5-07 (=H5.7) | Rolling prompt compression; `_compress_heal_step`; 6K cap | TC-3855 | DONE |
| H5-06 | `asyncio.gather` section parallelism | — | DEFERRED — high regression risk |
| H5-08 (=H5.8) | Section-level granularity + checkpoint protocol | — | DEFERRED — depends H5-06 |

---

## Deferred Items

| ID | Scope | Reason |
|----|-------|--------|
| HL-03 | `emit_event` at 4 heal session points | Low priority; heal sessions work without it |
| H5-06 | `asyncio.gather` section parallelism in generate/worker.py | High regression risk to deterministic output |
| H5-08 | Section-level target + checkpoint protocol | Depends on H5-06 architecture |

---

## Previous Sprints (COMPLETE)

- TC-3853, TC-3854, TC-3855, TC-3867: H5 Optimization Phase DONE (2026-03-08) — 2936 tests
- TC-3868: Heal Execution Modes (worker/full/diagnose) DONE (2026-03-08) — 2936 tests; stub replaced with `_execute_worker_rerun()`; `--mode` flag added; 7 new tests
- HL-02, HL-04, RD-01, RD-02, GL-01, GL-02: Heal/Readability/Golden correctness DONE (2026-03-08) — 2929 tests
- MP-01..MP-16: v2 Plan Self-Healing DONE (2026-03-08)
- TC-3857..TC-3863: Evaluation Check Defects Full Audit DONE (2026-03-08) — 2863 tests
- HC-01..HC-06: TreeSitter Healing DONE
- TH-01..TH-05: Trademark Cleanup DONE
- CQ-01..CQ-08: Claim Extraction Quality DONE
- SR-01..SR-07: Template-Directive Healing DONE
- TC-3774 + TC-3775: Embeddings Module DONE
- TC-3790 + TC-3791: TreeSitter Foundation DONE

---

## Phase 6 — Understand A-Grade Hardening (2026-03-11)

Plan: `C:\Users\prora\.claude\plans\wild-growing-volcano.md`
Goal: Pipeline through Understand produces A-grade output (LLM claims ≥60%, PDF removed, correct verification, ≥15 docstring classes)

| TC | Title | Status | Files | Priority |
|----|-------|--------|-------|----------|
| TC-4091 | Fix LLM prompt path: parents[2]→parents[3] in _llm.py | **ACTIVE** | `extract/_llm.py` | CRITICAL |
| TC-4092 | Format detection false positive: negative context filter for PDF | **ACTIVE** | `extract/_deterministic.py` | HIGH |
| TC-4093 | Fix install recipe verification code: canonical_import not runtime_import | **ACTIVE** | `extract/_deterministic.py` | MEDIUM |
| TC-4094 | Raise docstring claim cap 50→200; add truncation warning | **ACTIVE** | `extract/_entry.py` | MEDIUM |
| TC-4095 | Python docstring type extraction (conditional on TC-4091) | **QUEUED** | `adapters/_python.py` | LOW |

### Stop Gate (all 4 mandatory TCs)
- `claim_source="llm"` ≥ 60% of total claims
- `supported_formats` does NOT contain PDF
- `install_recipe.verification_code` starts with `import aspose_cells_foss`
- Docstring claims cover ≥ 15 classes
- Self-review `passed=True`

---

# TASK_BACKLOG — Scout + Understand Hardening + Phase Store Sprint (IN PROGRESS — 2026-03-11)

Plan: `C:\Users\prora\.claude\plans\quizzical-hatching-ember.md`
Mission: Harden Scout/Understand phases and enable phase_store for all phases.

## Phase A — Scout Hardening

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4100 | Namespace recursion: explore ALL submodules | IN-PROGRESS | `src/launcher/workers/understand/extract/_api_surface.py` |
| TC-4101 | Resume path: stale file detection + warning | IN-PROGRESS | `src/launcher/workers/understand/worker.py` |
| TC-4102 | Doc importance rank: substring matching | IN-PROGRESS | `src/launcher/workers/scout/scout.py` |

## Phase B — Understand Hardening

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4103 | Format matrix: Strategy 4 (format class names) | IN-PROGRESS | `src/launcher/workers/understand/extract/_deterministic.py` |

## Phase C — Phase Store All Phases

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-4104 | phase_store: scout.json + understanding_bundle.json | IN-PROGRESS | `src/launcher/workers/scout/worker.py`, `src/launcher/workers/understand/worker.py`, `src/launcher/deploy/phase_promoter.py` |

## Stop Gate

- TC-4100: extraction_audit.json public_class_count includes classes from all submodules
- TC-4101: stale_files_on_resume appears in scout_inventory.json on resume runs
- TC-4102: Unit tests pass for compound stem names
- TC-4103: format_matrix_count > 0 for repos using FbxSaveOptions/ObjLoadOptions patterns
- TC-4104: phase_store/3d/python/scout.json + understand.json exist after promote

---

## Integration Completion Sprint — 2026-03-11T21:50

**Goal**: Close the phase_store loop — run `260311_164147_3d_python_3f6f` through evaluate so promoter fires.

| ID | Task | Owner | Status | Acceptance |
|----|------|-------|--------|------------|
| INT-001 | Resume run from planner → generate → evaluate | Orchestrator | Pending | Run exits 0; workers_completed includes 'evaluate' |
| INT-002 | Verify phase_store/3d/python/scout.json written | Orchestrator | Pending | `files_enumerated > 0` |
| INT-003 | Verify phase_store/3d/python/understand.json written | Orchestrator | Pending | `format_matrix_count > 0`, `claims > 0` |
| INT-004 | Confirm existing plan/generate/evaluate.json still present | Orchestrator | Pending | All 3 still exist in phase_store/3d/python/ |
| INT-005 | Unit tests 3587 passed 0 failed | Orchestrator | Pending | `pytest tests/unit/ -q` green |

---

# TASK_BACKLOG — Hallucination Reduction Sprint (COMPLETE — 2026-03-11)

Plan: `C:\Users\prora\.claude\plans\zippy-pondering-plum.md`
Goal: Reduce hallucination rate from 94.7% to ≤5% on the 3d-python pilot run
Trigger: 412/435 claims from `llm_fallback` (LLM call failed), 20 factual_accuracy=HIGH findings

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-HAL-01 | Contradiction resolver: method/property split | **DONE** | `_contradiction_resolver.py` |
| TC-HAL-02 | Contradiction resolver: lowercase API check | **DONE** | `_contradiction_resolver.py` |
| TC-HAL-03 | Contradiction resolver: enum member check | **DONE** | `_contradiction_resolver.py` |
| TC-HAL-04 | LLM fallback quality gate + strict api filtering | **DONE** | `_llm.py`, `_entry.py` |
| TC-HAL-05 | Docstring property callable fix | **DONE** | `_entry.py` |
| TC-HAL-06 | Claim confidence field | **DONE** | `models/claims.py`, `_validation.py`, schema |
| TC-HAL-07 | Snippet import path validation | **DONE** | `_snippets.py`, `_entry.py` |
| TC-HAL-08 | Generate confidence threshold gate | **DONE** | `section_prompt.py` |
| TC-HAL-09 | Evaluate hallucination_rate check | **DONE** | `evaluate/checks/hallucination_rate.py`, `worker.py` |
| TC-HAL-10 | Hallucination metrics in extraction_audit | **DONE** | `understand/worker.py` |

Tests: 4121 passed, 1 skipped, 3 xfailed (PYTHONHASHSEED=0)


---

# TASK_BACKLOG — Post-Sprint Gap Closure (IN PROGRESS — 2026-03-12)

Plan: `C:\Users\prora\.claude\plans\calm-discovering-cookie.md`
Goal: Close two residual spec deviations from the Understand Strengthening sprint

## Workstream A: Error Hierarchy (TC-GAP-01)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-GAP-01 | Introduce WorkerError + replace ValueError in checkpoint loaders | **DONE** | `src/launcher/util/errors.py`, `src/launcher/workers/evaluate/worker.py`, `src/launcher/orchestrator/run_loop.py` |

## Workstream B: C# Adapter Quality (TC-GAP-02)

| ID | Title | Status | Files |
|----|-------|--------|-------|
| TC-GAP-02 | Fix C# enum member extraction in ts_analyzer | **DONE** | `src/launcher/shared/ts_analyzer.py`, `tests/unit/workers/understand/test_dotnet_adapter.py` |

---

## Sprint: Pipeline Quality Root-Cause Fix (2026-03-12)
Source: breezy-cooking-storm plan | Baseline: 260311_202204 (0% A+B, 3 cycles NO-GO)

### Phase U — Understand Stability
| ID | Task | TC | Status |
|----|------|----|--------|
| U-1 | Add retry before LLM fallback | TC-4224 | In-Progress |
| U-2 | Block low-confidence claims from checkpoint | TC-4225 | In-Progress |
| U-3 | Pin temperature=0.0 for claim extraction | TC-4226 | In-Progress |

### Phase G — Generate Structural Fixes
| ID | Task | TC | Status |
|----|------|----|--------|
| G-1 | Fix canonical_import injection | TC-4227 | In-Progress |
| G-2 | Fix L1 validator missing type key | TC-4228 | In-Progress |
| G-3 | Enforce code blocks in reference pages | TC-4229 | In-Progress |
| G-4 | Cap claim injection per section | TC-4230 | In-Progress |

### Phase P — Planner Relevance
| ID | Task | TC | Status |
|----|------|----|--------|
| P-1 | Add page-level claim relevance filtering | TC-4231 | In-Progress |

### Phase E — Evaluate Calibration
| ID | Task | TC | Status |
|----|------|----|--------|
| E-1 | Calibrate hallucination_rate threshold | TC-4232 | In-Progress |

### Acceptance Gate
- [ ] fallback_rate = 0.0 in understand checkpoint
- [ ] Zero canonical_import violations in generated pages
- [ ] Zero L1_VALIDATOR_FAIL_FINAL per cycle
- [ ] Zero Section gate FAIL for reference pages
- [ ] A+B rate >= 30% in pilot run
- [ ] D+F rate <= 30% consistently across runs

---

# TASK_BACKLOG — Scout/Intake Module A/A+ Grade Fixes (2026-03-12)

Plan: `C:\Users\prora\.claude\plans\bubbly-strolling-toast.md`
Goal: Elevate Scout from B+ → A/A+ grade across 4 root-cause gaps
Execution: TC-4233..TC-4236

## Workstream A: Scout Core (scout.py)

| ID | Title | Status | Files | Owner |
|----|-------|--------|-------|-------|
| TC-4233 | Scout README section-aware extraction (replace `[:4000]`) | **IN-PROGRESS** | `src/launcher/workers/scout/scout.py`, `tests/unit/workers/test_scout.py` | Agent-B |
| TC-4234 | Scout multi-factor file importance ranking (0-7, 4 factors) | **IN-PROGRESS** | `src/launcher/workers/scout/scout.py`, `tests/unit/workers/test_scout.py` | Agent-B |
| TC-4235 | Platform-aware manifest parsing with rich metadata (all platforms) | **IN-PROGRESS** | `src/launcher/workers/scout/scout.py`, `tests/unit/workers/test_scout_facts.py` | Agent-B |

## Workstream B: Scout Model + Worker

| ID | Title | Status | Files | Owner |
|----|-------|--------|-------|-------|
| TC-4236 | Scout important-file coverage guarantee (depends on TC-4234) | **PENDING TC-4234** | `src/launcher/models/understanding.py`, `src/launcher/workers/scout/scout.py`, `src/launcher/workers/scout/worker.py`, `tests/unit/workers/test_scout.py`, `tests/unit/workers/test_scout_budget_log_cap.py` | Agent-B |

## Acceptance Criteria (all 4 TCs)

- `readme_summary` length ≥ 4000 chars on comprehensive READMEs (was capped at 4000)
- `_file_importance_rank("OVERVIEW.md", FileCategory.doc)` returns ≥ 3 (was 0)
- `SharedFacts.description` non-empty for Node/Java/C# fake repos
- `repo_info.important_files_skipped` field in scout_bundle.json
- All existing tests pass PYTHONHASHSEED=0
- ≥15 new test cases
