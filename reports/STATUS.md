# Pipeline Status — Session 33: TC-5331/5332/5333/5334/5335 + fresh C++ pilot run (2026-04-02)

## Summary (Session 33 — Current)

Five taskcards completed. Fresh C++ pilot run started with all fixes applied.

- **TC-5331**: `check_ecosystem_contamination()` wired in evaluate worker — detects .NET/C++CLI tokens in C++ code fences (Done — was already implemented).
- **TC-5332**: 100 regression tests for contamination scanner, ecosystem check, and import rule (Done — all passing).
- **TC-5333**: Platform detection bug fixed (`content[:500]` → `content`), cpp routing changed to `review: standard`, 3 regression tests added.
- **TC-5334**: Platform-unaware `_STRUCTURE_DIRECTIVES` fixed. Added `_CPP_SECTION_DIRECTIVES` for install sections (find_package, not pip). Added Python-fence detection in generate worker retry loop.
- **TC-5335**: Extended C++ forbidden types prohibition to prose as well as code blocks.
- **Tests**: 5932 passed, 8 skipped (unit suite)

### Expected improvements in next pilot run

| Fix | Expected effect |
|-----|----------------|
| TC-5334: cmake directives | 2 F-grade _index pages → C/D (pip install eliminated) |
| TC-5334: Python fence retry | 4 D-grade pages improve (installation, fix-errors, presentation-creation, slide-manipulation) |
| TC-5335: prose prohibition | api_allowlist:HIGH for System/MakeObject/Drawing in prose → reduced |

---

# Pipeline Status — Session 32: TC-5329/5330/5333 + fresh C++ pilot run (2026-04-02)

## Summary (Session 32 — Current)

Three taskcards implemented. Fresh C++ pilot run `260402_065901_slides_cpp_889a` started.

- **TC-5329**: Added `_CPP_STDLIB` (47 entries) to `api_allowlist.py`. C++ stdlib + exception types exempt from api_allowlist false-positive findings.
- **TC-5330**: Wired `_build_cpp_forbidden_types_block()` into `_build_import_rule_block()` for C++. Added `InvalidOperationException`, snake_case method name guidance.
- **TC-5333**: Fixed platform detection bug (`content[:500]` → `content`) in `api_allowlist.py` + `code_platform.py`. Changed cpp pilot routing: `review: reasoning` → `review: standard`. Added 3 regression tests.
- **Tests**: 6207 passed (up from 6199), 9 skipped, 3 xfailed

### Session 32 C++ Pilot Results (run: 260402_065901_slides_cpp_889a — partial from checkpoint)

| Grade | Old (S31) | New (S32) | Change |
|-------|-----------|-----------|--------|
| A | 0 | 2 | +2 |
| B | 4 | 3 | -1 |
| C | 17 | 9 | -8 |
| D | 1 | 6 | +5 |
| F | 0 | 2 | +2 |

**Go criteria:**
- [FAIL] D+F rate: 36% (threshold: ≤30%) — regression from 5% in S31
- [FAIL] A+B rate: 23% (threshold: ≥50%)

**Note**: S32 run is from NEW generate content (TC-5330 prompt changes). Old S31 run used different content. The D/F regression reflects both: (a) new content having more code_platform/canonical_import issues, and (b) qwen3-next grader vs `recommended` grading differently. factual_accuracy:high improved significantly: **26 → 13** (TC-5330 effect).

**Key finding - platform detection bug was causing 52 false api_allowlist:medium findings.**
After TC-5333 fix: api_allowlist:medium = **13** (restored to correct baseline).

**Remaining bottlenecks:**
1. LLM still writing .NET code in 5/22 pages (MakeObject, System::String, Drawing::PointF) despite TC-5330 prompt
2. `code_platform` failing 6/22 pages (wrong fence language or install command)
3. `canonical_import` failing 3/22 pages
4. `completeness` failing 9/22 pages

---

# Pipeline Status — Session 31: TC-5328 C++ enum class fix + verified run (2026-04-01)

## Summary (Session 31 — Previous)

TC-5328 implemented and verified: C++ `enum class` types now enter `api_surface.public_classes`.
Run `260330_163303_slides_cpp_d438` confirms all api_allowlist false positives eliminated.

- **TC-5328**: SR-01 forward-declaration filter now exempts `is_enum=True` entries. `SaveFormat` + enum members enter `public_classes` and `api_identifiers`. **api_allowlist HIGHs: 19 → 0.**
- **public_classes**: 180 → 222 (+42 enum class types extracted)
- **Tests**: 6181 passed, 9 skipped, 3 xfailed (up from 6138)

### Session 31 C++ Pilot Results (run: 260330_163303_slides_cpp_d438)

| Grade | Count | % | vs Session 30 |
|-------|-------|---|--------------|
| A | 0 | 0% | — |
| B | 4 | 18% | +2 |
| C | 17 | 77% | -1 |
| D | 1 | 4% | -1 |

**Go criteria:**
- [PASS] D+F rate: 4% (threshold: ≤30%) ← was 9% in session 30
- [FAIL] A+B rate: 18% (threshold: ≥50%)

**api_allowlist HIGHs: 0** (SaveFormat, Pptx, Pdf, Png, Jpeg, Svg — all eliminated)

**Remaining bottleneck: LLM code quality**
- LLM writes .NET-style code for C++ (System, IO, Drawing, MakeObject, etc.)
- FPR-03 violations persist: Aspose, Foss, Slides, MakeObject not in public_classes (namespace components vs class names)
- code_correctness HIGHs drive most C→D demotions

---

## Previous Status (Session 30 — 2026-03-29)

Three pipeline-blocker fixes. C++ Slides pilot completed: **22 pages, B=2 C=18 D=2**.
- **TC-5326**: `intake_bundle.schema.json` missing 6 TC-5321 fields → schema validation crash at intake. Fixed.
- **TC-5327**: `claim_coverage` ratio > 1.0 when pages use claims beyond assigned set → schema crash at evaluate. Fixed (conditional intersection).
- **Tests**: 6138 passed, 9 skipped, 3 xfailed (up from 6123).

