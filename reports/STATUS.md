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