### Session 30 C++ Pilot Results (run: 260329_154405_slides_cpp_fa02)

| Grade | Count | % |
|-------|-------|---|
| A | 0 | 0% |
| B | 2 | 9% |
| C | 18 | 82% |
| D | 2 | 9% |

**Go criteria:**
- [PASS] CRITICAL findings: 0 (threshold: 0)
- [PASS] D+F rate: 9% (threshold: ≤30%)  ← was 16% in session 28
- [PASS] Editorial-critical HIGH rate: 9% (threshold: ≤15%)
- [FAIL] A+B rate: 9% (threshold: ≥50%)

**Top HIGH findings by check:**
| Check | HIGHs | Notes |
|-------|-------|-------|
| factual_accuracy | 23 | LLM review (capped to MEDIUM in grading) |
| api_allowlist | 19 | 6/22 pages — TC-5325 helped (was 13/18 pages) |
| api_consistency | 17 | LLM review (capped to MEDIUM) |
| code_correctness | 15 | Deterministic — real code errors |
| content_grounding | 5 | Deterministic |
| completeness | 5 | Deterministic |
| canonical_import | 4 | Wrong import in content |

**D pages:**
- `frequently-asked-questions`: claim_coverage HIGH (editorial-critical)
- `add-shape`: route_consistency + artifacts HIGH (editorial-critical)

**Remaining api_allowlist root cause (TC-5328):**
- `SaveFormat`, `Pptx`, `Pdf`, `Png`, `Jpeg`, `Svg` → `enum class SaveFormat` not extracted
- `System`, `IO`, `Stream` → LLM hallucinating .NET-style code for C++ (real quality issue)
- `Rectangle`, `Drawing` → geometry/drawing namespace types missing from api_surface

**Next step:** TC-5328 — Add `enum class` extraction to C++ api_surface adapter. Expected to eliminate ~10/19 api_allowlist HIGHs (SaveFormat and its values).

---

## Summary (Session 29 — Previous)

Four structural root-cause fixes applied to the C++ pipeline seams. No pilot run yet (TC-5322/5323/5324 affect Scout/Understand/Generate workers which require a full pipeline rerun to measure impact). All 4 taskcards Done. Full test suite: **6127 passed, 9 skipped, 3 xfailed**.

| TC | Phase | Root Cause Fixed | Impact |
|----|-------|-----------------|--------|
| TC-5322 | Scout | `.h` → "c" primary_language (260 .h > 206 .cpp) | `primary_language="cpp"` → correct install recipe |
| TC-5323 | Understand | `::Internal` namespace leaked into import_allowlist | Allowlist stays clean; canonical namespace breaks early |
| TC-5324 | Generate | `#include <Aspose::Slides::Foss>` invalid C++ in prompt | `using namespace Aspose::Slides::Foss;` → LLM generates valid C++ |
| TC-5325 | Evaluate | `_build_allowlist` split on `.` only (not `::`) | Namespace qualifiers exempt from api_allowlist; 82% false-positive rate expected to drop to ~0% |

### Expected Impact on Session 28 Failing Checks

| Check | Session 28 Rate | Expected After Fix | Fix |
|-------|-----------------|-------------------|-----|
| api_allowlist | 82% (18/22) | ~5-15% (real hallucinations only) | TC-5325 |
| code_correctness | 73% (16/22) | ~30-50% | TC-5324 (correct import instruction) |
| factual_accuracy | 100% (22/22) | ~80-90% (LLM quality gap) | TC-5324 (better namespace context) |
| api_consistency | 77% (17/22) | ~60-70% | TC-5323/5324 |

### Stale Phase Store — Snippet Gap (NOT a code bug)

Both `phase_store/slides/cpp/understand.json` and `phase_store/3d/java/understand.json` show **0 snippet_facts** — these are old cached artifacts. The current code extracts snippets correctly:

- **C++ README**: 9 `cpp` fenced code blocks with correct `using namespace Aspose::Slides::Foss;` + real API usage (`Presentation`, `save()`, `slides()`)
- **Java 3D SceneTest.java**: `_extract_java_test_slices` extracts 2 slices with real `Scene`, `Node`, `Transform` usage
- tree-sitter validation passes for both

A pipeline re-run regenerates the phase_store with real snippets injected into LLM prompts — directly addressing `factual_accuracy: 100%` failure rate.

### Expected Grade Impact After Re-Run

With TC-5322/5323/5324/5325 + snippet extraction:
- `api_allowlist` 82% → ~5-15% (TC-5325 eliminates namespace qualifier false positives)
- `code_correctness` 73% → ~20-40% (correct `using namespace` instruction + real code examples)
- `factual_accuracy` 100% → ~40-60% (9 C++ snippets from README show correct API usage)
- Grade: 0% A+B → target **20-40% A+B** (optimistic: 30%+)

### Next Step: Pipeline Re-Run

Run C++ pilot with all fixes to measure actual grade improvement:
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-slides-foss-cpp.yaml
```

### Evidence Files

- `reports/TC-5322/evidence.md` — Scout primary_language fix
- `reports/TC-5323/evidence.md` — Understand allowlist fix
- `reports/TC-5324/evidence.md` — Generate import statement fix
- `reports/TC-5325/evidence.md` — Evaluate allowlist split fix

---

# Pipeline Status — Session 28: TC-5312 Pilot Rerun Comparison (2026-03-28)

## Summary (Session 28 — Current)

Pilot rerun completed for C++ Slides (`260327_163318_slides_cpp_a36c`) with TC-5310/TC-5312 extraction fixes. Full before/after comparison produced.

### Extraction Quality (TC-5310 + TC-5312)

| Metric | BEFORE (260324_180011) | AFTER (260327_163318) | Delta |
|--------|------------------------|------------------------|-------|
| public_classes | **0** | **180** | +180 |
| api_identifiers | **0** | **1003** | +1003 |
| import_allowlist | **0** | **30** | +30 |
| claims | 29 | 92 | +317% |
| class_briefs | 0 | 180 | +180 |
| snippets | 9 | 77 | +756% |
| richness_tier | **C** | **A** | C→A |
| api_confidence | **low** | **high** | low→high |
| SR-01 fwd-decl filtered | — | 71 stubs | — |

### Evaluation Grade Distribution

| Grade | BEFORE (18 pages) | AFTER (22 pages) | Delta |
|-------|-------------------|------------------|-------|
| A | 0 (0%) | 0 (0%) | — |
| B | 0 (0%) | 0 (0%) | — |
| C | 16 (89%) | 21 (95%) | — |
| D | 2 (11%) | 1 (5%) | **-6%** |
| F | 0 (0%) | 0 (0%) | — |
| **A+B** | **0%** | **0%** | — |
| **D+F** | **11%** | **5%** | **-6%** |

### Check Failures (count/pages)

| Check | BEFORE | AFTER | Direction |
|-------|--------|-------|-----------|
| factual_accuracy | 18/18 (100%) | 22/22 (100%) | unchanged |
| api_allowlist | 16/18 (89%) | 18/22 (82%) | ↑ improved |
| code_correctness | 18/18 (100%) | 16/22 (73%) | **↑ improved** |
| api_consistency | 14/18 (78%) | 17/22 (77%) | unchanged |
| code_formatting | 7/18 (39%) | 3/22 (14%) | **↑ improved** |
| content_density | 7/18 (39%) | 5/22 (23%) | **↑ improved** |
| artifacts | 3/18 (17%) | 0/22 (0%) | **✓ eliminated** |
| claim_coverage | 1/18 | 0/22 | **✓ eliminated** |

### Analysis

TC-5312 extraction fixes proved: 0→180 classes, 0→1003 identifiers, richness tier C→A. Generation quality improved measurably (code_formatting 39%→14%, code_correctness 100%→73%, artifacts eliminated). **Remaining bottleneck**: LLM generates .NET-style PascalCase C++ code (`Aspose::Slides::Presentation`) instead of actual FOSS C++ snake_case API (`Aspose::Slides::Foss`, `add_auto_shape()`). Requires canonical_import fix and better prompting for the C++ FOSS namespace.

### New Issues Found

- **Schema sync bug**: `evaluation_report.schema.json` missing `graded_severity` field → evaluate checkpoint can't be written (TC-5316 model change not propagated to schema)
- **content_manifest schema sync bug**: `understanding_checkpoint_run_id` and `extraction_completeness` not in schema at pipeline start → generate checkpoint failed → manually reconstructed
- **FPR-03 false retries**: LLM correctly uses `Aspose::Slides::Foss` namespace but `Aspose`, `Slides` are not in `public_classes`. Causes 2 retries per section, tripling LLM calls. Needs C++ namespace exemptions.
- **canonical_import wrong**: Config has `"Aspose::Slides"` but actual namespace is `"Aspose::Slides::Foss"`. LLM learns wrong namespace from config.

---

# Pipeline Status — Session 27: TC-5313..TC-5318 Production Architecture Fixes (2026-03-27)

## Summary (Session 27 — Current)

6-taskcard execution from plan `logical-squishing-cascade.md` (production architectural review). All 6 structural root causes addressed in Phase 0 (platform correctness) and Phase 1 (heal loop quality).

| TC | Title | Status | Files Changed |
|----|-------|--------|---------------|
| TC-5313 | Platform-aware fallback.py (no Python-hardcoded content for C++/Java/.NET) | **Done** | fallback.py |
| TC-5314 | Import normalization platform guard in section_validator.py | **Done** | section_validator.py |
| TC-5315 | _JAVA_STDLIB allowlist in api_allowlist.py (eliminate Java false positives) | **Done** | api_allowlist.py |
| TC-5316 | graded_severity field on Finding + annotate_graded_severity() | **Done** | evaluation.py, grader.py, worker.py |
| TC-5317 | Identifier repair: mark-not-delete code lines (replace with _UNKNOWN_ marker) | **Done** | _identifier_repair.py, api_allowlist.py |
| TC-5318 | Finding-derived targeted heal directives (_FINDING_TO_DIRECTIVE mapping) | **Done** | graph_builder.py |

**Full unit suite: 5824 passed, 8 skipped, 0 failed** (self-review added +19 tests)

### Root Causes Fixed (Session 27)

- **Root Cause B (TC-5313, TC-5314)**: Fallback path no longer produces Python-specific content (pip install, Python 3.7+, `import` syntax) for C++/Java/.NET products. Platform-dispatch dicts `_RUNTIME_REQUIREMENTS`, `_INSTALL_COMMANDS`, `_IMPORT_SYNTAX` added. Import normalization in `section_validator.py` now guarded by `product.platform == "python"` check.
- **Root Cause B (TC-5315)**: Java stdlib false positives eliminated. `_JAVA_STDLIB` frozenset (~80 entries: java.lang, java.util, java.io, common generics) added to `api_allowlist.py`. Applied when frontmatter platform == "java".
- **Root Cause C (TC-5316)**: Severity cap is now visible. `Finding.graded_severity` field added (default `""`). `annotate_graded_severity()` function added to `grader.py`. `evaluate/worker.py` calls it before building `PageEvaluation`. Routing can now use `graded_severity` instead of `severity` for consistency with actual page grade.
- **Root Cause A (TC-5317)**: Identifier repair no longer silently deletes code lines (TC-GEN-601). Lines with hallucinated identifiers are preserved with `_UNKNOWN_{token}_` substitution. Surrounding code structure remains coherent. `api_allowlist.py` now detects `_UNKNOWN_` markers and fires HIGH findings.
- **Root Cause heal directives (TC-5318)**: `_build_failing_check_directives()` now uses `_FINDING_TO_DIRECTIVE` mapping to produce specific actionable instructions per failing check (e.g., "UNKNOWN IDENTIFIER detected" for api_allowlist, "CODE ERROR detected" for code_correctness) instead of generic "Top failing checks: X, Y" labels. Uses `graded_severity` when available.

### Expected Impact

- **Java pilot**: api_allowlist false positives from Java stdlib drop to zero. D+F rate reduction expected.
- **C++/Java fallback path**: Pages hitting deterministic fallback no longer fail `code_platform` check immediately. Content now contains platform-appropriate install commands and import syntax.
- **C++ pilot**: `[identifier omitted]` placeholder problem addressed — lines are preserved with visible markers instead of being deleted, preserving code structure. Heal cycles will have better signal.
- **Heal loop**: Directives now tell the LLM *what specifically went wrong*, not just which claims to cover. Heal convergence expected to improve.

---

# Pipeline Status — Session 26: TC-5312 C++ Extraction Quality Filters (2026-03-27)

## Summary (Session 26 — Current)

Continuation of orchestrator plan `bright-nibbling-elephant.md`. Session 26 completed TC-5312.

| TC | Title | Status | New Tests |
|----|-------|--------|-----------|
| TC-5312 | C++ extraction quality filters — SR-01 fwd-decl, SR-02 internal paths, SR-03 cap | **Done** | +9 |

**Full unit suite: 5804 passed, 8 skipped, 0 failed**

### Root Causes Fixed (Session 26)

- **ISSUE-04 follow-up (TC-5312)**: Three C++ extraction quality improvements applied:
  - **SR-01**: Forward-declaration stubs (0 methods + 0 method_details + 0 properties in `.h`/`.hpp`/etc.) are now dropped from `public_classes`. Eliminates `OpcPackage`, `InMemoryOpcPackage`, `CommentAuthorsPart` and similar internal forward-declaration noise.
  - **SR-02**: `CppExtractor.build_import_allowlist()` now skips headers under `_internal/` directories. Only public API headers are included.
  - **SR-03**: `_find_source_files()` default `max_files` raised from 300 → 500, allowing full discovery of C++ repos with 250+ header files.

### Phases Remaining

| Phase | TC | Scope | Status |
|-------|----|-------|--------|
| Phase 3 follow-up | TC-5309-BBN-02 | Remove `_filter_weak_evidence()` BBN-02 sparse elevation (optional) | Future |
| Pilot run | — | Run C++ + Java pilots with all fixes to verify A+B improvement | **Next step** |

---

# Pipeline Status — Session 25: TC-5311 Full Scope + TC-5309 Sparse Grounding Bypass (2026-03-27)

## Summary (Session 25)

Continuation of orchestrator plan `bright-nibbling-elephant.md`. Session 25 completed TC-5311 full scope and TC-5309.

| TC | Title | Status | New Tests |
|----|-------|--------|-----------|
| TC-5311 | Deterministic routing — full scope: heal_understand wired in graph + PipelineAdvice | **Done** | +6 |
| TC-5309 | Remove llm_sparse_grounding bypass — drop unbound LLM claims | **Done** | +15 |

**Full unit suite: 5797 passed, 8 skipped, 0 failed**

### Root Causes Fixed (Session 25)

- **ISSUE-07 (complete)**: `heal_understand` routing fully implemented. When `extraction_quality` fires HIGH on first re-run, `route_after_evaluate()` returns `"heal_understand"`. Graph routes through `__re_run_understand__` → understand → planner → generate. `re_run_count == 0` guard prevents infinite loops.
- **ISSUE-03 (partial — `_validate_fact_binding` fixed)**: `llm_sparse_grounding` bypass removed from `_validate_fact_binding()`. Unbound LLM claims are now dropped. `harvest_evidence_claims()` (already in pipeline) provides deterministic fallback. Citation rate WARNING fires when < 50% bound. BBN-02 path in `_filter_weak_evidence()` is a separate follow-up.

### TC-5309 Impact

Claims with no valid `source_fact_id` in ExtractionDatabase are dropped instead of being admitted at confidence=0.55 with `claim_source="llm_sparse_grounding"`. This removes one class of hallucination risk from the generation pipeline. The existing `harvest_evidence_claims()` call (TC-UND-211) ensures deterministic coverage from ExtractionDatabase api_facts/format_facts/snippet_facts.

---

# Pipeline Status — Session 24: C++ Extraction Root Cause Fix (2026-03-27)

## Summary (Session 24)

Continuation of orchestrator plan `bright-nibbling-elephant.md`. Session 24 completed TC-5310 and TC-5311 (partial → deterministic advisor logic).

| TC | Title | Status | New Tests |
|----|-------|--------|-----------|
| TC-5311 | Deterministic routing — route_after_evaluate() | **Done (reduced scope, completed session 25)** | 23 |
| TC-5310 | C++ file discovery fix — add C++ extensions to _CODE_EXTENSIONS + adapter routing | **Done** | 14 |

**Total new tests session 24: +37**
**Full unit suite: 5777 passed, 8 skipped, 0 failed**

### Root Causes Fixed (Session 24)

- **ISSUE-04 (root cause fixed)**: C++ `api_class_count` was 0 because `.h`/`.hpp`/`.cpp` were missing from `_CODE_EXTENSIONS`. Fix: added C++ extensions + route through `adapter.extract_class_details()` (ts_analyzer language="cpp"). Result: **251 classes extracted** from aspose_slides_cpp (was 0).

### Impact of TC-5310

```
api_class_count: 0 → 251
api_method_count: 0 → hundreds
overall_completeness: 0.26 → expected ≥ 0.7
```
Expected downstream impact: A+B target ≥ 30% (from 5%), api_allowlist failures drop from 13/18, `[identifier omitted]` placeholders target 0.

---

# Pipeline Status — Session 23: Architectural Revamp — Canonical Evidence Architecture (2026-03-27)

## Summary (Session 23)

Orchestrator-led plan `bright-nibbling-elephant.md` — 7 taskcards across Phases 0–2 of the canonical evidence architecture revamp.

| TC | Title | Status | New Tests |
|----|-------|--------|-----------|
| TC-5304 | Fix claim_coverage always-1.0 bug (evaluate/worker.py:547) | **Done** | 5 |
| TC-5305 | Wire verify worker in _resolve_input_model() | **Done** | 3 |
| TC-5306 | Annotate generate side-load + understanding_checkpoint_run_id | **Done** | ~2 |
| TC-5307 | Platform config unification (families_loader.py) | **Done** | 59 |
| TC-5308 | Extraction quality check (check_extraction_quality) | **Done** | 9 |

**Total new tests: +68**
**Full unit suite: 5740 passed, 0 failed** (baseline: 5672 session-start)

---

# Pipeline Status — Session 22: A+B Production Redesign (2026-03-27)

## Summary (Session 22 — Current)

Orchestrator-led plan `snug-petting-quill.md` — 5 taskcards targeting D:21 3D DotNet root causes.

| TC | Title | Status | New Tests |
|----|-------|--------|-----------|
| TC-5301 | Remove skeleton directive from fallback.py | **Done** | 4 |
| TC-5303 | Normalize internal links post-processor | **Done** | 7 |
| TC-5300 | Intake stale-cache fallback + worker_failed event | **Done** | 4 |
| TC-5302 | Fix output token budget + finish_reason=length retry | **Done** | 6 |
| TC-HEAL-003 | Heading-relevance ranking for class_briefs | **Done** | 4 |
| Test fixes | Update _call_llm mocks to return tuples | **Done** | — |

**Total new tests: 25**
**Full unit suite: 5664 passed, 0 failed** (confirmed)

### Root Causes Fixed

- **RC-3**: `fallback.py` no longer emits `"{display_name} -- {content_hint}."` → skeleton_high = 0 for fallback sections
- **RC-2**: `_sec_max_tokens` floor raised from 1024 → 2048 (+1024 for code-required); `finish_reason=length` now retried with doubled budget
- **RC-4**: `_normalize_internal_links()` strips `/docs.aspose.org/` subdomain prefixes from generated links; prompt instruction added
- **RC-1 (SW-1)**: Stale cache preserved before fresh clone attempt; `worker_failed` event emitted on all worker exceptions. Directly addresses confirmed intake failures.
- **RC-6**: `_prioritize_class_briefs()` now ranks by section heading/content_hint overlap (primary) + claim mention (secondary)

### Post-Diagnosis Findings (Session 22) — Three Diagnostic Agents

**Reconciled findings across agents:**

| Finding | Evidence | Impact |
|---------|----------|--------|
| finish_reason="length": 223/514 calls (43.4%) | events.ndjson from 3D DotNet run | ✓ TC-5302 was critical |
| Intake CONFIRMED failing for 10/11 pilots | Failed run events.ndjson = 2 lines only; successful = 241 lines | TC-5300 directly relevant |
| Pattern: ALL non-dotnet pilots fail before clone_completed | events.ndjson analysis of cells/python vs 3d/dotnet | Root cause still unknown — now observable via worker_failed |
| 347+ historical successful runs exist | Older run directories | Non-blocking — past success doesn't prevent current failures |
| class_briefs docstring_snippet = empty for 3D DotNet | understand.json analysis | AST extraction didn't yield docs |

**RC-1 Status**: Intake IS failing. The exception is caught by `graph_builder.py:297-302` without emitting `worker_failed`. TC-5300 fixes: (1) stale-cache fallback so clone failures use cached content, (2) `worker_failed` event now emitted — next run will expose the exact error message.

**Unknown**: WHY clone fails for non-dotnet pilots. Could be network, path, or platform-specific. Will be visible in `worker_failed.error` field on next run.

### Expected Impact

| Pilot | Current A+B | Target A+B | Blocking Fix |
|-------|------------|------------|-------------|
| 3D DotNet | ~0% (D:21) | ≥60% | TC-5301 + TC-5302 (confirmed critical) |
| Python/Java/C++ pilots | Blocked | Unblocked | TC-5300 stale-cache fallback |
| Java 3D | ~19% → higher | ≥50% | TC-5300 + TC-HEAL-003 |
| C++ Slides | ~5% → higher | ≥30% | TC-5300 + TC-HEAL-003 |

---

# Pipeline Status — Session 21: Unified Quality Fix (2026-03-25)

## Summary (Session 21 — Current)

Orchestrator-led swarm executing unified quality fix plan (`elegant-spinning-blanket.md`).
Cross-plan re-evaluation of 3 prior plans; 12-item execution sequence.

**Tests baseline: 5484 passed → 5513+ passed (growing as agents land)**

| Agent | TC | Items | Status | Tests |
|-------|----|----|-------|-------|
| A — Governance | TC-5200 | GOV-1/2/3: 18 commits, agents.md, evidence script | **Done** | 5484/0 |
| B — Evaluate FP | TC-5200 | EVL-2+3+4: string-aware scan, enum members, Test filter | **Done** | 5479/0 |
| C — Generate Q | TC-5201/02 | GEN-1+2+3: reasoning model, anti-echo, identifier repair | **Done** | 5484/0 |
| D — Worker.py | TC-5203/04 | EVL-1+GEN-4+6: syntax gate, strip-replace, See Also | **Done** | 5513/0 |
| E — Context | TC-5205 | GEN-5: cross-section context injection | Running | — |
| F — Snippets | TC-5206 | UND-1: snippet extraction from test files | Running | — |

**Remaining (planned):** ARC-1 (code synthesis), ARC-2 (heal loop), ARC-3 (repetition gate)

## Key Changes Landing in This Session

- **generate: reasoning** in all 11 pilot configs → `recommended` model for generation
- **Anti-echo guard** in section_writer.txt → no more "ProductName -- [content hint]" echo
- **Identifier repair softened** → case-insensitive, property-path aware
- **String-aware class scan** in api_verification.py → formula/cell-ref false positives eliminated
- **Enum member recognition** in api_verification.py
- **Syntax gate enforced** → invalid code blocks stripped after retry exhaustion
- **Strip-and-replace** → HG-16 now tries snippet pool before dropping code block
- **Deterministic See Also** → bypasses LLM, built from cross_links
- **Cross-section context** → prior sections' claim_ids injected into next section prompt (GEN-5)
- **Test snippet extraction** → snippet pool ~3 → ~15+ per product (UND-1)

---

# Pipeline Status — Session 20: Intake + Understand Phase Hardening (2026-03-25)

## Summary

Orchestrator-led swarm assessed and hardened the first two pipeline phases (Intake and Understand).
**Verdict: Both phases GO.** Architecture is mature and trustworthy. 3 targeted fixes applied.
Tests: 1366 passed (intake+understand+scout), 0 failures.

## Key Discovery

The v2 codebase is significantly more mature than initially assumed. 11 of 11 listed concerns
were either already addressed or refuted by evidence. Only 1 real bug found (TC-5191).

## Changes Made

| TC | Title | Files | Impact |
|----|-------|-------|--------|
| TC-5191 | canonical_import_overrides for non-alphabetic families | `configs/families.yaml`, `src/launcher/shared/identity.py` | Fixes `3d` family producing wrong imports on 6 platforms |
| TC-5192 | truncated_file_count in scout_inventory.json | `src/launcher/workers/scout/scout.py` | Diagnostic improvement |
| TC-5193 | dropped_snippet_summary in extraction_audit.json | `src/launcher/workers/understand/worker.py` | Diagnostic improvement |

## Verification Evidence

- 10 VERIFY tasks completed (3 parallel agent batches)
- 3 IMPLEMENT tasks with taskcards
- 11/11 canonical_import override assertions PASS
- 1366/1366 tests PASS
- 8 pilot scout artifacts audited (all zero overflow)
- Full evidence: `reports/agents/orchestrator/phase1_phase2_verification_evidence.md`

## What Downstream Can Trust

1. Identity resolution correct for all families including `3d`
2. Clone fails hard on unusable state
3. Scout reads 96-99% of files with zero budget overflow
4. Deterministic AST extraction before any LLM
5. Trust levels tracked (0.35-1.0 confidence by source)
6. Self-review blocks empty outputs (15 checks, 8 HIGH)
7. Resume path equivalent to fresh run
8. All artifacts inspectable without reading code

## What Still Cannot Be Trusted

1. LLM claims without fact binding (llm_sparse_grounding, 0.55)
2. Empty extraction_db on tree-sitter failure (unbounded LLM)
3. Cache freshness (verified SHA vs network-fail fallback indistinguishable in artifact)

---

# Pipeline Status — Session 19: Java & C++ Gap Closure (2026-03-24)

## Summary
Phase A + C complete: 4 critical C++ bug fixes + 3 quality improvements (7 taskcards total).
All 1604 tests pass (understand+evaluate+generate), 0 regressions.
Phase B (pilot runs) deferred to next session — litellm_key is in system env vars.

## Phase A Results (DONE)

| Taskcard | Gap | Fix | Tests | Status |
|----------|-----|-----|-------|--------|
| TC-CPP-410 | C++ missing from install recipe dispatch | Added `"cpp"` to `_NON_PYTHON_PLATFORMS`, `_CACHED_CMD_TPL`, `_CACHED_LABEL`; added `_extract_cpp_recipe()` | 5 new tests | **Done** |
| TC-CPP-411 | Verification fence hardcodes `` ```python `` | Added `_VERIFICATION_LANG` dict; fence now platform-aware | Agent-verified 550 pass | **Done** |
| TC-CPP-412 | api_allowlist splits by `.` only | Changed to `re.split(r"(?::|\\.)", ident)`; updated backtick regex | 2 new tests (10/10) | **Done** |
| TC-CPP-413 | LLM hallucinates `Aspose::Slides::Foss` | Strengthened `_build_wrong_import_warning`, `_build_import_rule_block`, canonical reminder for C++ | Agent-verified 138+22 pass | **Done** |

## Files Changed

- `src/launcher/workers/understand/extract/_deterministic.py` — C++ install recipe dispatch + `_extract_cpp_recipe()`
- `src/launcher/workers/generate/section_prompt.py` — Platform-aware verification fence + C++ import enforcement
- `src/launcher/workers/evaluate/checks/api_allowlist.py` — `::` separator support
- `tests/unit/workers/understand/test_extract.py` — 5 new C++ install recipe tests
- `tests/unit/workers/evaluate/checks/test_api_allowlist.py` — 2 new C++ separator tests

## Test Evidence

```
1590 passed, 15 skipped in 8.33s (understand + evaluate + generate suites)
5/5 C++ install recipe tests PASS
10/10 api_allowlist tests PASS (8 existing + 2 new)
```

## Phase C Results (DONE)

| Taskcard | Gap | Fix | Tests | Status |
|----------|-----|-----|-------|--------|
| TC-JAVA-411 | Overloaded method Javadoc picks first match | Added `_count_params_in_line()` + param-count matching in enrichment loop | 10 new tests (3 overload + 7 helper) | **Done** |
| TC-CPP-416 | C++ install cmd too generic (`find_package`) | 3-strategy detection: vcpkg.json > conanfile > CMakeLists.txt | 4 new tests + 1 updated | **Done** |

## Remaining Work (Phase B — next session)

| ID | What | Status | Notes |
|----|------|--------|-------|
| TC-CPP-414 | C++ slides pilot re-run | Ready | `litellm_key` in system env; run: `.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-slides-foss-cpp.yaml` |
| TC-JAVA-410 | Java full pipeline run | Ready | Run: `.venv/Scripts/python.exe -m launcher.cli.main run configs/pilots/aspose-3d-foss-java.yaml` |
| TC-CPP-415 | Tree-sitter hard dep/fallback | Pending | Low priority — tree-sitter rarely fails |

---

# Pipeline Status — Session 18: FPRPS Healing Sprint (2026-03-24)

## Summary
Self-review remediation of TC-5175, TC-UND-209, TC-UND-210. 6 gaps identified, all 6 fixed.
Full suite: 275 passed (FPRPS-scope), 2 pre-existing failures, 0 new regressions.

## Verdict: PASS — All 12 dimensions 5/5

| Task | Owner | Status | Evidence |
|------|-------|--------|----------|
| FPRPS-01: PascalCase regex fix | Agent-B1 | **Done** | `_linking.py:456` regex fixed, 2 tests added |
| FPRPS-02: TC-UND-209 spec alignment | Agent-B2 | **Done** | Taskcard updated, comment in `worker.py` |
| FPRPS-03: Dedup regression test | Agent-B1 | **Done** | 2 tests in `TestSourcePriorityDedup` |
| FPRPS-04: Unused import cleanup | Agent-B2 | **Done** | `call` removed from `test_clone.py:13` |
| FPRPS-05: DEBUG logging | Agent-B1 | **Done** | `_linking.py:463` logger.debug added |
| FPRPS-06: Import hoist + arch eval | Agent-B2 | **Done** | Import hoisted to `worker.py:26`, call kept in worker |

### Files changed
- `src/launcher/workers/understand/extract/_linking.py` — regex fix + DEBUG logging
- `src/launcher/workers/understand/worker.py` — import hoisted + comment added
- `tests/unit/workers/understand/test_confidence_bucketing.py` — 4 new tests
- `tests/unit/workers/intake/test_clone.py` — unused import removed
- `plans/taskcards/TC-UND-209_worktree-missing-diagnostic-event.md` — scope clarified

### Test command
```bash
PYTHONHASHSEED=0 .venv/Scripts/python.exe -m pytest tests/unit/workers/understand/test_confidence_bucketing.py tests/unit/workers/understand/test_confidence_values.py tests/unit/workers/understand/test_extract.py tests/unit/workers/intake/test_clone.py tests/unit/orchestrator/test_pipeline_mode_routing.py -v
```

### Pilot Runs (E2E Verification)

| Pilot | Run ID | Duration | Claims | Promoted | Verdict |
|-------|--------|----------|--------|----------|---------|
| cells/python | 260324_104503_cells_python_3b26 | 111.6s | 68 | 12 llm_corroborated | PASS |
| 3d/dotnet | 260324_104751_3d_dotnet_9374 | 668.6s | 29 | 0 (expected) | PASS |

**FPRPS-01 regression found + fixed during pilot**: v1 regex `\b[A-Z][a-z]...` too restrictive (rejected CSVHandler). Fixed to v2 `\b[A-Z][a-zA-Z0-9]*[a-z][a-zA-Z0-9]*\b`. All tests pass.

Full comparison: `reports/agents/B1/FPRPS-01/pilot_comparison.md`

---

# Pipeline Status — Session 16: Pipeline Audit Hardening (2026-03-20)

## Summary
Self-review remediation of TC-PA-01..05. 5 patches applied, 13 new tests written,
5 taskcards closed to Done. Full suite: 5923 passed, 5 pre-existing failures.

## Verdict: PASS — All 12 dimensions >=4/5

| Task | Status | Evidence |
|------|--------|----------|
| PA-H01..H05 (5 patches) | Done | `reports/agents/B_implementation/PA-H01-H05/` |
| PA-T01..T04 (13 tests) | Done | `reports/agents/C_tests/PA-T01-T04/` |
| PA-D01 (5 taskcards → Done) | Done | `reports/agents/D_docs/PA-D01/` |
| Final verification | Done | 374/374 TC-PA tests pass |

---

# Pipeline Status — Session 14: Post-Execution Audit + Quality Gate Sprint (2026-03-16)

## Summary
Post-execution audit of enchanted-noodling-lemur + optimized-chasing-music plans.
Two new root causes identified and fixed (TC-NEW-001, TC-NEW-002).
E2E pilot running to establish verified baseline.
Plan source: `C:\Users\prora\.claude\plans\keen-yawning-pretzel.md`

## Audit Findings

- Latest verified A+B: **23%** (run 260312_221338_cells_python_9afc)
- Optimized-plan claimed 35.2%: **unverified** (no evaluation_report.json found)
- TC-HT-008/009/010: Code implemented, taskcards still "In-Progress", unverified by E2E
- Golden corpus generalization: Complete (22 files with placeholder templates)
- `_RUBRIC_SUPPLEMENTS` (Option D): Complete (6 roles, 800-1200 chars)
- Option B (Python-native golden files): Partially done (heading expansion only, no real code patterns)

## New Fixes (Session 14)

### TC-NEW-001: Python Syntax Validation Gate (Done)
- `section_validator.py`: `check_python_syntax()` — runs `ast.parse()` on Python code blocks
- `worker.py`: Phase C re-validates `syntax_valid=None` snippets before injection
- 7 new tests, 4827/4827 full suite pass

### TC-NEW-002: Docstring Return Type Extraction (Done)
- `code_analyzer.py`: `_extract_return_type_from_docstring()` — parses Google, NumPy, Sphinx formats
- `worker.py`: Fixed `_render_methods_section()` — no longer shows misleading `→ None`
- 11 new tests, 4827/4827 full suite pass

## E2E Pilot Results — Run 260316_095218_cells_python_6697

| Metric | Baseline (260312) | This Run (260316) | Delta | GO Threshold |
|--------|:-:|:-:|:-:|:-:|
| A+B rate | 23.0% | **19.0%** | -4pp | ≥ 50% |
| D+F rate | 13.6% | **4.8%** | -8.8pp | ≤ 30% |
| CRITICAL | ? | **1** | — | 0 |
| Editorial-critical HIGH | ? | **0%** | — | ≤ 15% |
| Verdict | NO_GO | **NO_GO** | — | — |

### Grade Distribution
| Grade | Count | % |
|-------|:-----:|:-:|
| A | 0 | 0% |
| B | 4 | 19% |
| C | 16 | 76% |
| D | 0 | 0% |
| F | 1 | 5% |

### Key Findings
- **D-grade eliminated**: D went from ~10% (260312) to 0%. TC-HT-008/009/010 fixes working — no more empty sections, keyword stuffing, scaffold leakage causing D grades
- **A+B regressed 4pp**: 16 pages stuck at C-grade. C→B gap is dominated by:
  - "Missing code block in Code Example section" (4 pages) — GEN-001 rejects LLM code but snippet injection fails to cover these sections
  - "Reference page has no code examples" (3 pages) — reference pages have prose but no illustrative code
  - Empty sections (0 words) in mandatory sections (multiple pages)
- **1 CRITICAL on formula page**: "Identifier repair artifact: hallucinated API identifier stripped (2 occurrences)" — the repair itself is working, but the CRITICAL finding is that the artifact/placeholder remains visible in output
- **1 F-grade (formula)**: 0-word sections in Overview, Core Concepts, Implementation, Code Examples. Page essentially empty after all generated content was rejected by validators

### Root Cause Analysis
1. **GEN-001 over-rejection**: Code blocks are correctly rejected (LLM-generated), but snippet injection doesn't fill the gap. Result: code-required sections have 0 code blocks
2. **Snippet coverage gap**: Only 31 snippets for 21 pages. Sections like "Code Example" on howto pages need snippets but none match
3. **Empty section cascade**: When code blocks are stripped, sections become empty. Prose floor (TC-HT-008, 30 words) doesn't catch sections that had only code blocks
4. **Identifier repair visibility**: TC-NEW-001 syntax gate works, but the identifier repair log artifact leaks into visible output as a CRITICAL finding

## Test Count

4827 passed, 64 skipped, 3 xfailed, 2 xpassed (PYTHONHASHSEED=0)

---

# Pipeline Status — Session 13: Skill System + Knowledge Projection (2026-03-15)

## Summary
Phases 1–5 complete. Structural generation fix (snippet-injection + prose-only LLM) implemented.
Knowledge trees projected for all 5 products. AGENTS.md governance written.
Plan source: `C:\Users\prora\.claude\plans\bubbly-cooking-moonbeam.md`

## Completed Phases (Session 13)

### Phase 1: Generation fix — snippet-injection + prose-only LLM (GEN-001)
- `generate/worker.py`: Phase A (deterministic snippet selection by claim_id overlap), Phase C (assembly)
- `generate/section_prompt.py`: `prose_only=True` param — rewrites OUTPUT FORMAT, relabels code as context
- `generate/section_validator.py`: GEN-001 — rejects any LLM code block before validation (not repair)
- **Scope narrowed**: HG-16 identifier repair preserved; new guard operates earlier and harder

### Phase 2: Foundation schemas
- `configs/knowledge_model.schema.json` — model.yaml schema
- `configs/allowed_paths.yaml` — canonical allowed/forbidden path registry
- `specs/schemas/stale_report.schema.json`, `diff_report.schema.json`

### Phase 3: Knowledge projection (S-10) — KNOW-001
- `src/launcher/skills/knowledge_project.py` — KnowledgeProjectSkill, fully deterministic, idempotent
- Projected all 5 products to `knowledge/`:
  - `cells/python`: tier=A, claims=135, snippets=31
  - `3d/python`: tier=B, claims=163, snippets=12
  - `3d/dotnet`: tier=C, claims=40, snippets=6
  - `3d/typescript`: tier=B, claims=201, snippets=22
  - `note/python`: tier=A, claims=165, snippets=37
- Each product: model.yaml, api_surface.md, api_surface.json, claims.md, claims.json, snippets/, formats.md, limitations.md, install.md, sync_manifest.yaml

### Phase 4: AGENTS.md — GOV-001
- `d:\onedrive\Documents\GitHub\aspose.org\AGENTS.md` — content governance with skill chains, stop conditions, escalation conditions, maintenance workflow, evidence proof in commits

### Phase 5: Safety gate skills
- `src/launcher/skills/skill_contract.py` — abstract base `SkillContract`, `SkillResult`
- `src/launcher/skills/path_guard.py` — S-01: ALLOW/DENY against allowed_paths.yaml (7/7 tests pass)
- `src/launcher/skills/ground_check.py` — S-23: import allowlist + backtick identifier scan + citation coverage
- `src/launcher/skills/citation_attach.py` — S-24: embeds `<!-- evidence: -->` HTML comments
- `src/launcher/skills/hallucination_guard.py` — S-02: inline code-block rejection + identifier scan

## Open Items (Phases 6–9 pending)
- Phase 6: S-12 (knowledge-diff), S-13 (stale-detect), S-14 (knowledge-update), S-20/S-21/S-25/S-26
- Phase 7: S-15 (sync-vector)
- Phase 8: S-11 (knowledge-build for slides/python — no understand.json)
- Phase 9: Integration pilot on cells/python — target A+B ≥ 55%, 0 api_consistency HIGH findings

---

# Pipeline Status — Golden Corpus Integration (2026-03-15)

## Summary
All 14 Golden Corpus Integration taskcards complete.
Tests: 4702 passed, 0 failed, 65 skipped.
Plan source: C:\Users\prora\.claude\plans\dazzling-puzzling-kahn.md

## Completed Phases

### Phase 1: Infrastructure + High-ROI Foundation
- I1: GoldenSection extended with 6 new signal fields + GoldenStyleRubric dataclass
- E3: Severity tier-awareness added to golden spec check (api_reference→critical, landing→low)
- G1: Style rubric injection replaces vague "match this example" with explicit writing rules
- P1: Golden-derived skeleton hints added to planner (golden_section_hints metadata key)

### Phase 2: Evidence Validation + Generation Guidance
- E1: Block sequence validation — detects code-first sections (MEDIUM)
- E2: Code completeness check — missing import (MEDIUM), missing output verification (LOW)
- G2: Block sequence prescription — injects numbered EXPECTED SECTION STRUCTURE outline
- G3: Code completeness checklist — explicit CODE BLOCK REQUIREMENTS in prompt
- E6: Golden-anchored Phase B grading — A-grade excerpt anchors LLM reviewer calibration

### Phase 3: Evidence Calibration + Advisory Signals
- U1: Evidence sufficiency thresholds calibrated from golden corpus
- P3: Per-section word count targets from golden (TARGET DEPTH in prompts)
- E4: Link density check (LOW — advisory signal for thin cross-references)
- E5: Use-case specificity check (LOW — detects code blocks without use-case bullets)

### H2/G5: Progressive Heal Escalation
- Attempt 1: Standard behavior (backward compatible)
- Attempt 2: Block sequence prescription + "DO NOT repeat" instruction
- Attempt 3+: Golden scaffold with slot markers

## Expected Quality Improvements
| Metric | Target | Mechanism |
|--------|--------|-----------|
| Grade stability (3 reruns) | ≥85% same grade | P1 deterministic skeleton + E6 calibration |
| A+B rate | ≥60% | E1/E2/E3 higher-severity findings + G1/G2/G3 better prompts |
| D+F rate | ≤20% | E3 escalation forces regeneration of API ref failures |
| Code completeness | ≥90% imports present | G3 + E2 |
| Block sequence compliance | ≥80% | G2 + E1 |
